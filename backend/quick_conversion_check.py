#!/usr/bin/env python3
"""
Quick Category Format Conversion Status Check
"""

from database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def quick_status_check():
    """Quick check of conversion status"""
    
    print(f"🔍 CATEGORY FORMAT CONVERSION STATUS - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)
    
    with SessionLocal() as session:
        # Get category distribution
        result = session.execute(text('''
            SELECT DISTINCT category, COUNT(*) as count
            FROM pyq_questions 
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY category
        '''))
        
        categories = result.fetchall()
        
        old_count = 0
        new_count = 0
        
        print("📊 Current Category Distribution:")
        for category, count in categories:
            if category.startswith(('A-', 'B-', 'C-', 'D-', 'E-')):
                print(f"   ❌ {category}: {count} questions (OLD FORMAT)")
                old_count += count
            else:
                print(f"   ✅ {category}: {count} questions (NEW FORMAT)")
                new_count += count
        
        total = old_count + new_count
        conversion_rate = (new_count / total * 100) if total > 0 else 0
        
        print(f"\n📈 Conversion Progress:")
        print(f"   Total Enriched: {total} questions")
        print(f"   Clean Format: {new_count} questions ({conversion_rate:.1f}%)")
        print(f"   Legacy Format: {old_count} questions ({100-conversion_rate:.1f}%)")
        
        if old_count == 0:
            print(f"\n🎉 CONVERSION COMPLETE! All questions use clean format!")
        else:
            print(f"\n🔄 {old_count} questions still need conversion...")
        
        # Get overall enrichment status
        overall_result = session.execute(text('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN concept_extraction_status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN concept_extraction_status = 'pending' THEN 1 END) as pending
            FROM pyq_questions
        '''))
        
        overall = overall_result.fetchone()
        
        print(f"\n📊 Overall Enrichment Status:")
        print(f"   Total Questions: {overall[0]}")
        print(f"   Completed: {overall[1]}")
        print(f"   Pending: {overall[2]}")
        print(f"   Progress: {(overall[1]/overall[0]*100):.1f}%")

if __name__ == "__main__":
    quick_status_check()