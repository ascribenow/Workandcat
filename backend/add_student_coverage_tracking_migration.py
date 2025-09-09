#!/usr/bin/env python3
"""
Migration: Add Student Coverage Tracking Table
Creates table to track which subcategory::type combinations each student has seen in Phase A
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    """Create student_coverage_tracking table"""
    
    # Import database configuration
    from database import DATABASE_URL
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("🔧 Creating student_coverage_tracking table...")
        
        # Create the coverage tracking table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS student_coverage_tracking (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subcategory_type_combination VARCHAR(300) NOT NULL,
                sessions_seen INTEGER DEFAULT 1,
                first_seen_session INTEGER NOT NULL,
                last_seen_session INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                
                UNIQUE(user_id, subcategory_type_combination)
            )
        """))
        
        # Create indexes for performance
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_student_coverage_user_id 
            ON student_coverage_tracking(user_id)
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_student_coverage_combination 
            ON student_coverage_tracking(subcategory_type_combination)
        """))
        
        db.commit()
        print("✅ student_coverage_tracking table created successfully!")
        
        # Verify table creation
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'student_coverage_tracking'
        """))
        
        if result.fetchone():
            print("✅ Table verification successful")
            
            # Show table structure
            result = db.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'student_coverage_tracking'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            print("📊 Table structure:")
            for col in columns:
                print(f"   {col[0]} {col[1]} {'NOT NULL' if col[2] == 'NO' else 'NULL'}")
        else:
            print("❌ Table verification failed")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()