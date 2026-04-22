from connect import get_db_engine
import pandas as pd
import sqlalchemy as sa
import os
from datetime import datetime
import json

# ============================================================================
# CURATED ZONE: Refined data ready for analytics (non-dimensional)
# ============================================================================
# Data flows: processed_zone (cleaned) → curated_zone (refined/denormalized)
# This is NOT dimensional modeling - that happens in data_warehouse
# Purpose: Clean, enriched data ready for consumption by warehouse ETL

def create_curated_zone_schema(engine, schema_name='curated_zone'):
    """Create curated_zone schema if it doesn't exist."""
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
        print(f"✓ Curated zone schema '{schema_name}' verified")
    except Exception as e:
        print(f"❌ Error creating curated zone schema: {str(e)}")

# ============================================================================
# REFINED TABLES - Clean, denormalized data for consumption
# ============================================================================

def create_orders_refined_table(engine, schema_name='curated_zone'):
    """Create refined orders table with enriched fields."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.orders_refined (
        order_id VARCHAR(255) PRIMARY KEY,
        customer_id VARCHAR(255) NOT NULL,
        order_status VARCHAR(50),
        
        -- Timestamps
        order_purchase_timestamp TIMESTAMP,
        order_approved_at TIMESTAMP,
        order_delivered_customer_date TIMESTAMP,
        order_estimated_delivery_date TIMESTAMP,
        
        -- Derived metrics for analytics
        days_to_delivery INT,
        is_on_time BOOLEAN,
        purchase_month DATE,
        
        -- Data quality
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_schema VARCHAR(100) DEFAULT 'processed_zone'
    );
    
    CREATE INDEX IF NOT EXISTS idx_orders_refined_customer_id ON {schema_name}.orders_refined (customer_id);
    CREATE INDEX IF NOT EXISTS idx_orders_refined_status ON {schema_name}.orders_refined (order_status);
    CREATE INDEX IF NOT EXISTS idx_orders_refined_purchase_month ON {schema_name}.orders_refined (purchase_month);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Orders refined table created")
    except Exception as e:
        print(f"❌ Error creating orders refined table: {str(e)}")

def create_order_items_refined_table(engine, schema_name='curated_zone'):
    """Create refined order items table."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.order_items_refined (
        order_item_id BIGSERIAL PRIMARY KEY,
        order_id VARCHAR(255) NOT NULL,
        product_id VARCHAR(255),
        seller_id VARCHAR(255),
        price NUMERIC(10,2),
        freight_value NUMERIC(10,2),
        total_item_value NUMERIC(10,2),
        
        -- Timestamps
        shipping_limit_date TIMESTAMP,
        
        -- Data quality
        data_quality_score NUMERIC(3,2),
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_schema VARCHAR(100) DEFAULT 'processed_zone'
    );
    
    CREATE INDEX IF NOT EXISTS idx_order_items_refined_order_id ON {schema_name}.order_items_refined (order_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_refined_product_id ON {schema_name}.order_items_refined (product_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_refined_seller_id ON {schema_name}.order_items_refined (seller_id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Order items refined table created")
    except Exception as e:
        print(f"❌ Error creating order items refined table: {str(e)}")

def create_customers_refined_table(engine, schema_name='curated_zone'):
    """Create refined customers table."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.customers_refined (
        customer_id VARCHAR(255) PRIMARY KEY,
        customer_unique_id VARCHAR(255),
        customer_zip_code_prefix VARCHAR(10),
        customer_city VARCHAR(255),
        customer_state VARCHAR(2),
        
        -- Data quality
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_schema VARCHAR(100) DEFAULT 'processed_zone'
    );
    
    CREATE INDEX IF NOT EXISTS idx_customers_refined_state ON {schema_name}.customers_refined (customer_state);
    CREATE INDEX IF NOT EXISTS idx_customers_refined_city ON {schema_name}.customers_refined (customer_city);
    CREATE INDEX IF NOT EXISTS idx_customers_refined_zip ON {schema_name}.customers_refined (customer_zip_code_prefix);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Customers refined table created")
    except Exception as e:
        print(f"❌ Error creating customers refined table: {str(e)}")

def create_sellers_refined_table(engine, schema_name='curated_zone'):
    """Create refined sellers table."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.sellers_refined (
        seller_id VARCHAR(255) PRIMARY KEY,
        seller_zip_code_prefix VARCHAR(10),
        seller_city VARCHAR(255),
        seller_state VARCHAR(2),
        
        -- Data quality
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_schema VARCHAR(100) DEFAULT 'processed_zone'
    );
    
    CREATE INDEX IF NOT EXISTS idx_sellers_refined_state ON {schema_name}.sellers_refined (seller_state);
    CREATE INDEX IF NOT EXISTS idx_sellers_refined_city ON {schema_name}.sellers_refined (seller_city);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Sellers refined table created")
    except Exception as e:
        print(f"❌ Error creating sellers refined table: {str(e)}")

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_orders_to_curated(engine, source_schema='processed_zone', 
                           target_schema='curated_zone'):
    """Load refined orders data from processed_zone to curated_zone."""
    try:
        print("\n  Loading orders to curated zone...")
        
        with engine.connect() as conn:
            # Step 1: Clear existing data
            conn.execute(sa.text(f"TRUNCATE TABLE {target_schema}.orders_refined CASCADE"))
            conn.commit()
            
            # Step 2: Insert new data
            insert_query = f"""
            INSERT INTO {target_schema}.orders_refined
            (order_id, customer_id, order_status, order_purchase_timestamp,
             order_approved_at, order_delivered_customer_date, order_estimated_delivery_date,
             days_to_delivery, is_on_time, purchase_month,
             data_quality_score, is_valid)
            SELECT 
                order_id,
                customer_id,
                order_status,
                order_purchase_timestamp::TIMESTAMP,
                order_approved_at::TIMESTAMP,
                order_delivered_customer_date::TIMESTAMP,
                order_estimated_delivery_date::TIMESTAMP,
                CASE 
                    WHEN order_delivered_customer_date IS NOT NULL 
                    THEN DATE(order_delivered_customer_date::TIMESTAMP) - DATE(order_purchase_timestamp::TIMESTAMP)
                    ELSE NULL 
                END as days_to_delivery,
                CASE 
                    WHEN order_status = 'delivered' AND (order_delivered_customer_date::TIMESTAMP) <= (order_estimated_delivery_date::TIMESTAMP)
                    THEN TRUE
                    ELSE FALSE
                END as is_on_time,
                DATE_TRUNC('month', order_purchase_timestamp::TIMESTAMP)::DATE as purchase_month,
                data_quality_score,
                is_valid
            FROM {source_schema}.orders
            WHERE is_valid = TRUE;
            """
            conn.execute(sa.text(insert_query))
            conn.commit()
        
        # Get counts
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT COUNT(*) FROM {target_schema}.orders_refined
            """))
            count = result.fetchone()[0]
        
        print(f"    ✓ Loaded {count:,} refined orders")
        
    except Exception as e:
        print(f"    ❌ Error loading orders: {str(e)}")

def load_order_items_to_curated(engine, source_schema='processed_zone', 
                                target_schema='curated_zone'):
    """Load refined order items data from processed_zone to curated_zone."""
    try:
        print("\n  Loading order items to curated zone...")
        
        with engine.connect() as conn:
            # Step 1: Clear existing data
            conn.execute(sa.text(f"TRUNCATE TABLE {target_schema}.order_items_refined CASCADE"))
            conn.commit()
            
            # Step 2: Insert new data
            insert_query = f"""
            INSERT INTO {target_schema}.order_items_refined
            (order_id, product_id, seller_id, price, freight_value, 
             total_item_value, shipping_limit_date, data_quality_score)
            SELECT 
                order_id,
                product_id,
                seller_id,
                price,
                freight_value,
                COALESCE(price, 0) + COALESCE(freight_value, 0) as total_item_value,
                shipping_limit_date::TIMESTAMP,
                data_quality_score
            FROM {source_schema}.order_items
            WHERE order_id IS NOT NULL;
            """
            conn.execute(sa.text(insert_query))
            conn.commit()
        
        # Get counts
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT COUNT(*) FROM {target_schema}.order_items_refined
            """))
            count = result.fetchone()[0]
        
        print(f"    ✓ Loaded {count:,} refined order items")
        
    except Exception as e:
        print(f"    ❌ Error loading order items: {str(e)}")

def load_customers_to_curated(engine, source_schema='processed_zone', 
                              target_schema='curated_zone'):
    """Load refined customers data from processed_zone to curated_zone."""
    try:
        print("\n  Loading customers to curated zone...")
        
        with engine.connect() as conn:
            # Step 1: Delete existing data
            conn.execute(sa.text(f"DELETE FROM {target_schema}.customers_refined"))
            conn.commit()
            
            # Step 2: Insert new data (deduplicate on customer_id, keep highest quality score)
            insert_query = f"""
            INSERT INTO {target_schema}.customers_refined
            (customer_id, customer_unique_id, customer_zip_code_prefix, 
             customer_city, customer_state, data_quality_score, is_valid)
            SELECT DISTINCT ON (customer_id)
                customer_id,
                customer_unique_id,
                customer_zip_code_prefix,
                customer_city,
                customer_state,
                data_quality_score,
                is_valid
            FROM {source_schema}.customers
            WHERE is_valid = TRUE
            ORDER BY customer_id, data_quality_score DESC;
            """
            conn.execute(sa.text(insert_query))
            conn.commit()
        
        # Get counts
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT COUNT(*) FROM {target_schema}.customers_refined
            """))
            count = result.fetchone()[0]
        
        print(f"    ✓ Loaded {count:,} refined customers")
        
    except Exception as e:
        print(f"    ❌ Error loading customers: {str(e)}")

def load_sellers_to_curated(engine, source_schema='processed_zone', 
                            target_schema='curated_zone'):
    """Load refined sellers data from processed_zone to curated_zone."""
    try:
        print("\n  Loading sellers to curated zone...")
        
        with engine.connect() as conn:
            # Step 1: Clear existing data
            conn.execute(sa.text(f"TRUNCATE TABLE {target_schema}.sellers_refined CASCADE"))
            conn.commit()
            
            # Step 2: Insert new data (deduplicate on seller_id, keep highest quality score)
            insert_query = f"""
            INSERT INTO {target_schema}.sellers_refined
            (seller_id, seller_zip_code_prefix, seller_city, seller_state,
             data_quality_score, is_valid)
            SELECT DISTINCT ON (seller_id)
                seller_id,
                seller_zip_code_prefix,
                seller_city,
                seller_state,
                data_quality_score,
                is_valid
            FROM {source_schema}.sellers
            WHERE is_valid = TRUE
            ORDER BY seller_id, data_quality_score DESC;
            """
            conn.execute(sa.text(insert_query))
            conn.commit()
        
        # Get counts
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT COUNT(*) FROM {target_schema}.sellers_refined
            """))
            count = result.fetchone()[0]
        
        print(f"    ✓ Loaded {count:,} refined sellers")
        
    except Exception as e:
        print(f"    ❌ Error loading sellers: {str(e)}")

def show_curated_statistics(engine, schema_name='curated_zone'):
    """Show curated zone statistics."""
    
    print("\n" + "="*70)
    print("CURATED ZONE - DATA SUMMARY")
    print("="*70)
    
    try:
        with engine.connect() as conn:
            # Orders summary
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    COUNT(CASE WHEN order_status = 'delivered' THEN 1 END) as delivered_orders,
                    COUNT(CASE WHEN is_on_time = TRUE THEN 1 END) as on_time_orders
                FROM {schema_name}.orders_refined
            """))
            row = result.fetchone()
            print(f"\nOrders:")
            print(f"  Total orders: {row[0]:,}")
            print(f"  Unique customers: {row[1]:,}")
            print(f"  Delivered orders: {row[2]:,}")
            print(f"  On-time deliveries: {row[3]:,}")
            
            # Order items summary
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(DISTINCT order_id) as unique_orders,
                    COUNT(DISTINCT product_id) as unique_products,
                    COUNT(DISTINCT seller_id) as unique_sellers
                FROM {schema_name}.order_items_refined
            """))
            row = result.fetchone()
            print(f"\nOrder Items:")
            print(f"  Total items: {row[0]:,}")
            print(f"  Unique orders: {row[1]:,}")
            print(f"  Unique products: {row[2]:,}")
            print(f"  Unique sellers: {row[3]:,}")
            
            # Customers summary
            result = conn.execute(sa.text(f"""
                SELECT COUNT(*) as total_customers
                FROM {schema_name}.customers_refined
            """))
            print(f"\nCustomers: {result.fetchone()[0]:,}")
            
            # Sellers summary
            result = conn.execute(sa.text(f"""
                SELECT COUNT(*) as total_sellers
                FROM {schema_name}.sellers_refined
            """))
            print(f"Sellers: {result.fetchone()[0]:,}")
            
    except Exception as e:
        print(f"❌ Error showing statistics: {str(e)}")

def main():
    """Main orchestration function."""
    
    print("\n" + "="*70)
    print("CURATED ZONE CREATION - REFINED DATA FOR DATA WAREHOUSE")
    print("="*70)
    
    engine = get_db_engine()
    
    # Step 1: Create schema and tables
    print("\n[Step 1] Creating curated zone schema and tables...")
    create_curated_zone_schema(engine, 'curated_zone')
    create_orders_refined_table(engine, 'curated_zone')
    create_order_items_refined_table(engine, 'curated_zone')
    create_customers_refined_table(engine, 'curated_zone')
    create_sellers_refined_table(engine, 'curated_zone')
    
    # Step 2: Load refined data from processed_zone
    print("\n[Step 2] Loading refined data from processed zone...")
    load_orders_to_curated(engine, 'processed_zone', 'curated_zone')
    load_order_items_to_curated(engine, 'processed_zone', 'curated_zone')
    load_customers_to_curated(engine, 'processed_zone', 'curated_zone')
    load_sellers_to_curated(engine, 'processed_zone', 'curated_zone')
    
    # Step 3: Show statistics
    show_curated_statistics(engine, 'curated_zone')
    
    print("\n" + "="*70)
    print("✓ Curated zone created successfully!")
    print("="*70)
    print("\nFeatures:")
    print("  ✓ Refined, clean tables ready for consumption")
    print("  ✓ Denormalized but structured data")
    print("  ✓ Enriched with calculated fields (on-time delivery, etc)")
    print("  ✓ Indexed for efficient queries")
    print("\nNext: Create dimensional model in data_warehouse schema")
    print("      → Use curated_zone tables as source for ETL")
    print("      → Build star schema with fact/dimension tables")
    print("      → Implement slowly changing dimensions")
    print("\n")

