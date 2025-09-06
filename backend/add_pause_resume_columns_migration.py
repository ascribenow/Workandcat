#!/usr/bin/env python3
"""
Add Pause/Resume Columns Migration
Adds pause and resume tracking columns to subscriptions table
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def add_pause_resume_columns():
    """Add pause/resume columns to subscriptions table"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not found")
        
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                print("🔧 Adding pause/resume columns to subscriptions table...")
                
                # Add paused_at column
                conn.execute(text("""
                    ALTER TABLE subscriptions 
                    ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP
                """))
                print("✅ Added paused_at column")
                
                # Add paused_days_remaining column
                conn.execute(text("""
                    ALTER TABLE subscriptions 
                    ADD COLUMN IF NOT EXISTS paused_days_remaining INTEGER
                """))
                print("✅ Added paused_days_remaining column")
                
                # Add pause_count column with default value
                conn.execute(text("""
                    ALTER TABLE subscriptions 
                    ADD COLUMN IF NOT EXISTS pause_count INTEGER DEFAULT 0
                """))
                print("✅ Added pause_count column")
                
                # Update existing records to have pause_count = 0
                result = conn.execute(text("""
                    UPDATE subscriptions 
                    SET pause_count = 0 
                    WHERE pause_count IS NULL
                """))
                print(f"✅ Updated {result.rowcount} existing records with pause_count = 0")
                
                trans.commit()
                print("🎉 Successfully added all pause/resume columns!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during migration: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

def verify_columns():
    """Verify that the new columns exist"""
    try:
        database_url = os.getenv('DATABASE_URL')
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'subscriptions' 
                AND column_name IN ('paused_at', 'paused_days_remaining', 'pause_count')
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            
            print("\n🔍 Verification - New columns in subscriptions table:")
            for column in columns:
                print(f"  - {column.column_name}: {column.data_type} (nullable: {column.is_nullable}, default: {column.column_default})")
            
            if len(columns) == 3:
                print("✅ All pause/resume columns successfully added!")
                return True
            else:
                print(f"❌ Expected 3 columns, found {len(columns)}")
                return False
                
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("PAUSE/RESUME COLUMNS MIGRATION")
    print("="*60)
    
    success = add_pause_resume_columns()
    
    if success:
        verify_columns()
        print("\n" + "="*60)
        print("Migration completed successfully!")
        print("The subscription system now supports pause/resume functionality.")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("Migration failed!")
        print("="*60)