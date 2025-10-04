#!/usr/bin/env python3
"""
LaTeX Delimiter Fix Script for Questions Table

Purpose: Fix LaTeX delimiters in questions table to be compatible with KaTeX renderer
Expected delimiters: \(...\) for inline, $$...$$ for display
LLM: GPT-4o for intelligent delimiter conversion

Fields to process:
- snap_read
- solution_approach
- detailed_solution
- principle_to_remember
"""

import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import openai

# Load environment
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BATCH_SIZE = 10  # Process 10 questions at a time
DRY_RUN = True  # Set to False to actually update database

# Fields to process
FIELDS_TO_PROCESS = ['snap_read', 'solution_approach', 'detailed_solution', 'principle_to_remember']

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Logging
log_file = f'/app/backend/scripts/mathexpression_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

def log(message, level="INFO"):
    """Log to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    with open(log_file, 'a') as f:
        f.write(log_message + '\n')

def create_backup():
    """Create backup of questions table"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        backup_table = f"questions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM questions")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        log(f"✅ Backup created: {backup_table}", "SUCCESS")
        return backup_table
    except Exception as e:
        log(f"❌ Backup failed: {e}", "ERROR")
        raise

def fix_latex_delimiters_with_llm(text, field_name):
    """
    Use GPT-4o to intelligently fix LaTeX delimiters
    """
    if not text or len(text.strip()) == 0:
        return text
    
    prompt = f"""You are a LaTeX formatting expert. Your task is to fix LaTeX delimiters in mathematical content to make it compatible with KaTeX renderer.

**Current text (from {field_name}):**
```
{text}
```

**Requirements:**
1. Identify ALL mathematical expressions in the text
2. Ensure ALL LaTeX commands are wrapped in proper delimiters:
   - Inline math: Use \\(...\\) for inline expressions (e.g., \\(x^2\\), \\(\\frac{{a}}{{b}}\\))
   - Display math: Use $$...$$ for centered display equations
3. DO NOT change any numbers, variables, or content
4. DO NOT add or remove any mathematical expressions
5. Only fix the delimiters around existing LaTeX commands
6. Preserve all other text exactly as is

**Examples:**
- `d = v \\times t \\` → `\\(d = v \\times t\\)`
- `\\boxed{{8 km}}` → `\\(\\boxed{{8 \\text{{ km}}}}\\)`
- `C_L = 4C_S` → `\\(C_L = 4C_S\\)`
- Already correct: `\\(C_L = 4C_S\\)` → Keep as is

**CRITICAL:** Return ONLY the corrected text, no explanations, no markdown code blocks, just the raw corrected text.
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a LaTeX formatting expert. Return only the corrected text with no explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=4000
        )
        
        corrected_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if corrected_text.startswith('```') and corrected_text.endswith('```'):
            lines = corrected_text.split('\n')
            corrected_text = '\n'.join(lines[1:-1])
        
        return corrected_text
    
    except Exception as e:
        log(f"❌ LLM call failed for {field_name}: {e}", "ERROR")
        return text  # Return original on error

def process_questions(dry_run=True):
    """Process all questions and fix LaTeX delimiters"""
    
    log("="*80)
    log(f"Starting LaTeX Delimiter Fix Script")
    log(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'LIVE MODE (changes will be saved)'}")
    log("="*80)
    
    # Create backup if not dry run
    if not dry_run:
        backup_table = create_backup()
        log(f"Backup table: {backup_table}")
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get total count
    cursor.execute("SELECT COUNT(*) as count FROM questions")
    total_questions = cursor.fetchone()['count']
    log(f"Total questions to process: {total_questions}")
    
    # Statistics
    stats = {
        'total': total_questions,
        'processed': 0,
        'modified': 0,
        'errors': 0,
        'skipped': 0
    }
    
    changes_log = []
    
    # Process in batches
    offset = 0
    while offset < total_questions:
        cursor.execute(f"""
            SELECT id, snap_read, solution_approach, detailed_solution, principle_to_remember
            FROM questions
            ORDER BY id
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        
        batch = cursor.fetchall()
        log(f"\n📦 Processing batch {offset//BATCH_SIZE + 1} (questions {offset+1}-{min(offset+BATCH_SIZE, total_questions)})")
        
        for question in batch:
            question_id = question['id']
            question_modified = False
            question_changes = {
                'id': question_id,
                'changes': []
            }
            
            try:
                # Process each field
                updates = {}
                
                for field in FIELDS_TO_PROCESS:
                    original_text = question[field]
                    
                    if not original_text:
                        continue
                    
                    # Fix delimiters using LLM
                    log(f"  Processing {field} for question {question_id[:8]}...")
                    corrected_text = fix_latex_delimiters_with_llm(original_text, field)
                    
                    # Check if changed
                    if corrected_text != original_text:
                        updates[field] = corrected_text
                        question_modified = True
                        question_changes['changes'].append({
                            'field': field,
                            'before': original_text[:100] + '...' if len(original_text) > 100 else original_text,
                            'after': corrected_text[:100] + '...' if len(corrected_text) > 100 else corrected_text
                        })
                        log(f"    ✏️  Modified {field}", "CHANGE")
                    else:
                        log(f"    ✅ No changes needed for {field}", "SKIP")
                    
                    # Rate limiting
                    time.sleep(0.5)  # Avoid hitting rate limits
                
                # Update database if changes detected and not dry run
                if question_modified and not dry_run:
                    set_clause = ', '.join([f"{field} = %s" for field in updates.keys()])
                    values = list(updates.values()) + [question_id]
                    
                    update_cursor = conn.cursor()
                    update_cursor.execute(f"""
                        UPDATE questions
                        SET {set_clause}
                        WHERE id = %s
                    """, values)
                    update_cursor.close()
                    conn.commit()
                    log(f"  💾 Updated question {question_id[:8]}", "SUCCESS")
                
                if question_modified:
                    stats['modified'] += 1
                    changes_log.append(question_changes)
                else:
                    stats['skipped'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                log(f"  ❌ Error processing question {question_id[:8]}: {e}", "ERROR")
                stats['errors'] += 1
                conn.rollback()  # Rollback on error
        
        offset += BATCH_SIZE
        log(f"Progress: {stats['processed']}/{total_questions} ({stats['processed']/total_questions*100:.1f}%)")
    
    cursor.close()
    conn.close()
    
    # Final report
    log("\n" + "="*80)
    log("FINAL REPORT")
    log("="*80)
    log(f"Total questions: {stats['total']}")
    log(f"Processed: {stats['processed']}")
    log(f"Modified: {stats['modified']}")
    log(f"Skipped (no changes): {stats['skipped']}")
    log(f"Errors: {stats['errors']}")
    log(f"Mode: {'DRY RUN' if dry_run else 'LIVE MODE'}")
    
    if dry_run:
        log("\n⚠️  This was a DRY RUN. No changes were saved to the database.")
        log("To apply changes, set DRY_RUN = False and run again.")
    
    # Save changes log
    if changes_log:
        changes_file = f'/app/backend/scripts/mathexpression_changes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(changes_file, 'w') as f:
            json.dump(changes_log, f, indent=2)
        log(f"\n📄 Detailed changes log saved to: {changes_file}")
    
    log(f"📄 Full log saved to: {log_file}")
    log("="*80)

if __name__ == "__main__":
    # Check for command line argument to override dry run
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        DRY_RUN = False
        log("⚠️  LIVE MODE ENABLED via command line argument", "WARNING")
    
    # Confirm before proceeding in live mode
    if not DRY_RUN:
        print("\n" + "!"*80)
        print("WARNING: You are about to modify the database in LIVE MODE")
        print("A backup will be created before making changes")
        print("!"*80)
        confirm = input("\nType 'YES' to proceed: ")
        if confirm != 'YES':
            print("Aborted.")
            sys.exit(0)
    
    try:
        process_questions(dry_run=DRY_RUN)
    except KeyboardInterrupt:
        log("\n⚠️  Script interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ Fatal error: {e}", "ERROR")
        sys.exit(1)
