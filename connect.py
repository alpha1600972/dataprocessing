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