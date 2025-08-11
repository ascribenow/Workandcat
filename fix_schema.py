#!/usr/bin/env python3
"""
Fix database schema by increasing subcategory column length
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

async def main():
    print("🔧 Fixing database schema - increasing subcategory column length...")
    
    async with engine.begin() as connection:
        # Check current column length
        result = await connection.execute(text("""
            SELECT column_name, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'questions' AND column_name = 'subcategory'
        """))
        
        row = result.fetchone()
        if row:
            print(f"Current subcategory column length: {row.character_maximum_length}")
        
        # Alter questions table
        print("Altering questions.subcategory column...")
        await connection.execute(text(
            "ALTER TABLE questions ALTER COLUMN subcategory TYPE VARCHAR(100)"
        ))
        
        # Also alter pyq_questions table if it exists
        print("Altering pyq_questions.subcategory column...")
        await connection.execute(text(
            "ALTER TABLE pyq_questions ALTER COLUMN subcategory TYPE VARCHAR(100)"
        ))
        
        # Verify the change
        result = await connection.execute(text("""
            SELECT column_name, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'questions' AND column_name = 'subcategory'
        """))
        
        row = result.fetchone()
        if row:
            print(f"✅ New subcategory column length: {row.character_maximum_length}")
        
        print("✅ Database schema fixed successfully!")

if __name__ == "__main__":
    asyncio.run(main())