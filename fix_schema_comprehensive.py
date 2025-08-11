#!/usr/bin/env python3
"""
Comprehensive database schema fix - increase all VARCHAR length constraints
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database import engine
from sqlalchemy import text

async def fix_all_varchar_constraints():
    """Fix all VARCHAR constraints that might be too small"""
    print("🔧 Comprehensive Schema Fix - All VARCHAR Constraints...")
    
    async with engine.begin() as connection:
        # Get all VARCHAR columns that are too short
        print("   📊 Checking all VARCHAR columns...")
        result = await connection.execute(text("""
            SELECT table_name, column_name, character_maximum_length, data_type
            FROM information_schema.columns 
            WHERE table_name IN ('questions', 'pyq_questions', 'topics') 
            AND data_type = 'character varying'
            AND character_maximum_length < 100
            ORDER BY table_name, column_name
        """))
        
        short_columns = result.fetchall()
        print(f"   Found {len(short_columns)} columns with length < 100:")
        
        for table_name, column_name, max_length, data_type in short_columns:
            print(f"      {table_name}.{column_name}: {data_type}({max_length})")
            
            # Determine appropriate new length
            if column_name in ['subcategory', 'type_of_question']:
                new_length = 150
            elif column_name in ['name', 'difficulty_band', 'frequency_band', 'importance_level', 'importance_band', 'learning_impact_band']:
                new_length = 100
            elif column_name in ['slug', 'section', 'source', 'question_type']:
                new_length = 100
            else:
                new_length = 100  # Default
            
            print(f"         Updating to VARCHAR({new_length})...")
            await connection.execute(text(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN {column_name} TYPE VARCHAR({new_length})
            """))
            print(f"         ✅ {table_name}.{column_name} updated")
        
        # Verify all changes
        print("\n   🔍 Verifying all changes...")
        result = await connection.execute(text("""
            SELECT table_name, column_name, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name IN ('questions', 'pyq_questions', 'topics') 
            AND data_type = 'character varying'
            ORDER BY table_name, column_name
        """))
        
        print("   Final schema:")
        all_columns = result.fetchall()
        for table_name, column_name, max_length in all_columns:
            status = "✅" if max_length >= 100 else "⚠️"
            print(f"      {table_name}.{column_name}: VARCHAR({max_length}) {status}")
        
        print("\n✅ All VARCHAR constraints fixed!")

async def main():
    try:
        await fix_all_varchar_constraints()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())