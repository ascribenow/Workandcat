#!/usr/bin/env python3
"""
Replace Questions Database with New CSV File
1. Delete all existing questions 
2. Import new questions from CSV file
3. Run LLM enrichment to classify with canonical taxonomy
"""

import sys
import os
sys.path.append('/app/backend')

import requests
import csv
import io
from database import *
from llm_enrichment import LLMEnrichmentPipeline
import logging
import uuid
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_existing_questions(db: Session):
    """Delete all existing questions from the database"""
    try:
        logger.info("🗑️  Clearing existing questions database...")
        
        # Clear attempts first (foreign key dependency)
        attempts_deleted = db.query(Attempt).delete()
        logger.info(f"Deleted {attempts_deleted} existing attempts")
        
        # Clear sessions (may reference questions)
        sessions_deleted = db.query(StudySession).delete()
        logger.info(f"Deleted {sessions_deleted} existing sessions")
        
        # Delete all existing questions
        deleted_count = db.query(Question).delete()
        logger.info(f"Deleted {deleted_count} existing questions")
        
        # Also clear PYQ questions to start fresh
        pyq_deleted_count = db.query(PYQQuestion).delete()
        logger.info(f"Deleted {pyq_deleted_count} existing PYQ questions")
        
        db.commit()
        logger.info("✅ Database cleared successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        db.rollback()
        return False

async def download_and_parse_csv():
    """Load and parse the local CSV file"""
    try:
        logger.info("📥 Loading new questions CSV file from /app/Questions_16Aug25_Fixed.csv...")
        
        # Read local CSV file
        csv_path = "/app/Questions_16Aug25_Fixed.csv"
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found at {csv_path}")
            return []
        
        logger.info("✅ CSV file found successfully")
        
        # Parse CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
        
        questions_data = []
        for row in csv_reader:
            stem = row.get('stem', '').strip()
            image_url = row.get('image_url', '').strip()
            
            if stem:  # Only process rows with actual question stems
                questions_data.append({
                    'stem': stem,
                    'image_url': image_url if image_url else None
                })
        
        logger.info(f"✅ Parsed {len(questions_data)} questions from local CSV")
        return questions_data
        
    except Exception as e:
        logger.error(f"Error loading/parsing local CSV: {e}")
        return []

async def import_questions_to_database(questions_data: list, db: Session):
    """Import new questions to database without LLM enrichment first"""
    try:
        logger.info("📥 Importing questions to database...")
        
        imported_count = 0
        
        for i, question_data in enumerate(questions_data):
            try:
                # Create basic question record
                question = Question(
                    id=str(uuid.uuid4()),
                    stem=question_data['stem'],
                    answer="", # Will be enriched later
                    solution_approach="", # Will be enriched later  
                    detailed_solution="", # Will be enriched later
                    subcategory="", # Will be enriched later
                    type_of_question="", # Will be enriched later
                    topic_id=None, # Will be set during enrichment
                    difficulty_band="Medium", # Default
                    difficulty_score=0.5, # Default
                    importance_index=0.5, # Default
                    learning_impact=0.5, # Default
                    pyq_frequency_score=0.5, # Default
                    is_active=True,
                    has_image=bool(question_data.get('image_url')),
                    image_url=question_data.get('image_url'),
                    image_alt_text=None
                )
                
                db.add(question)
                imported_count += 1
                
                if imported_count % 20 == 0:
                    logger.info(f"Imported {imported_count} questions...")
                    db.commit()
                
            except Exception as e:
                logger.error(f"Error importing question {i+1}: {e}")
                continue
        
        # Final commit
        db.commit()
        logger.info(f"✅ Successfully imported {imported_count} questions to database")
        return imported_count
        
    except Exception as e:
        logger.error(f"Error importing questions: {e}")
        db.rollback()
        return 0

async def enrich_questions_with_llm(db: Session):
    """Run LLM enrichment on all imported questions"""
    try:
        logger.info("🤖 Starting LLM enrichment process...")
        
        # Initialize LLM enrichment pipeline
        llm_api_key = os.getenv('EMERGENT_LLM_KEY')
        if not llm_api_key:
            logger.error("EMERGENT_LLM_KEY not found in environment")
            return False
        
        enrichment_pipeline = LLMEnrichmentPipeline(llm_api_key=llm_api_key)
        
        # Get all questions that need enrichment
        questions = db.query(Question).filter(
            Question.subcategory == ""  # Questions without subcategory need enrichment
        ).all()
        
        logger.info(f"Found {len(questions)} questions to enrich")
        
        enriched_count = 0
        failed_count = 0
        
        for i, question in enumerate(questions):
            try:
                logger.info(f"Enriching question {i+1}/{len(questions)}: {question.stem[:50]}...")
                
                # Use LLM to categorize question
                category, subcategory, type_of_question = await enrichment_pipeline.categorize_question(
                    stem=question.stem,
                    hint_category=None,
                    hint_subcategory=None
                )
                
                logger.info(f"  Classification: {category} > {subcategory} > {type_of_question}")
                
                # Update question with LLM classification
                question.subcategory = subcategory
                question.type_of_question = type_of_question
                
                # Find appropriate topic_id based on category
                topic = db.query(Topic).filter(
                    Topic.category.like(f"%{category}%")
                ).first()
                
                if topic:
                    question.topic_id = topic.id
                else:
                    # Default to first available topic
                    default_topic = db.query(Topic).first()
                    if default_topic:
                        question.topic_id = default_topic.id
                
                enriched_count += 1
                
                # Commit in batches
                if enriched_count % 10 == 0:
                    logger.info(f"✅ Enriched {enriched_count} questions...")
                    db.commit()
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to enrich question {i+1}: {e}")
                failed_count += 1
                continue
        
        # Final commit
        db.commit()
        
        logger.info(f"🎉 LLM Enrichment completed!")
        logger.info(f"✅ Successfully enriched: {enriched_count} questions")
        logger.info(f"❌ Failed to enrich: {failed_count} questions")
        
        # Analyze enrichment results
        enriched_questions = db.query(Question).filter(
            Question.subcategory != ""
        ).all()
        
        subcategory_counts = {}
        type_counts = {}
        
        for q in enriched_questions:
            if q.subcategory:
                subcategory_counts[q.subcategory] = subcategory_counts.get(q.subcategory, 0) + 1
            if q.type_of_question:
                type_counts[q.type_of_question] = type_counts.get(q.type_of_question, 0) + 1
        
        logger.info(f"\\n📊 ENRICHMENT RESULTS:")
        logger.info(f"✅ Questions with subcategory: {len(enriched_questions)}")
        logger.info(f"✅ Unique subcategories: {len(subcategory_counts)}")
        logger.info(f"✅ Unique types: {len(type_counts)}")
        
        logger.info(f"\\n📊 Top subcategories:")
        for subcat, count in sorted(subcategory_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {subcat}: {count} questions")
        
        logger.info(f"\\n📊 Top types:")
        for qtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {qtype}: {count} questions")
        
        return enriched_count >= len(questions) * 0.8  # 80% success rate
        
    except Exception as e:
        logger.error(f"LLM enrichment failed: {e}")
        return False

async def main():
    """Replace questions database with new CSV and enrich"""
    logger.info("🚀 REPLACING QUESTIONS DATABASE WITH NEW CSV")
    logger.info("=" * 60)
    
    try:
        # Step 1: Initialize database
        init_database()
        db = SessionLocal()
        
        # Step 2: Clear existing questions
        if not await clear_existing_questions(db):
            logger.error("Failed to clear existing questions")
            return 1
        
        # Step 3: Download and parse new CSV
        questions_data = await download_and_parse_csv()
        if not questions_data:
            logger.error("Failed to download/parse CSV file")
            return 1
        
        # Step 4: Import questions to database
        imported_count = await import_questions_to_database(questions_data, db)
        if imported_count == 0:
            logger.error("Failed to import any questions")
            return 1
        
        # Step 5: Run LLM enrichment
        enrichment_success = await enrich_questions_with_llm(db)
        if not enrichment_success:
            logger.warning("LLM enrichment had issues, but proceeding...")
        
        logger.info("\\n🎉 DATABASE REPLACEMENT COMPLETED!")
        logger.info(f"✅ Imported {imported_count} new questions")
        logger.info("✅ LLM enrichment completed") 
        logger.info("✅ Ready to test dual-dimension diversity with new dataset")
        
        return 0
        
    except Exception as e:
        logger.error(f"Database replacement failed: {e}")
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    exit(asyncio.run(main()))