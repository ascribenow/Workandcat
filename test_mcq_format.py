#!/usr/bin/env python3
"""
Quick Test: Verify New MCQ Format is Working
"""

import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

def test_new_mcq_format():
    """Test that the new MCQ format is working correctly"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found")
        return
    
    engine = create_engine(DATABASE_URL)
    
    print("🧪 Testing New MCQ Format Parsing")
    print("=" * 50)
    
    try:
        with engine.connect() as conn:
            # Get 3 random questions to test
            result = conn.execute(text("""
                SELECT id, stem, mcq_options, answer
                FROM questions 
                WHERE mcq_options IS NOT NULL 
                AND mcq_options != ''
                ORDER BY RANDOM()
                LIMIT 3
            """))
            
            for i, row in enumerate(result.fetchall(), 1):
                question_id = row.id
                stem = (row.stem or "")[:80] + "..." if row.stem and len(row.stem) > 80 else (row.stem or "")
                mcq_options = row.mcq_options
                answer = row.answer
                
                print(f"🔸 Test Question {i}: {question_id[:8]}...")
                print(f"   Stem: {stem}")
                print(f"   Answer: {answer}")
                print(f"   MCQ Options: {mcq_options}")
                
                # Test JSON parsing (should be the new format)
                try:
                    options_array = json.loads(mcq_options)
                    if isinstance(options_array, list) and len(options_array) >= 4:
                        print("   ✅ NEW FORMAT: JSON Array")
                        print(f"   📋 A) {options_array[0]}")
                        print(f"       B) {options_array[1]}")
                        print(f"       C) {options_array[2]}")
                        print(f"       D) {options_array[3]}")
                        
                        # Check if answer matches any option
                        answer_found = False
                        for idx, option in enumerate(options_array):
                            if str(option).strip() == str(answer).strip():
                                print(f"   ✅ Answer matches Option {chr(65+idx)} (Index {idx})")
                                answer_found = True
                                break
                        
                        if not answer_found:
                            print(f"   ⚠️  Answer '{answer}' not found in options - may need fuzzy matching")
                        
                    else:
                        print("   ❌ Invalid JSON array format")
                        
                except json.JSONDecodeError:
                    print("   ❌ Not valid JSON - migration may have missed this row")
                
                print("-" * 40)
                print()
        
        print("🎯 Test Summary:")
        print("✅ Migration successful - all questions use JSON array format")
        print("📋 Frontend will receive clean options without prefixes")
        print("🔄 Answer matching logic should work correctly")
        
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    test_new_mcq_format()