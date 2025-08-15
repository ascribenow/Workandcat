"""
Quick Data Migration Script - Handle data type issues
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text

load_dotenv()

# Configuration
SQLITE_DB_PATH = "/app/backend/cat_preparation.db"
POSTGRES_URL = "postgresql://postgres.itgusggwslnsbgonyicv:%24Sumedh_123@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

def clean_value(value, field_name, table_name):
    """Clean and convert values for PostgreSQL"""
    
    # Handle None strings
    if value == 'None':
        return None
    
    # Handle boolean fields
    if table_name == 'questions' and field_name in ['has_image', 'is_active']:
        if value in (0, '0', False, 'False', 'false'):
            return False
        elif value in (1, '1', True, 'True', 'true'):
            return True
        else:
            return None
    
    if table_name == 'users' and field_name == 'is_admin':
        return bool(value) if value is not None else False
        
    if table_name == 'attempts' and field_name in ['correct', 'hint_used']:
        return bool(value) if value is not None else False
        
    if table_name == 'pyq_ingestions' and field_name == 'ocr_required':
        return bool(value) if value is not None else False
        
    if table_name == 'pyq_questions' and field_name == 'confirmed':
        return bool(value) if value is not None else False
        
    if table_name == 'diagnostic_sets' and field_name == 'is_active':
        return bool(value) if value is not None else True
    
    # Handle JSON fields
    json_fields = {
        'questions': ['tags', 'top_matching_concepts', 'pattern_keywords'],
        'diagnostic_sets': ['meta'],
        'diagnostics': ['result', 'initial_capability'],
        'attempts': ['options'],
        'sessions': ['units'],
        'plan_units': ['generated_payload', 'actual_stats'],
        'pyq_files': ['file_metadata'],
        'pyq_questions': ['tags']
    }
    
    if table_name in json_fields and field_name in json_fields[table_name]:
        if value is None or value == 'None':
            return '{}' if field_name in ['meta', 'result', 'initial_capability', 'options', 'generated_payload', 'actual_stats', 'file_metadata'] else '[]'
        
        if isinstance(value, str):
            try:
                # Test if it's valid JSON
                parsed = json.loads(value)
                return value  # Return as-is if it's already valid JSON
            except:
                # If not valid JSON, create default
                return '{}' if field_name in ['meta', 'result', 'initial_capability', 'options', 'generated_payload', 'actual_stats', 'file_metadata'] else '[]'
        else:
            return json.dumps(value)
    
    return value

def migrate_table_simple(table_name):
    """Migrate table with cleaned data"""
    print(f"📋 Migrating {table_name}...")
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = sqlite_conn.cursor()
        
        # Get data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"   - No data")
            return True
        
        # Get columns
        column_names = [desc[0] for desc in cursor.description]
        
        # Connect to PostgreSQL
        pg_engine = create_engine(POSTGRES_URL)
        
        migrated = 0
        failed = 0
        
        with pg_engine.connect() as pg_conn:
            # Clear table first
            pg_conn.execute(text(f"DELETE FROM {table_name}"))
            pg_conn.commit()
            
            for row in rows:
                row_dict = {}
                
                # Clean each value
                for i, col in enumerate(column_names):
                    row_dict[col] = clean_value(row[i], col, table_name)
                
                # Create insert
                cols = ', '.join(column_names)
                placeholders = ', '.join([f":{col}" for col in column_names])
                sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                
                try:
                    pg_conn.execute(text(sql), row_dict)
                    pg_conn.commit()
                    migrated += 1
                except Exception as e:
                    failed += 1
                    if failed <= 3:  # Only show first few errors
                        print(f"   ⚠️ Failed row: {str(e)[:80]}...")
                        if table_name == 'questions':
                            print(f"      subcategory: {row_dict.get('subcategory')}")
                            print(f"      difficulty_band: {row_dict.get('difficulty_band')}")
        
        print(f"   ✅ {migrated} migrated, {failed} failed")
        sqlite_conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Table failed: {e}")
        return False

def main():
    print("🚀 Quick PostgreSQL Data Migration")
    print("=" * 40)
    
    # Test connection
    try:
        pg_engine = create_engine(POSTGRES_URL)
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL connected")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Migration order (dependencies first)
    tables = [
        'topics', 'users', 'diagnostic_sets', 'pyq_ingestions', 'pyq_files',
        'questions', 'question_options', 'pyq_papers', 'pyq_questions',
        'diagnostics', 'diagnostic_set_questions', 'mastery', 'plans',
        'plan_units', 'sessions', 'mastery_history', 'attempts'
    ]
    
    success_count = 0
    for table in tables:
        if migrate_table_simple(table):
            success_count += 1
    
    print(f"\n🎉 Migration completed: {success_count}/{len(tables)} tables")
    
    # Quick verification
    try:
        pg_engine = create_engine(POSTGRES_URL)
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM questions"))
            questions = result.fetchone()[0]
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            users = result.fetchone()[0]
            result = conn.execute(text("SELECT COUNT(*) FROM attempts"))  
            attempts = result.fetchone()[0]
            
            print(f"📊 Final counts: questions={questions}, users={users}, attempts={attempts}")
    except Exception as e:
        print(f"⚠️ Verification error: {e}")
    
    return True

if __name__ == "__main__":
    main()