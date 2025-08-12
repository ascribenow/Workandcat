#!/usr/bin/env python3
"""
Create Test Data for Conceptual Frequency Analysis
Adds sample questions and PYQ data to test the system
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import uuid
from datetime import datetime

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from database import (
    get_database, Question, Topic, PYQQuestion, PYQPaper, PYQIngestion
)
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

async def create_test_data():
    """Create test questions and PYQ data"""
    
    try:
        async for db in get_database():
            # Create test topics first
            topics_data = [
                {"name": "Arithmetic", "category": "A", "slug": "arithmetic"},
                {"name": "Time-Speed-Distance", "category": "A", "slug": "time-speed-distance"},
                {"name": "Work and Time", "category": "A", "slug": "work-time"},
                {"name": "Percentages", "category": "A", "slug": "percentages"},
                {"name": "Algebra", "category": "B", "slug": "algebra"}
            ]
            
            topics = []
            for topic_data in topics_data:
                # Check if topic exists
                result = await db.execute(
                    select(Topic).where(Topic.slug == topic_data["slug"])
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    topic = Topic(
                        name=topic_data["name"],
                        category=topic_data["category"], 
                        slug=topic_data["slug"],
                        centrality=0.8
                    )
                    db.add(topic)
                    topics.append(topic)
                else:
                    topics.append(existing)
            
            await db.flush()
            logger.info(f"✅ Created/found {len(topics)} topics")
            
            # Create test questions
            arithmetic_topic = next(t for t in topics if t.slug == "arithmetic")
            
            test_questions = [
                {
                    "stem": "A train travels 120 km in 2 hours. What is its speed in km/h?",
                    "answer": "60",
                    "subcategory": "Time-Speed-Distance",
                    "type_of_question": "Basic Speed Calculation",
                    "solution_approach": "Speed = Distance / Time"
                },
                {
                    "stem": "If 20 men can complete a work in 15 days, how many days will 30 men take to complete the same work?",
                    "answer": "10",
                    "subcategory": "Work and Time",
                    "type_of_question": "Work Rate Problem", 
                    "solution_approach": "Use inverse proportion: Men × Days = Constant"
                },
                {
                    "stem": "What is 25% of 240?",
                    "answer": "60",
                    "subcategory": "Percentages",
                    "type_of_question": "Basic Percentage Calculation",
                    "solution_approach": "25% of 240 = (25/100) × 240"
                },
                {
                    "stem": "A car covers a distance of 360 km at a speed of 60 km/h. How much time does it take?",
                    "answer": "6",
                    "subcategory": "Time-Speed-Distance", 
                    "type_of_question": "Time Calculation",
                    "solution_approach": "Time = Distance / Speed"
                },
                {
                    "stem": "If the price of sugar increases by 20%, by how much percent should consumption be reduced to keep expenditure same?",
                    "answer": "16.67",
                    "subcategory": "Percentages",
                    "type_of_question": "Percentage Change Problem",
                    "solution_approach": "Use formula: Reduction% = (Increase%)/(100 + Increase%) × 100"
                }
            ]
            
            questions = []
            for q_data in test_questions:
                question = Question(
                    topic_id=arithmetic_topic.id,
                    subcategory=q_data["subcategory"],
                    type_of_question=q_data["type_of_question"],
                    stem=q_data["stem"],
                    answer=q_data["answer"],
                    solution_approach=q_data["solution_approach"],
                    detailed_solution=f"Detailed solution for: {q_data['stem']}",
                    difficulty_score=0.5,
                    difficulty_band="Medium",
                    is_active=True,
                    source="test_data"
                )
                db.add(question)
                questions.append(question)
            
            await db.flush()
            logger.info(f"✅ Created {len(questions)} test questions")
            
            # Create PYQ ingestion and paper
            ingestion = PYQIngestion(
                upload_filename="test_cat_2023.pdf",
                storage_key="test_storage_key",
                year=2023,
                slot="A",
                parse_status="done"
            )
            db.add(ingestion)
            await db.flush()
            
            paper = PYQPaper(
                year=2023,
                slot="A",
                ingestion_id=ingestion.id
            )
            db.add(paper)
            await db.flush()
            
            # Create PYQ questions similar to our test questions
            pyq_questions_data = [
                {
                    "stem": "A motorcycle travels 180 km in 3 hours. Find its average speed.",
                    "answer": "60",
                    "subcategory": "Time-Speed-Distance",
                    "type_of_question": "Speed Calculation"
                },
                {
                    "stem": "Train covers 200 km distance at 50 km/h speed. Calculate time taken.",
                    "answer": "4",
                    "subcategory": "Time-Speed-Distance",
                    "type_of_question": "Time Calculation"
                },
                {
                    "stem": "15 workers complete a project in 20 days. How many days for 25 workers?",
                    "answer": "12",
                    "subcategory": "Work and Time", 
                    "type_of_question": "Work Rate Problem"
                },
                {
                    "stem": "Calculate 30% of 150.",
                    "answer": "45",
                    "subcategory": "Percentages",
                    "type_of_question": "Basic Percentage"
                },
                {
                    "stem": "A bus travels at 40 km/h for first 2 hours, then 60 km/h for next 3 hours. Find average speed.",
                    "answer": "52",
                    "subcategory": "Time-Speed-Distance",
                    "type_of_question": "Average Speed"
                }
            ]
            
            pyq_questions = []
            for pyq_data in pyq_questions_data:
                pyq_question = PYQQuestion(
                    paper_id=paper.id,
                    topic_id=arithmetic_topic.id,
                    subcategory=pyq_data["subcategory"],
                    type_of_question=pyq_data["type_of_question"],
                    stem=pyq_data["stem"],
                    answer=pyq_data["answer"],
                    confirmed=True
                )
                db.add(pyq_question)
                pyq_questions.append(pyq_question)
            
            await db.commit()
            logger.info(f"✅ Created {len(pyq_questions)} PYQ questions")
            
            logger.info("🎉 Test data creation completed successfully!")
            logger.info(f"   • Topics: {len(topics)}")
            logger.info(f"   • Questions: {len(questions)}")  
            logger.info(f"   • PYQ Questions: {len(pyq_questions)}")
            
            break
            
    except Exception as e:
        logger.error(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_test_data())