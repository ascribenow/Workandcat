"""
Enhanced Question Processing Service
Integrates PYQ frequency analysis during question upload
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database import Question
from conceptual_frequency_analyzer import ConceptualFrequencyAnalyzer
from time_weighted_frequency_analyzer import TimeWeightedFrequencyAnalyzer, CAT_ANALYSIS_CONFIG

logger = logging.getLogger(__name__)

class EnhancedQuestionProcessor:
    """
    Processes questions during upload with integrated PYQ frequency analysis
    """
    
    def __init__(self, llm_pipeline):
        self.llm_pipeline = llm_pipeline
        self.conceptual_analyzer = ConceptualFrequencyAnalyzer(llm_pipeline)
        self.time_analyzer = TimeWeightedFrequencyAnalyzer(CAT_ANALYSIS_CONFIG)
        
    async def process_question_with_frequency_analysis(
        self, 
        question: Question, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Enhanced question processing with integrated PYQ frequency analysis
        """
        try:
            logger.info(f"Processing question {question.id} with PYQ frequency analysis")
            
            # Step 1: Conceptual Frequency Analysis
            conceptual_result = await self.conceptual_analyzer.calculate_conceptual_frequency(
                db, question, years_window=10
            )
            
            # Step 2: Time-Weighted Frequency Analysis
            temporal_result = await self.calculate_temporal_frequency(question, db)
            
            # Step 3: Calculate Integrated PYQ Frequency Score
            integrated_score = self.calculate_integrated_frequency_score(
                conceptual_result, temporal_result
            )
            
            # Step 4: Update question with frequency data
            await self.update_question_with_frequency_data(
                question, conceptual_result, temporal_result, integrated_score, db
            )
            
            return {
                'status': 'success',
                'question_id': str(question.id),
                'pyq_frequency_score': integrated_score,
                'conceptual_analysis': conceptual_result,
                'temporal_analysis': temporal_result,
                'processing_method': 'enhanced_integrated_analysis'
            }
            
        except Exception as e:
            logger.error(f"Error processing question {question.id}: {e}")
            # Set default values if analysis fails
            question.pyq_frequency_score = 0.5  # Default medium frequency
            question.frequency_analysis_method = 'fallback_default'
            question.frequency_last_updated = datetime.utcnow()
            
            await db.commit()
            
            return {
                'status': 'error',
                'question_id': str(question.id),
                'error': str(e),
                'pyq_frequency_score': 0.5
            }
    
    async def calculate_temporal_frequency(self, question: Question, db: AsyncSession) -> Dict[str, Any]:
        """
        Calculate temporal frequency using time-weighted analyzer
        """
        try:
            # Mock yearly occurrences data - in production this would come from PYQ database
            # For now, we'll simulate based on subcategory patterns
            yearly_occurrences = await self.get_yearly_occurrences_for_question(question, db)
            total_pyq_per_year = await self.get_total_pyq_per_year(db)
            
            # Calculate time-weighted frequency
            frequency_metrics = self.time_analyzer.calculate_time_weighted_frequency(
                yearly_occurrences, total_pyq_per_year
            )
            
            # Create temporal pattern
            temporal_pattern = self.time_analyzer.create_temporal_pattern(
                f"{question.subcategory}_{question.type_of_question or 'general'}",
                yearly_occurrences,
                total_pyq_per_year
            )
            
            # Generate insights
            insights = self.time_analyzer.generate_frequency_insights(temporal_pattern)
            
            return {
                'status': 'completed',
                'frequency_metrics': frequency_metrics,
                'temporal_pattern': {
                    'total_occurrences': temporal_pattern.total_occurrences,
                    'relevance_window_occurrences': temporal_pattern.relevance_window_occurrences,
                    'weighted_frequency_score': temporal_pattern.weighted_frequency_score,
                    'trend_direction': temporal_pattern.trend_direction,
                    'trend_strength': temporal_pattern.trend_strength,
                    'recency_score': temporal_pattern.recency_score
                },
                'insights': insights,
                'analysis_method': 'time_weighted_temporal'
            }
            
        except Exception as e:
            logger.error(f"Error in temporal frequency calculation: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'frequency_metrics': {'final_frequency_score': 0.5}
            }
    
    async def get_yearly_occurrences_for_question(self, question: Question, db: AsyncSession) -> Dict[int, int]:
        """
        Get yearly occurrences for question pattern from PYQ database
        In production, this would query actual PYQ data
        """
        try:
            # For now, simulate based on subcategory frequency patterns
            # TODO: Replace with actual PYQ database query when PYQ data is available
            
            # Simulate frequency based on CAT subcategory importance
            high_frequency_subcategories = [
                "Time–Speed–Distance (TSD)", "Percentages", "Profit–Loss–Discount (PLD)",
                "Linear Equations", "Triangles", "Divisibility", "Permutation–Combination (P&C)"
            ]
            
            medium_frequency_subcategories = [
                "Time & Work", "Ratio–Proportion–Variation", "Averages & Alligation",
                "Quadratic Equations", "Circles", "HCF–LCM", "Probability"
            ]
            
            # Generate realistic yearly data
            base_frequency = 0
            if question.subcategory in high_frequency_subcategories:
                base_frequency = 8  # High frequency topics
            elif question.subcategory in medium_frequency_subcategories:
                base_frequency = 4  # Medium frequency topics
            else:
                base_frequency = 2  # Lower frequency topics
            
            # Create 20-year data with emphasis on last 10 years
            yearly_data = {}
            current_year = datetime.now().year
            
            for year in range(current_year - 19, current_year + 1):
                if year >= current_year - 9:  # Last 10 years - higher frequency
                    yearly_data[year] = max(0, base_frequency + (year - (current_year - 10)))
                else:  # Older years - lower frequency
                    yearly_data[year] = max(0, base_frequency - 3)
            
            return yearly_data
            
        except Exception as e:
            logger.error(f"Error getting yearly occurrences: {e}")
            return {}
    
    async def get_total_pyq_per_year(self, db: AsyncSession) -> Dict[int, int]:
        """
        Get total PYQ questions per year for normalization
        """
        try:
            # Simulate total PYQ counts per year
            # CAT typically has 100 questions per year in QA section
            current_year = datetime.now().year
            total_per_year = {}
            
            for year in range(current_year - 19, current_year + 1):
                total_per_year[year] = 100  # CAT QA section questions per year
            
            return total_per_year
            
        except Exception as e:
            logger.error(f"Error getting total PYQ per year: {e}")
            return {}
    
    def calculate_integrated_frequency_score(
        self, 
        conceptual_result: Dict[str, Any], 
        temporal_result: Dict[str, Any]
    ) -> float:
        """
        Calculate integrated PYQ frequency score from conceptual and temporal analysis
        """
        try:
            # Extract scores from analysis results
            conceptual_score = conceptual_result.get('conceptual_score', 0.0) / 100.0  # Normalize to 0-1
            temporal_score = temporal_result.get('frequency_metrics', {}).get('final_frequency_score', 0.5)
            
            # Weight the scores: 60% conceptual (content understanding), 40% temporal (exam pattern)
            conceptual_weight = 0.6
            temporal_weight = 0.4
            
            integrated_score = (conceptual_score * conceptual_weight) + (temporal_score * temporal_weight)
            
            # Ensure score is between 0 and 1
            integrated_score = max(0.0, min(1.0, integrated_score))
            
            logger.info(f"Integrated score: {integrated_score:.4f} (conceptual: {conceptual_score:.4f}, temporal: {temporal_score:.4f})")
            
            return integrated_score
            
        except Exception as e:
            logger.error(f"Error calculating integrated frequency score: {e}")
            return 0.5  # Default to medium frequency
    
    async def update_question_with_frequency_data(
        self,
        question: Question,
        conceptual_result: Dict[str, Any],
        temporal_result: Dict[str, Any],
        integrated_score: float,
        db: AsyncSession
    ):
        """
        Update question with all frequency analysis data
        """
        try:
            # Update primary PYQ frequency score
            question.pyq_frequency_score = integrated_score
            
            # Update conceptual analysis data
            if conceptual_result.get('status') == 'completed':
                question.pyq_conceptual_matches = conceptual_result.get('conceptual_matches', 0)
                question.frequency_score = conceptual_result.get('conceptual_score', 0.0) / 100.0
                
                # Store pattern keywords and solution approach
                pattern_keywords = conceptual_result.get('pattern_keywords', [])
                solution_approach = conceptual_result.get('solution_approach', '')
                
                question.pattern_keywords = str(pattern_keywords) if pattern_keywords else '[]'
                question.pattern_solution_approach = solution_approach
            
            # Update temporal analysis data
            if temporal_result.get('status') == 'completed':
                temporal_pattern = temporal_result.get('temporal_pattern', {})
                question.pyq_occurrences_last_10_years = temporal_pattern.get('relevance_window_occurrences', 0)
                question.total_pyq_count = temporal_pattern.get('total_occurrences', 0)
            
            # Update frequency band based on integrated score
            if integrated_score >= 0.7:
                question.frequency_band = "High"
            elif integrated_score >= 0.4:
                question.frequency_band = "Medium"
            else:
                question.frequency_band = "Low"
            
            # Update metadata
            question.frequency_analysis_method = 'integrated_conceptual_temporal'
            question.frequency_last_updated = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Updated question {question.id} with integrated frequency data")
            
        except Exception as e:
            logger.error(f"Error updating question with frequency data: {e}")
            await db.rollback()
    
    async def batch_process_questions(
        self, 
        question_ids: List[str], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Batch process multiple questions with frequency analysis
        """
        try:
            results = []
            processed_count = 0
            error_count = 0
            
            for question_id in question_ids:
                try:
                    # Get question
                    from sqlalchemy import select
                    result = await db.execute(
                        select(Question).where(Question.id == question_id)
                    )
                    question = result.scalar_one_or_none()
                    
                    if not question:
                        logger.warning(f"Question {question_id} not found")
                        continue
                    
                    # Process question
                    processing_result = await self.process_question_with_frequency_analysis(
                        question, db
                    )
                    
                    results.append(processing_result)
                    
                    if processing_result['status'] == 'success':
                        processed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing question {question_id}: {e}")
                    error_count += 1
            
            return {
                'status': 'completed',
                'total_questions': len(question_ids),
                'processed_successfully': processed_count,
                'errors': error_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }