"""
Data Warehouse Star Schema Implementation
ETL scripts to transform data from curated_zone into star schema for analytics
Implements Slowly Changing Dimensions (SCD Type 2) for sellers
Works with available tables: orders_refined, order_items_refined, customers_refined, sellers_refined
"""

import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
from connect import get_db_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# WAREHOUSE SCHEMA SETUP
# ============================================================================

def create_warehouse_schema(engine, schema_name='data_warehouse'):
    """Create data warehouse schema if it doesn't exist."""
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
        logger.info(f"✓ Warehouse schema '{schema_name}' created/verified (fresh start)")
    except Exception as e:
        logger.error(f"❌ Error creating warehouse schema: {str(e)}")
        raise


# ============================================================================
# DIMENSION TABLES
# ============================================================================

def create_dim_date_table(engine, schema_name='data_warehouse'):
    """Create dimension table for dates (time dimension)."""
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.dim_date (
            date_id INTEGER PRIMARY KEY,
            date_value DATE NOT NULL UNIQUE,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            quarter INTEGER,
            week INTEGER,
            day_of_week VARCHAR(10),
            is_weekend BOOLEAN,
            is_holiday BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_dim_date_value ON {schema_name}.dim_date (date_value);
        CREATE INDEX IF NOT EXISTS idx_dim_date_year_month ON {schema_name}.dim_date (year, month);
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        logger.info(f"✓ Created dimension table: {schema_name}.dim_date")
    except Exception as e:
        logger.error(f"❌ Error creating dim_date table: {str(e)}")
        raise


def create_dim_customer_table(engine, schema_name='data_warehouse'):
    """Create dimension table for customers."""
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.dim_customer (
            dim_customer_id BIGSERIAL PRIMARY KEY,
            customer_id VARCHAR(255) NOT NULL UNIQUE,
            customer_unique_id VARCHAR(255),
            customer_state VARCHAR(2),
            customer_city VARCHAR(255),
            customer_zip_code_prefix VARCHAR(10),
            data_quality_score NUMERIC(3,2),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_dim_customer_id ON {schema_name}.dim_customer (customer_id);
        CREATE INDEX IF NOT EXISTS idx_dim_customer_state ON {schema_name}.dim_customer (customer_state);
        CREATE INDEX IF NOT EXISTS idx_dim_customer_city ON {schema_name}.dim_customer (customer_city);
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        logger.info(f"✓ Created dimension table: {schema_name}.dim_customer")
    except Exception as e:
        logger.error(f"❌ Error creating dim_customer table: {str(e)}")
        raise


def create_dim_product_table(engine, schema_name='data_warehouse'):
    """Create dimension table for products (extracted from order_items)."""
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.dim_product (
            dim_product_id BIGSERIAL PRIMARY KEY,
            product_id VARCHAR(255) NOT NULL UNIQUE,
            avg_price NUMERIC(12,2),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_dim_product_id ON {schema_name}.dim_product (product_id);
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        logger.info(f"✓ Created dimension table: {schema_name}.dim_product")
    except Exception as e:
        logger.error(f"❌ Error creating dim_product table: {str(e)}")
        raise


def create_dim_seller_scd_table(engine, schema_name='data_warehouse'):
    """
    Create SCD Type 2 dimension table for sellers.
    Tracks seller location changes over time.
    """
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.dim_seller_scd (
            scd_id BIGSERIAL PRIMARY KEY,
            seller_id VARCHAR(255) NOT NULL,
            seller_state VARCHAR(2),
            seller_city VARCHAR(255),
            seller_zip_code_prefix VARCHAR(10),
            is_active BOOLEAN DEFAULT TRUE,
            is_current BOOLEAN DEFAULT TRUE,
            
            -- SCD Type 2 fields
            valid_from DATE NOT NULL,
            valid_to DATE,
            change_reason VARCHAR(255),
            
            -- Audit fields
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100) DEFAULT 'ETL',
            
            UNIQUE (seller_id, valid_from)
        );
        
        CREATE INDEX IF NOT EXISTS idx_scd_seller_id ON {schema_name}.dim_seller_scd (seller_id);
        CREATE INDEX IF NOT EXISTS idx_scd_seller_current ON {schema_name}.dim_seller_scd (seller_id, is_current);
        CREATE INDEX IF NOT EXISTS idx_scd_valid_dates ON {schema_name}.dim_seller_scd (valid_from, valid_to);
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        logger.info(f"✓ Created SCD Type 2 dimension table: {schema_name}.dim_seller_scd")
    except Exception as e:
        logger.error(f"❌ Error creating dim_seller_scd table: {str(e)}")
        raise


def create_dim_location_table(engine, schema_name='data_warehouse'):
    """Create dimension table for locations (cities/states)."""
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.dim_location (
            dim_location_id BIGSERIAL PRIMARY KEY,
            location_key VARCHAR(50) NOT NULL UNIQUE,
            state_code VARCHAR(2),
            city_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_dim_location_key ON {schema_name}.dim_location (location_key);
        CREATE INDEX IF NOT EXISTS idx_dim_location_state ON {schema_name}.dim_location (state_code);
        CREATE INDEX IF NOT EXISTS idx_dim_location_city ON {schema_name}.dim_location (city_name);
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        logger.info(f"✓ Created dimension table: {schema_name}.dim_location")
    except Exception as e:
        logger.error(f"❌ Error creating dim_location table: {str(e)}")
        raise


# ============================================================================
# FACT TABLE
# ============================================================================

def create_fct_orders_table(engine, schema_name='data_warehouse'):
    """Create fact table for orders."""
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.fct_orders (
            fact_order_id BIGSERIAL PRIMARY KEY,
            
            -- Foreign keys to dimensions
            order_id VARCHAR(255) NOT NULL,
            dim_customer_id BIGINT,
            dim_product_id BIGINT,
            dim_date_id INTEGER,
            dim_location_id BIGINT,
            
            -- Measures
            quantity INTEGER DEFAULT 1,
            price_amount NUMERIC(12,2),
            freight_value NUMERIC(12,2),
            total_order_value NUMERIC(12,2),
            
            -- Order metrics
            order_status VARCHAR(50),
            days_to_delivery INTEGER,
            is_on_time BOOLEAN,
            
            -- Timestamps
            order_date DATE,
            delivery_date DATE,
            estimated_delivery_date DATE,
            
            -- Data quality
            data_quality_score NUMERIC(3,2),
            
            -- Audit
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (dim_customer_id) REFERENCES {schema_name}.dim_customer (dim_customer_id),
            FOREIGN KEY (dim_product_id) REFERENCES {schema_name}.dim_product (dim_product_id),
            FOREIGN KEY (dim_date_id) REFERENCES {schema_name}.dim_date (date_id),
            FOREIGN KEY (dim_location_id) REFERENCES {schema_name}.dim_location (dim_location_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_fct_orders_order_id ON {schema_name}.fct_orders (order_id);
        CREATE INDEX IF NOT EXISTS idx_fct_orders_customer ON {schema_name}.fct_orders (dim_customer_id);
        CREATE INDEX IF NOT EXISTS idx_fct_orders_product ON {schema_name}.fct_orders (dim_product_id);
        CREATE INDEX IF NOT EXISTS idx_fct_orders_date ON {schema_name}.fct_orders (dim_date_id);
        CREATE INDEX IF NOT EXISTS idx_fct_orders_status ON {schema_name}.fct_orders (order_status);
        CREATE INDEX IF NOT EXISTS idx_fct_orders_location ON {schema_name}.fct_orders (dim_location_id);
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        logger.info(f"✓ Created fact table: {schema_name}.fct_orders")
    except Exception as e:
        logger.error(f"❌ Error creating fct_orders table: {str(e)}")
        raise


# ============================================================================
# ETL FUNCTIONS - DATE DIMENSION
# ============================================================================

def populate_dim_date(engine, start_date=None, end_date=None, schema_name='data_warehouse'):
    """
    Populate date dimension table.
    Generates one row for each date in the specified range.
    """
    try:
        if start_date is None:
            start_date = '2015-01-01'
        if end_date is None:
            end_date = '2025-12-31'
        
        logger.info(f"  Populating dim_date from {start_date} to {end_date}...")
        
        query = f"""
        WITH date_series AS (
            SELECT generate_series('{start_date}'::DATE, '{end_date}'::DATE, '1 day'::INTERVAL)::DATE AS date_value
        )
        INSERT INTO {schema_name}.dim_date
        (date_id, date_value, year, month, day, quarter, week, day_of_week, is_weekend, is_holiday)
        SELECT
            TO_CHAR(date_value, 'YYYYMMDD')::INTEGER as date_id,
            date_value,
            EXTRACT(YEAR FROM date_value)::INTEGER as year,
            EXTRACT(MONTH FROM date_value)::INTEGER as month,
            EXTRACT(DAY FROM date_value)::INTEGER as day,
            EXTRACT(QUARTER FROM date_value)::INTEGER as quarter,
            EXTRACT(WEEK FROM date_value)::INTEGER as week,
            TO_CHAR(date_value, 'Dy') as day_of_week,
            EXTRACT(DOW FROM date_value) IN (0, 6) as is_weekend,
            FALSE as is_holiday
        FROM date_series
        ON CONFLICT (date_id) DO NOTHING;
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        # Count inserted records
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.dim_date"))
            count = result.scalar()
        
        logger.info(f"    ✓ Populated dim_date with {count:,} records")
        
    except Exception as e:
        logger.error(f"    ❌ Error populating dim_date: {str(e)}")
        raise


# ============================================================================
# ETL FUNCTIONS - CUSTOMER DIMENSION
# ============================================================================

def load_dim_customer(engine, source_schema='curated_zone', 
                     target_schema='data_warehouse'):
    """Load customer dimension from curated zone."""
    try:
        logger.info(f"  Loading dim_customer from {source_schema}...")
        
        # Insert customer data
        query = f"""
        INSERT INTO {target_schema}.dim_customer
        (customer_id, customer_unique_id, customer_state, customer_city, 
         customer_zip_code_prefix, data_quality_score, is_active)
        SELECT
            c.customer_id,
            c.customer_unique_id,
            c.customer_state,
            c.customer_city,
            c.customer_zip_code_prefix,
            c.data_quality_score,
            CASE WHEN c.is_valid = TRUE THEN TRUE ELSE FALSE END as is_active
        FROM {source_schema}.customers_refined c
        WHERE c.customer_id IS NOT NULL
        ON CONFLICT (customer_id) DO UPDATE
        SET updated_at = NOW()
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        # Get count
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {target_schema}.dim_customer"))
            count = result.scalar()
        
        logger.info(f"    ✓ Loaded {count:,} customers")
        
    except Exception as e:
        logger.error(f"    ❌ Error loading dim_customer: {str(e)}")
        raise


# ============================================================================
# ETL FUNCTIONS - LOCATION DIMENSION
# ============================================================================

def load_dim_location(engine, source_schema='curated_zone', 
                     target_schema='data_warehouse'):
    """Load location dimension from customer and seller data."""
    try:
        logger.info(f"  Loading dim_location from {source_schema}...")
        
        query = f"""
        WITH location_data AS (
            SELECT 
                customer_state as state_code,
                customer_city as city_name
            FROM {source_schema}.customers_refined
            WHERE customer_state IS NOT NULL AND customer_city IS NOT NULL
            GROUP BY customer_state, customer_city
            
            UNION ALL
            
            SELECT
                seller_state,
                seller_city
            FROM {source_schema}.sellers_refined
            WHERE seller_state IS NOT NULL AND seller_city IS NOT NULL
            GROUP BY seller_state, seller_city
        )
        INSERT INTO {target_schema}.dim_location
        (location_key, state_code, city_name, is_active)
        SELECT
            CONCAT(state_code, '-', city_name) as location_key,
            state_code,
            city_name,
            TRUE
        FROM location_data
        ON CONFLICT (location_key) DO NOTHING
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        # Get count
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {target_schema}.dim_location"))
            count = result.scalar()
        
        logger.info(f"    ✓ Loaded {count:,} locations")
        
    except Exception as e:
        logger.error(f"    ❌ Error loading dim_location: {str(e)}")
        raise


# ============================================================================
# ETL FUNCTIONS - SELLER DIMENSION (SCD Type 2)
# ============================================================================

def load_dim_seller_scd(engine, source_schema='curated_zone', 
                       target_schema='data_warehouse'):
    """
    Load seller dimension with SCD Type 2 (track location changes over time).
    When a seller's location changes, old record is closed and new record is created.
    """
    try:
        logger.info(f"  Loading dim_seller_scd (SCD Type 2) from {source_schema}...")
        
        today = datetime.now().date()
        
        # First, load initial sellers if table is empty
        initial_load = f"""
        INSERT INTO {target_schema}.dim_seller_scd
        (seller_id, seller_state, seller_city, seller_zip_code_prefix, 
         is_active, is_current, valid_from, change_reason, created_by)
        SELECT
            s.seller_id,
            s.seller_state,
            s.seller_city,
            s.seller_zip_code_prefix,
            TRUE,
            TRUE,
            '{today}'::DATE,
            'Initial load',
            'ETL'
        FROM {source_schema}.sellers_refined s
        WHERE s.seller_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM {target_schema}.dim_seller_scd scd 
              WHERE scd.seller_id = s.seller_id
          )
        ON CONFLICT (seller_id, valid_from) DO NOTHING
        """
        
        with engine.connect() as conn:
            conn.execute(text(initial_load))
            conn.commit()
        
        # Then, track changes (seller location changes)
        change_tracking = f"""
        WITH source_sellers AS (
            SELECT 
                s.seller_id,
                s.seller_state,
                s.seller_city,
                s.seller_zip_code_prefix
            FROM {source_schema}.sellers_refined s
            WHERE s.seller_id IS NOT NULL
        ),
        sellers_with_changes AS (
            SELECT 
                ss.seller_id,
                ss.seller_state,
                ss.seller_city,
                ss.seller_zip_code_prefix,
                scd.scd_id,
                scd.seller_state as old_state,
                scd.seller_city as old_city
            FROM source_sellers ss
            LEFT JOIN {target_schema}.dim_seller_scd scd 
                ON ss.seller_id = scd.seller_id AND scd.is_current = TRUE
            WHERE scd.seller_state IS NULL 
               OR scd.seller_city IS NULL
               OR (scd.seller_state != ss.seller_state OR scd.seller_city != ss.seller_city)
        )
        UPDATE {target_schema}.dim_seller_scd scd
        SET is_current = FALSE, valid_to = '{today}'::DATE, 
            change_reason = 'Location changed'
        FROM sellers_with_changes swc
        WHERE scd.scd_id = swc.scd_id;
        
        -- Insert new records for changed sellers
        INSERT INTO {target_schema}.dim_seller_scd
        (seller_id, seller_state, seller_city, seller_zip_code_prefix,
         is_active, is_current, valid_from, change_reason, created_by)
        SELECT
            swc.seller_id,
            swc.seller_state,
            swc.seller_city,
            swc.seller_zip_code_prefix,
            TRUE,
            TRUE,
            '{today}'::DATE,
            'Location updated',
            'ETL'
        FROM (
            SELECT 
                s.seller_id,
                s.seller_state,
                s.seller_city,
                s.seller_zip_code_prefix
            FROM {source_schema}.sellers_refined s
            WHERE s.seller_id IS NOT NULL
        ) swc
        WHERE NOT EXISTS (
            SELECT 1 FROM {target_schema}.dim_seller_scd scd
            WHERE scd.seller_id = swc.seller_id AND scd.is_current = TRUE
        )
        ON CONFLICT (seller_id, valid_from) DO NOTHING
        """
        
        with engine.connect() as conn:
            conn.execute(text(change_tracking))
            conn.commit()
        
        # Get count
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM {target_schema}.dim_seller_scd 
                WHERE is_current = TRUE
            """))
            count = result.scalar()
        
        logger.info(f"    ✓ Loaded {count:,} active sellers (SCD Type 2)")
        
    except Exception as e:
        logger.error(f"    ❌ Error loading dim_seller_scd: {str(e)}")
        raise


# ============================================================================
# ETL FUNCTIONS - PRODUCT DIMENSION
# ============================================================================

def load_dim_product(engine, source_schema='curated_zone', 
                    target_schema='data_warehouse'):
    """Load product dimension from order items data."""
    try:
        logger.info(f"  Loading dim_product from {source_schema}...")
        
        query = f"""
        INSERT INTO {target_schema}.dim_product
        (product_id, avg_price, is_active)
        SELECT DISTINCT
            oi.product_id,
            AVG(oi.price) OVER (PARTITION BY oi.product_id)::NUMERIC(12,2) as avg_price,
            TRUE
        FROM {source_schema}.order_items_refined oi
        WHERE oi.product_id IS NOT NULL
        ON CONFLICT (product_id) DO NOTHING
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        # Get count
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {target_schema}.dim_product"))
            count = result.scalar()
        
        logger.info(f"    ✓ Loaded {count:,} unique products")
        
    except Exception as e:
        logger.error(f"    ❌ Error loading dim_product: {str(e)}")
        raise


# ============================================================================
# ETL FUNCTIONS - FACT TABLE (ORDERS)
# ============================================================================

def load_fct_orders(engine, source_schema='curated_zone', 
                   target_schema='data_warehouse'):
    """Load fact table with order data from curated zone."""
    try:
        logger.info(f"  Loading fct_orders fact table from {source_schema}...")
        
        query = f"""
        INSERT INTO {target_schema}.fct_orders
        (order_id, dim_customer_id, dim_product_id, dim_date_id, dim_location_id,
         quantity, price_amount, freight_value, total_order_value,
         order_status, days_to_delivery, is_on_time,
         order_date, delivery_date, estimated_delivery_date, data_quality_score)
        
        SELECT
            o.order_id,
            dc.dim_customer_id,
            dp.dim_product_id,
            TO_CHAR(o.order_purchase_timestamp::DATE, 'YYYYMMDD')::INTEGER as dim_date_id,
            dl.dim_location_id,
            COUNT(oi.order_item_id)::INTEGER as quantity,
            COALESCE(SUM(oi.price), 0)::NUMERIC(12,2) as price_amount,
            COALESCE(SUM(oi.freight_value), 0)::NUMERIC(12,2) as freight_value,
            (COALESCE(SUM(oi.price), 0) + COALESCE(SUM(oi.freight_value), 0))::NUMERIC(12,2) as total_order_value,
            o.order_status,
            o.days_to_delivery,
            o.is_on_time,
            o.order_purchase_timestamp::DATE,
            o.order_delivered_customer_date::DATE,
            o.order_estimated_delivery_date::DATE,
            o.data_quality_score
        FROM {source_schema}.orders_refined o
        LEFT JOIN {source_schema}.order_items_refined oi ON o.order_id = oi.order_id
        LEFT JOIN {target_schema}.dim_customer dc ON o.customer_id = dc.customer_id
        LEFT JOIN {target_schema}.dim_product dp ON oi.product_id = dp.product_id
        LEFT JOIN {target_schema}.dim_location dl 
            ON dl.location_key = CONCAT(
                (SELECT customer_state FROM {source_schema}.customers_refined c WHERE c.customer_id = o.customer_id LIMIT 1),
                '-',
                (SELECT customer_city FROM {source_schema}.customers_refined c WHERE c.customer_id = o.customer_id LIMIT 1)
            )
        WHERE o.order_id IS NOT NULL
        GROUP BY o.order_id, dc.dim_customer_id, o.customer_id, o.order_purchase_timestamp,
                 o.order_status, o.days_to_delivery, o.is_on_time,
                 o.order_delivered_customer_date, o.order_estimated_delivery_date,
                 o.data_quality_score, dp.dim_product_id, dl.dim_location_id
        ON CONFLICT DO NOTHING
        """
        
        with engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        # Get count
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {target_schema}.fct_orders"))
            count = result.scalar()
        
        logger.info(f"    ✓ Loaded {count:,} fact order records")
        
    except Exception as e:
        logger.error(f"    ❌ Error loading fct_orders: {str(e)}")
        raise


# ============================================================================
# REFRESH FUNCTIONS
# ============================================================================

def refresh_warehouse(engine, source_schema='curated_zone', 
                     target_schema='data_warehouse', full_refresh=False):
    """
    Refresh the entire data warehouse.
    
    Args:
        engine: SQLAlchemy database engine
        source_schema: Source schema name (curated_zone)
        target_schema: Target schema name (data_warehouse)
        full_refresh: If True, rebuild all dimensions; if False, incremental load
    """
    try:
        print("\n" + "="*80)
        print("STARTING DATA WAREHOUSE REFRESH")
        print("="*80)
        
        # Create schema
        create_warehouse_schema(engine, target_schema)
        
        # Create all tables
        print("\nCreating dimension and fact tables...")
        create_dim_date_table(engine, target_schema)
        create_dim_customer_table(engine, target_schema)
        create_dim_location_table(engine, target_schema)
        create_dim_product_table(engine, target_schema)
        create_dim_seller_scd_table(engine, target_schema)
        create_fct_orders_table(engine, target_schema)
        
        # Populate static dimensions
        print("\nPopulating static dimensions...")
        populate_dim_date(engine, schema_name=target_schema)
        
        # Load dimensions from source
        print("\nLoading dimensions from source...")
        load_dim_customer(engine, source_schema, target_schema)
        load_dim_location(engine, source_schema, target_schema)
        load_dim_product(engine, source_schema, target_schema)
        load_dim_seller_scd(engine, source_schema, target_schema)
        
        # Load facts
        print("\nLoading fact tables...")
        load_fct_orders(engine, source_schema, target_schema)
        
        # Validate warehouse
        print("\nValidating warehouse...")
        validate_warehouse(engine, target_schema)
        
        print("\n" + "="*80)
        print("✓ DATA WAREHOUSE REFRESH COMPLETED SUCCESSFULLY")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ Error during warehouse refresh: {str(e)}")
        raise


# ============================================================================
# VALIDATION & REPORTING
# ============================================================================

def validate_warehouse(engine, schema_name='data_warehouse'):
    """Validate warehouse integrity and report statistics."""
    try:
        print(f"\n  Warehouse Validation Report:")
        print(f"  " + "-"*76)
        
        queries = {
            'Dates': f"SELECT COUNT(*) FROM {schema_name}.dim_date",
            'Customers': f"SELECT COUNT(*) FROM {schema_name}.dim_customer",
            'Products': f"SELECT COUNT(*) FROM {schema_name}.dim_product",
            'Sellers (Current SCD)': f"SELECT COUNT(*) FROM {schema_name}.dim_seller_scd WHERE is_current = TRUE",
            'Seller History Records': f"SELECT COUNT(*) FROM {schema_name}.dim_seller_scd",
            'Locations': f"SELECT COUNT(*) FROM {schema_name}.dim_location",
            'Orders (Fact)': f"SELECT COUNT(*) FROM {schema_name}.fct_orders",
            'Total Order Value': f"SELECT COALESCE(SUM(total_order_value), 0) FROM {schema_name}.fct_orders"
        }
        
        with engine.connect() as conn:
            for label, query in queries.items():
                result = conn.execute(text(query)).scalar()
                if result is None:
                    result = 0
                if isinstance(result, (int, float)):
                    print(f"  {label:<40} {result:>20,.2f}" if isinstance(result, float) and result >= 1 else f"  {label:<40} {result:>20,}")
                else:
                    print(f"  {label:<40} {result:>20}")
        
        print(f"  " + "-"*76)
        
    except Exception as e:
        logger.error(f"Error validating warehouse: {str(e)}")


def get_scd_history(engine, seller_id, schema_name='data_warehouse'):
    """Retrieve complete history of a seller (SCD Type 2 tracking)."""
    try:
        query = f"""
        SELECT 
            scd_id,
            seller_id,
            seller_state,
            seller_city,
            valid_from,
            valid_to,
            is_current,
            change_reason,
            created_at
        FROM {schema_name}.dim_seller_scd
        WHERE seller_id = '{seller_id}'
        ORDER BY valid_from DESC
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            print(f"\nSeller Location History for ID {seller_id}:")
            print("-" * 120)
            for row in rows:
                print(f"  {row}")
        
    except Exception as e:
        logger.error(f"Error retrieving SCD history: {str(e)}")


def get_warehouse_summary(engine, schema_name='data_warehouse'):
    """Get summary statistics of the warehouse."""
    try:
        query = f"""
        SELECT
            COUNT(DISTINCT dim_customer_id) as unique_customers,
            COUNT(DISTINCT dim_product_id) as unique_products,
            COUNT(DISTINCT dim_location_id) as unique_locations,
            COUNT(DISTINCT order_date) as unique_order_dates,
            SUM(total_order_value)::NUMERIC(15,2) as total_revenue,
            AVG(total_order_value)::NUMERIC(12,2) as avg_order_value,
            COUNT(*) as total_orders
        FROM {schema_name}.fct_orders
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(query)).fetchone()
            
            print("\n" + "="*80)
            print("DATA WAREHOUSE SUMMARY")
            print("="*80)
            print(f"Unique Customers:     {result[0]:>15,}")
            print(f"Unique Products:      {result[1]:>15,}")
            print(f"Unique Locations:     {result[2]:>15,}")
            print(f"Unique Order Dates:   {result[3]:>15,}")
            print(f"Total Revenue:        ${result[4]:>14,.2f}")
            print(f"Average Order Value:  ${result[5]:>14,.2f}")
            print(f"Total Orders:         {result[6]:>15,}")
            print("="*80)
        
    except Exception as e:
        logger.error(f"Error getting warehouse summary: {str(e)}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for warehouse ETL."""
    try:
        engine = get_db_engine()
        
        # Full refresh of warehouse
        refresh_warehouse(
            engine,
            source_schema='curated_zone',
            target_schema='data_warehouse',
            full_refresh=True
        )
        
        # Display summary
        get_warehouse_summary(engine, schema_name='data_warehouse')
        
    except Exception as e:
        logger.error(f"❌ Error in main: {str(e)}")
        raise