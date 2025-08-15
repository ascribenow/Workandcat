"""
Final Migration Script - Handle foreign keys and data properly
"""

import os
import sys
import sqlite3
import json
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text

load_dotenv()

SQLITE_DB_PATH = "/app/backend/cat_preparation.db"
POSTGRES_URL = "postgresql://postgres.itgusggwslnsbgonyicv:%24Sumedh_123@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

def clean_value(value, field_name, table_name):
    """Clean and convert values for PostgreSQL"""
    
    # Handle None strings
    if value == 'None':
        return None
    
    # Handle boolean fields
    boolean_fields = {
        'questions': ['has_image', 'is_active'],
        'users': ['is_admin'],
        'attempts': ['correct', 'hint_used'],
        'pyq_ingestions': ['ocr_required'],
        'pyq_questions': ['confirmed'],
        'diagnostic_sets': ['is_active']
    }
    
    if table_name in boolean_fields and field_name in boolean_fields[table_name]:
        if value in (0, '0', False, 'False', 'false'):
            return False
        elif value in (1, '1', True, 'True', 'true'):
            return True
        else:
            return None if field_name != 'is_active' else True
    
    # Handle JSON fields - keep as string for PostgreSQL JSON columns
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
                json.loads(value)
                return value  # Return as-is if already valid JSON
            except:
                # Create default JSON
                return '{}' if field_name in ['meta', 'result', 'initial_capability', 'options', 'generated_payload', 'actual_stats', 'file_metadata'] else '[]'
        else:
            return json.dumps(value)
    
    return value

def main():
    print("🚀 Final PostgreSQL Migration")
    print("=" * 30)
    
    try:
        # Connect to databases
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        pg_engine = create_engine(POSTGRES_URL)
        
        # Test connections
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connections established")
        
        # Step 1: Clear all data in proper order (children first)
        print("🧹 Clearing PostgreSQL data...")
        clear_order = [
            'attempts', 'diagnostic_set_questions', 'question_options',
            'plan_units', 'sessions', 'mastery_history', 'mastery',
            'diagnostics', 'pyq_questions', 'pyq_papers', 'pyq_ingestions',
            'plans', 'diagnostic_sets', 'questions', 'users', 'topics', 'pyq_files'
        ]
        
        with pg_engine.connect() as pg_conn:
            for table in clear_order:
                try:
                    pg_conn.execute(text(f"DELETE FROM {table}"))
                    print(f"   Cleared {table}")
                except Exception as e:
                    print(f"   Warning: {table} - {e}")
            pg_conn.commit()
        
        # Step 2: Migrate data in dependency order (parents first)
        print("📋 Migrating data...")
        migration_order = [
            'topics', 'users', 'diagnostic_sets', 'pyq_ingestions', 'pyq_files',
            'questions', 'question_options', 'pyq_papers', 'pyq_questions',
            'diagnostics', 'diagnostic_set_questions', 'mastery', 'plans',
            'plan_units', 'sessions', 'mastery_history', 'attempts'
        ]
        
        total_migrated = 0
        
        for table_name in migration_order:
            cursor = sqlite_conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"   {table_name}: No data")
                continue
                
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            
            migrated = 0
            failed = 0
            
            with pg_engine.connect() as pg_conn:
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
                        migrated += 1
                    except Exception as e:
                        failed += 1
                        if failed <= 2:  # Show first couple errors
                            print(f"     Error: {str(e)[:60]}...")
                
                pg_conn.commit()
            
            print(f"   {table_name}: {migrated} migrated, {failed} failed")
            total_migrated += migrated
        
        sqlite_conn.close()
        
        # Step 3: Verify results
        print("🔍 Verification...")
        with pg_engine.connect() as conn:
            for table in ['topics', 'users', 'questions', 'attempts']:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                print(f"   {table}: {count} rows")
        
        print(f"\n🎉 Migration completed! Total rows: {total_migrated}")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    main()