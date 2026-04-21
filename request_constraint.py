from connect import get_db_engine, print_db_tables
# from connect import print_db_tables
import pandas as pd
import sqlalchemy as sa
import os

def index_table(engine, table_name, column_name, schema_name='source_data'):
    """Create an index on a specified column of a table."""
    index_name = f"{table_name}_{column_name}_idx"
    with engine.connect() as conn:
        conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {schema_name}.{table_name} ({column_name});"))
        conn.commit()
        print(f"✓ Index '{index_name}' created on {schema_name}.{table_name}({column_name})")

def constraint_table(engine, table_name, column_name, constraint_type='unique', schema_name='source_data'):
    """Add a constraint to a specified column of a table."""
    constraint_name = f"{table_name}_{column_name}_{constraint_type}_constraint"
    with engine.connect() as conn:
        if constraint_type == 'unique':
            conn.execute(sa.text(f"ALTER TABLE {schema_name}.{table_name} ADD CONSTRAINT {constraint_name} UNIQUE ({column_name});"))
        elif constraint_type == 'not_null':
            conn.execute(sa.text(f"ALTER TABLE {schema_name}.{table_name} ALTER COLUMN {column_name} SET NOT NULL;"))
        else:
            print(f"❌ Unsupported constraint type: {constraint_type}")
            return
        conn.commit()
        print(f"✓ Constraint '{constraint_name}' added to {schema_name}.{table_name}({column_name})")

if __name__ == "__main__":
    engine = get_db_engine()
    index_table(engine, 'olist_customers_dataset', 'customer_id')
    constraint_table(engine, 'olist_customers_dataset', 'customer_id', 'not_null')
    constraint_table(engine, 'olist_customers_dataset', 'customer_id', 'unique')

    index_table(engine, 'olist_products_dataset', 'product_id')
    constraint_table(engine, 'olist_products_dataset', 'product_id', 'not_null')
    constraint_table(engine, 'olist_products_dataset', 'product_id', 'unique')


    index_table(engine, 'olist_orders_dataset', 'order_id')
    constraint_table(engine, 'olist_orders_dataset', 'order_id', 'not_null')
    constraint_table(engine, 'olist_orders_dataset', 'order_id', 'unique')

    index_table(engine, 'olist_sellers_dataset', 'seller_id')
    constraint_table(engine, 'olist_sellers_dataset', 'seller_id', 'not_null')
    constraint_table(engine, 'olist_sellers_dataset', 'seller_id', 'unique')


    
    print_db_tables(engine)