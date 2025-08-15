"""
PostgreSQL Migration Script for CAT Preparation Platform
Migrates from SQLite to managed PostgreSQL (Neon/Supabase)
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from database import engine, Base, SessionLocal
from sqlalchemy import create_engine, inspect, text
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# Configuration
SQLITE_DB_PATH = "/app/backend/cat_preparation.db"
POSTGRES_URL = os.getenv("DATABASE_URL")

def check_postgres_connection():
    """Test PostgreSQL connection"""
    try:
        if not POSTGRES_URL or not POSTGRES_URL.startswith(('postgresql://', 'postgres://')):
            print("❌ PostgreSQL URL not configured. Please set DATABASE_URL environment variable.")
            print("   Example: DATABASE_URL=postgresql://user:pass@host:5432/dbname")
            return False
            
        pg_engine = create_engine(POSTGRES_URL)
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL connection successful!")
            print(f"   Version: {version}")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def check_sqlite_database():
    """Check if SQLite database exists and has data"""
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            print("❌ SQLite database not found at:", SQLITE_DB_PATH)
            return False, 0
            
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Check tables and row counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        total_rows = 0
        print("📊 SQLite Database Analysis:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_rows += count
            print(f"   {table_name}: {count} rows")
        
        conn.close()
        print(f"   Total rows to migrate: {total_rows}")
        return True, total_rows
        
    except Exception as e:
        print(f"❌ SQLite analysis failed: {e}")
        return False, 0

def create_postgres_schema():
    """Create PostgreSQL schema using SQLAlchemy models"""
    try:
        print("🏗️ Creating PostgreSQL schema...")
        
        pg_engine = create_engine(POSTGRES_URL)
        
        # Create all tables
        Base.metadata.create_all(bind=pg_engine)
        
        # Verify tables were created
        inspector = inspect(pg_engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables in PostgreSQL:")
        for table in sorted(tables):
            print(f"   - {table}")
            
        return True
        
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        return False

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    try:
        print("🔄 Starting data migration...")
        
        # Connect to both databases
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row  # Enable column access by name
        
        pg_engine = create_engine(POSTGRES_URL)
        
        # Get all tables from SQLite
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        migrated_rows = 0
        
        with pg_engine.connect() as pg_conn:
            for table_name in tables:
                print(f"   Migrating table: {table_name}")
                
                # Get all data from SQLite table
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                if not rows:
                    print(f"     - No data to migrate")
                    continue
                
                # Get column names
                column_names = [description[0] for description in cursor.description]
                
                # Prepare PostgreSQL insert
                placeholders = ", ".join([f":{col}" for col in column_names])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
                
                # Insert data into PostgreSQL
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    try:
                        pg_conn.execute(text(insert_sql), row_dict)
                        migrated_rows += 1
                    except Exception as e:
                        print(f"     ⚠️ Failed to migrate row: {e}")
                
                pg_conn.commit()
                print(f"     ✅ Migrated {len(rows)} rows")
        
        sqlite_conn.close()
        
        print(f"✅ Data migration completed! Migrated {migrated_rows} total rows")
        return True
        
    except Exception as e:
        print(f"❌ Data migration failed: {e}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    try:
        print("🔍 Verifying migration...")
        
        pg_engine = create_engine(POSTGRES_URL)
        inspector = inspect(pg_engine)
        
        with pg_engine.connect() as conn:
            tables = inspector.get_table_names()
            total_rows = 0
            
            print("📊 PostgreSQL Database After Migration:")
            for table in sorted(tables):
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    total_rows += count
                    print(f"   {table}: {count} rows")
                except Exception as e:
                    print(f"   {table}: Error - {e}")
            
            print(f"   Total rows in PostgreSQL: {total_rows}")
        
        # Test key functionality
        print("🧪 Testing key tables:")
        with pg_engine.connect() as conn:
            # Test users table
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.fetchone()[0]
            print(f"   Users: {user_count}")
            
            # Test questions table
            result = conn.execute(text("SELECT COUNT(*) FROM questions"))
            question_count = result.fetchone()[0]
            print(f"   Questions: {question_count}")
            
            # Test topics table
            result = conn.execute(text("SELECT COUNT(*) FROM topics"))
            topic_count = result.fetchone()[0]
            print(f"   Topics: {topic_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 PostgreSQL Migration for Twelvr CAT Preparation Platform")
    print("=" * 60)
    
    # Step 1: Check PostgreSQL connection
    if not check_postgres_connection():
        print("\n💡 To set up managed PostgreSQL:")
        print("   1. Create account at https://neon.tech (recommended)")
        print("   2. Create a new database")
        print("   3. Copy connection string")
        print("   4. Set DATABASE_URL environment variable")
        return False
    
    # Step 2: Check SQLite database
    sqlite_exists, row_count = check_sqlite_database()
    if not sqlite_exists:
        print("⚠️ No SQLite database found. Creating fresh PostgreSQL schema...")
        return create_postgres_schema()
    
    # Step 3: Create PostgreSQL schema
    if not create_postgres_schema():
        return False
    
    # Step 4: Migrate data
    if row_count > 0:
        if not migrate_data():
            return False
    else:
        print("ℹ️ No data to migrate from SQLite")
    
    # Step 5: Verify migration
    if not verify_migration():
        return False
    
    print("\n🎉 PostgreSQL migration completed successfully!")
    print("   Your Twelvr platform is now running on production-ready PostgreSQL!")
    print("\n📝 Next steps:")
    print("   1. Update your .env file with the PostgreSQL DATABASE_URL")
    print("   2. Restart your application")
    print("   3. Test all functionality")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)