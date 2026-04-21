from connect import get_db_engine
import pandas as pd
import sqlalchemy as sa
import os
import json
from datetime import datetime
import numpy as np

# ============================================================================
# RAW ZONE: Store original data in JSONB format
# ============================================================================

def convert_pandas_types(obj):
    """
    Convert pandas-specific types (NaN, NaT, inf) to JSON-compatible values.
    NaN, NaT, inf → None (becomes null in JSON)
    """
    if isinstance(obj, dict):
        return {k: convert_pandas_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_pandas_types(item) for item in obj]
    elif pd.isna(obj):  # Handles NaN, NaT, None
        return None
    elif isinstance(obj, (np.floating, np.integer)):
        # Convert numpy types to native Python types
        return obj.item()
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    else:
        return obj

def create_raw_zone_table(engine, table_name, schema_name='raw_zone'):
    """
    Create a JSONB table in raw_zone schema to store original data as-is.
    
    Schema:
    - raw_id: Auto-incrementing primary key
    - data: JSONB column storing the original record
    - source_table: Which source table this came from
    - loaded_at: Timestamp of when data was loaded
    - file_hash: Hash for deduplication (optional)
    """
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.{table_name}_raw (
        raw_id BIGSERIAL PRIMARY KEY,
        data JSONB NOT NULL,
        source_table VARCHAR(255),
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_hash VARCHAR(64),
        created_by VARCHAR(100) DEFAULT 'system'
    );
    
    -- Create GIN index on JSONB column for efficient queries
    CREATE INDEX IF NOT EXISTS idx_{table_name}_raw_data 
    ON {schema_name}.{table_name}_raw USING GIN (data);
    
    -- Index on source_table for filtering
    CREATE INDEX IF NOT EXISTS idx_{table_name}_raw_source 
    ON {schema_name}.{table_name}_raw (source_table);
    
    -- Index on loaded_at for time-based queries
    CREATE INDEX IF NOT EXISTS idx_{table_name}_raw_loaded_at 
    ON {schema_name}.{table_name}_raw (loaded_at);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Raw zone table '{schema_name}.{table_name}_raw' created successfully")
    except Exception as e:
        print(f"❌ Error creating raw zone table: {str(e)}")

def create_metadata_table(engine, schema_name='raw_zone'):
    """
    Create a metadata table to track data lineage and transformations.
    """
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.data_metadata (
        metadata_id BIGSERIAL PRIMARY KEY,
        table_name VARCHAR(255),
        total_records BIGINT,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_file VARCHAR(255),
        record_count BIGINT,
        status VARCHAR(50) DEFAULT 'loaded'
    );
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(sa.text(query))
            conn.commit()
        print(f"✓ Metadata table '{schema_name}.data_metadata' created successfully")
    except Exception as e:
        print(f"❌ Error creating metadata table: {str(e)}")

def load_source_data_to_raw_zone(engine, source_schema='source_data', raw_zone_schema='raw_zone'):
    """
    Load all tables from source_data schema into raw_zone as JSONB.
    Converts each row to JSON and stores in JSONB column.
    """
    
    try:
        with engine.connect() as conn:
            # Get all tables in source_data schema
            result = conn.execute(sa.text(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{source_schema}'
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result]
            
            if not tables:
                print(f"❌ No tables found in {source_schema} schema")
                return
            
            print(f"\nLoading {len(tables)} tables from {source_schema} to {raw_zone_schema}...")
            
            for table_name in tables:
                print(f"\n  Processing: {table_name}")
                load_table_to_jsonb(engine, table_name, source_schema, raw_zone_schema)
                
    except Exception as e:
        print(f"❌ Error during raw zone loading: {str(e)}")

def load_table_to_jsonb(engine, table_name, source_schema='source_data', 
                        raw_zone_schema='raw_zone'):
    """
    Convert a table to JSONB and load into raw zone.
    Each row becomes a JSON object in the data column.
    """
    
    try:
        # Read the source table
        df = pd.read_sql_table(table_name, engine, schema=source_schema)
        
        if df.empty:
            print(f"    ⚠ Table {table_name} is empty, skipping...")
            return
        
        # Create raw zone table if it doesn't exist
        create_raw_zone_table(engine, table_name, raw_zone_schema)
        
        # Convert DataFrame rows to JSONB records
        records = []
        for idx, row in df.iterrows():
            # Convert row to dictionary and clean pandas-specific types
            row_dict = row.to_dict()
            row_dict_clean = convert_pandas_types(row_dict)
            # Convert dict to JSON string for proper JSONB insertion
            records.append({
                'data': json.dumps(row_dict_clean),
                'source_table': table_name,
                'loaded_at': datetime.now()
            })
        
        # Batch insert into raw_zone table
        chunk_size = 1000
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            
            # Convert to DataFrame for bulk insert
            chunk_df = pd.DataFrame(chunk)
            
            # Use raw SQL for more reliable JSONB insertion
            with engine.connect() as conn:
                for _, row_data in chunk_df.iterrows():
                    conn.execute(sa.text(f"""
                        INSERT INTO {raw_zone_schema}.{table_name}_raw 
                        (data, source_table, loaded_at)
                        VALUES (:data, :source_table, :loaded_at)
                    """), {
                        'data': row_data['data'],
                        'source_table': row_data['source_table'],
                        'loaded_at': row_data['loaded_at']
                    })
                conn.commit()
        
        # Log metadata
        with engine.connect() as conn:
            conn.execute(sa.text(f"""
                INSERT INTO {raw_zone_schema}.data_metadata 
                (table_name, total_records, source_file, record_count)
                VALUES ('{table_name}', {len(df)}, '{source_schema}.{table_name}', {len(df)})
            """))
            conn.commit()
        
        print(f"    ✓ Loaded {len(df)} records into {raw_zone_schema}.{table_name}_raw")
        
    except Exception as e:
        print(f"    ❌ Error loading {table_name}: {str(e)}")

def query_raw_zone_examples(engine, schema_name='raw_zone'):
    """
    Show example queries for accessing JSONB data in raw zone.
    """
    
    examples = {
        "Get specific field from JSON": f"""
            SELECT 
                raw_id, 
                data->>'customer_id' as customer_id,
                data->>'city' as city,
                loaded_at
            FROM {schema_name}.olist_customers_raw
            LIMIT 5;
        """,
        
        "Filter by JSON field value": f"""
            SELECT COUNT(*) as count
            FROM {schema_name}.olist_customers_raw
            WHERE data->>'state' = 'SP';
        """,
        
        "Get entire JSON record": f"""
            SELECT 
                raw_id,
                jsonb_pretty(data) as original_record,
                source_table,
                loaded_at
            FROM {schema_name}.olist_customers_raw
            LIMIT 3;
        """,
        
        "Search within JSON arrays/nested fields": f"""
            SELECT raw_id, data
            FROM {schema_name}.olist_customers_raw
            WHERE data @> '{{"state": "SP"}}'::jsonb;
        """,
        
        "Extract JSON keys": f"""
            SELECT DISTINCT jsonb_object_keys(data) as field_names
            FROM {schema_name}.olist_customers_raw
            LIMIT 1;
        """,
        
        "Convert JSONB back to normalized table": f"""
            SELECT 
                raw_id,
                (data->>'customer_id')::text as customer_id,
                data->>'customer_unique_id' as customer_unique_id,
                data->>'customer_zip_code_prefix' as zip_code,
                data->>'customer_city' as city,
                data->>'customer_state' as state
            FROM {schema_name}.olist_customers_raw;
        """
    }
    
    print("\n" + "="*60)
    print("JSONB Query Examples for Raw Zone")
    print("="*60)
    
    for description, query in examples.items():
        print(f"\n{description}:")
        print(f"  {query}")

def create_table_row_zone(engine, table_name, schema_name='row_zone'):
    """
    Create a normalized table in row_zone (processed data).
    This is for flattened, normalized data after transformation from raw_zone.
    """
    pass

def main():
    """
    Main function to orchestrate data lake creation:
    1. Create raw_zone schema and JSONB tables
    2. Load source_data into raw_zone in JSONB format
    3. Create metadata tracking
    """
    
    print("\n" + "="*70)
    print("DATA LAKE CREATION - RAW ZONE WITH JSONB")
    print("="*70)
    
    # Get database connection
    engine = get_db_engine()
    
    # Step 1: Create metadata table
    # print("\n[Step 1] Creating metadata table...")
    # create_metadata_table(engine, 'raw_zone')
    
    # # Step 2: Load all source data into raw_zone as JSONB
    # print("\n[Step 2] Loading source data into raw zone...")
    # load_source_data_to_raw_zone(engine, 'source_data', 'raw_zone')
    
    # # Step 3: Show query examples
    # query_raw_zone_examples(engine, 'raw_zone')
    
    # print("\n" + "="*70)
    # print("✓ Raw zone created successfully!")
    # print("="*70)
    # print("\nNext steps:")
    # print("  1. Access JSONB data: SELECT data FROM raw_zone.<table_name>_raw;")
    # print("  2. Extract fields: SELECT data->>'field_name' FROM raw_zone.<table>_raw;")
    # print("  3. Query examples shown above for advanced JSONB operations")
    # print("\n")

if __name__ == "__main__":
    main()