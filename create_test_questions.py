#!/usr/bin/env python3
"""
Create test questions for Enhanced Nightly Engine Integration testing
"""

import asyncio
import sys
import os
sys.path.append('/app/backend')

from database import get_database, Question, Topic
from sqlalchemy import select
import uuid
from datetime import datetime

async def create_test_questions():
    """Create active test questions for testing"""
    
    async for db in get_database():
        try:
            # Get some topics
            topics_result = await db.execute(select(Topic).limit(5))
            topics = topics_result.scalars().all()
            
            if not topics:
                print("No topics found!")
                return
            
            # Create test questions
            test_questions = [
                {
                    "stem": "A train travels 120 km in 2 hours. What is its speed in km/h?",
                    "answer": "60",
                    "subcategory": "Time–Speed–Distance (TSD)",
                    "solution_approach": "Speed = Distance / Time = 120/2 = 60 km/h",
                    "difficulty_score": 0.3,
                    "difficulty_band": "Easy",
                    "learning_impact": 0.7,
                    "importance_index": 0.8
                },
                {
                    "stem": "If 20% of a number is 40, what is the number?",
                    "answer": "200", 
                    "subcategory": "Percentages",
                    "solution_approach": "Let x be the number. 20% of x = 40, so 0.2x = 40, x = 200",
                    "difficulty_score": 0.4,
                    "difficulty_band": "Medium",
                    "learning_impact": 0.6,
                    "importance_index": 0.7
                },
                {
                    "stem": "Find the area of a circle with radius 7 cm.",
                    "answer": "154",
                    "subcategory": "Circles",
                    "solution_approach": "Area = πr² = π × 7² = 22/7 × 49 = 154 cm²",
                    "difficulty_score": 0.5,
                    "difficulty_band": "Medium", 
                    "learning_impact": 0.8,
                    "importance_index": 0.6
                },
                {
                    "stem": "Solve: 2x + 5 = 15",
                    "answer": "5",
                    "subcategory": "Linear Equations",
                    "solution_approach": "2x + 5 = 15, 2x = 10, x = 5",
                    "difficulty_score": 0.2,
                    "difficulty_band": "Easy",
                    "learning_impact": 0.5,
                    "importance_index": 0.6
                },
                {
                    "stem": "In how many ways can 5 people sit in a row?",
                    "answer": "120",
                    "subcategory": "Permutation–Combination (P&C)",
                    "solution_approach": "5! = 5 × 4 × 3 × 2 × 1 = 120",
                    "difficulty_score": 0.6,
                    "difficulty_band": "Hard",
                    "learning_impact": 0.9,
                    "importance_index": 0.8
                }
            ]
            
            created_count = 0
            for i, q_data in enumerate(test_questions):
                topic = topics[i % len(topics)]
                
                question = Question(
                    id=uuid.uuid4(),
                    topic_id=topic.id,
                    subcategory=q_data["subcategory"],
                    type_of_question="Standard",
                    stem=q_data["stem"],
                    answer=q_data["answer"],
                    solution_approach=q_data["solution_approach"],
                    detailed_solution=q_data["solution_approach"],
                    difficulty_score=q_data["difficulty_score"],
                    difficulty_band=q_data["difficulty_band"],
                    frequency_band="Medium",
                    learning_impact=q_data["learning_impact"],
                    learning_impact_band="Medium",
                    importance_index=q_data["importance_index"],
                    importance_band="High",
                    tags=["test_question", "nightly_engine_test"],
                    source="Test Data",
                    version=1,
                    is_active=True,  # Make them active immediately
                    created_at=datetime.utcnow()
                )
                
                db.add(question)
                created_count += 1
            
            await db.commit()
            print(f"✅ Created {created_count} active test questions")
            
            # Verify questions were created
            questions_result = await db.execute(
                select(Question).where(Question.is_active == True)
            )
            active_questions = questions_result.scalars().all()
            print(f"✅ Total active questions in database: {len(active_questions)}")
            
        except Exception as e:
            print(f"❌ Error creating test questions: {e}")
            await db.rollback()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(create_test_questions())