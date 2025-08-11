#!/usr/bin/env python3
"""
Database Schema Migration for v1.3 Feedback Compliance
Implements all schema enhancements as specified in feedback document
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database import get_database
from sqlalchemy import text

async def run_schema_migrations():
    """Execute all v1.3 schema migrations"""
    print("🔧 Running v1.3 Schema Migrations...")
    
    migrations = [
        {
            "name": "Add version_number to questions table",
            "sql": "ALTER TABLE questions ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;"
        },
        {
            "name": "Add preparedness_target to plans table", 
            "sql": "ALTER TABLE plans ADD COLUMN IF NOT EXISTS preparedness_target NUMERIC(5,2);"
        },
        {
            "name": "Add last_attempt_date to attempts table",
            "sql": "ALTER TABLE attempts ADD COLUMN IF NOT EXISTS last_attempt_date TIMESTAMP;"
        },
        {
            "name": "Create mastery_history table",
            "sql": """
                CREATE TABLE IF NOT EXISTS mastery_history (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id),
                    subcategory VARCHAR(100) NOT NULL,
                    mastery_score NUMERIC(3,2),
                    recorded_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """
        },
        {
            "name": "Create mastery_history indexes",
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_mastery_history_user_date ON mastery_history (user_id, recorded_date);
            """
        },
        {
            "name": "Create mastery_history subcategory index",
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_mastery_history_subcategory ON mastery_history (subcategory);
            """
        },
        {
            "name": "Create pyq_files table",
            "sql": """
                CREATE TABLE IF NOT EXISTS pyq_files (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    filename TEXT NOT NULL,
                    year INTEGER,
                    upload_date TIMESTAMP DEFAULT NOW(),
                    processing_status VARCHAR(20) DEFAULT 'pending',
                    file_size BIGINT,
                    storage_path TEXT,
                    metadata JSON
                );
            """
        },
        {
            "name": "Create pyq_files year index",
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_pyq_files_year ON pyq_files (year);
            """
        },
        {
            "name": "Create pyq_files status index", 
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_pyq_files_status ON pyq_files (processing_status);
            """
        },
        {
            "name": "Add PYQ frequency tracking to questions",
            "sql": """
                ALTER TABLE questions ADD COLUMN IF NOT EXISTS pyq_occurrences_last_10_years INTEGER DEFAULT 0;
                ALTER TABLE questions ADD COLUMN IF NOT EXISTS total_pyq_count INTEGER DEFAULT 0;
                ALTER TABLE questions ADD COLUMN IF NOT EXISTS frequency_score NUMERIC(3,2);
            """
        },
        {
            "name": "Add v1.3 formula fields to questions",
            "sql": """
                ALTER TABLE questions ADD COLUMN IF NOT EXISTS importance_score_v13 NUMERIC(5,2);
                ALTER TABLE questions ADD COLUMN IF NOT EXISTS learning_impact_v13 NUMERIC(5,2);
                ALTER TABLE questions ADD COLUMN IF NOT EXISTS difficulty_score_v13 NUMERIC(3,2);
            """
        },
        {
            "name": "Update attempts table for spacing rules",
            "sql": """
                ALTER TABLE attempts ADD COLUMN IF NOT EXISTS incorrect_count INTEGER DEFAULT 0;
                CREATE INDEX IF NOT EXISTS idx_attempts_spacing ON attempts (user_id, question_id, last_attempt_date);
            """
        }
    ]
    
    try:
        async for db in get_database():
            for migration in migrations:
                print(f"   🔄 {migration['name']}...")
                
                # Execute migration SQL
                await db.execute(text(migration['sql']))
                
                print(f"   ✅ {migration['name']} - COMPLETE")
            
            await db.commit()
            print(f"\n✅ All {len(migrations)} migrations completed successfully!")
            
            # Verify schema changes
            await verify_schema_changes(db)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_schema_changes(db):
    """Verify that all schema changes were applied correctly"""
    print("\n🔍 Verifying schema changes...")
    
    verifications = [
        {
            "name": "questions.version_number",
            "sql": "SELECT column_name FROM information_schema.columns WHERE table_name = 'questions' AND column_name = 'version_number';"
        },
        {
            "name": "plans.preparedness_target", 
            "sql": "SELECT column_name FROM information_schema.columns WHERE table_name = 'plans' AND column_name = 'preparedness_target';"
        },
        {
            "name": "attempts.last_attempt_date",
            "sql": "SELECT column_name FROM information_schema.columns WHERE table_name = 'attempts' AND column_name = 'last_attempt_date';"
        },
        {
            "name": "mastery_history table",
            "sql": "SELECT table_name FROM information_schema.tables WHERE table_name = 'mastery_history';"
        },
        {
            "name": "pyq_files table",
            "sql": "SELECT table_name FROM information_schema.tables WHERE table_name = 'pyq_files';"
        }
    ]
    
    for verification in verifications:
        result = await db.execute(text(verification['sql']))
        exists = result.fetchone() is not None
        
        if exists:
            print(f"   ✅ {verification['name']} - EXISTS")
        else:
            print(f"   ❌ {verification['name']} - MISSING")


async def main():
    """Main migration function"""
    print("🚀 V1.3 DATABASE SCHEMA MIGRATION")
    print("=" * 50)
    print("Implementing feedback requirements:")
    print("1. Question versioning")
    print("2. Mastery history retention") 
    print("3. Preparedness ambition storage")
    print("4. Attempt spacing metadata")
    print("5. PYQ files tracking")
    print("=" * 50)
    
    success = await run_schema_migrations()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SCHEMA MIGRATION COMPLETE!")
        print("✅ Database ready for v1.3 compliance")
    else:
        print("⚠️  Schema migration encountered issues")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)