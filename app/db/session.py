import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager

# Read database URL, default to a local SQLite database for development/testing
database_url = os.getenv("POSTGRES_URL", "sqlite:///./kharchasaathi.db")

# Force PostgreSQL connections to use the pure-python pg8000 driver
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+pg8000://", 1)

# SQLite-specific arguments (connect_args required for sqlite threading)
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(database_url, connect_args=connect_args, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

# Declarative Base for models
Base = declarative_base()

@contextmanager
def get_db():
    """
    Context manager for database sessions, ensuring sessions are closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
