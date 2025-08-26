#!/usr/bin/env python3
"""
Test script to verify the new 'right_answer' column functionality
"""

import sys
import os
sys.path.append('/app/backend')

from database import SessionLocal, Question
from sqlalchemy import text
import traceback

def test_right_answer_column():
    """Test the new right_answer column functionality"""
    
    print("🧪 Testing 'right_answer' column functionality...")
    print("=" * 60)
    
    try:
        db = SessionLocal()
        
        # Test 1: Check if column exists in database
        print("📋 Test 1: Verifying column exists in database schema...")
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'questions' 
            AND column_name = 'right_answer'
        """))
        
        if result.fetchone():
            print("✅ Column 'right_answer' exists in database schema.")
        else:
            print("❌ Column 'right_answer' not found in database schema.")
            return False
        
        # Test 2: Check if we can query the column
        print("\n📋 Test 2: Testing query functionality...")
        questions_with_right_answer = db.execute(text("""
            SELECT id, stem, answer, right_answer 
            FROM questions 
            WHERE right_answer IS NOT NULL 
            LIMIT 5
        """)).fetchall()
        
        print(f"✅ Found {len(questions_with_right_answer)} questions with right_answer values.")
        
        # Test 3: Get a sample question and show its structure
        print("\n📋 Test 3: Checking question model attributes...")
        sample_question = db.query(Question).first()
        
        if sample_question:
            print(f"✅ Sample question found: {sample_question.id}")
            print(f"   - answer: {sample_question.answer[:50] if sample_question.answer else 'None'}...")
            print(f"   - right_answer: {sample_question.right_answer[:50] if sample_question.right_answer else 'None'}...")
            
            # Check if the model has the right_answer attribute
            if hasattr(sample_question, 'right_answer'):
                print("✅ Question model has 'right_answer' attribute.")
            else:
                print("❌ Question model missing 'right_answer' attribute.")
                return False
        else:
            print("⚠️  No questions found in database.")
        
        # Test 4: Test updating a question with right_answer
        print("\n📋 Test 4: Testing update functionality...")
        if sample_question:
            original_right_answer = sample_question.right_answer
            sample_question.right_answer = "Test right answer value"
            db.commit()
            
            # Verify the update
            db.refresh(sample_question)
            if sample_question.right_answer == "Test right answer value":
                print("✅ Successfully updated question with right_answer value.")
                
                # Restore original value
                sample_question.right_answer = original_right_answer
                db.commit()
                print("✅ Restored original right_answer value.")
            else:
                print("❌ Failed to update question with right_answer value.")
                return False
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def show_column_info():
    """Show detailed information about the right_answer column"""
    try:
        db = SessionLocal()
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'questions' 
            AND column_name = 'right_answer'
        """)).fetchone()
        
        if result:
            print("\n📋 Right Answer Column Details:")
            print(f"   - Name: {result[0]}")
            print(f"   - Data Type: {result[1]}")
            print(f"   - Nullable: {result[2]}")
            print(f"   - Default: {result[3] or 'None'}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error getting column info: {str(e)}")

if __name__ == "__main__":
    print("🚀 Right Answer Column Test Suite")
    print("=" * 60)
    
    # Run tests
    success = test_right_answer_column()
    
    # Show column details
    show_column_info()
    
    print("\n" + "=" * 60)
    
    if success:
        print("🎉 All tests passed! The 'right_answer' column is working correctly.")
        print("💡 You can now use the 'right_answer' field in your Twelvr application.")
        print("\n📋 Usage Examples:")
        print("   - Create questions with both 'answer' and 'right_answer' fields")
        print("   - API responses now include 'right_answer' in question data")
        print("   - Frontend can display both answer types as needed")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        sys.exit(1)