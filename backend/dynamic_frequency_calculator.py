#!/usr/bin/env python3
"""
Dynamic Frequency Calculator
Real-time PYQ frequency calculation based on conceptual matching for regular questions
"""

import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from database import PYQQuestion, PYQPaper, Question
from production_concept_extractor import ProductionConceptExtractor
from advanced_similarity_calculator import AdvancedSimilarityCalculator

logger = logging.getLogger(__name__)

class DynamicFrequencyCalculator:
    """
    Calculate true PYQ frequency for regular questions based on sophisticated conceptual matching
    Replaces hardcoded frequency scores with real CAT exam intelligence
    """
    
    def __init__(self):
        self.concept_extractor = ProductionConceptExtractor()
        self.similarity_calculator = AdvancedSimilarityCalculator()
        
        # Configuration
        self.similarity_threshold = 0.4  # Minimum similarity for meaningful match
        self.recent_years_window = 5     # Years for time-weighted analysis  
        self.total_years_window = 10     # Total historical analysis window
    
    async def calculate_true_pyq_frequency(self, regular_question: Question, db: AsyncSession) -> Dict[str, Any]:
        """
        Calculate actual PYQ frequency based on conceptual matching with historical CAT questions
        This replaces the hardcoded 0.4-0.8 frequency scores with real exam intelligence
        """
        try:
            logger.info(f"🧮 Calculating true PYQ frequency for regular question {regular_question.id}")
            
            # STEP 1: Extract concepts from the regular question
            regular_concepts = await self.concept_extractor.extract_question_concepts(regular_question)
            
            if not regular_concepts or not regular_concepts.get('core_concepts'):
                logger.warning(f"⚠️ No concepts extracted for question {regular_question.id}")
                return self._create_default_frequency_result()
            
            logger.info(f"📋 Extracted {len(regular_concepts['core_concepts'])} concepts from regular question")
            
            # STEP 2: Get all active PYQ questions from analysis window
            active_pyqs = await self._get_active_pyq_questions(db, self.total_years_window)
            
            if not active_pyqs:
                logger.warning(f"⚠️ No active PYQ questions found for frequency analysis")
                return self._create_default_frequency_result()
            
            logger.info(f"📊 Analyzing against {len(active_pyqs)} active PYQ questions")
            
            # STEP 3: Find conceptual matches with similarity scoring
            conceptual_matches = await self._find_conceptual_matches(regular_concepts, active_pyqs)
            
            # STEP 4: Calculate frequency metrics
            frequency_metrics = self._calculate_frequency_metrics(conceptual_matches, len(active_pyqs))
            
            # STEP 5: Time-weighted analysis
            time_weighted_metrics = self._calculate_time_weighted_metrics(conceptual_matches, len(active_pyqs))
            
            # STEP 6: Generate comprehensive frequency analysis
            frequency_result = {
                'frequency_score': frequency_metrics['base_frequency'],
                'time_weighted_frequency': time_weighted_metrics['recent_frequency'],
                'conceptual_matches_count': len(conceptual_matches),
                'total_pyq_analyzed': len(active_pyqs),
                'average_similarity': frequency_metrics['average_similarity'],
                'confidence_score': frequency_metrics['confidence_score'],
                'top_matching_years': time_weighted_metrics['top_categories'],
                'matching_concepts_summary': frequency_metrics['concept_summary'],
                'frequency_trend': time_weighted_metrics['trend_analysis'],
                'calculation_metadata': {
                    'similarity_threshold': self.similarity_threshold,
                    'analysis_window_years': self.total_years_window,
                    'recent_years_window': self.recent_years_window,
                    'calculation_timestamp': datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"✅ Frequency analysis complete: {frequency_result['frequency_score']:.3f} overall, {frequency_result['time_weighted_frequency']:.3f} recent")
            return frequency_result
            
        except Exception as e:
            logger.error(f"❌ Error calculating true PYQ frequency: {e}")
            return self._create_default_frequency_result(error=str(e))
    
    async def _get_active_pyq_questions(self, db: AsyncSession, years_window: int = None) -> List[PYQQuestion]:
        """
        Get all active PYQ questions from the database (no year filtering as per user requirement)
        Frequency calculated based on overall populated entries of PYQ database
        """
        try:
            result = await db.execute(
                select(PYQQuestion)
                .where(
                    and_(
                        PYQQuestion.is_active == True,
                        PYQQuestion.core_concepts.isnot(None)
                    )
                )
                .order_by(desc(PYQQuestion.created_at))
            )
            
            pyq_questions = result.scalars().all()
            logger.info(f"📊 Retrieved {len(pyq_questions)} active PYQ questions from entire database (no year filtering)")
            
            return pyq_questions
            
        except Exception as e:
            logger.error(f"❌ Error retrieving active PYQ questions: {e}")
            return []
    
    async def _find_conceptual_matches(self, regular_concepts: Dict[str, Any], active_pyqs: List[PYQQuestion]) -> List[Dict[str, Any]]:
        """
        Find PYQ questions that match the regular question conceptually
        """
        try:
            conceptual_matches = []
            
            for pyq_q in active_pyqs:
                try:
                    # Parse PYQ concepts
                    if not pyq_q.core_concepts:
                        continue
                    
                    pyq_concepts = {
                        'core_concepts': json.loads(pyq_q.core_concepts),
                        'solution_method': pyq_q.solution_method or 'general_approach',
                        'operations': json.loads(pyq_q.operations_required) if pyq_q.operations_required else [],
                        'structure_type': pyq_q.problem_structure or 'standard_problem',
                        'complexity_indicators': json.loads(pyq_q.concept_difficulty) if pyq_q.concept_difficulty else [],
                        'concept_keywords': json.loads(pyq_q.concept_keywords) if pyq_q.concept_keywords else []
                    }
                    
                    # Calculate similarity
                    similarity_score = self.similarity_calculator.calculate_advanced_conceptual_similarity(
                        regular_concepts, pyq_concepts
                    )
                    
                    # Check if similarity meets threshold
                    if similarity_score >= self.similarity_threshold:
                        conceptual_matches.append({
                            'pyq_id': str(pyq_q.id),
                            'similarity': similarity_score,
                            'concepts': pyq_concepts['core_concepts'],
                            'difficulty_band': pyq_q.difficulty_band,
                            'subcategory': pyq_q.subcategory
                        })
                
                except Exception as parse_error:
                    logger.warning(f"⚠️ Error parsing PYQ {pyq_q.id}: {parse_error}")
                    continue
            
            logger.info(f"🎯 Found {len(conceptual_matches)} conceptual matches above threshold {self.similarity_threshold}")
            return conceptual_matches
            
        except Exception as e:
            logger.error(f"❌ Error finding conceptual matches: {e}")
            return []
    
    def _calculate_frequency_metrics(self, conceptual_matches: List[Dict[str, Any]], total_pyqs: int) -> Dict[str, Any]:
        """
        Calculate base frequency metrics from conceptual matches
        """
        try:
            if not conceptual_matches or not total_pyqs:
                return {
                    'base_frequency': 0.0,
                    'average_similarity': 0.0,
                    'confidence_score': 0.0,
                    'concept_summary': []
                }
            
            # Base frequency = matches / total
            base_frequency = len(conceptual_matches) / total_pyqs
            
            # Average similarity score
            similarities = [match['similarity'] for match in conceptual_matches]
            average_similarity = np.mean(similarities)
            
            # Confidence score based on number of matches and similarity strength
            match_confidence = min(1.0, len(conceptual_matches) / 10)  # More matches = higher confidence
            similarity_confidence = average_similarity  # Higher similarity = higher confidence
            confidence_score = (match_confidence + similarity_confidence) / 2
            
            # Concept summary - most common concepts in matches
            all_concepts = []
            for match in conceptual_matches:
                all_concepts.extend(match.get('concepts', []))
            
            concept_counts = {}
            for concept in all_concepts:
                concept_counts[concept] = concept_counts.get(concept, 0) + 1
            
            concept_summary = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'base_frequency': min(1.0, base_frequency),  # Cap at 1.0
                'average_similarity': average_similarity,
                'confidence_score': confidence_score,
                'concept_summary': concept_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating frequency metrics: {e}")
            return {
                'base_frequency': 0.0,
                'average_similarity': 0.0,
                'confidence_score': 0.0,
                'concept_summary': []
            }
    
    def _calculate_time_weighted_metrics(self, conceptual_matches: List[Dict[str, Any]], total_pyqs: int) -> Dict[str, Any]:
        """
        Calculate weighted frequency metrics based on overall PYQ database entries (no year dependency)
        """
        try:
            if not conceptual_matches:
                return {
                    'recent_frequency': 0.0,
                    'top_categories': [],
                    'trend_analysis': 'insufficient_data'
                }
            
            # Calculate frequency based on total conceptual matches
            overall_frequency = len(conceptual_matches) / total_pyqs if total_pyqs > 0 else 0.0
            
            # Category distribution instead of year distribution
            category_counts = {}
            for match in conceptual_matches:
                category = match.get('subcategory', 'Unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Trend analysis based on category distribution
            if len(top_categories) >= 3:
                # Simple trend analysis based on category diversity
                total_matches = sum(count for category, count in top_categories)
                top_category_dominance = top_categories[0][1] / total_matches if total_matches > 0 else 0
                
                if top_category_dominance > 0.6:
                    trend_analysis = 'concentrated'  # One category dominates
                elif top_category_dominance < 0.3:
                    trend_analysis = 'diverse'  # Well distributed across categories
                else:
                    trend_analysis = 'balanced'  # Moderate distribution
            else:
                trend_analysis = 'limited_data'
            
            return {
                'recent_frequency': min(1.0, overall_frequency),
                'top_categories': [category for category, count in top_categories],
                'trend_analysis': trend_analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating time-weighted metrics: {e}")
            return {
                'recent_frequency': 0.0,
                'top_categories': [],
                'trend_analysis': 'calculation_error'
            }
    
    def _create_default_frequency_result(self, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Create default frequency result for error cases or when no data available
        """
        return {
            'frequency_score': 0.5,  # Neutral default
            'time_weighted_frequency': 0.5,
            'conceptual_matches_count': 0,
            'total_pyq_analyzed': 0,
            'average_similarity': 0.0,
            'confidence_score': 0.0,
            'top_matching_years': [],
            'matching_concepts_summary': [],
            'frequency_trend': 'no_data',
            'calculation_metadata': {
                'similarity_threshold': self.similarity_threshold,
                'analysis_window_years': self.total_years_window,
                'recent_years_window': self.recent_years_window,
                'calculation_timestamp': datetime.utcnow().isoformat(),
                'error': error
            }
        }
    
    async def batch_calculate_frequencies(self, question_ids: List[str], db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """
        Calculate frequencies for multiple questions in batch for efficiency
        """
        try:
            logger.info(f"🔄 Starting batch frequency calculation for {len(question_ids)} questions")
            
            results = {}
            
            # Get all questions at once
            questions_result = await db.execute(
                select(Question)
                .where(Question.id.in_(question_ids))
            )
            questions = {str(q.id): q for q in questions_result.scalars()}
            
            # Get PYQ data once for all calculations
            active_pyqs = await self._get_active_pyq_questions(db, self.total_years_window)
            
            if not active_pyqs:
                logger.warning("⚠️ No active PYQ questions for batch calculation")
                return {qid: self._create_default_frequency_result() for qid in question_ids}
            
            # Process each question
            for question_id in question_ids:
                if question_id in questions:
                    question = questions[question_id]
                    try:
                        result = await self.calculate_true_pyq_frequency(question, db)
                        results[question_id] = result
                        logger.info(f"✅ Calculated frequency for question {question_id}")
                    except Exception as q_error:
                        logger.error(f"❌ Error calculating frequency for question {question_id}: {q_error}")
                        results[question_id] = self._create_default_frequency_result(error=str(q_error))
                else:
                    logger.warning(f"⚠️ Question {question_id} not found")
                    results[question_id] = self._create_default_frequency_result(error="Question not found")
            
            logger.info(f"✅ Batch frequency calculation complete: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in batch frequency calculation: {e}")
            return {qid: self._create_default_frequency_result(error=str(e)) for qid in question_ids}

# Utility functions for integration
async def calculate_frequency_for_question(question_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Utility function to calculate frequency for a single question
    """
    try:
        from database import Question
        
        question = await db.get(Question, question_id)
        if not question:
            return {"success": False, "error": "Question not found"}
        
        calculator = DynamicFrequencyCalculator()
        frequency_result = await calculator.calculate_true_pyq_frequency(question, db)
        
        return {"success": True, "frequency_data": frequency_result}
        
    except Exception as e:
        logger.error(f"Error calculating frequency for question: {e}")
        return {"success": False, "error": str(e)}

async def update_all_question_frequencies(db: AsyncSession, batch_size: int = 50) -> Dict[str, Any]:
    """
    Update PYQ frequency scores for all active questions
    """
    try:
        logger.info("🔄 Starting mass frequency update for all questions")
        
        # Get all active questions
        result = await db.execute(
            select(Question)
            .where(Question.is_active == True)
        )
        all_questions = result.scalars().all()
        
        if not all_questions:
            return {"success": False, "error": "No active questions found"}
        
        total_questions = len(all_questions)
        logger.info(f"📊 Found {total_questions} active questions to update")
        
        calculator = DynamicFrequencyCalculator()
        updated_count = 0
        error_count = 0
        
        # Process in batches
        for i in range(0, total_questions, batch_size):
            batch = all_questions[i:i + batch_size]
            batch_ids = [str(q.id) for q in batch]
            
            logger.info(f"🔄 Processing batch {i//batch_size + 1}: questions {i+1}-{min(i+batch_size, total_questions)}")
            
            # Calculate frequencies for batch
            batch_results = await calculator.batch_calculate_frequencies(batch_ids, db)
            
            # Update questions with results
            for question in batch:
                question_id = str(question.id)
                if question_id in batch_results:
                    frequency_data = batch_results[question_id]
                    
                    # Update question with new frequency data
                    question.pyq_frequency_score = frequency_data['frequency_score']
                    question.pyq_conceptual_matches = frequency_data['conceptual_matches_count']
                    question.frequency_analysis_method = 'dynamic_conceptual_matching'
                    
                    updated_count += 1
                else:
                    error_count += 1
            
            # Commit batch
            await db.commit()
            logger.info(f"✅ Batch {i//batch_size + 1} complete")
        
        logger.info(f"🎉 Mass frequency update complete: {updated_count} updated, {error_count} errors")
        
        return {
            "success": True,
            "total_questions": total_questions,
            "updated_count": updated_count,
            "error_count": error_count,
            "batch_size": batch_size
        }
        
    except Exception as e:
        logger.error(f"❌ Error in mass frequency update: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test the dynamic frequency calculator
    import asyncio
    
    async def test_calculator():
        calculator = DynamicFrequencyCalculator()
        print("✅ Dynamic Frequency Calculator initialized successfully")
        print(f"🎯 Similarity threshold: {calculator.similarity_threshold}")
        print(f"📊 Analysis window: {calculator.total_years_window} years")
    
    asyncio.run(test_calculator())