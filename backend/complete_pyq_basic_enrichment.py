#!/usr/bin/env python3
"""
Complete PYQ Basic Enrichment Service
Completes the missing basic enrichment for PYQ questions that still have placeholder text
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import PYQQuestion
from advanced_llm_enrichment_service import AdvancedLLMEnrichmentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompletePYQBasicEnrichmentService:
    """Service to complete missing basic enrichment for PYQ questions"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize database connection
        self.mongo_url = os.getenv('MONGO_URL')
        if not self.mongo_url:
            raise ValueError("MONGO_URL environment variable not found")
        
        self.engine = create_engine(self.mongo_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize the advanced LLM service
        self.advanced_enricher = AdvancedLLMEnrichmentService()
        
        logger.info("✅ CompletePYQBasicEnrichmentService initialized")
    
    async def complete_missing_enrichment(self) -> dict:
        """Complete missing basic enrichment for all PYQ questions"""
        try:
            logger.info("🚀 Starting Complete PYQ Basic Enrichment Process...")
            
            with self.SessionLocal() as db:
                # Find all PYQ questions with placeholder text
                incomplete_questions = self._find_incomplete_pyq_questions(db)
                
                logger.info(f"📊 Found {len(incomplete_questions)} PYQ questions with incomplete enrichment")
                
                results = {
                    "total_incomplete": len(incomplete_questions),
                    "processed_successfully": 0,
                    "processing_errors": 0,
                    "detailed_results": [],
                    "processing_started_at": datetime.utcnow().isoformat()
                }
                
                for i, question in enumerate(incomplete_questions):
                    logger.info(f"🔄 Processing question {i+1}/{len(incomplete_questions)}: {question.stem[:50]}...")
                    
                    try:
                        # Complete the basic enrichment
                        enrichment_result = await self._complete_question_enrichment(question, db)
                        
                        if enrichment_result["success"]:
                            results["processed_successfully"] += 1
                            logger.info("✅ Successfully completed enrichment")
                        else:
                            results["processing_errors"] += 1
                            logger.error(f"❌ Failed to complete enrichment: {enrichment_result['error']}")
                        
                        results["detailed_results"].append({
                            "question_id": question.id,
                            "stem": question.stem[:100],
                            "success": enrichment_result["success"],
                            "error": enrichment_result.get("error"),
                            "fields_completed": enrichment_result.get("fields_completed", [])
                        })
                        
                        # Small delay to avoid overwhelming the API
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing question {question.id}: {e}")
                        results["processing_errors"] += 1
                        results["detailed_results"].append({
                            "question_id": question.id,
                            "stem": question.stem[:100],
                            "success": False,
                            "error": str(e),
                            "fields_completed": []
                        })
                
                results["processing_completed_at"] = datetime.utcnow().isoformat()
                results["success_rate"] = (results["processed_successfully"] / len(incomplete_questions) * 100) if incomplete_questions else 100
                
                logger.info(f"🎉 PYQ Basic Enrichment Completion finished!")
                logger.info(f"📈 Success Rate: {results['success_rate']:.1f}% ({results['processed_successfully']}/{len(incomplete_questions)})")
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Complete PYQ Basic Enrichment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_completed_at": datetime.utcnow().isoformat()
            }
    
    def _find_incomplete_pyq_questions(self, db: Session) -> list:
        """Find all PYQ questions with placeholder text in basic fields"""
        try:
            # Query for questions with placeholder text
            query = """
            SELECT * FROM pyq_questions 
            WHERE is_active = true 
            AND (
                answer = 'To be generated by LLM' 
                OR subcategory = 'To be classified by LLM' 
                OR type_of_question = 'To be classified by LLM'
            )
            ORDER BY created_at DESC
            """
            
            result = db.execute(text(query))
            rows = result.fetchall()
            
            # Convert to PYQQuestion objects
            incomplete_questions = []
            for row in rows:
                question = db.query(PYQQuestion).filter(PYQQuestion.id == row.id).first()
                if question:
                    incomplete_questions.append(question)
            
            logger.info(f"🔍 Found {len(incomplete_questions)} incomplete PYQ questions")
            return incomplete_questions
            
        except Exception as e:
            logger.error(f"❌ Error finding incomplete questions: {e}")
            return []
    
    async def _complete_question_enrichment(self, question: PYQQuestion, db: Session) -> dict:
        """Complete enrichment for a single PYQ question"""
        try:
            fields_completed = []
            
            # Identify what needs to be completed
            needs_answer = not question.answer or question.answer == "To be generated by LLM"
            needs_subcategory = not question.subcategory or question.subcategory == "To be classified by LLM"
            needs_type = not question.type_of_question or question.type_of_question == "To be classified by LLM"
            
            logger.info(f"📋 Question needs - Answer: {needs_answer}, Subcategory: {needs_subcategory}, Type: {needs_type}")
            
            if needs_answer or needs_subcategory or needs_type:
                # Use the advanced enrichment service to complete the question
                enrichment_result = await self.advanced_enricher.enrich_pyq_question(question, db)
                
                if enrichment_result["success"]:
                    # Check what was completed
                    updated_question = db.query(PYQQuestion).filter(PYQQuestion.id == question.id).first()
                    
                    if needs_answer and updated_question.answer and updated_question.answer != "To be generated by LLM":
                        fields_completed.append("answer")
                    
                    if needs_subcategory and updated_question.subcategory and updated_question.subcategory != "To be classified by LLM":
                        fields_completed.append("subcategory")
                    
                    if needs_type and updated_question.type_of_question and updated_question.type_of_question != "To be classified by LLM":
                        fields_completed.append("type_of_question")
                    
                    logger.info(f"✅ Completed fields: {fields_completed}")
                    
                    return {
                        "success": True,
                        "fields_completed": fields_completed,
                        "enrichment_method": "advanced_llm_service"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Advanced enrichment failed: {enrichment_result.get('error', 'Unknown error')}",
                        "fields_completed": []
                    }
            else:
                return {
                    "success": True,
                    "fields_completed": [],
                    "message": "No fields needed completion"
                }
                
        except Exception as e:
            logger.error(f"❌ Error completing enrichment for question {question.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "fields_completed": []
            }

async def main():
    """Main function to run the complete PYQ basic enrichment"""
    try:
        service = CompletePYQBasicEnrichmentService()
        results = await service.complete_missing_enrichment()
        
        print("\n" + "="*60)
        print("COMPLETE PYQ BASIC ENRICHMENT RESULTS")
        print("="*60)
        print(f"Total Incomplete Questions: {results.get('total_incomplete', 0)}")
        print(f"Successfully Processed: {results.get('processed_successfully', 0)}")
        print(f"Processing Errors: {results.get('processing_errors', 0)}")
        print(f"Success Rate: {results.get('success_rate', 0):.1f}%")
        print("="*60)
        
        # Show detailed results for failed questions
        failed_questions = [r for r in results.get('detailed_results', []) if not r['success']]
        if failed_questions:
            print(f"\n❌ FAILED QUESTIONS ({len(failed_questions)}):")
            for result in failed_questions[:5]:  # Show first 5 failures
                print(f"- {result['question_id']}: {result['error']}")
            if len(failed_questions) > 5:
                print(f"... and {len(failed_questions) - 5} more")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main())