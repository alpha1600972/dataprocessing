#!/usr/bin/env python3
"""
Script to check database structure for olist_customers_dataset and olist_orders_dataset tables
"""
import sqlalchemy as sa
from connect import get_db_engine
import pandas as pd

def get_table_columns(engine, schema_name, table_name):
    """Get column details for a specific table."""
    query = f"""
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
    ORDER BY ordinal_position;
    """
    with engine.connect() as conn:
        result = conn.execute(sa.text(query))
        return result.fetchall()

def get_primary_keys(engine, schema_name, table_name):
    """Get primary key columns for a specific table."""
    query = f"""
    SELECT 
        a.attname as column_name
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    JOIN pg_class t ON t.oid = i.indrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = '{schema_name}' AND t.relname = '{table_name}' AND i.indisprimary;
    """
    with engine.connect() as conn:
        result = conn.execute(sa.text(query))
        return result.fetchall()

def get_foreign_keys(engine, schema_name, table_name):
    """Get foreign key columns for a specific table."""
    query = f"""
    SELECT 
        tc.constraint_name,
        kcu.column_name,
        ccu.table_name AS referenced_table_name,
        ccu.column_name AS referenced_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = '{schema_name}'
        AND tc.table_name = '{table_name}';
    """
    with engine.connect() as conn:
        result = conn.execute(sa.text(query))
        return result.fetchall()

def main():
    try:
        # Get database engine
        engine = get_db_engine()
        
        schema = 'source_data'
        tables = ['olist_customers_dataset', 'olist_orders_dataset']
        
        print("\n" + "="*80)
        print("DATABASE STRUCTURE ANALYSIS")
        print("="*80)
        
        for table_name in tables:
            print(f"\n{'='*80}")
            print(f"TABLE: {table_name}")
            print(f"{'='*80}")
            
            # Get columns
            columns = get_table_columns(engine, schema, table_name)
            print(f"\nColumns in {table_name}:")
            print("-" * 80)
            print(f"{'Column Name':<35} {'Data Type':<20} {'Nullable':<12} {'Default':<15}")
            print("-" * 80)
            for col in columns:
                col_name, data_type, is_nullable, default = col
                nullable = "YES" if is_nullable == "YES" else "NO"
                default_val = default if default else "None"
                print(f"{col_name:<35} {data_type:<20} {nullable:<12} {default_val:<15}")
            
            # Get primary keys
            pks = get_primary_keys(engine, schema, table_name)
            print(f"\nPrimary Keys in {table_name}:")
            print("-" * 80)
            if pks:
                for pk in pks:
                    print(f"  • {pk[0]}")
            else:
                print("  No primary keys found")
            
            # Get foreign keys
            fks = get_foreign_keys(engine, schema, table_name)
            print(f"\nForeign Keys in {table_name}:")
            print("-" * 80)
            if fks:
                for fk in fks:
                    constraint_name, col_name, ref_table, ref_col = fk
                    print(f"  • {col_name} → {ref_table}.{ref_col}")
                    print(f"    (Constraint: {constraint_name})")
            else:
                print("  No foreign keys found")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        # Summary for olist_customers_dataset
        print("\nolist_customers_dataset:")
        pks = get_primary_keys(engine, schema, 'olist_customers_dataset')
        if pks:
            pk_col = pks[0][0]
            columns = get_table_columns(engine, schema, 'olist_customers_dataset')
            for col in columns:
                if col[0] == pk_col:
                    print(f"  Primary Key: {pk_col} ({col[1]})")
        
        # Summary for olist_orders_dataset
        print("\nolist_orders_dataset:")
        fks = get_foreign_keys(engine, schema, 'olist_orders_dataset')
        if fks:
            for fk in fks:
                constraint_name, col_name, ref_table, ref_col = fk
                if ref_table == 'olist_customers_dataset':
                    # Get the data type
                    columns = get_table_columns(engine, schema, 'olist_orders_dataset')
                    for col in columns:
                        if col[0] == col_name:
                            print(f"  Foreign Key to customers: {col_name} ({col[1]}) → {ref_table}.{ref_col}")
        
        print("\n" + "="*80)
        engine.dispose()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
