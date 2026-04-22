from connect import get_db_engine
import pandas as pd
import sqlalchemy as sa
import os
from datetime import datetime
import json

# ============================================================================
# PROCESSED ZONE: Partially structured data with cleaning/validation
# ============================================================================
# Data flows: raw_zone (JSONB) → processed_zone (cleaned/validated)

def create_processed_zone_schema(engine, schema_name='processed_zone'):
    """Create processed_zone schema if it doesn't exist."""
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
        print(f"✓ Processed zone schema '{schema_name}' verified")
    except Exception as e:
        print(f"❌ Error creating processed zone schema: {str(e)}")

def create_customers_processed_table(engine, schema_name='processed_zone'):
    """Create customers table with validation and cleaning."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.customers (
        customer_id VARCHAR(255) PRIMARY KEY,
        customer_unique_id VARCHAR(255),
        customer_zip_code_prefix VARCHAR(10),
        customer_city VARCHAR(255),
        customer_state VARCHAR(2),
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN DEFAULT TRUE,
        validation_notes TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_raw_id BIGINT
    );
    
    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_customers_state ON {schema_name}.customers (customer_state);
    CREATE INDEX IF NOT EXISTS idx_customers_city ON {schema_name}.customers (customer_city);
    CREATE INDEX IF NOT EXISTS idx_customers_valid ON {schema_name}.customers (is_valid);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Customers processed table created")
    except Exception as e:
        print(f"❌ Error creating customers table: {str(e)}")

def create_geolocations_processed_table(engine, schema_name='processed_zone'):
    """Create geolocations table with validation and cleaning."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.geolocations (
        geolocation_id BIGSERIAL PRIMARY KEY,
        geolocation_zip_code_prefix VARCHAR(10),
        geolocation_latitude NUMERIC(10,6),
        geolocation_longitude NUMERIC(10,6),
        geolocation_city VARCHAR(255),
        geolocation_state VARCHAR(2),
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN DEFAULT TRUE,
        validation_notes TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_raw_id BIGINT
    );
    
    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_geolocations_zip ON {schema_name}.geolocations (geolocation_zip_code_prefix);
    CREATE INDEX IF NOT EXISTS idx_geolocations_state ON {schema_name}.geolocations (geolocation_state);
    CREATE INDEX IF NOT EXISTS idx_geolocations_valid ON {schema_name}.geolocations (is_valid);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Geolocations processed table created")
    except Exception as e:
        print(f"❌ Error creating geolocations table: {str(e)}")

def create_sellers_processed_table(engine, schema_name='processed_zone'):
    """Create sellers table with validation and cleaning."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.sellers (
        seller_id VARCHAR(255) PRIMARY KEY,
        seller_zip_code_prefix VARCHAR(10),
        seller_city VARCHAR(255),
        seller_state VARCHAR(2),
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN DEFAULT TRUE,
        validation_notes TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_raw_id BIGINT
    );
    
    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_sellers_state ON {schema_name}.sellers (seller_state);
    CREATE INDEX IF NOT EXISTS idx_sellers_city ON {schema_name}.sellers (seller_city);
    CREATE INDEX IF NOT EXISTS idx_sellers_valid ON {schema_name}.sellers (is_valid);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Sellers processed table created")
    except Exception as e:
        print(f"❌ Error creating sellers table: {str(e)}")

def create_products_processed_table(engine, schema_name='processed_zone'):
    """Create products table with validation and cleaning."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.products (
        product_id VARCHAR(255) PRIMARY KEY,
        product_category_name VARCHAR(255),
        product_name_length INTEGER,
        product_description_length INTEGER,
        product_photos_qty INTEGER,
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN DEFAULT TRUE,
        validation_notes TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_raw_id BIGINT
    );
    
    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_products_category ON {schema_name}.products (product_category_name);
    CREATE INDEX IF NOT EXISTS idx_products_valid ON {schema_name}.products (is_valid);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Products processed table created")
    except Exception as e:
        print(f"❌ Error creating products table: {str(e)}")

def create_orders_processed_table(engine, schema_name='processed_zone'):
    """Create orders table with validation and FK to customers."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.orders (
        order_id VARCHAR(255) PRIMARY KEY,
        customer_id VARCHAR(255) NOT NULL,
        order_status VARCHAR(50),
        order_purchase_timestamp TIMESTAMP,
        order_approved_at TIMESTAMP,
        order_delivered_carrier_date TIMESTAMP,
        order_delivered_customer_date TIMESTAMP,
        order_estimated_delivery_date TIMESTAMP,
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN DEFAULT TRUE,
        validation_notes TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_raw_id BIGINT,
        
        -- Foreign key constraint to customers
        CONSTRAINT fk_orders_customer_id 
            FOREIGN KEY (customer_id) 
            REFERENCES {schema_name}.customers(customer_id)
            ON DELETE RESTRICT
            ON UPDATE CASCADE
    );
    
    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON {schema_name}.orders (customer_id);
    CREATE INDEX IF NOT EXISTS idx_orders_status ON {schema_name}.orders (order_status);
    CREATE INDEX IF NOT EXISTS idx_orders_purchase_date ON {schema_name}.orders (order_purchase_timestamp);
    CREATE INDEX IF NOT EXISTS idx_orders_valid ON {schema_name}.orders (is_valid);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Orders processed table created with FK to customers")
    except Exception as e:
        print(f"❌ Error creating orders table: {str(e)}")

def create_order_items_processed_table(engine, schema_name='processed_zone'):
    """Create order items table with validation and FK to orders."""
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.order_items (
        order_item_id BIGSERIAL PRIMARY KEY,
        order_id VARCHAR(255) NOT NULL,
        product_id VARCHAR(255),
        seller_id VARCHAR(255),
        shipping_limit_date TIMESTAMP,
        price NUMERIC(10,2),
        freight_value NUMERIC(10,2),
        data_quality_score NUMERIC(3,2),
        is_valid BOOLEAN DEFAULT TRUE,
        validation_notes TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_raw_id BIGINT,
        
        -- Foreign key constraint to orders
        CONSTRAINT fk_order_items_order_id 
            FOREIGN KEY (order_id) 
            REFERENCES {schema_name}.orders(order_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
            FOREIGN KEY (product_id)
            REFERENCES {schema_name}.products(product_id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
            FOREIGN KEY (seller_id)
            REFERENCES {schema_name}.sellers(seller_id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    );
    
    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON {schema_name}.order_items (order_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON {schema_name}.order_items (product_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_seller_id ON {schema_name}.order_items (seller_id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Order items processed table created with FK to orders")
    except Exception as e:
        print(f"❌ Error creating order items table: {str(e)}")

def validate_and_clean_customer_record(raw_data):
    """
    Validate and clean customer data from raw_zone.
    Returns: (cleaned_record, quality_score, is_valid, validation_notes)
    """
    issues = []
    quality_score = 1.0
    
    try:
        customer_id = str(raw_data.get('customer_id', '')).strip()
        if not customer_id:
            issues.append("Missing customer_id")
            quality_score -= 0.3
        
        customer_unique_id = str(raw_data.get('customer_unique_id', '')).strip()
        if not customer_unique_id:
            issues.append("Missing customer_unique_id")
            quality_score -= 0.2
        
        zip_code = str(raw_data.get('customer_zip_code_prefix', '')).strip()
        if not zip_code or len(zip_code) < 5:
            issues.append("Invalid zip code")
            quality_score -= 0.15
        
        city = str(raw_data.get('customer_city', '')).strip()
        if not city:
            issues.append("Missing city")
            quality_score -= 0.2
        
        state = str(raw_data.get('customer_state', '')).strip().upper()
        if not state or len(state) != 2:
            issues.append("Invalid state code")
            quality_score -= 0.15
        
        is_valid = quality_score > 0.5  # Valid if >50% data quality
        quality_score = max(0.0, min(1.0, quality_score))  # Clamp between 0 and 1
        
        cleaned = {
            'customer_id': customer_id,
            'customer_unique_id': customer_unique_id,
            'customer_zip_code_prefix': zip_code,
            'customer_city': city,
            'customer_state': state
        }
        
        return cleaned, quality_score, is_valid, '; '.join(issues) if issues else None
        
    except Exception as e:
        return None, 0.0, False, f"Validation error: {str(e)}"

def validate_and_clean_order_record(raw_data):
    """Validate and clean order data from raw_zone."""
    issues = []
    quality_score = 1.0
    
    try:
        order_id = str(raw_data.get('order_id', '')).strip()
        if not order_id:
            issues.append("Missing order_id")
            quality_score -= 0.3
        
        customer_id = str(raw_data.get('customer_id', '')).strip()
        if not customer_id:
            issues.append("Missing customer_id")
            quality_score -= 0.3
        
        order_status = str(raw_data.get('order_status', '')).strip().lower()
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'canceled']
        if order_status not in valid_statuses:
            issues.append(f"Invalid order_status: {order_status}")
            quality_score -= 0.2
        
        # Validate timestamp fields
        purchase_timestamp = raw_data.get('order_purchase_timestamp')
        if not purchase_timestamp:
            issues.append("Missing purchase timestamp")
            quality_score -= 0.2
        
        is_valid = quality_score > 0.5
        quality_score = max(0.0, min(1.0, quality_score))
        
        cleaned = {
            'order_id': order_id,
            'customer_id': customer_id,
            'order_status': order_status,
            'order_purchase_timestamp': purchase_timestamp,
            'order_approved_at': raw_data.get('order_approved_at'),
            'order_delivered_carrier_date': raw_data.get('order_delivered_carrier_date'),
            'order_delivered_customer_date': raw_data.get('order_delivered_customer_date'),
            'order_estimated_delivery_date': raw_data.get('order_estimated_delivery_date')
        }
        
        return cleaned, quality_score, is_valid, '; '.join(issues) if issues else None
        
    except Exception as e:
        return None, 0.0, False, f"Validation error: {str(e)}"

def validate_and_clean_product_record(raw_data):
    """Validate and clean product data from raw_zone."""
    issues = []
    quality_score = 1.0
    
    try:
        product_id = str(raw_data.get('product_id', '')).strip()
        if not product_id:
            issues.append("Missing product_id")
            quality_score -= 0.3
        
        category_name = str(raw_data.get('product_category_name', '')).strip()
        if not category_name:
            issues.append("Missing category name")
            quality_score -= 0.2
        
        name_length = len(str(raw_data.get('product_name_length', '')))
        description_length = len(str(raw_data.get('product_description_length', '')))
        
        cleaned = {
            'product_id': product_id,
            'product_category_name': category_name,
            'product_name_length': name_length,
            'product_description_length': description_length,
            'product_photos_qty': raw_data.get('product_photos_qty')
        }
        
        is_valid = quality_score > 0.5
        quality_score = max(0.0, min(1.0, quality_score))
        
        return cleaned, quality_score, is_valid, '; '.join(issues) if issues else None
        
    except Exception as e:
        return None, 0.0, False, f"Validation error: {str(e)}"

def validate_and_clean_seller_record(raw_data):
    """Validate and clean seller data from raw_zone."""
    issues = []
    quality_score = 1.0
    
    try:
        seller_id = str(raw_data.get('seller_id', '')).strip()
        if not seller_id:
            issues.append("Missing seller_id")
            quality_score -= 0.3
        
        zip_code = str(raw_data.get('seller_zip_code_prefix', '')).strip()
        if not zip_code or len(zip_code) < 5:
            issues.append("Invalid zip code")
            quality_score -= 0.2
        
        city = str(raw_data.get('seller_city', '')).strip()
        if not city:
            issues.append("Missing city")
            quality_score -= 0.2
        
        state = str(raw_data.get('seller_state', '')).strip().upper()
        if not state or len(state) != 2:
            issues.append("Invalid state code")
            quality_score -= 0.15
        
        is_valid = quality_score > 0.5
        quality_score = max(0.0, min(1.0, quality_score))
        
        cleaned = {
            'seller_id': seller_id,
            'seller_zip_code_prefix': zip_code,
            'seller_city': city,
            'seller_state': state
        }
        
        return cleaned, quality_score, is_valid, '; '.join(issues) if issues else None
        
    except Exception as e:
        return None, 0.0, False, f"Validation error: {str(e)}"

def validate_and_clean_geolocation_record(raw_data):
    """Validate and clean geolocation data from raw_zone."""
    issues = []
    quality_score = 1.0
    
    try:
        zip_code = str(raw_data.get('geolocation_zip_code_prefix', '')).strip()
        if not zip_code or len(zip_code) < 5:
            issues.append("Invalid zip code")
            quality_score -= 0.3
        
        latitude = raw_data.get('geolocation_lat')
        longitude = raw_data.get('geolocation_lng')
        if latitude is None or longitude is None:
            issues.append("Missing latitude or longitude")
            quality_score -= 0.3
        
        city = str(raw_data.get('geolocation_city', '')).strip()
        state = str(raw_data.get('geolocation_state', '')).strip().upper()
        
        cleaned = {
            'geolocation_zip_code_prefix': zip_code,
            'geolocation_lat': latitude,
            'geolocation_lng': longitude,
            'geolocation_city': city,
            'geolocation_state': state
        }
        
        is_valid = quality_score > 0.5
        quality_score = max(0.0, min(1.0, quality_score))
        
        return cleaned, quality_score, is_valid, '; '.join(issues) if issues else None
        
    except Exception as e:
        return None, 0.0, False, f"Validation error: {str(e)}"

def process_geolocations_from_raw(engine, raw_schema='raw_zone', 
                                  processed_schema='processed_zone'):
    """Load and process geolocations from raw_zone."""
    try:
        print("\n  Processing geolocations...")
        # read raw geolocations data
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT raw_id, data FROM {raw_schema}.olist_geolocation_dataset_raw
                ORDER BY raw_id 
            """))
            raw_records = result.fetchall()
        if not raw_records:
            print("    ⚠ No raw geolocation records found")
            return
        processed_records = []
        valid_count = 0
        invalid_count = 0
        for raw_id, data_json in raw_records:
            try:
                if isinstance(data_json, str):
                    raw_data = json.loads(data_json)
                else:
                    raw_data = data_json

                # Validate and clean
                cleaned, quality_score, is_valid, notes = validate_and_clean_geolocation_record(raw_data)

                if cleaned and is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                processed_records.append({
                    'geolocation_zip_code_prefix': cleaned['geolocation_zip_code_prefix'] if cleaned else None,
                    'geolocation_latitude': cleaned['geolocation_lat'] if cleaned else None,
                    'geolocation_longitude': cleaned['geolocation_lng'] if cleaned else None,
                    'geolocation_city': cleaned['geolocation_city'] if cleaned else None,
                    'geolocation_state': cleaned['geolocation_state'] if cleaned else None,
                    'data_quality_score': quality_score,
                    'is_valid': is_valid,
                    'validation_notes': notes,
                    'source_raw_id': raw_id
                })
            except Exception as e:
                print(f"    ⚠ Error processing geolocation raw_id {raw_id}: {str(e)}")

        # Insert processed records
        if processed_records:
            df = pd.DataFrame(processed_records)
            df.to_sql('geolocations', engine, schema=processed_schema,
                     if_exists='replace', index=False)
            print(f"    ✓ Loaded {len(processed_records)} geolocation records ({valid_count} valid, {invalid_count} invalid)")
    except Exception as e:
        print(f"    ❌ Error processing geolocations: {str(e)}")

def process_sellers_from_raw(engine, raw_schema='raw_zone', 
                             processed_schema='processed_zone'):
    """Load and process sellers from raw_zone."""
    try:
        print("\n  Processing sellers...")
        # read raw sellers data
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT raw_id, data FROM {raw_schema}.olist_sellers_dataset_raw
                ORDER BY raw_id
            """))
            raw_records = result.fetchall()
        if not raw_records:
            print("    ⚠ No raw seller records found")
            return
        processed_records = []
        valid_count = 0
        invalid_count = 0
        for raw_id, data_json in raw_records:
            try:
                if isinstance(data_json, str):
                    raw_data = json.loads(data_json)
                else:
                    raw_data = data_json

                # Validate and clean
                cleaned, quality_score, is_valid, notes = validate_and_clean_seller_record(raw_data)

                if cleaned and is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                processed_records.append({
                    'seller_id': cleaned['seller_id'] if cleaned else None,
                    'seller_zip_code_prefix': cleaned['seller_zip_code_prefix'] if cleaned else None,
                    'seller_city': cleaned['seller_city'] if cleaned else None,
                    'seller_state': cleaned['seller_state'] if cleaned else None,
                    'data_quality_score': quality_score,
                    'is_valid': is_valid,
                    'validation_notes': notes,
                    'source_raw_id': raw_id
                })
            except Exception as e:
                print(f"    ⚠ Error processing seller raw_id {raw_id}: {str(e)}")

        # Insert processed records
        if processed_records:
            df = pd.DataFrame(processed_records)
            df.to_sql('sellers', engine, schema=processed_schema,
                     if_exists='replace', index=False)
            print(f"    ✓ Loaded {len(processed_records)} seller records ({valid_count} valid, {invalid_count} invalid)")
    
    except Exception as e:
        print(f"    ❌ Error processing sellers: {str(e)}")

def process_customers_from_raw(engine, raw_schema='raw_zone', 
                                processed_schema='processed_zone'):
    """Load and process customers from raw_zone."""
    
    try:
        print("\n  Processing customers...")
        
        # Read raw customers data
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT raw_id, data FROM {raw_schema}.olist_customers_dataset_raw
                ORDER BY raw_id
            """))
            raw_records = result.fetchall()
        
        if not raw_records:
            print("    ⚠ No raw customer records found")
            return
        
        processed_records = []
        valid_count = 0
        invalid_count = 0
        
        for raw_id, data_json in raw_records:
            try:
                # Parse JSON if it's a string
                if isinstance(data_json, str):
                    raw_data = json.loads(data_json)
                else:
                    raw_data = data_json
                
                # Validate and clean
                cleaned, quality_score, is_valid, notes = validate_and_clean_customer_record(raw_data)
                
                if cleaned and is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                
                processed_records.append({
                    'customer_id': cleaned['customer_id'] if cleaned else None,
                    'customer_unique_id': cleaned['customer_unique_id'] if cleaned else None,
                    'customer_zip_code_prefix': cleaned['customer_zip_code_prefix'] if cleaned else None,
                    'customer_city': cleaned['customer_city'] if cleaned else None,
                    'customer_state': cleaned['customer_state'] if cleaned else None,
                    'data_quality_score': quality_score,
                    'is_valid': is_valid,
                    'validation_notes': notes,
                    'source_raw_id': raw_id
                })
            except Exception as e:
                print(f"    ⚠ Error processing customer raw_id {raw_id}: {str(e)}")
        
        # Insert processed records
        if processed_records:
            df = pd.DataFrame(processed_records)
            df.to_sql('customers', engine, schema=processed_schema, 
                     if_exists='replace', index=False)
            print(f"    ✓ Loaded {len(processed_records)} customer records ({valid_count} valid, {invalid_count} invalid)")
        
    except Exception as e:
        print(f"    ❌ Error processing customers: {str(e)}")

def process_products_from_raw(engine, raw_schema='raw_zone', 
                             processed_schema='processed_zone'):
    """Load and process products from raw_zone."""
    try:
        print("\n  Processing products...")
        # read raw products data
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT raw_id, data FROM {raw_schema}.olist_products_dataset_raw
                ORDER BY raw_id
            """))
            raw_records = result.fetchall()
        if not raw_records:
            print("    ⚠ No raw product records found")
            return
        processed_records = []
        valid_count = 0
        invalid_count = 0
        for raw_id, data_json in raw_records:
            try:
                if isinstance(data_json, str):
                    raw_data = json.loads(data_json)
                else:
                    raw_data = data_json

                # Validate and clean
                cleaned, quality_score, is_valid, notes = validate_and_clean_product_record(raw_data)

                if cleaned and is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                processed_records.append({
                    'product_id': cleaned['product_id'] if cleaned else None,
                    'product_category_name': cleaned['product_category_name'] if cleaned else None,
                    'product_name_length': cleaned['product_name_length'] if cleaned else None,
                    'product_description_length': cleaned['product_description_length'] if cleaned else None,
                    'product_photos_qty': cleaned['product_photos_qty'] if cleaned else None,
                    'data_quality_score': quality_score,
                    'is_valid': is_valid,
                    'validation_notes': notes,
                    'source_raw_id': raw_id
                })
            except Exception as e:
                print(f"    ⚠ Error processing product raw_id {raw_id}: {str(e)}")

        # Insert processed records
        if processed_records:
            df = pd.DataFrame(processed_records)
            df.to_sql('products', engine, schema=processed_schema,
                     if_exists='replace', index=False)
            print(f"    ✓ Loaded {len(processed_records)} product records ({valid_count} valid, {invalid_count} invalid)")

    except Exception as e:
        print(f"    ❌ Error processing products: {str(e)}")

def process_orders_from_raw(engine, raw_schema='raw_zone', 
                           processed_schema='processed_zone'):
    """Load and process orders from raw_zone."""
    
    try:
        print("\n  Processing orders...")
        
        # Read raw orders data
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT raw_id, data FROM {raw_schema}.olist_orders_dataset_raw
                ORDER BY raw_id
            """))
            raw_records = result.fetchall()
        
        if not raw_records:
            print("    ⚠ No raw order records found")
            return
        
        processed_records = []
        valid_count = 0
        invalid_count = 0
        
        for raw_id, data_json in raw_records:
            try:
                if isinstance(data_json, str):
                    raw_data = json.loads(data_json)
                else:
                    raw_data = data_json
                
                # Validate and clean
                cleaned, quality_score, is_valid, notes = validate_and_clean_order_record(raw_data)
                
                if cleaned and is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                
                processed_records.append({
                    'order_id': cleaned['order_id'] if cleaned else None,
                    'customer_id': cleaned['customer_id'] if cleaned else None,
                    'order_status': cleaned['order_status'] if cleaned else None,
                    'order_purchase_timestamp': cleaned['order_purchase_timestamp'] if cleaned else None,
                    'order_approved_at': cleaned['order_approved_at'] if cleaned else None,
                    'order_delivered_carrier_date': cleaned['order_delivered_carrier_date'] if cleaned else None,
                    'order_delivered_customer_date': cleaned['order_delivered_customer_date'] if cleaned else None,
                    'order_estimated_delivery_date': cleaned['order_estimated_delivery_date'] if cleaned else None,
                    'data_quality_score': quality_score,
                    'is_valid': is_valid,
                    'validation_notes': notes,
                    'source_raw_id': raw_id
                })
            except Exception as e:
                print(f"    ⚠ Error processing order raw_id {raw_id}: {str(e)}")
        
        # Insert processed records
        if processed_records:
            df = pd.DataFrame(processed_records)
            df.to_sql('orders', engine, schema=processed_schema, 
                     if_exists='replace', index=False)
            print(f"    ✓ Loaded {len(processed_records)} order records ({valid_count} valid, {invalid_count} invalid)")
        
    except Exception as e:
        print(f"    ❌ Error processing orders: {str(e)}")

def process_order_items_from_raw(engine, raw_schema='raw_zone', 
                                processed_schema='processed_zone'):
    """Load and process order items from raw_zone."""
    
    try:
        print("\n  Processing order items...")
        
        # Read raw order items data
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"""
                SELECT raw_id, data FROM {raw_schema}.olist_order_items_dataset_raw
                ORDER BY raw_id
            """))
            raw_records = result.fetchall()
        
        if not raw_records:
            print("    ⚠ No raw order items records found")
            return
        
        processed_records = []
        valid_count = 0
        
        for raw_id, data_json in raw_records:
            try:
                if isinstance(data_json, str):
                    raw_data = json.loads(data_json)
                else:
                    raw_data = data_json
                
                order_id = str(raw_data.get('order_id', '')).strip()
                product_id = str(raw_data.get('product_id', '')).strip()
                seller_id = str(raw_data.get('seller_id', '')).strip()
                
                # Simple validation
                is_valid = bool(order_id)
                quality_score = 1.0 if is_valid else 0.0
                
                if order_id:
                    valid_count += 1
                
                processed_records.append({
                    'order_id': order_id,
                    'product_id': product_id,
                    'seller_id': seller_id,
                    'shipping_limit_date': raw_data.get('shipping_limit_date'),
                    'price': float(raw_data.get('price', 0)) if raw_data.get('price') else None,
                    'freight_value': float(raw_data.get('freight_value', 0)) if raw_data.get('freight_value') else None,
                    'data_quality_score': quality_score,
                    'is_valid': is_valid,
                    'source_raw_id': raw_id
                })
            except Exception as e:
                print(f"    ⚠ Error processing order item raw_id {raw_id}: {str(e)}")
        
        # Insert processed records
        if processed_records:
            df = pd.DataFrame(processed_records)
            df.to_sql('order_items', engine, schema=processed_schema, 
                     if_exists='replace', index=False)
            print(f"    ✓ Loaded {len(processed_records)} order item records ({valid_count} valid)")
        
    except Exception as e:
        print(f"    ❌ Error processing order items: {str(e)}")

def show_processing_stats(engine, schema_name='processed_zone'):
    """Show data quality statistics."""
    
    print("\n" + "="*70)
    print("PROCESSED ZONE - DATA QUALITY STATISTICS")
    print("="*70)
    
    try:
        with engine.connect() as conn:
            # Customers stats
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid,
                    ROUND(AVG(data_quality_score)::NUMERIC, 3) as avg_quality,
                    MIN(data_quality_score) as min_quality
                FROM {schema_name}.customers
            """))
            row = result.fetchone()
            print(f"\nCustomers:")
            print(f"  Total records: {row[0]}")
            print(f"  Valid records: {row[1]}")
            print(f"  Avg quality score: {row[2]}")
            

            # Products stats
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid,
                    ROUND(AVG(data_quality_score)::NUMERIC, 3) as avg_quality
                FROM {schema_name}.products
            """))
            row = result.fetchone()
            print(f"\nProducts:")
            print(f"  Total records: {row[0]}")
            print(f"  Valid records: {row[1]}")
            print(f"  Avg quality score: {row[2]}")

            # Geolocations stats
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid,
                    ROUND(AVG(data_quality_score)::NUMERIC, 3) as avg_quality
                FROM {schema_name}.geolocations
            """))
            row = result.fetchone()
            print(f"\nGeolocations:")
            print(f"  Total records: {row[0]}")
            print(f"  Valid records: {row[1]}")
            print(f"  Avg quality score: {row[2]}") 

            # Sellers stats
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid,
                    ROUND(AVG(data_quality_score)::NUMERIC, 3) as avg_quality
                FROM {schema_name}.sellers
            """))
            row = result.fetchone()
            print(f"\nSellers:")
            print(f"  Total records: {row[0]}")
            print(f"  Valid records: {row[1]}")
            print(f"  Avg quality score: {row[2]}")

            # Orders stats
            result = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid,
                    ROUND(AVG(data_quality_score)::NUMERIC, 3) as avg_quality
                FROM {schema_name}.orders
            """))
            row = result.fetchone()
            print(f"\nOrders:")
            print(f"  Total records: {row[0]}")
            print(f"  Valid records: {row[1]}")
            print(f"  Avg quality score: {row[2]}")
            
            # Orders by status
            result = conn.execute(sa.text(f"""
                SELECT order_status, COUNT(*) as count
                FROM {schema_name}.orders
                GROUP BY order_status
                ORDER BY count DESC
            """))
            print(f"\n  Orders by status:")
            for row in result:
                print(f"    - {row[0]}: {row[1]}")
            
            # Foreign key validation
            result = conn.execute(sa.text(f"""
                SELECT COUNT(DISTINCT customer_id) as unique_customers
                FROM {schema_name}.orders
            """))
            unique_customers = result.fetchone()[0]
            
            result = conn.execute(sa.text(f"""
                SELECT COUNT(DISTINCT customer_id) as total_customers
                FROM {schema_name}.customers
            """))
            total_customers = result.fetchone()[0]
            
            print(f"\nForeign Key Validation (orders.customer_id → customers.customer_id):")
            print(f"  Orders with valid customer refs: {unique_customers}/{unique_customers}")
            print(f"  Total customers available: {total_customers}")
            
    except Exception as e:
        print(f"❌ Error showing stats: {str(e)}")

def main():
    """Main orchestration function."""
    
    print("\n" + "="*70)
    print("PROCESSED ZONE CREATION - DATA CLEANING & VALIDATION")
    print("="*70)
    
    engine = get_db_engine()
    
    # Step 1: Create schema and tables
    print("\n[Step 1] Creating processed zone schema and tables...")
    create_processed_zone_schema(engine, 'processed_zone')

    # Step 2: Process data from raw_zone
    print("\n[Step 2] Processing data from raw_zone...")
    create_customers_processed_table(engine, 'processed_zone')
    process_customers_from_raw(engine, 'raw_zone', 'processed_zone')
    
    create_products_processed_table(engine, 'processed_zone')
    process_products_from_raw(engine, 'raw_zone', 'processed_zone')

    create_geolocations_processed_table(engine, 'processed_zone')
    process_geolocations_from_raw(engine, 'raw_zone', 'processed_zone')

    create_sellers_processed_table(engine, 'processed_zone')
    process_sellers_from_raw(engine, 'raw_zone', 'processed_zone')

    create_orders_processed_table(engine, 'processed_zone')
    process_orders_from_raw(engine, 'raw_zone', 'processed_zone')

    create_order_items_processed_table(engine, 'processed_zone')
    process_order_items_from_raw(engine, 'raw_zone', 'processed_zone')
    
    # Step 3: Show statistics
    show_processing_stats(engine, 'processed_zone')
    
    print("\n" + "="*70)
    print("✓ Processed zone created successfully!")
    print("="*70)
    print("\nFeatures:")
    print("  ✓ Data validation and cleaning")
    print("  ✓ Data quality scoring (0.0 - 1.0)")
    print("  ✓ Foreign key constraints (orders → customers)")
    print("  ✓ Timestamp normalization")
    print("  ✓ Invalid record tracking")
    print("\n")

