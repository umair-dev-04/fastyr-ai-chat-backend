#!/usr/bin/env python3
"""
Database setup script for PostgreSQL
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from models import Base
from database import SQLALCHEMY_DATABASE_URL

def create_database():
    """Create the database if it doesn't exist"""
    # Extract database name from URL
    db_name = os.getenv("POSTGRES_DB", "auth_app")
    
    # Create connection URL without database name
    base_url = SQLALCHEMY_DATABASE_URL.rsplit('/', 1)[0]
    engine = create_engine(f"{base_url}/postgres")
    
    try:
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if not result.fetchone():
                # Create database
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"Database '{db_name}' created successfully!")
            else:
                print(f"Database '{db_name}' already exists.")
    except OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")
        print("Please make sure PostgreSQL is running and credentials are correct.")
        sys.exit(1)

def create_tables():
    """Create all tables"""
    from database import engine
    
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)

def main():
    """Main setup function"""
    print("Setting up PostgreSQL database for FastAPI Authentication System...")
    
    # Create database
    create_database()
    
    # Create tables
    create_tables()
    
    print("Database setup completed successfully!")
    print("\nYou can now run the application with:")
    print("python main.py")

if __name__ == "__main__":
    main() 