"""
Fixed Data Migration Script for PostgreSQL
Handles boolean conversion and complete data migration from SQLite to PostgreSQL
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError

load_dotenv()

# Configuration
SQLITE_DB_PATH = "/app/backend/cat_preparation.db"
POSTGRES_URL = os.getenv("DATABASE_URL")

# Tables and their boolean fields
BOOLEAN_FIELDS = {
    'topics': [],
    'users': ['is_admin'],
    'questions': ['has_image', 'is_active'],
    'question_options': [],
    'pyq_ingestions': ['ocr_required'],
    'pyq_papers': [],
    'pyq_questions': ['confirmed'],
    'diagnostic_sets': ['is_active'],
    'diagnostic_set_questions': [],
    'diagnostics': [],
    'attempts': ['correct', 'hint_used'],
    'mastery': [],
    'plans': [],
    'plan_units': [],
    'sessions': [],
    'mastery_history': [],
    'pyq_files': [],
}

def convert_boolean_fields(row_dict, table_name):
    """Convert 0/1 integer values to proper boolean values for PostgreSQL"""
    if table_name in BOOLEAN_FIELDS:
        for field in BOOLEAN_FIELDS[table_name]:
            if field in row_dict and row_dict[field] is not None:
                # Convert 0/1 to False/True
                row_dict[field] = bool(row_dict[field])
    return row_dict

def convert_json_fields(row_dict, table_name):
    """Convert JSON string fields to proper objects"""
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
    
    if table_name in json_fields:
        for field in json_fields[table_name]:
            if field in row_dict and row_dict[field] is not None:
                try:
                    # If it's a string, try to parse as JSON
                    if isinstance(row_dict[field], str):
                        # Handle empty strings and arrays
                        if row_dict[field] == '[]':
                            row_dict[field] = []
                        elif row_dict[field] == '{}':
                            row_dict[field] = {}
                        else:
                            row_dict[field] = json.loads(row_dict[field])
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, keep as string or set default
                    if field in ['tags', 'top_matching_concepts', 'pattern_keywords']:
                        row_dict[field] = []
                    else:
                        row_dict[field] = {}
    return row_dict

def migrate_table_data(table_name, sqlite_conn, pg_engine):
    """Migrate data from a specific table with proper type conversion"""
    print(f"   📋 Migrating table: {table_name}")
    
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"     - No data to migrate")
            return True
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        migrated_count = 0
        skipped_count = 0
        
        with pg_engine.connect() as pg_conn:
            # Clear existing data first to avoid duplicates
            pg_conn.execute(text(f"DELETE FROM {table_name}"))
            pg_conn.commit()
            
            for row in rows:
                row_dict = dict(zip(column_names, row))
                
                # Apply type conversions
                row_dict = convert_boolean_fields(row_dict, table_name)
                row_dict = convert_json_fields(row_dict, table_name)
                
                # Prepare insert statement
                placeholders = ", ".join([f":{col}" for col in column_names])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
                
                try:
                    pg_conn.execute(text(insert_sql), row_dict)
                    migrated_count += 1
                except Exception as e:
                    # Provide more detailed error information
                    error_msg = str(e)
                    if table_name == 'questions':
                        print(f"     ⚠️ Question row failed - ID: {row_dict.get('id', 'unknown')[:8]}...")
                        print(f"       Subcategory: '{row_dict.get('subcategory', '')}'")
                        print(f"       Error: {error_msg[:150]}...")
                    elif table_name == 'attempts':
                        print(f"     ⚠️ Attempt row failed - ID: {row_dict.get('id', 'unknown')[:8]}...")
                        print(f"       Options type: {type(row_dict.get('options', ''))}")
                        print(f"       Error: {error_msg[:100]}...")
                    else:
                        print(f"     ⚠️ Failed to migrate row: {error_msg[:100]}...")
                    skipped_count += 1
                    
                    # Rollback failed transaction and continue
                    try:
                        pg_conn.rollback()
                    except:
                        pass
            
            # Commit all changes for this table
            pg_conn.commit()
        
        print(f"     ✅ Migrated {migrated_count} rows, skipped {skipped_count}")
        return True
        
    except Exception as e:
        print(f"     ❌ Table migration failed: {e}")
        return False

def clear_existing_data():
    """Clear existing data from PostgreSQL to ensure clean migration"""
    print("🧹 Clearing existing data from PostgreSQL...")
    
    try:
        pg_engine = create_engine(POSTGRES_URL)
        
        # Order tables for foreign key dependencies (children first)
        tables_to_clear = [
            'attempts', 'diagnostic_set_questions', 'question_options', 
            'plan_units', 'sessions', 'mastery_history', 'mastery',
            'diagnostics', 'pyq_questions', 'pyq_papers', 'pyq_ingestions',
            'plans', 'diagnostic_sets', 'questions', 'users', 'topics', 'pyq_files'
        ]
        
        with pg_engine.connect() as conn:
            for table in tables_to_clear:
                try:
                    conn.execute(text(f"DELETE FROM {table}"))
                    print(f"   - Cleared {table}")
                except Exception as e:
                    print(f"   - Failed to clear {table}: {e}")
            
            conn.commit()
        
        print("✅ Existing data cleared")
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear existing data: {e}")
        return False

def migrate_all_data():
    """Migrate all data from SQLite to PostgreSQL with proper ordering"""
    print("🔄 Starting complete data migration...")
    
    try:
        # Connect to databases
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        pg_engine = create_engine(POSTGRES_URL)
        
        # Get tables from SQLite in dependency order (parents first)
        migration_order = [
            'topics',           # No dependencies
            'users',           # No dependencies  
            'diagnostic_sets', # No dependencies
            'pyq_ingestions',  # No dependencies
            'pyq_files',       # No dependencies
            'questions',       # Depends on topics
            'question_options', # Depends on questions
            'pyq_papers',      # Depends on pyq_ingestions
            'pyq_questions',   # Depends on pyq_papers and topics
            'diagnostics',     # Depends on users and diagnostic_sets
            'diagnostic_set_questions', # Depends on diagnostic_sets and questions
            'mastery',         # Depends on users and topics
            'plans',           # Depends on users
            'plan_units',      # Depends on plans and topics
            'sessions',        # Depends on users
            'mastery_history', # Depends on users
            'attempts',        # Depends on users and questions
        ]
        
        total_migrated = 0
        successful_tables = 0
        
        for table_name in migration_order:
            if migrate_table_data(table_name, sqlite_conn, pg_engine):
                successful_tables += 1
                
                # Count migrated rows
                with pg_engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    total_migrated += count
        
        sqlite_conn.close()
        
        print(f"\n✅ Data migration completed!")
        print(f"   Successfully migrated {successful_tables}/{len(migration_order)} tables")
        print(f"   Total rows migrated: {total_migrated}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data migration failed: {e}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    print("🔍 Verifying migration results...")
    
    try:
        # Compare row counts
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        pg_engine = create_engine(POSTGRES_URL)
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📊 Migration Verification:")
        mismatches = 0
        
        for table in sorted(tables):
            try:
                # Get SQLite count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = cursor.fetchone()[0]
                
                # Get PostgreSQL count
                with pg_engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    pg_count = result.fetchone()[0]
                
                status = "✅" if sqlite_count == pg_count else "❌"
                if sqlite_count != pg_count:
                    mismatches += 1
                
                print(f"   {status} {table}: SQLite({sqlite_count}) → PostgreSQL({pg_count})")
                
            except Exception as e:
                print(f"   ❌ {table}: Error - {e}")
                mismatches += 1
        
        sqlite_conn.close()
        
        if mismatches == 0:
            print("🎉 All tables migrated successfully!")
            return True
        else:
            print(f"⚠️ {mismatches} table(s) have mismatched row counts")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def test_postgresql_functionality():
    """Test key PostgreSQL functionality after migration"""
    print("🧪 Testing PostgreSQL functionality...")
    
    try:
        pg_engine = create_engine(POSTGRES_URL)
        
        with pg_engine.connect() as conn:
            # Test 1: Check users table with boolean field
            result = conn.execute(text("SELECT email, is_admin FROM users WHERE is_admin = true LIMIT 1"))
            admin_user = result.fetchone()
            if admin_user:
                print(f"   ✅ Admin user found: {admin_user[0]}")
            else:
                print("   ⚠️ No admin users found")
            
            # Test 2: Check questions with boolean fields
            result = conn.execute(text("SELECT COUNT(*) FROM questions WHERE is_active = true"))
            active_questions = result.fetchone()[0]
            print(f"   ✅ Active questions: {active_questions}")
            
            # Test 3: Check JSON field
            result = conn.execute(text("SELECT tags FROM questions WHERE tags IS NOT NULL LIMIT 1"))
            question_with_tags = result.fetchone()
            if question_with_tags:
                print(f"   ✅ JSON field working: {type(question_with_tags[0])}")
            
            # Test 4: Check relationships
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM questions q 
                JOIN topics t ON q.topic_id = t.id
            """))
            questions_with_topics = result.fetchone()[0]
            print(f"   ✅ Question-Topic relationships: {questions_with_topics}")
        
        print("✅ PostgreSQL functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 Fixed PostgreSQL Data Migration for Twelvr")
    print("=" * 50)
    
    # Check if SQLite database exists
    if not os.path.exists(SQLITE_DB_PATH):
        print("❌ SQLite database not found")
        return False
    
    # Check PostgreSQL connection
    try:
        pg_engine = create_engine(POSTGRES_URL)
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print(f"✅ PostgreSQL connected: {result.fetchone()[0].split(',')[0]}")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False
    
    # Step 1: Clear existing data
    if not clear_existing_data():
        return False
    
    # Step 2: Migrate all data with proper type conversion
    if not migrate_all_data():
        return False
    
    # Step 3: Verify migration
    if not verify_migration():
        return False
    
    # Step 4: Test functionality
    if not test_postgresql_functionality():
        return False
    
    print("\n🎉 Complete PostgreSQL migration successful!")
    print("   Your Twelvr platform is now fully migrated to PostgreSQL!")
    print("\n📝 Next steps:")
    print("   1. Restart your backend services")
    print("   2. Test authentication and sessions")
    print("   3. Verify all functionality works correctly")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)