#!/usr/bin/env python3
"""
LaTeX Delimiter Fix Script - RESUME VERSION

Resumes from question 201 onwards
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
BATCH_SIZE = 10
DRY_RUN = False  # LIVE MODE
RESUME_FROM_QUESTION = 201  # Resume from this question number

# Fields to process
FIELDS_TO_PROCESS = ['snap_read', 'solution_approach', 'detailed_solution', 'principle_to_remember']

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Logging
log_file = f'/app/backend/scripts/mathexpression_resume_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

def log(message, level="INFO"):
    """Log to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    with open(log_file, 'a') as f:
        f.write(log_message + '\n')

def fix_latex_delimiters_with_llm(text, field_name):
    """Use GPT-4o to fix LaTeX delimiters with retry logic"""
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

**CRITICAL:** Return ONLY the corrected text, no explanations, no markdown code blocks, just the raw corrected text.
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a LaTeX formatting expert. Return only the corrected text with no explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                timeout=30  # 30 second timeout
            )
            
            corrected_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if corrected_text.startswith('```') and corrected_text.endswith('```'):
                lines = corrected_text.split('\n')
                corrected_text = '\n'.join(lines[1:-1])
            
            return corrected_text
        
        except Exception as e:
            log(f"❌ LLM call failed for {field_name} (attempt {attempt+1}/{max_retries}): {e}", "ERROR")
            if attempt < max_retries - 1:
                time.sleep(5)  # Wait 5 seconds before retry
            else:
                return text  # Return original after all retries fail

def process_questions_resume():
    """Resume processing from a specific question"""
    
    log("="*80)
    log(f"Starting LaTeX Delimiter Fix Script - RESUME MODE")
    log(f"Resuming from question {RESUME_FROM_QUESTION}")
    log(f"Mode: LIVE MODE (changes will be saved)")
    log("="*80)
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get total count
    cursor.execute("SELECT COUNT(*) as count FROM questions")
    total_questions = cursor.fetchone()['count']
    log(f"Total questions in database: {total_questions}")
    log(f"Questions to process: {total_questions - RESUME_FROM_QUESTION + 1}")
    
    # Statistics
    stats = {
        'total': total_questions - RESUME_FROM_QUESTION + 1,
        'processed': 0,
        'modified': 0,
        'errors': 0,
        'skipped': 0
    }
    
    changes_log = []
    
    # Process from RESUME_FROM_QUESTION onwards
    offset = RESUME_FROM_QUESTION - 1
    
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
            
            try:
                updates = {}
                
                for field in FIELDS_TO_PROCESS:
                    original_text = question[field]
                    
                    if not original_text:
                        continue
                    
                    log(f"  Processing {field} for question {question_id[:8]}...")
                    corrected_text = fix_latex_delimiters_with_llm(original_text, field)
                    
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
                    
                    time.sleep(0.5)  # Rate limiting
                
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
                    log(f"  💾 Updated question {question_id[:8]}", "SUCCESS")
                    stats['modified'] += 1
                    changes_log.append(question_changes)
                else:
                    stats['skipped'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                log(f"  ❌ Error processing question {question_id[:8]}: {e}", "ERROR")
                stats['errors'] += 1
                conn.rollback()
        
        offset += BATCH_SIZE
        log(f"Progress: {stats['processed']}/{stats['total']} ({stats['processed']/stats['total']*100:.1f}%)")
    
    cursor.close()
    conn.close()
    
    # Final report
    log("\n" + "="*80)
    log("FINAL REPORT - RESUME RUN")
    log("="*80)
    log(f"Questions to process: {stats['total']}")
    log(f"Processed: {stats['processed']}")
    log(f"Modified: {stats['modified']}")
    log(f"Skipped (no changes): {stats['skipped']}")
    log(f"Errors: {stats['errors']}")
    
    # Save changes log
    if changes_log:
        changes_file = f'/app/backend/scripts/mathexpression_resume_changes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(changes_file, 'w') as f:
            json.dump(changes_log, f, indent=2)
        log(f"\n📄 Detailed changes log saved to: {changes_file}")
    
    log(f"📄 Full log saved to: {log_file}")
    log("="*80)

if __name__ == "__main__":
    log("⚠️  RESUME MODE - Starting from question 201", "WARNING")
    log("⚠️  LIVE MODE - Changes will be saved to database", "WARNING")
    
    try:
        process_questions_resume()
    except KeyboardInterrupt:
        log("\n⚠️  Script interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
