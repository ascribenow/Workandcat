#!/usr/bin/env python3
"""
Create comprehensive sample data for CAT Preparation Platform v2.0
"""

import asyncio
import sys
import os
sys.path.append('/app/backend')

from database import (
    get_database, init_database, User, Topic, Question, 
    DiagnosticSet, DiagnosticSetQuestion, Mastery
)
from sqlalchemy import select, func
from auth_service import AuthService
from llm_enrichment import LLMEnrichmentPipeline, CANONICAL_TAXONOMY
from diagnostic_system import DiagnosticSystem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample questions with rich content
SAMPLE_QUESTIONS = [
    {
        "stem": "A train travels at 60 km/h and covers a distance of 240 km. How much time does it take?",
        "answer": "4 hours",
        "subcategory": "Time–Speed–Distance (TSD)",
        "category": "Arithmetic",
        "source": "Sample",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Time–Speed–Distance (TSD)"
    },
    {
        "stem": "If 20% of a number is 80, what is 25% of that number?",
        "answer": "100",
        "subcategory": "Percentages",
        "category": "Arithmetic",
        "source": "Sample",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Percentages"
    },
    {
        "stem": "Solve for x: 2x + 5 = 13",
        "answer": "4",
        "subcategory": "Linear Equations",
        "category": "Algebra",
        "source": "Sample",
        "hint_category": "Algebra",
        "hint_subcategory": "Linear Equations"
    },
    {
        "stem": "Find the area of a triangle with base 10 cm and height 8 cm.",
        "answer": "40 cm²",
        "subcategory": "Triangles",
        "category": "Geometry & Mensuration",
        "source": "Sample",
        "hint_category": "Geometry & Mensuration",
        "hint_subcategory": "Triangles"
    },
    {
        "stem": "What is the HCF of 24 and 36?",
        "answer": "12",
        "subcategory": "HCF–LCM",
        "category": "Number System",
        "source": "Sample",
        "hint_category": "Number System",
        "hint_subcategory": "HCF–LCM"
    },
    {
        "stem": "In how many ways can 5 people be arranged in a row?",
        "answer": "120",
        "subcategory": "Permutation–Combination (P&C)",
        "category": "Modern Math",
        "source": "Sample",
        "hint_category": "Modern Math",
        "hint_subcategory": "Permutation–Combination (P&C)"
    },
    {
        "stem": "A man can complete a job in 12 days. A woman can complete the same job in 18 days. How long will it take if they work together?",
        "answer": "7.2 days",
        "subcategory": "Time & Work",
        "category": "Arithmetic",
        "source": "Sample",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Time & Work"
    },
    {
        "stem": "If x² - 7x + 12 = 0, find the sum of the roots.",
        "answer": "7",
        "subcategory": "Quadratic Equations",
        "category": "Algebra",
        "source": "Sample",
        "hint_category": "Algebra",
        "hint_subcategory": "Quadratic Equations"
    },
    {
        "stem": "The probability of getting a head when a coin is tossed is:",
        "answer": "0.5",
        "subcategory": "Probability",
        "category": "Modern Math",
        "source": "Sample",
        "hint_category": "Modern Math",
        "hint_subcategory": "Probability"
    },
    {
        "stem": "Simple Interest on ₹1000 at 10% per annum for 2 years is:",
        "answer": "₹200",
        "subcategory": "Simple & Compound Interest (SI–CI)",
        "category": "Arithmetic",
        "source": "Sample",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Simple & Compound Interest (SI–CI)"
    },
    {
        "stem": "A car travels from city A to city B at 40 km/h and returns at 60 km/h. What is the average speed for the entire journey?",
        "answer": "48 km/h",
        "subcategory": "Time–Speed–Distance (TSD)",
        "category": "Arithmetic",
        "source": "Sample",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Time–Speed–Distance (TSD)"
    },
    {
        "stem": "Find the value of log₂ 8.",
        "answer": "3",
        "subcategory": "Logarithms & Exponents",
        "category": "Algebra",
        "source": "Sample",
        "hint_category": "Algebra",
        "hint_subcategory": "Logarithms & Exponents"
    },
    {
        "stem": "What is the circumference of a circle with radius 7 cm? (Take π = 22/7)",
        "answer": "44 cm",
        "subcategory": "Circles",
        "category": "Geometry & Mensuration",
        "source": "Sample",
        "hint_category": "Geometry & Mensuration",
        "hint_subcategory": "Circles"
    },
    {
        "stem": "A number when divided by 7 leaves remainder 3. What remainder will it leave when divided by 14?",
        "answer": "3 or 10",
        "subcategory": "Remainders & Modular Arithmetic",
        "category": "Number System",
        "source": "Sample",
        "hint_category": "Number System",
        "hint_subcategory": "Remainders & Modular Arithmetic"
    },
    {
        "stem": "In a class of 30 students, 18 study Mathematics and 12 study Physics. If 5 students study both subjects, how many study neither?",
        "answer": "5",
        "subcategory": "Set Theory & Venn Diagrams",
        "category": "Modern Math",
        "source": "Sample",
        "hint_category": "Modern Math",
        "hint_subcategory": "Set Theory & Venn Diagrams"
    },
    # Additional questions for diagnostic completeness
    {
        "stem": "Two trains approach each other at speeds of 60 km/h and 40 km/h. They are initially 200 km apart. After how much time will they meet?",
        "answer": "2 hours",
        "subcategory": "Time–Speed–Distance (TSD)",
        "category": "Arithmetic",
        "source": "Diagnostic",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Time–Speed–Distance (TSD)"
    },
    {
        "stem": "The ratio of ages of A and B is 3:4. If A is 15 years old, what is B's age?",
        "answer": "20 years",
        "subcategory": "Ratio–Proportion–Variation",
        "category": "Arithmetic",
        "source": "Diagnostic",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Ratio–Proportion–Variation"
    },
    {
        "stem": "A shopkeeper marks an article 30% above cost price and gives 20% discount. Find his profit percentage.",
        "answer": "4%",
        "subcategory": "Profit–Loss–Discount (PLD)",
        "category": "Arithmetic",
        "source": "Diagnostic",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Profit–Loss–Discount (PLD)"
    },
    {
        "stem": "The average of 5 numbers is 27. If one more number is added, the average becomes 25. What is the sixth number?",
        "answer": "15",
        "subcategory": "Averages & Alligation",
        "category": "Arithmetic",
        "source": "Diagnostic",
        "hint_category": "Arithmetic",
        "hint_subcategory": "Averages & Alligation"
    },
    {
        "stem": "Find the value of x if x² - 5x + 6 = 0.",
        "answer": "2 or 3",
        "subcategory": "Quadratic Equations",
        "category": "Algebra",
        "source": "Diagnostic",
        "hint_category": "Algebra",
        "hint_subcategory": "Quadratic Equations"
    },
    {
        "stem": "If |x - 3| = 5, find all possible values of x.",
        "answer": "8 or -2",
        "subcategory": "Inequalities",
        "category": "Algebra",
        "source": "Diagnostic",
        "hint_category": "Algebra",
        "hint_subcategory": "Inequalities"
    },
    {
        "stem": "In an AP, if the first term is 5 and common difference is 3, what is the 10th term?",
        "answer": "32",
        "subcategory": "Progressions",
        "category": "Algebra",
        "source": "Diagnostic",
        "hint_category": "Algebra",
        "hint_subcategory": "Progressions"
    },
    {
        "stem": "Find the domain of f(x) = 1/(x-2).",
        "answer": "R - {2}",
        "subcategory": "Functions & Graphs",
        "category": "Algebra",
        "source": "Diagnostic",
        "hint_category": "Algebra",
        "hint_subcategory": "Functions & Graphs"
    },
    {
        "stem": "In a right triangle, one angle is 30°. If the hypotenuse is 10 cm, find the length of the side opposite to 30°.",
        "answer": "5 cm",
        "subcategory": "Triangles",
        "category": "Geometry & Mensuration",
        "source": "Diagnostic",
        "hint_category": "Geometry & Mensuration",
        "hint_subcategory": "Triangles"
    },
    {
        "stem": "A chord of length 8 cm is drawn in a circle of radius 5 cm. Find the distance of the chord from the center.",
        "answer": "3 cm",
        "subcategory": "Circles",
        "category": "Geometry & Mensuration",
        "source": "Diagnostic",
        "hint_category": "Geometry & Mensuration",
        "hint_subcategory": "Circles"
    }
]

async def create_topics():
    """Create topic hierarchy from canonical taxonomy"""
    async for db in get_database():
        try:
            # Check if topics already exist
            existing_count = await db.scalar(
                select(func.count(Topic.id))
            )
            
            if existing_count > 0:
                logger.info(f"Topics already exist ({existing_count} found)")
                return
            
            logger.info("Creating topic hierarchy...")
            
            # Create main categories and subcategories
            for category, subcategories in CANONICAL_TAXONOMY.items():
                # Create main category
                main_topic = Topic(
                    name=category,
                    slug=category.lower().replace(" ", "_").replace("&", "and"),
                    centrality=0.8,
                    section="QA"
                )
                db.add(main_topic)
                await db.flush()  # Get ID
                
                logger.info(f"Created category: {category}")
                
                # Create subcategories
                for subcategory in subcategories.keys():
                    sub_topic = Topic(
                        name=subcategory,
                        parent_id=main_topic.id,
                        slug=subcategory.lower().replace(" ", "_").replace("–", "_").replace("(", "").replace(")", "").replace("/", "_"),
                        centrality=0.6,
                        section="QA"
                    )
                    db.add(sub_topic)
                
                logger.info(f"Created {len(subcategories)} subcategories for {category}")
            
            await db.commit()
            logger.info("✅ Topic hierarchy created successfully")
            break
            
        except Exception as e:
            logger.error(f"Error creating topics: {e}")
            await db.rollback()
            raise

async def create_users():
    """Create admin and sample users"""
    async for db in get_database():
        try:
            auth_service = AuthService()
            
            # Check if admin already exists
            from sqlalchemy import select
            existing_admin = await db.execute(
                select(User).where(User.email == "sumedhprabhu18@gmail.com")
            )
            if existing_admin.scalar_one_or_none():
                logger.info("Admin user already exists")
            else:
                # Create admin user
                admin_user = User(
                    email="sumedhprabhu18@gmail.com",
                    full_name="Sumedh Prabhu",
                    password_hash=auth_service.hash_password("admin2025"),
                    is_admin=True
                )
                db.add(admin_user)
                logger.info("✅ Created admin user: sumedhprabhu18@gmail.com")
            
            # Create sample student
            existing_student = await db.execute(
                select(User).where(User.email == "student@catprep.com")
            )
            if existing_student.scalar_one_or_none():
                logger.info("Student user already exists")
            else:
                student_user = User(
                    email="student@catprep.com",
                    full_name="Test Student",
                    password_hash=auth_service.hash_password("student123"),
                    is_admin=False
                )
                db.add(student_user)
                logger.info("✅ Created student user: student@catprep.com")
            
            await db.commit()
            break
            
        except Exception as e:
            logger.error(f"Error creating users: {e}")
            await db.rollback()
            raise

async def create_questions():
    """Create sample questions with LLM enrichment"""
    async for db in get_database():
        try:
            from sqlalchemy import select
            
            # Check if questions already exist
            existing_count = await db.scalar(
                select(func.count(Question.id))
            )
            
            if existing_count > 0:
                logger.info(f"Questions already exist ({existing_count} found)")
                return
            
            logger.info("Creating sample questions with LLM enrichment...")
            
            # Initialize LLM pipeline
            llm_pipeline = LLMEnrichmentPipeline(os.getenv('EMERGENT_LLM_KEY'))
            
            created_questions = []
            
            for i, question_data in enumerate(SAMPLE_QUESTIONS):
                try:
                    logger.info(f"Processing question {i+1}/{len(SAMPLE_QUESTIONS)}: {question_data['stem'][:50]}...")
                    
                    # Find the topic for this question
                    topic_result = await db.execute(
                        select(Topic).where(Topic.name == question_data["subcategory"])
                    )
                    topic = topic_result.scalar_one_or_none()
                    
                    if not topic:
                        logger.warning(f"Topic not found for: {question_data['subcategory']}")
                        continue
                    
                    # Create basic question first
                    question = Question(
                        stem=question_data["stem"],
                        answer=question_data["answer"],
                        subcategory=question_data["subcategory"],
                        topic_id=topic.id,
                        source=question_data["source"],
                        is_active=False  # Will be activated after enrichment
                    )
                    
                    db.add(question)
                    await db.flush()  # Get ID
                    
                    # Run LLM enrichment
                    enrichment_result = await llm_pipeline.enrich_question(
                        question_data["stem"],
                        question_data["answer"],
                        question_data["source"],
                        question_data["hint_category"],
                        question_data["hint_subcategory"]
                    )
                    
                    # Update question with enrichment data
                    question.subcategory = enrichment_result["subcategory"]
                    question.solution_approach = enrichment_result["solution_approach"]
                    question.detailed_solution = enrichment_result["detailed_solution"]
                    question.difficulty_score = enrichment_result["difficulty_score"]
                    question.difficulty_band = enrichment_result["difficulty_band"]
                    question.frequency_band = enrichment_result["frequency_band"]
                    question.frequency_notes = enrichment_result.get("frequency_notes", "")
                    question.learning_impact = enrichment_result["learning_impact"]
                    question.learning_impact_band = enrichment_result["learning_impact_band"]
                    question.importance_index = enrichment_result["importance_index"]
                    question.importance_band = enrichment_result["importance_band"]
                    question.video_url = enrichment_result["video_url"]
                    question.version = 1
                    question.is_active = True
                    
                    created_questions.append(question)
                    logger.info(f"✅ Enriched question: {question.difficulty_band} difficulty, {question.importance_band} importance")
                    
                    # Small delay to avoid overwhelming the LLM API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing question {i+1}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"✅ Created {len(created_questions)} enriched questions")
            break
            
        except Exception as e:
            logger.error(f"Error creating questions: {e}")
            await db.rollback()
            raise

async def create_diagnostic_set():
    """Create the 25-question diagnostic set"""
    async for db in get_database():
        try:
            diagnostic_system = DiagnosticSystem()
            
            # Create diagnostic set (this will select appropriate questions)
            diagnostic_set = await diagnostic_system.create_diagnostic_set(db)
            
            logger.info(f"✅ Created diagnostic set: {diagnostic_set.name}")
            break
            
        except Exception as e:
            logger.error(f"Error creating diagnostic set: {e}")
            raise

async def create_sample_mastery():
    """Create sample mastery data for demonstration"""
    async for db in get_database():
        try:
            from sqlalchemy import select
            
            # Get student user
            student_result = await db.execute(
                select(User).where(User.email == "student@catprep.com")
            )
            student = student_result.scalar_one_or_none()
            
            if not student:
                logger.warning("Student user not found, skipping mastery creation")
                return
            
            # Get some topics
            topics_result = await db.execute(
                select(Topic).where(Topic.parent_id.isnot(None)).limit(5)
            )
            topics = topics_result.scalars().all()
            
            # Create sample mastery data
            for topic in topics:
                mastery = Mastery(
                    user_id=student.id,
                    topic_id=topic.id,
                    exposure_score=5.0 + (hash(str(topic.id)) % 10),
                    accuracy_easy=0.6 + (hash(str(topic.id)) % 30) / 100,
                    accuracy_med=0.4 + (hash(str(topic.id)) % 40) / 100,
                    accuracy_hard=0.2 + (hash(str(topic.id)) % 30) / 100,
                    efficiency_score=0.5 + (hash(str(topic.id)) % 40) / 100,
                    mastery_pct=0.3 + (hash(str(topic.id)) % 50) / 100
                )
                db.add(mastery)
            
            await db.commit()
            logger.info(f"✅ Created sample mastery data for {len(topics)} topics")
            break
            
        except Exception as e:
            logger.error(f"Error creating sample mastery: {e}")
            await db.rollback()
            raise

async def main():
    """Main function to create all sample data"""
    logger.info("🚀 Creating comprehensive sample data for CAT Preparation Platform v2.0")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        logger.info("1. Initializing database...")
        await init_database()
        
        # Create topics
        logger.info("2. Creating topic hierarchy...")
        await create_topics()
        
        # Create users
        logger.info("3. Creating users...")
        await create_users()
        
        # Create questions
        logger.info("4. Creating and enriching questions...")
        await create_questions()
        
        # Create diagnostic set
        logger.info("5. Creating diagnostic set...")
        await create_diagnostic_set()
        
        # Create sample mastery data
        logger.info("6. Creating sample mastery data...")
        await create_sample_mastery()
        
        logger.info("=" * 80)
        logger.info("🎉 Sample data creation completed successfully!")
        logger.info("\n📋 Login Credentials:")
        logger.info("   👨‍💼 Admin: sumedhprabhu18@gmail.com / admin2025")
        logger.info("   🧑‍🎓 Student: student@catprep.com / student123")
        logger.info("\n🌐 Access the app at:")
        logger.info("   https://learning-tutor.preview.emergentagent.com")
        
    except Exception as e:
        logger.error(f"❌ Error in sample data creation: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())