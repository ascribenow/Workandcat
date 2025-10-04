#!/usr/bin/env python3
"""
LaTeX Display Math Delimiter Conversion Script

Purpose: Convert \[...\] to $$...$$ in all question fields
This is a simple regex replacement - NO content changes, ONLY delimiter format

Fields to process:
- snap_read
- solution_approach
- detailed_solution
- principle_to_remember
"""

import os
import sys
import json
import re
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
BATCH_SIZE = 50  # Larger batch since no LLM calls
DRY_RUN = False  # LIVE MODE

# Fields to process
FIELDS_TO_PROCESS = ['snap_read', 'solution_approach', 'detailed_solution', 'principle_to_remember']

# Logging
log_file = f'/app/backend/scripts/delimiter_conversion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

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
        
        backup_table = f"questions_backup_delimiter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM questions")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        log(f"✅ Backup created: {backup_table}", "SUCCESS")
        return backup_table
    except Exception as e:
        log(f"❌ Backup failed: {e}", "ERROR")
        raise

def convert_display_math_delimiters(text):
    """
    Convert \[...\] to $$...$$
    Uses regex to ensure ONLY delimiters are changed, content stays intact
    """
    if not text:
        return text, False
    
    # Pattern to match \[ and \] delimiters
    # This captures everything between \[ and \]
    pattern = r'\\?\\\[([^\]]+?)\\?\\\]'
    
    # Replace with $$ delimiters
    converted_text = re.sub(pattern, r'$$ \1 $$', text)
    
    # Check if any changes were made
    changed = (converted_text != text)
    
    return converted_text, changed

def process_questions():
    """Process all questions and convert display math delimiters"""
    
    log("="*80)
    log(f"Starting Display Math Delimiter Conversion Script")
    log(f"Converting: \\[...\\] → $$...$$")
    log(f"Mode: LIVE MODE (changes will be saved)")
    log("="*80)
    
    # Create backup
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
        'skipped': 0,
        'total_conversions': 0
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
        log(f"\n📦 Processing batch (questions {offset+1}-{min(offset+BATCH_SIZE, total_questions)})")
        
        for question in batch:
            question_id = question['id']
            question_modified = False
            question_changes = {
                'id': question_id,
                'changes': []
            }
            field_conversion_count = 0
            
            try:
                updates = {}
                
                for field in FIELDS_TO_PROCESS:
                    original_text = question[field]
                    
                    if not original_text:
                        continue
                    
                    # Convert display math delimiters
                    converted_text, changed = convert_display_math_delimiters(original_text)
                    
                    if changed:
                        updates[field] = converted_text
                        question_modified = True
                        
                        # Count conversions in this field
                        conversion_count = original_text.count('\\[')
                        field_conversion_count += conversion_count
                        
                        question_changes['changes'].append({
                            'field': field,
                            'conversions': conversion_count,
                            'sample_before': original_text[:150] + '...' if len(original_text) > 150 else original_text,
                            'sample_after': converted_text[:150] + '...' if len(converted_text) > 150 else converted_text
                        })
                        log(f"  ✏️  {field}: {conversion_count} delimiter(s) converted", "CHANGE")
                
                # Update database if changes detected
                if question_modified:
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
                    
                    stats['modified'] += 1
                    stats['total_conversions'] += field_conversion_count
                    changes_log.append(question_changes)
                    log(f"  💾 Updated question {question_id[:8]} ({field_conversion_count} total conversions)", "SUCCESS")
                else:
                    stats['skipped'] += 1
                    log(f"  ✅ No conversions needed for question {question_id[:8]}", "SKIP")
                
                stats['processed'] += 1
                
            except Exception as e:
                log(f"  ❌ Error processing question {question_id[:8]}: {e}", "ERROR")
                stats['errors'] += 1
                conn.rollback()
        
        offset += BATCH_SIZE
        log(f"Progress: {stats['processed']}/{total_questions} ({stats['processed']/total_questions*100:.1f}%)")
    
    cursor.close()
    conn.close()
    
    # Final report
    log("\n" + "="*80)
    log("FINAL REPORT - DELIMITER CONVERSION")
    log("="*80)
    log(f"Total questions: {stats['total']}")
    log(f"Processed: {stats['processed']}")
    log(f"Modified: {stats['modified']}")
    log(f"Skipped (no changes): {stats['skipped']}")
    log(f"Errors: {stats['errors']}")
    log(f"Total \\[...\\] → $$...$$ conversions: {stats['total_conversions']}")
    
    # Save changes log
    if changes_log:
        changes_file = f'/app/backend/scripts/delimiter_conversion_changes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(changes_file, 'w') as f:
            json.dump(changes_log, f, indent=2)
        log(f"\n📄 Detailed changes log saved to: {changes_file}")
    
    log(f"📄 Full log saved to: {log_file}")
    log(f"💾 Backup table: {backup_table}")
    log("="*80)
    
    # Verification
    log("\n🔍 VERIFICATION:")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if any \[ remain
    cursor.execute("""
        SELECT COUNT(*) FROM questions
        WHERE snap_read LIKE '%\\[%'
           OR solution_approach LIKE '%\\[%'
           OR detailed_solution LIKE '%\\[%'
           OR principle_to_remember LIKE '%\\[%'
    """)
    remaining = cursor.fetchone()[0]
    
    if remaining == 0:
        log("✅ SUCCESS: No \\[ delimiters remaining in database!", "SUCCESS")
    else:
        log(f"⚠️  WARNING: {remaining} questions still contain \\[ delimiters", "WARNING")
        log("   (These might be escaped or in non-math context)", "WARNING")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    log("⚠️  DELIMITER CONVERSION MODE", "WARNING")
    log("⚠️  Converting \\[...\\] → $$...$$", "WARNING")
    log("⚠️  LIVE MODE - Changes will be saved to database", "WARNING")
    
    try:
        process_questions()
        log("\n✅ Delimiter conversion completed successfully!", "SUCCESS")
    except KeyboardInterrupt:
        log("\n⚠️  Script interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
