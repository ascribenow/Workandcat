#!/usr/bin/env python3
"""
Fix the systematic status inconsistency in regular questions
"""

import sys
from database import SessionLocal, Question
from sqlalchemy import select, and_, func

def fix_regular_questions_status():
    """Fix all regular questions with core_concepts but incorrect status"""
    
    db = SessionLocal()
    try:
        print("🚨 FIXING SYSTEMATIC STATUS INCONSISTENCY IN REGULAR QUESTIONS")
        print("=" * 70)
        
        # Find all inconsistent questions
        inconsistent_questions = db.execute(
            select(Question)
            .where(
                and_(
                    Question.concept_extraction_status == 'pending',
                    Question.core_concepts.isnot(None)
                )
            )
        ).scalars().all()
        
        print(f"📊 Found {len(inconsistent_questions)} questions with status inconsistency")
        print("   All have core_concepts populated but status = 'pending'")
        
        fixed_count = 0
        
        for i, question in enumerate(inconsistent_questions, 1):
            try:
                print(f"🔧 Fixing {i}/{len(inconsistent_questions)}: {question.id[:8]}... | {question.subcategory}")
                
                # Check if this question has all the enrichment fields populated
                has_core_concepts = question.core_concepts is not None
                has_keywords = question.concept_keywords is not None
                has_snap_read = question.snap_read is not None
                has_detailed_solution = question.detailed_solution is not None
                has_difficulty = question.difficulty_score is not None
                
                enrichment_fields_count = sum([
                    has_core_concepts, has_keywords, has_snap_read, 
                    has_detailed_solution, has_difficulty
                ])
                
                print(f"   📋 Enrichment fields populated: {enrichment_fields_count}/5")
                
                # If question has core concepts (minimum requirement), mark as completed
                if has_core_concepts:
                    question.concept_extraction_status = 'completed'
                    fixed_count += 1
                    
                    # If it has most/all enrichment fields, mark as quality verified
                    if enrichment_fields_count >= 4:  # At least 4 out of 5 fields
                        question.quality_verified = True
                        print(f"   ✅ Status: pending → completed, Quality: False → True")
                    else:
                        print(f"   ✅ Status: pending → completed, Quality: False (needs more enrichment)")
                
            except Exception as e:
                print(f"   ❌ Error fixing {question.id[:8]}...: {e}")
        
        # Commit all changes
        print(f"\n💾 Committing {fixed_count} status fixes...")
        db.commit()
        
        # Verify the fix
        print(f"\n🔍 VERIFICATION:")
        
        remaining_inconsistent = db.execute(
            select(func.count(Question.id))
            .where(
                and_(
                    Question.concept_extraction_status == 'pending',
                    Question.core_concepts.isnot(None)
                )
            )
        ).scalar()
        
        total_completed = db.execute(
            select(func.count(Question.id))
            .where(Question.concept_extraction_status == 'completed')
        ).scalar()
        
        total_verified = db.execute(
            select(func.count(Question.id))
            .where(Question.quality_verified == True)
        ).scalar()
        
        total_questions = db.execute(select(func.count(Question.id))).scalar()
        
        print(f"   Remaining inconsistent questions: {remaining_inconsistent}")
        print(f"   Total completed status: {total_completed}/{total_questions} ({(total_completed/total_questions)*100:.1f}%)")
        print(f"   Total quality verified: {total_verified}/{total_questions} ({(total_verified/total_questions)*100:.1f}%)")
        
        if remaining_inconsistent == 0:
            print(f"\n🎉 ✅ ALL STATUS INCONSISTENCIES FIXED!")
        else:
            print(f"\n⚠️ {remaining_inconsistent} inconsistencies remain")
        
        return {
            'success': True,
            'fixed_count': fixed_count,
            'remaining_inconsistent': remaining_inconsistent,
            'total_completed': total_completed,
            'total_verified': total_verified
        }
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        db.rollback()
        return {'success': False, 'error': str(e)}
        
    finally:
        db.close()

if __name__ == "__main__":
    result = fix_regular_questions_status()
    
    if result['success']:
        print(f"\n🚀 REGULAR QUESTIONS STATUS FIX COMPLETED!")
        print(f"   Fixed: {result['fixed_count']} questions")
        print(f"   Remaining inconsistencies: {result['remaining_inconsistent']}")
        print(f"   Total completed: {result['total_completed']}")
        print(f"   Total verified: {result['total_verified']}")
    else:
        print(f"\n❌ Fix failed: {result['error']}")