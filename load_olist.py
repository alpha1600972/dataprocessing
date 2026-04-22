import sqlalchemy as sa
import pandas as pd
import glob, os
from connect import get_db_engine
from pathlib import Path


def create_schema(engine, schema_name):
    """Create a new schema in the database if it doesn't exist."""
    with engine.connect() as conn:
        conn.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))
        conn.commit()
        print(f"✓ Schema '{schema_name}' created/verified")

def load_csv_to_db(engine, csv_file, table_name, schema_name='source_data'):
    """Load a CSV file into a specified table in the database."""
    try:
        df = pd.read_csv(csv_file)
        df.to_sql(
            table_name,
            engine,
            schema=schema_name,
            if_exists='replace',
            index=False,
            chunksize=1000 # Load in chunks to handle large files
        )
        print(f"✓ Loaded {len(df)} rows into {schema_name}.{table_name}")
    except Exception as e:
        print(f"❌ Error loading {table_name}: {str(e)}")

def index_table(engine, table_name, column_name, schema_name='source_data'):
    """Create an index on a specified column of a table."""
    index_name = f"{table_name}_{column_name}_idx"
    with engine.connect() as conn:
        conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {schema_name}.{table_name} ({column_name});"))
        conn.commit()
        print(f"✓ Index '{index_name}' created on {schema_name}.{table_name}({column_name})")

def main():
    # Database connection
    engine = get_db_engine()
    
    # Path to Olist CSV files
    data_path = os.getenv("SOURCE_DIR")
    
    if not os.path.exists(data_path):
        print(f"❌ Data path '{data_path}' not found.")
        print("Please download the Olist dataset from Kaggle and place CSV files in './Data_list' folder")
        return
    
    csv_files = glob.glob(os.path.join(data_path, '*.csv')) # Get all CSV files in the directory
    
    if not csv_files:
        print(f"❌ No CSV files found in '{data_path}'")
        return
    
    print(f"Found {len(csv_files)} CSV files")
    
    # Create source_data schema if it doesn't exist
    create_schema(engine, 'source_data')
    
    # Load each CSV into the database
    for csv_file in csv_files:
        table_name = Path(csv_file).stem  # Get filename without extension
        
        print(f"\nLoading {table_name}...")
        
        load_csv_to_db(engine, csv_file, table_name)

    # Verify loaded tables
    print("\n" + "="*50)
    print("Tables in source_data schema:")
    print("="*50)
    
    with engine.connect() as conn:
        result = conn.execute(sa.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'source_data'
            ORDER BY table_name;
        """))
        
        for row in result:
            print(f"  - {row[0]}")

if __name__ == "__main__":
    main()
