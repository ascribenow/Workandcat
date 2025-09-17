#!/usr/bin/env python3
"""
MCQ Options Cleanup Script - Test Phase
Converts mcq_options field to standardized JSON array format
"""

import os
import json
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def parse_existing_mcq_options(mcq_options):
    """
    Parse mcq_options from various existing formats and return clean 4-value array
    Preserves A→B→C→D order
    """
    if not mcq_options:
        return ["Option A", "Option B", "Option C", "Option D"]
    
    try:
        # Case 1: Already JSON format
        if isinstance(mcq_options, dict):
            return extract_ordered_options_from_dict(mcq_options)
        elif isinstance(mcq_options, list) and len(mcq_options) >= 4:
            return mcq_options[:4]  # Take first 4
        elif isinstance(mcq_options, str):
            # Try JSON parsing first
            try:
                parsed = json.loads(mcq_options)
                if isinstance(parsed, dict):
                    return extract_ordered_options_from_dict(parsed)
                elif isinstance(parsed, list) and len(parsed) >= 4:
                    return parsed[:4]
            except json.JSONDecodeError:
                pass
            
            # Case 2: Text format with prefixes like "(A) 20%\n(B) 30%\n(C) 35.2%\n(D) 40%"
            return parse_text_mcq_options(mcq_options)
        else:
            return ["Option A", "Option B", "Option C", "Option D"]
            
    except Exception as e:
        print(f"⚠️  Error parsing mcq_options: {e}")
        return ["Option A", "Option B", "Option C", "Option D"]

def extract_ordered_options_from_dict(mcq_dict):
    """Extract options from dict in A→B→C→D order"""
    options = []
    
    # Try different key formats: 'a'/'A', 'option_a', etc.
    for key_prefix in ['', 'option_']:
        for letter in ['a', 'b', 'c', 'd']:
            key_variants = [
                f"{key_prefix}{letter}",
                f"{key_prefix}{letter.upper()}",
            ]
            
            found_value = None
            for key in key_variants:
                if key in mcq_dict:
                    found_value = clean_option_text(mcq_dict[key])
                    break
            
            if found_value:
                options.append(found_value)
            else:
                options.append(f"Option {letter.upper()}")
    
    return options[:4]  # Ensure exactly 4 options

def parse_text_mcq_options(text_options):
    """Parse text format like '(A) 20%\\n(B) 30%\\n(C) 35.2%\\n(D) 40%'"""
    options = ["Option A", "Option B", "Option C", "Option D"]
    
    try:
        # Split by lines and parse each option
        lines = text_options.strip().split('\n')
        
        option_map = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Match patterns like "(A) 20%" or "A) 30%" or "A. text"
            if line.startswith('(A)') or line.startswith('A)') or line.startswith('A.'):
                option_map['a'] = extract_option_content(line)
            elif line.startswith('(B)') or line.startswith('B)') or line.startswith('B.'):
                option_map['b'] = extract_option_content(line)
            elif line.startswith('(C)') or line.startswith('C)') or line.startswith('C.'):
                option_map['c'] = extract_option_content(line)
            elif line.startswith('(D)') or line.startswith('D)') or line.startswith('D.'):
                option_map['d'] = extract_option_content(line)
        
        # Map to ordered array
        for i, letter in enumerate(['a', 'b', 'c', 'd']):
            if letter in option_map:
                options[i] = option_map[letter]
                
    except Exception as e:
        print(f"⚠️  Error parsing text options: {e}")
    
    return options

def extract_option_content(line):
    """Extract content after (A), A), or A. prefix"""
    # Remove prefixes and clean up
    content = line
    content = re.sub(r'^\([A-D]\)\s*', '', content)  # Remove (A)
    content = re.sub(r'^[A-D]\)\s*', '', content)    # Remove A)
    content = re.sub(r'^[A-D]\.\s*', '', content)    # Remove A.
    return clean_option_text(content.strip())

def clean_option_text(text):
    """Clean option text - remove extra whitespace, etc."""
    if not text:
        return text
    return str(text).strip()

def test_mcq_cleanup():
    """Test the cleanup on first 5 rows"""
    
    # Connect to database
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        return
    
    engine = create_engine(DATABASE_URL)
    
    print("🔍 Testing MCQ Options Cleanup - First 5 Rows")
    print("=" * 80)
    
    try:
        with engine.connect() as conn:
            # Get first 5 rows with mcq_options data
            result = conn.execute(text("""
                SELECT id, stem, mcq_options, answer
                FROM questions 
                WHERE mcq_options IS NOT NULL 
                AND mcq_options != ''
                LIMIT 5
            """))
            
            rows = result.fetchall()
            
            if not rows:
                print("❌ No questions found with mcq_options data")
                return
            
            print(f"📊 Found {len(rows)} questions to test")
            print()
            
            for i, row in enumerate(rows, 1):
                question_id = row.id
                stem = (row.stem or "")[:100] + "..." if row.stem and len(row.stem) > 100 else (row.stem or "")
                current_mcq = row.mcq_options
                answer = row.answer
                
                print(f"🔸 Question {i}: {question_id[:8]}...")
                print(f"   Stem: {stem}")
                print(f"   Answer: {answer}")
                print(f"   Current mcq_options: {current_mcq}")
                print(f"   Type: {type(current_mcq)}")
                
                # Test conversion
                try:
                    new_options = parse_existing_mcq_options(current_mcq)
                    new_json = json.dumps(new_options)
                    
                    print(f"   ✅ NEW Format: {new_json}")
                    print(f"   📋 Options: A='{new_options[0]}', B='{new_options[1]}', C='{new_options[2]}', D='{new_options[3]}'")
                    
                except Exception as e:
                    print(f"   ❌ CONVERSION ERROR: {e}")
                
                print("-" * 60)
                print()
            
            print("🎯 Test Summary:")
            print("- JSON Array Format: [\"option1\",\"option2\",\"option3\",\"option4\"]")
            print("- Order preserved: A→B→C→D")
            print("- Clean values without prefixes")
            print()
            print("⚠️  This was a TEST RUN - no data was modified")
            print("📝 Review the results above before proceeding with full migration")
            
    except Exception as e:
        print(f"❌ Database error: {e}")

def run_full_migration():
    """Run the full migration (only after test approval)"""
    print("🚨 FULL MIGRATION - This will modify the database!")
    print("This function should only be called after test approval")
    
    # Will implement this after test results are approved
    pass

if __name__ == "__main__":
    print("🧹 MCQ Options Cleanup Script")
    print("Phase 1: Testing on first 5 rows")
    print()
    
    test_mcq_cleanup()