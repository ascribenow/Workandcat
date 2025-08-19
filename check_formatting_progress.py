#!/usr/bin/env python3
"""
Check solution formatting progress
"""

import psycopg2
import os
from dotenv import load_dotenv

def check_formatting_quality():
    load_dotenv('backend/.env')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Check formatting quality
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN detailed_solution LIKE '%**Step 1:**%' THEN 1 ELSE 0 END) as has_step_formatting,
                SUM(CASE WHEN detailed_solution LIKE '%\n\n%' THEN 1 ELSE 0 END) as has_line_breaks,
                AVG(LENGTH(detailed_solution) - LENGTH(REPLACE(detailed_solution, '\n', ''))) as avg_line_breaks
            FROM questions
            WHERE detailed_solution IS NOT NULL AND detailed_solution != ''
        """)
        
        stats = cur.fetchone()
        total, step_formatted, has_breaks, avg_breaks = stats
        
        print(f"📊 SOLUTION FORMATTING PROGRESS")
        print(f"=" * 50)
        print(f"Total questions: {total}")
        print(f"With **Step** formatting: {step_formatted}/{total} ({step_formatted/total*100:.1f}%)")
        print(f"With line breaks: {has_breaks}/{total} ({has_breaks/total*100:.1f}%)")
        print(f"Average line breaks: {avg_breaks:.1f}")
        
        # Check a recent sample
        cur.execute("""
            SELECT stem, detailed_solution
            FROM questions 
            WHERE detailed_solution LIKE '%**Step 1:**%'
            ORDER BY id DESC
            LIMIT 1
        """)
        
        sample = cur.fetchone()
        if sample:
            stem, detailed = sample
            print(f"\n📋 Sample well-formatted solution:")
            print(f"Question: {stem[:60]}...")
            print("Solution structure:")
            lines = detailed.split('\n')[:5]  # First 5 lines
            for line in lines:
                if line.strip():
                    print(f"  {line[:60]}...")
        
        conn.close()
        
        formatting_quality = step_formatted / total * 100
        return formatting_quality >= 80  # 80% well-formatted
        
    except Exception as e:
        print(f"Error checking formatting: {e}")
        return False

if __name__ == "__main__":
    is_complete = check_formatting_quality()
    if is_complete:
        print("\n🎉 FORMATTING QUALITY IS GOOD!")
    else:
        print("\n⏳ Formatting still in progress...")