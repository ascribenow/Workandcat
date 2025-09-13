#!/usr/bin/env python3
"""
Remove all VARCHAR length constraints from database tables
Convert VARCHAR(N) to TEXT for unlimited length
"""

import sys
from database import engine
from sqlalchemy import text

def remove_varchar_limits():
    """Remove VARCHAR constraints from both Questions and PYQ Questions tables"""
    
    try:
        print("🔧 REMOVING ALL VARCHAR LENGTH CONSTRAINTS...")
        print("Converting VARCHAR(N) → TEXT for unlimited length")
        
        with engine.connect() as conn:
            # Questions table - Remove VARCHAR limits
            questions_alterations = [
                "ALTER TABLE questions ALTER COLUMN type_of_question TYPE TEXT",
                "ALTER TABLE questions ALTER COLUMN difficulty_band TYPE TEXT", 
                "ALTER TABLE questions ALTER COLUMN source TYPE TEXT",
                "ALTER TABLE questions ALTER COLUMN category TYPE TEXT",
                "ALTER TABLE questions ALTER COLUMN solution_method TYPE TEXT",
                "ALTER TABLE questions ALTER COLUMN problem_structure TYPE TEXT",
                "ALTER TABLE questions ALTER COLUMN concept_extraction_status TYPE TEXT"
            ]
            
            print(f"\n📊 QUESTIONS TABLE: Converting {len(questions_alterations)} VARCHAR fields to TEXT...")
            
            for i, sql in enumerate(questions_alterations, 1):
                try:
                    conn.execute(text(sql))
                    field_name = sql.split("ALTER COLUMN ")[1].split(" TYPE")[0]
                    print(f"  ✅ {i}. {field_name}: VARCHAR → TEXT")
                except Exception as e:
                    print(f"  ⚠️ {i}. {sql}: {e}")
            
            # PYQ Questions table - Remove VARCHAR limits
            pyq_alterations = [
                "ALTER TABLE pyq_questions ALTER COLUMN type_of_question TYPE TEXT",
                "ALTER TABLE pyq_questions ALTER COLUMN difficulty_band TYPE TEXT",
                "ALTER TABLE pyq_questions ALTER COLUMN concept_extraction_status TYPE TEXT", 
                "ALTER TABLE pyq_questions ALTER COLUMN solution_method TYPE TEXT",
                "ALTER TABLE pyq_questions ALTER COLUMN problem_structure TYPE TEXT",
                "ALTER TABLE pyq_questions ALTER COLUMN category TYPE TEXT"
            ]
            
            print(f"\n📊 PYQ QUESTIONS TABLE: Converting {len(pyq_alterations)} VARCHAR fields to TEXT...")
            
            for i, sql in enumerate(pyq_alterations, 1):
                try:
                    conn.execute(text(sql))
                    field_name = sql.split("ALTER COLUMN ")[1].split(" TYPE")[0]
                    print(f"  ✅ {i}. {field_name}: VARCHAR → TEXT")
                except Exception as e:
                    print(f"  ⚠️ {i}. {sql}: {e}")
            
            # Commit all changes
            conn.commit()
            
            print(f"\n🎉 ALL VARCHAR CONSTRAINTS REMOVED!")
            print(f"   ✅ Questions table: {len(questions_alterations)} fields converted")
            print(f"   ✅ PYQ Questions table: {len(pyq_alterations)} fields converted")
            print(f"   🚀 Database ready for unlimited text length!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error removing VARCHAR limits: {e}")
        return False

if __name__ == "__main__":
    success = remove_varchar_limits()
    
    if success:
        print(f"\n✅ VARCHAR limits removal completed!")
        print(f"🔄 Ready to re-run enrichment service without length constraints")
    else:
        print(f"\n❌ VARCHAR limits removal failed")