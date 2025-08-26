#!/usr/bin/env python3
"""
Migration script to add 'right_answer' column to the questions table
"""

import sys
import os
sys.path.append('/app/backend')

from sqlalchemy import text, create_engine
from database import engine, SessionLocal
import traceback

def add_right_answer_column():
    """Add right_answer column to questions table"""
    
    print("🔧 Starting migration to add 'right_answer' column...")
    
    try:
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'questions' 
                AND column_name = 'right_answer'
            """))
            
            if result.fetchone():
                print("✅ Column 'right_answer' already exists in questions table.")
                return True
            
            # Add the new column
            print("➕ Adding 'right_answer' column to questions table...")
            connection.execute(text("""
                ALTER TABLE questions 
                ADD COLUMN right_answer TEXT
            """))
            
            connection.commit()
            print("✅ Successfully added 'right_answer' column to questions table.")
            
            # Verify the column was added
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'questions' 
                AND column_name = 'right_answer'
            """))
            
            if result.fetchone():
                print("✅ Verification successful: 'right_answer' column exists.")
                return True
            else:
                print("❌ Verification failed: 'right_answer' column not found after creation.")
                return False
                
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def show_table_structure():
    """Show the current questions table structure"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'questions'
                ORDER BY ordinal_position
            """))
            
            print("\n📋 Current questions table structure:")
            for row in result:
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                print(f"  - {row[0]}: {row[1]} ({nullable})")
                
    except Exception as e:
        print(f"❌ Error showing table structure: {str(e)}")

if __name__ == "__main__":
    print("🚀 Questions Table Migration: Adding 'right_answer' column")
    print("=" * 60)
    
    # Show current structure
    print("📋 Current table structure (before migration):")
    show_table_structure()
    
    print("\n" + "=" * 60)
    
    # Perform migration
    success = add_right_answer_column()
    
    print("\n" + "=" * 60)
    
    # Show updated structure
    if success:
        print("📋 Updated table structure (after migration):")
        show_table_structure()
        print(f"\n🎉 Migration completed successfully!")
        print(f"💡 The 'right_answer' column is now available for use in your Twelvr application.")
    else:
        print("❌ Migration failed. Please check the error messages above.")
        sys.exit(1)