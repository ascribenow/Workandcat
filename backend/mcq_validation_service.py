#!/usr/bin/env python3
"""
MCQ Validation Service for Twelvr Platform
Validates and fixes MCQ options to ensure admin answer appears in exactly one option
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import asyncio
import re
from database import Question, SessionLocal
from standardized_enrichment_engine import StandardizedEnrichmentEngine

logger = logging.getLogger(__name__)

class MCQValidationService:
    """
    Service to validate and fix MCQ options against admin-provided answers
    """
    
    def __init__(self):
        self.standardized_enricher = StandardizedEnrichmentEngine()
        logger.info("🎯 MCQ Validation Service initialized")
    
    def validate_mcq_options(self, question: Question) -> Dict[str, Any]:
        """
        Validate that admin answer appears in exactly one MCQ option
        
        Returns:
            Dict with validation result and details
        """
        try:
            if not question.mcq_options or not question.answer:
                return {
                    "valid": False,
                    "reason": "Missing MCQ options or admin answer",
                    "needs_regeneration": True
                }
            
            # Parse MCQ options
            try:
                mcq_data = json.loads(question.mcq_options)
            except json.JSONDecodeError:
                return {
                    "valid": False,
                    "reason": "Invalid JSON in MCQ options",
                    "needs_regeneration": True
                }
            
            if not isinstance(mcq_data, dict) or 'correct' not in mcq_data:
                return {
                    "valid": False,
                    "reason": "MCQ options missing required structure",
                    "needs_regeneration": True
                }
            
            # Extract MCQ choice values
            choices = {}
            for key in ['A', 'B', 'C', 'D']:
                if key in mcq_data:
                    choices[key] = mcq_data[key]
            
            if len(choices) != 4:
                return {
                    "valid": False,
                    "reason": f"Expected 4 MCQ options, found {len(choices)}",
                    "needs_regeneration": True
                }
            
            # Check if admin answer matches any MCQ option
            admin_answer = question.answer.strip()
            matching_options = []
            
            for option_key, option_value in choices.items():
                if self._answers_match(admin_answer, str(option_value)):
                    matching_options.append(option_key)
            
            # Validation logic
            if len(matching_options) == 0:
                return {
                    "valid": False,
                    "reason": f"Admin answer '{admin_answer}' not found in any MCQ option",
                    "mcq_options": choices,
                    "matching_options": matching_options,
                    "needs_regeneration": True
                }
            elif len(matching_options) > 1:
                return {
                    "valid": False,
                    "reason": f"Admin answer appears in multiple MCQ options: {matching_options}",
                    "mcq_options": choices,
                    "matching_options": matching_options,
                    "needs_regeneration": True
                }
            else:
                # Exactly one match - check if it's marked as correct
                correct_option = matching_options[0]
                marked_correct = mcq_data.get('correct', '').upper()
                
                if correct_option == marked_correct:
                    return {
                        "valid": True,
                        "reason": f"Admin answer correctly appears in option {correct_option}",
                        "matching_options": matching_options,
                        "needs_regeneration": False
                    }
                else:
                    return {
                        "valid": False,
                        "reason": f"Admin answer in option {correct_option}, but {marked_correct} marked as correct",
                        "matching_options": matching_options,
                        "needs_regeneration": True
                    }
        
        except Exception as e:
            logger.error(f"❌ MCQ validation failed for question {question.id}: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "needs_regeneration": True
            }
    
    def _answers_match(self, admin_answer: str, mcq_option: str) -> bool:
        """
        Check if admin answer matches an MCQ option using multiple criteria
        """
        try:
            admin_clean = admin_answer.strip().lower()
            option_clean = mcq_option.strip().lower()
            
            # 1. Exact match
            if admin_clean == option_clean:
                return True
            
            # 2. Admin answer contained in MCQ option or vice versa
            if admin_clean in option_clean or option_clean in admin_clean:
                return True
            
            # 3. Numeric match (extract and compare numbers)
            admin_numbers = re.findall(r'\d+\.?\d*', admin_answer)
            option_numbers = re.findall(r'\d+\.?\d*', mcq_option)
            
            if admin_numbers and option_numbers:
                try:
                    admin_num = float(admin_numbers[0])
                    option_num = float(option_numbers[0])
                    if abs(admin_num - option_num) < 0.01:
                        return True
                except (ValueError, IndexError):
                    pass
            
            # 4. Key word matching (at least 2 meaningful words)
            admin_words = set(admin_clean.split()) - {'the', 'is', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for', 'on', 'with'}
            option_words = set(option_clean.split()) - {'the', 'is', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for', 'on', 'with'}
            
            common_meaningful = admin_words.intersection(option_words)
            if len(common_meaningful) >= 2:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Answer matching failed: {e}")
            return False
    
    async def regenerate_mcq_options(self, question: Question, db: Session) -> Dict[str, Any]:
        """
        Regenerate MCQ options for a question to ensure admin answer is included
        """
        try:
            logger.info(f"🔄 Regenerating MCQ options for question {question.id}")
            
            # Generate new MCQ options using the standardized enricher
            mcq_result = await self.standardized_enricher.generate_mcq_options_with_schema(
                question.stem,
                question.answer,  # Use admin answer as the correct answer
                question.subcategory or "General"
            )
            
            if mcq_result and isinstance(mcq_result, dict):
                # Update question with new MCQ options
                question.mcq_options = json.dumps(mcq_result)
                db.commit()
                
                logger.info(f"✅ MCQ options regenerated for question {question.id}")
                return {
                    "success": True,
                    "new_mcq_options": mcq_result
                }
            else:
                logger.error(f"❌ MCQ regeneration failed for question {question.id}")
                return {
                    "success": False,
                    "error": "MCQ generation returned invalid data"
                }
        
        except Exception as e:
            logger.error(f"❌ MCQ regeneration error for question {question.id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_and_fix_question(self, question: Question, db: Session) -> Dict[str, Any]:
        """
        Validate and fix MCQ options for a single question
        """
        try:
            # Validate current MCQ options
            validation_result = self.validate_mcq_options(question)
            
            if validation_result["valid"]:
                return {
                    "question_id": str(question.id),
                    "action": "no_action_needed",
                    "result": "MCQ options are valid",
                    "validation": validation_result
                }
            
            # Regenerate if needed
            if validation_result["needs_regeneration"]:
                regeneration_result = await self.regenerate_mcq_options(question, db)
                
                if regeneration_result["success"]:
                    # Validate again after regeneration
                    post_validation = self.validate_mcq_options(question)
                    
                    return {
                        "question_id": str(question.id),
                        "action": "regenerated",
                        "result": "MCQ options regenerated and validated",
                        "initial_validation": validation_result,
                        "regeneration": regeneration_result,
                        "final_validation": post_validation
                    }
                else:
                    return {
                        "question_id": str(question.id),
                        "action": "regeneration_failed",
                        "result": "MCQ options could not be regenerated",
                        "validation": validation_result,
                        "regeneration_error": regeneration_result
                    }
            
            return {
                "question_id": str(question.id),
                "action": "validation_only",
                "result": "Validation completed but no regeneration needed",
                "validation": validation_result
            }
        
        except Exception as e:
            logger.error(f"❌ Question validation and fix failed for {question.id}: {e}")
            return {
                "question_id": str(question.id),
                "action": "error",
                "result": f"Processing error: {str(e)}"
            }
    
    async def nightly_mcq_validation_batch(self, limit: int = 100) -> Dict[str, Any]:
        """
        Nightly batch process to validate and fix MCQ options
        """
        logger.info(f"🌙 Starting nightly MCQ validation batch (limit: {limit})")
        
        results = {
            "total_processed": 0,
            "valid_questions": 0,
            "regenerated_questions": 0,
            "failed_questions": 0,
            "errors": []
        }
        
        try:
            db = SessionLocal()
            
            # Get questions with MCQ options that need validation
            questions = db.query(Question).filter(
                Question.mcq_options.isnot(None),
                Question.answer.isnot(None),
                Question.is_active == True
            ).limit(limit).all()
            
            logger.info(f"📋 Found {len(questions)} questions to validate")
            
            for question in questions:
                try:
                    result = await self.validate_and_fix_question(question, db)
                    results["total_processed"] += 1
                    
                    if result["action"] == "no_action_needed":
                        results["valid_questions"] += 1
                    elif result["action"] == "regenerated":
                        results["regenerated_questions"] += 1
                    elif result["action"] in ["regeneration_failed", "error"]:
                        results["failed_questions"] += 1
                        results["errors"].append(result)
                    
                    # Progress logging
                    if results["total_processed"] % 10 == 0:
                        logger.info(f"📊 Progress: {results['total_processed']}/{len(questions)} processed")
                    
                    # Small delay to be nice to APIs
                    await asyncio.sleep(0.1)
                
                except Exception as e:
                    results["failed_questions"] += 1
                    results["errors"].append({
                        "question_id": str(question.id),
                        "error": str(e)
                    })
                    logger.error(f"❌ Failed to process question {question.id}: {e}")
            
            db.close()
            
            # Final results
            success_rate = (results["valid_questions"] + results["regenerated_questions"]) / results["total_processed"] * 100 if results["total_processed"] > 0 else 0
            
            logger.info(f"🎉 Nightly MCQ validation completed!")
            logger.info(f"📊 Results: {results['total_processed']} processed, {results['valid_questions']} valid, {results['regenerated_questions']} regenerated, {results['failed_questions']} failed")
            logger.info(f"📈 Success rate: {success_rate:.1f}%")
            
            results["success_rate"] = success_rate
            return results
        
        except Exception as e:
            logger.error(f"❌ Nightly MCQ validation batch failed: {e}")
            results["errors"].append({"batch_error": str(e)})
            return results

# Global instance
mcq_validation_service = MCQValidationService()