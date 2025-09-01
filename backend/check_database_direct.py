#!/usr/bin/env python3
"""
Check Database Direct
"""

import os
import asyncio
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_database_direct():
    """
    Check database directly for unified fields
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check the most recent questions
            result = conn.execute(text("""
                SELECT 
                    stem, category, right_answer, core_concepts, 
                    solution_method, quality_verified, concept_extraction_status,
                    created_at
                FROM questions 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            questions = result.fetchall()
            print(f"Found {len(questions)} recent questions")
            
            for i, q in enumerate(questions):
                print(f"\nQuestion {i+1}:")
                print(f"  Stem: {q.stem[:50] if q.stem else 'None'}...")
                print(f"  Category: {q.category}")
                print(f"  Right Answer: {q.right_answer}")
                print(f"  Core Concepts: {q.core_concepts}")
                print(f"  Solution Method: {q.solution_method}")
                print(f"  Quality Verified: {q.quality_verified}")
                print(f"  Extraction Status: {q.concept_extraction_status}")
                print(f"  Created: {q.created_at}")
                
                if q.category and q.core_concepts:
                    print(f"  ✅ UNIFIED FIELDS PRESENT IN DATABASE!")
                    return True
        
        return False
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_database_direct()
    print(f"\nDatabase Check: {'SUCCESS' if success else 'FAILED'}")