#!/usr/bin/env python3
"""
Fix PYQ Column Lengths
Expand column lengths to accommodate sophisticated enrichment data
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def fix_column_lengths():
    """Fix column length constraints in pyq_questions table"""
    try:
        database_url = os.getenv('DATABASE_URL')
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("🔧 Expanding column lengths for sophisticated enrichment...")
                
                # Expand problem_structure from 50 to 200 characters
                conn.execute(text("""
                    ALTER TABLE pyq_questions 
                    ALTER COLUMN problem_structure TYPE VARCHAR(200)
                """))
                print("✅ Expanded problem_structure to 200 characters")
                
                # Expand solution_method from 100 to 200 characters for more detailed methods
                conn.execute(text("""
                    ALTER TABLE pyq_questions 
                    ALTER COLUMN solution_method TYPE VARCHAR(200)
                """))
                print("✅ Expanded solution_method to 200 characters")
                
                # Expand concept_extraction_status from 50 to 100 characters
                conn.execute(text("""
                    ALTER TABLE pyq_questions 
                    ALTER COLUMN concept_extraction_status TYPE VARCHAR(100)
                """))
                print("✅ Expanded concept_extraction_status to 100 characters")
                
                # Expand type_of_question from 150 to 250 characters for very specific types
                conn.execute(text("""
                    ALTER TABLE pyq_questions 
                    ALTER COLUMN type_of_question TYPE VARCHAR(250)
                """))
                print("✅ Expanded type_of_question to 250 characters")
                
                # Commit changes
                trans.commit()
                print("🎉 All column expansions completed successfully!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during column expansion: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Failed to fix column lengths: {e}")

if __name__ == "__main__":
    fix_column_lengths()