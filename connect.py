import sqlalchemy as sa
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def get_db_engine():
    """Create and return a SQLAlchemy engine using environment variables."""
    try:
        engine = sa.create_engine(
            f'postgresql://{os.getenv("DATABASE_USERNAME")}:{os.getenv("DATABASE_PASSWORD")}@{os.getenv("DATABASE_HOST")}:{os.getenv("DATABASE_PORT")}/{os.getenv("DATABASE_NAME")}'
        )
        print("✓ Database engine created successfully")
        return engine
    except Exception as e:
        print(f"❌ Error creating database engine: {str(e)}")
        raise

def print_db_tables(engine, schema_name='source_data'):
    """Print the list of tables in the specified schema."""
    with engine.connect() as conn:
        result = conn.execute(sa.text(f"""
                            SELECT table_name 
                            FROM information_schema.tables
                            WHERE table_schema = '{schema_name}';"""))
        tables = result.fetchall()
        print(f"\n✓ Tables in '{schema_name}' schema:")
        for table in tables:
            print(f"  - {table[0]}")