#!/usr/bin/env python3
"""
Monitor comprehensive re-enrichment progress
"""

import psycopg2
import os
import time
from dotenv import load_dotenv

def check_enrichment_progress():
    load_dotenv('backend/.env')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get enrichment statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN answer IS NOT NULL AND answer != '' AND answer != 'To Be Enriched' AND answer != 'Error in answer generation' THEN 1 ELSE 0 END) as good_answers,
                SUM(CASE WHEN solution_approach IS NOT NULL AND LENGTH(solution_approach) > 20 THEN 1 ELSE 0 END) as good_approaches,
                SUM(CASE WHEN detailed_solution IS NOT NULL AND LENGTH(detailed_solution) > 50 THEN 1 ELSE 0 END) as good_detailed,
                SUM(CASE WHEN mcq_options IS NOT NULL AND mcq_options != '' AND mcq_options != 'null' THEN 1 ELSE 0 END) as has_mcq
            FROM questions
        """)
        
        stats = cur.fetchone()
        total, good_answers, good_approaches, good_detailed, has_mcq = stats
        
        print(f"📊 ENRICHMENT PROGRESS REPORT")
        print(f"=" * 50)
        print(f"Total questions: {total}")
        print(f"Good answers: {good_answers}/{total} ({good_answers/total*100:.1f}%)")
        print(f"Good approaches: {good_approaches}/{total} ({good_approaches/total*100:.1f}%)")
        print(f"Good detailed solutions: {good_detailed}/{total} ({good_detailed/total*100:.1f}%)")
        print(f"Has MCQ options: {has_mcq}/{total} ({has_mcq/total*100:.1f}%)")
        
        # Calculate overall completion
        fully_enriched = min(good_answers, good_approaches, good_detailed, has_mcq)
        completion_rate = fully_enriched / total * 100
        
        print(f"📈 Overall completion: {fully_enriched}/{total} ({completion_rate:.1f}%)")
        
        # Sample some recent questions
        cur.execute("""
            SELECT stem, answer, 
                   CASE WHEN LENGTH(solution_approach) > 20 THEN 'Good' ELSE 'Poor' END as approach_quality,
                   CASE WHEN LENGTH(detailed_solution) > 50 THEN 'Good' ELSE 'Poor' END as detailed_quality,
                   CASE WHEN mcq_options IS NOT NULL AND mcq_options != '' THEN 'Yes' ELSE 'No' END as has_mcq_options
            FROM questions 
            ORDER BY id
            LIMIT 5
        """)
        
        samples = cur.fetchall()
        print(f"\n📋 Sample questions:")
        for i, (stem, answer, approach_q, detailed_q, mcq_status) in enumerate(samples, 1):
            print(f"{i}. {stem[:60]}...")
            print(f"   Answer: {answer}")
            print(f"   Approach: {approach_q}, Detailed: {detailed_q}, MCQ: {mcq_status}")
        
        conn.close()
        
        return completion_rate >= 95.0  # Consider complete when 95%+ done
        
    except Exception as e:
        print(f"Error monitoring progress: {e}")
        return False

if __name__ == "__main__":
    is_complete = check_enrichment_progress()
    if is_complete:
        print("\n🎉 ENRICHMENT APPEARS COMPLETE!")
    else:
        print("\n⏳ Enrichment still in progress...")