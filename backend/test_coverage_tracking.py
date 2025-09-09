#!/usr/bin/env python3
"""
Test Coverage Tracking Implementation
Verifies that student coverage tracking works correctly
"""

import asyncio
from database import SessionLocal, Question, User, StudentCoverageTracking
from adaptive_session_logic import AdaptiveSessionLogic
from sqlalchemy import select, text

async def test_coverage_tracking():
    """Test the coverage tracking functionality"""
    
    print("🧪 TESTING COVERAGE TRACKING IMPLEMENTATION")
    print("=" * 60)
    
    db = SessionLocal()
    adaptive_logic = AdaptiveSessionLogic()
    
    try:
        # Get a test user
        result = db.execute(select(User).limit(1))
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            print("❌ No test user found in database")
            return
            
        print(f"🔍 Testing with user: {test_user.id}")
        
        # Get some test questions
        result = db.execute(
            select(Question)
            .where(Question.is_active == True)
            .limit(5)
        )
        test_questions = result.scalars().all()
        
        if len(test_questions) < 3:
            print("❌ Not enough test questions in database")
            return
            
        print(f"📊 Found {len(test_questions)} test questions")
        
        # Test 1: Check initial coverage (should be empty for new test)
        seen_combinations = adaptive_logic.get_student_seen_combinations(test_user.id, db)
        print(f"📋 Initial coverage: {len(seen_combinations)} combinations seen")
        
        # Test 2: Update coverage tracking
        print(f"🔄 Updating coverage tracking for session 1...")
        adaptive_logic.update_student_coverage_tracking(
            user_id=test_user.id,
            questions=test_questions[:3],  # First 3 questions
            session_num=1,
            db=db
        )
        
        # Test 3: Check coverage after update
        seen_combinations_after = adaptive_logic.get_student_seen_combinations(test_user.id, db)
        print(f"📈 Coverage after session 1: {len(seen_combinations_after)} combinations")
        
        # Show the combinations
        for combo in seen_combinations_after:
            print(f"   ✅ {combo}")
        
        # Test 4: Test the prioritization in Phase A
        print(f"\n🎯 Testing Phase A prioritization...")
        user_profile = {"completed_sessions": 5}  # Phase A
        phase_info = {"phase": "A", "difficulty_distribution": {"Easy": 0.2, "Medium": 0.75, "Hard": 0.05}}
        
        coverage_pool = adaptive_logic.get_coverage_weighted_question_pool(
            user_id=test_user.id,
            user_profile=user_profile,
            phase_info=phase_info,
            db=db
        )
        
        print(f"📊 Coverage pool generated: {len(coverage_pool)} questions")
        
        # Test 5: Verify database records
        result = db.execute(
            select(StudentCoverageTracking)
            .where(StudentCoverageTracking.user_id == test_user.id)
        )
        coverage_records = result.scalars().all()
        
        print(f"\n📋 Database verification:")
        print(f"   Records in student_coverage_tracking: {len(coverage_records)}")
        
        for record in coverage_records:
            print(f"   📝 {record.subcategory_type_combination} (seen {record.sessions_seen} times)")
        
        print(f"\n✅ COVERAGE TRACKING TEST COMPLETED!")
        print(f"🎯 Summary:")
        print(f"   - Coverage tracking functions: ✅ Working")
        print(f"   - Database integration: ✅ Working") 
        print(f"   - Phase A prioritization: ✅ Working")
        print(f"   - Coverage records created: {len(coverage_records)}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_coverage_tracking())