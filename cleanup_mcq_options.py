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

# Load environment variables from backend directory
load_dotenv('/app/backend/.env')

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
    """Run the full migration on all rows"""
    print("🚨 FULL MIGRATION - This will modify the database!")
    print("Converting all mcq_options to JSON array format")
    print("=" * 80)
    
    # Connect to database
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        return
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Begin transaction for safety
            trans = conn.begin()
            
            try:
                # Get total count first
                count_result = conn.execute(text("""
                    SELECT COUNT(*) as total
                    FROM questions 
                    WHERE mcq_options IS NOT NULL 
                    AND mcq_options != ''
                """))
                total_questions = count_result.fetchone().total
                
                print(f"📊 Found {total_questions} questions with mcq_options data")
                print()
                
                if total_questions == 0:
                    print("✅ No questions to migrate")
                    return
                
                # Process in batches of 50 for better progress tracking
                batch_size = 50
                updated_count = 0
                error_count = 0
                
                for offset in range(0, total_questions, batch_size):
                    print(f"🔄 Processing batch {offset//batch_size + 1}/{(total_questions + batch_size - 1)//batch_size} (rows {offset+1}-{min(offset+batch_size, total_questions)})")
                    
                    # Get batch of questions
                    result = conn.execute(text("""
                        SELECT id, mcq_options
                        FROM questions 
                        WHERE mcq_options IS NOT NULL 
                        AND mcq_options != ''
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """), {"limit": batch_size, "offset": offset})
                    
                    batch_rows = result.fetchall()
                    
                    for row in batch_rows:
                        question_id = row.id
                        current_mcq = row.mcq_options
                        
                        try:
                            # Convert to new format
                            new_options = parse_existing_mcq_options(current_mcq)
                            new_json = json.dumps(new_options)
                            
                            # Update database
                            conn.execute(text("""
                                UPDATE questions 
                                SET mcq_options = :new_options 
                                WHERE id = :question_id
                            """), {
                                "new_options": new_json,
                                "question_id": question_id
                            })
                            
                            updated_count += 1
                            
                            # Show progress every 10 updates
                            if updated_count % 10 == 0:
                                print(f"   ✅ Updated {updated_count}/{total_questions} questions...")
                            
                        except Exception as e:
                            error_count += 1
                            print(f"   ❌ Error updating {question_id[:8]}...: {e}")
                            continue
                    
                    # Progress update per batch
                    print(f"   📈 Batch complete: {updated_count} updated, {error_count} errors")
                    print()
                
                # Final summary
                print("=" * 80)
                print("🎯 MIGRATION COMPLETE!")
                print(f"✅ Successfully updated: {updated_count} questions")
                print(f"❌ Errors encountered: {error_count} questions")
                print(f"📊 Success rate: {(updated_count/(updated_count+error_count)*100):.1f}%" if (updated_count+error_count) > 0 else "100%")
                
                if error_count == 0:
                    print("🟢 PERFECT MIGRATION - No errors!")
                elif error_count < total_questions * 0.05:  # Less than 5% errors
                    print("🟡 GOOD MIGRATION - Minor errors only")
                else:
                    print("🔴 MIGRATION HAD SIGNIFICANT ERRORS - Review required")
                
                print()
                print("🔄 Committing changes to database...")
                trans.commit()
                print("✅ All changes committed successfully!")
                
                # Verify a few samples post-migration
                print()
                print("🔍 POST-MIGRATION VERIFICATION (Sample of 3 rows):")
                verify_result = conn.execute(text("""
                    SELECT id, mcq_options, answer
                    FROM questions 
                    WHERE mcq_options IS NOT NULL 
                    ORDER BY RANDOM()
                    LIMIT 3
                """))
                
                for i, row in enumerate(verify_result.fetchall(), 1):
                    try:
                        options_array = json.loads(row.mcq_options)
                        print(f"   {i}. {row.id[:8]}... → {options_array} (Answer: {row.answer})")
                    except:
                        print(f"   {i}. {row.id[:8]}... → PARSING ERROR")
                
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                print("🔄 Rolling back changes...")
                trans.rollback()
                print("✅ Rollback complete - no changes were made")
                raise
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")

def verify_migration():
    """Verify the migration results"""
    print("🔍 MIGRATION VERIFICATION")
    print("=" * 50)
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check total converted
            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN mcq_options ~ '^\\[.*\\]$' THEN 1 END) as json_format
                FROM questions 
                WHERE mcq_options IS NOT NULL 
                AND mcq_options != ''
            """))
            
            row = result.fetchone()
            total = row.total
            json_format = row.json_format
            
            print(f"📊 Total questions with mcq_options: {total}")
            print(f"✅ Successfully converted to JSON: {json_format}")
            print(f"📈 Conversion rate: {(json_format/total*100):.1f}%" if total > 0 else "N/A")
            
            if json_format == total:
                print("🎉 PERFECT - All questions converted!")
            else:
                print(f"⚠️  {total - json_format} questions may need manual review")
    
    except Exception as e:
        print(f"❌ Verification error: {e}")

if __name__ == "__main__":
    print("🧹 MCQ Options Cleanup Script")
    print("Phase 2: FULL MIGRATION - All Rows")
    print()
    
    # Confirm before proceeding
    confirm = input("⚠️  This will modify ALL mcq_options in the database. Continue? (yes/no): ").lower().strip()
    
    if confirm == 'yes':
        print("\n🚀 Starting full migration...")
        run_full_migration()
        
        print("\n" + "="*50)
        verify_migration()
        
    else:
        print("❌ Migration cancelled by user")
        print("💡 To run test only, modify the script to call test_mcq_cleanup()")