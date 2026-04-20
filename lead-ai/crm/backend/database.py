"""
Database configuration and setup
Centralized database connection - Uses Supabase REST API when configured, SQLite as fallback
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_database_url():
    """
    Get the database URL.
    
    Priority:
    1. DATABASE_URL environment variable (direct PostgreSQL connection string)
    2. Auto-build from SUPABASE_URL + SUPABASE_DB_PASSWORD
    3. SQLite fallback for local development only
    """
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Render provides postgres:// but SQLAlchemy needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        print(f"✅ Using DATABASE_URL (PostgreSQL)")
        return database_url
    
    # Auto-build from Supabase URL + DB password
    supabase_db_password = os.getenv("SUPABASE_DB_PASSWORD")
    if SUPABASE_URL and supabase_db_password:
        # Extract project ref from https://goeybffajdqcwztazfmk.supabase.co
        project_ref = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
        db_url = f"postgresql://postgres.{project_ref}:{supabase_db_password}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        print(f"✅ Using Supabase PostgreSQL (auto-built from SUPABASE_URL)")
        return db_url
    
    # Fallback to SQLite for local development
    print("⚠️  No DATABASE_URL or SUPABASE_DB_PASSWORD set - using SQLite (ephemeral, data lost on restart)")
    return "sqlite:///./crm_database.db"

SQLALCHEMY_DATABASE_URL = get_database_url()

# Create engine with appropriate settings
if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    # PostgreSQL (Supabase) configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False
    )
else:
    # SQLite configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
