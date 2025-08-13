#!/usr/bin/env python3
"""
Test script to verify SQLite database migration is working correctly
"""

import sys
import os
sys.path.append('/app/backend')

from database import engine, Base, SessionLocal, Topic, Question, User
from sqlalchemy import text
import uuid

def test_database_connection():
    """Test basic database connection and table creation"""
    print("🔍 Testing SQLite database connection...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ Database connection test: {result.scalar()}")
        
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_basic_crud_operations():
    """Test basic CRUD operations"""
    print("\n🔍 Testing basic CRUD operations...")
    
    try:
        db = SessionLocal()
        
        # Create a test topic
        test_topic = Topic(
            id=str(uuid.uuid4()),
            name="Test Topic",
            slug="test-topic",
            section="QA",
            centrality=0.5
        )
        db.add(test_topic)
        db.commit()
        print("✅ Topic creation successful")
        
        # Create a test question
        test_question = Question(
            id=str(uuid.uuid4()),
            topic_id=test_topic.id,
            subcategory="Test Subcategory",
            stem="What is 2 + 2?",
            answer="4",
            solution_approach="Add the numbers",
            is_active=True
        )
        db.add(test_question)
        db.commit()
        print("✅ Question creation successful")
        
        # Query the data
        topics = db.query(Topic).all()
        questions = db.query(Question).all()
        
        print(f"✅ Found {len(topics)} topics and {len(questions)} questions")
        
        # Clean up
        db.delete(test_question)
        db.delete(test_topic)
        db.commit()
        print("✅ Cleanup successful")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ CRUD operations failed: {e}")
        return False

def test_json_fields():
    """Test JSON field handling in SQLite"""
    print("\n🔍 Testing JSON field handling...")
    
    try:
        db = SessionLocal()
        
        # Create a test topic
        test_topic = Topic(
            id=str(uuid.uuid4()),
            name="JSON Test Topic",
            slug="json-test-topic",
            section="QA"
        )
        db.add(test_topic)
        db.flush()
        
        # Create a question with JSON-like fields (stored as text in SQLite)
        test_question = Question(
            id=str(uuid.uuid4()),
            topic_id=test_topic.id,
            subcategory="JSON Test",
            stem="Test question with tags",
            answer="Test answer",
            tags='["tag1", "tag2", "json_test"]',  # JSON string
            top_matching_concepts='["concept1", "concept2"]',  # JSON string
            is_active=True
        )
        db.add(test_question)
        db.commit()
        
        # Query and verify
        retrieved_question = db.query(Question).filter(Question.id == test_question.id).first()
        print(f"✅ JSON fields stored: tags={retrieved_question.tags}")
        
        # Clean up
        db.delete(test_question)
        db.delete(test_topic)
        db.commit()
        db.close()
        
        print("✅ JSON field handling successful")
        return True
        
    except Exception as e:
        print(f"❌ JSON field test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting SQLite Migration Tests")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_basic_crud_operations,
        test_json_fields
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! SQLite migration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())