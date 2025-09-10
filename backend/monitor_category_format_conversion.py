#!/usr/bin/env python3
"""
Monitor Category Format Conversion Progress
Track remaining A-E format questions and confirm when all are converted
"""

import time
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text

def check_category_format_status():
    """Check current status of category format conversion"""
    
    with SessionLocal() as session:
        result = session.execute(text('''
            SELECT DISTINCT category, COUNT(*) as count
            FROM pyq_questions 
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY category
        '''))
        
        categories = result.fetchall()
        
        old_format_questions = []
        new_format_questions = []
        
        for category, count in categories:
            if category.startswith(('A-', 'B-', 'C-', 'D-', 'E-')):
                old_format_questions.append((category, count))
            else:
                new_format_questions.append((category, count))
        
        old_count = sum(count for _, count in old_format_questions)
        new_count = sum(count for _, count in new_format_questions)
        total_enriched = old_count + new_count
        
        return {
            'old_format': old_format_questions,
            'new_format': new_format_questions,
            'old_count': old_count,
            'new_count': new_count,
            'total_enriched': total_enriched,
            'conversion_rate': (new_count / total_enriched * 100) if total_enriched > 0 else 0
        }

def monitor_conversion_progress():
    """Monitor and report conversion progress until completion"""
    
    print("🔄 MONITORING CATEGORY FORMAT CONVERSION PROGRESS")
    print("=" * 60)
    print("📊 Tracking remaining A-E format questions...")
    print("🎯 Target: 100% conversion to clean format")
    print()
    
    start_time = datetime.now()
    check_count = 0
    last_old_count = None
    
    while True:
        check_count += 1
        current_time = datetime.now()
        
        try:
            status = check_category_format_status()
            
            print(f"📅 Check #{check_count} - {current_time.strftime('%H:%M:%S')}")
            print(f"🔄 Conversion Progress: {status['conversion_rate']:.1f}%")
            print(f"✅ Clean Format: {status['new_count']} questions")
            print(f"❌ Old A-E Format: {status['old_count']} questions")
            
            if status['old_format']:
                print("   Legacy questions remaining:")
                for category, count in status['old_format']:
                    print(f"     - {category}: {count}")
            else:
                print("   🎉 NO LEGACY QUESTIONS REMAINING!")
            
            # Check for progress
            if last_old_count is not None and status['old_count'] < last_old_count:
                converted = last_old_count - status['old_count']
                print(f"   📈 Progress: {converted} questions converted since last check!")
            
            last_old_count = status['old_count']
            
            # Check if conversion is complete
            if status['old_count'] == 0:
                elapsed_time = current_time - start_time
                print(f"\n🎉 CONVERSION COMPLETE!")
                print(f"✅ All {status['new_count']} enriched questions now use clean format")
                print(f"⏱️ Total monitoring time: {elapsed_time}")
                print(f"🏆 100% CONVERSION ACHIEVED!")
                
                print("\n📊 Final Category Distribution:")
                for category, count in status['new_format']:
                    print(f"   ✅ {category}: {count} questions")
                
                break
            
            print()
            
            # Wait 30 seconds before next check
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            time.sleep(10)
            continue

if __name__ == "__main__":
    monitor_conversion_progress()