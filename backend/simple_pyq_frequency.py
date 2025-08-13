"""
Simple PYQ Frequency Calculator
Calculates question frequency based on simple counting from uploaded PYQ documents
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from database import Question, PYQQuestion, PYQPaper, PYQIngestion, AsyncSession

logger = logging.getLogger(__name__)

class SimplePYQFrequencyCalculator:
    """
    Simple frequency calculator based on uploaded PYQ documents
    No complex time-weighting or conceptual analysis - just straightforward counting
    """
    
    def __init__(self):
        self.frequency_bands = {
            'High': (6, float('inf')),    # 6+ occurrences
            'Medium': (3, 5),            # 3-5 occurrences  
            'Low': (1, 2)                # 1-2 occurrences
        }
    
    async def calculate_simple_frequencies(self, db: AsyncSession) -> Dict[str, any]:
        """
        Calculate simple PYQ frequencies for all questions based on subcategory matching
        """
        try:
            logger.info("Starting simple PYQ frequency calculation...")
            
            # Get all active questions
            questions_result = await db.execute(
                select(Question).where(Question.is_active == True)
            )
            questions = questions_result.scalars().all()
            
            # Get PYQ frequency data by subcategory
            pyq_frequencies = await self.get_pyq_frequency_by_subcategory(db)
            
            updated_count = 0
            frequency_stats = {'High': 0, 'Medium': 0, 'Low': 0, 'None': 0}
            
            for question in questions:
                # Simple matching by subcategory
                subcategory = question.subcategory
                pyq_count = pyq_frequencies.get(subcategory, 0)
                
                # Determine frequency band
                frequency_band = self.determine_frequency_band(pyq_count)
                
                # Update question with simple frequency data
                question.frequency_band = frequency_band
                question.frequency_score = float(pyq_count)
                question.pyq_conceptual_matches = pyq_count  # Simple count
                question.total_pyq_analyzed = sum(pyq_frequencies.values())
                question.frequency_analysis_method = 'simple_subcategory_count'
                question.frequency_last_updated = func.now()
                question.pyq_occurrences_last_10_years = pyq_count  # Simplified - all as recent
                question.total_pyq_count = pyq_count
                
                frequency_stats[frequency_band] += 1
                updated_count += 1
            
            await db.commit()
            
            logger.info(f"Simple PYQ frequency calculation completed:")
            logger.info(f"  - Updated {updated_count} questions")
            logger.info(f"  - High frequency: {frequency_stats['High']} questions")
            logger.info(f"  - Medium frequency: {frequency_stats['Medium']} questions") 
            logger.info(f"  - Low frequency: {frequency_stats['Low']} questions")
            logger.info(f"  - No PYQ data: {frequency_stats['None']} questions")
            
            return {
                'status': 'completed',
                'updated_questions': updated_count,
                'frequency_distribution': frequency_stats,
                'total_pyq_subcategories': len(pyq_frequencies)
            }
            
        except Exception as e:
            logger.error(f"Error in simple PYQ frequency calculation: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'updated_questions': 0
            }
    
    async def get_pyq_frequency_by_subcategory(self, db: AsyncSession) -> Dict[str, int]:
        """
        Get simple count of PYQ questions by subcategory from uploaded documents
        """
        try:
            # Query PYQ questions grouped by subcategory
            result = await db.execute(
                select(
                    PYQQuestion.subcategory,
                    func.count(PYQQuestion.id).label('count')
                )
                .group_by(PYQQuestion.subcategory)
                .having(func.count(PYQQuestion.id) > 0)
            )
            
            frequency_map = {}
            for row in result:
                if row.subcategory and row.subcategory.strip():
                    frequency_map[row.subcategory.strip()] = int(row.count)
            
            logger.info(f"Found PYQ frequency data for {len(frequency_map)} subcategories")
            
            return frequency_map
            
        except Exception as e:
            logger.error(f"Error getting PYQ frequency by subcategory: {e}")
            return {}
    
    def determine_frequency_band(self, count: int) -> str:
        """
        Determine frequency band based on simple count thresholds
        """
        if count == 0:
            return 'None'
        
        for band, (min_val, max_val) in self.frequency_bands.items():
            if min_val <= count <= max_val:
                return band
        
        return 'Low'  # Default fallback
    
    async def get_frequency_summary(self, db: AsyncSession) -> Dict[str, any]:
        """
        Get summary of current PYQ frequency analysis
        """
        try:
            # Get frequency distribution from questions
            result = await db.execute(
                select(
                    Question.frequency_band,
                    func.count(Question.id).label('count'),
                    func.avg(Question.frequency_score).label('avg_score')
                )
                .where(Question.is_active == True)
                .group_by(Question.frequency_band)
            )
            
            distribution = {}
            total_questions = 0
            
            for row in result:
                band = row.frequency_band or 'None'
                count = int(row.count)
                distribution[band] = {
                    'count': count,
                    'average_score': float(row.avg_score or 0)
                }
                total_questions += count
            
            # Get total PYQ data available
            pyq_result = await db.execute(
                select(func.count(PYQQuestion.id))
            )
            total_pyq_questions = pyq_result.scalar() or 0
            
            # Get total PYQ papers/documents
            papers_result = await db.execute(
                select(func.count(PYQPaper.id))
            )
            total_pyq_papers = papers_result.scalar() or 0
            
            return {
                'total_questions_analyzed': total_questions,
                'frequency_distribution': distribution,
                'pyq_data_summary': {
                    'total_pyq_questions': total_pyq_questions,
                    'total_pyq_papers': total_pyq_papers
                },
                'analysis_method': 'simple_subcategory_count',
                'last_updated': 'Available in individual question records'
            }
            
        except Exception as e:
            logger.error(f"Error getting frequency summary: {e}")
            return {
                'total_questions_analyzed': 0,
                'frequency_distribution': {},
                'error': str(e)
            }
    
    async def update_question_frequency(self, question_id: str, db: AsyncSession) -> Dict[str, any]:
        """
        Update frequency for a single question based on current PYQ data
        """
        try:
            # Get the question
            result = await db.execute(
                select(Question).where(Question.id == question_id)
            )
            question = result.scalar_one_or_none()
            
            if not question:
                return {'status': 'error', 'message': 'Question not found'}
            
            # Get PYQ count for this subcategory
            pyq_count = await self.get_subcategory_pyq_count(question.subcategory, db)
            
            # Update question
            question.frequency_band = self.determine_frequency_band(pyq_count)
            question.frequency_score = float(pyq_count)
            question.pyq_conceptual_matches = pyq_count
            question.frequency_analysis_method = 'simple_subcategory_count'
            question.frequency_last_updated = func.now()
            question.pyq_occurrences_last_10_years = pyq_count
            question.total_pyq_count = pyq_count
            
            await db.commit()
            
            return {
                'status': 'updated',
                'question_id': question_id,
                'subcategory': question.subcategory,
                'pyq_count': pyq_count,
                'frequency_band': question.frequency_band
            }
            
        except Exception as e:
            logger.error(f"Error updating single question frequency: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_subcategory_pyq_count(self, subcategory: str, db: AsyncSession) -> int:
        """
        Get PYQ count for a specific subcategory
        """
        try:
            result = await db.execute(
                select(func.count(PYQQuestion.id))
                .where(PYQQuestion.subcategory == subcategory)
            )
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting subcategory PYQ count: {e}")
            return 0
    
    async def get_high_frequency_topics(self, db: AsyncSession, limit: int = 20) -> List[Dict[str, any]]:
        """
        Get top high-frequency topics based on simple PYQ counting
        """
        try:
            result = await db.execute(
                select(
                    Question.subcategory,
                    Question.frequency_band,
                    func.avg(Question.frequency_score).label('avg_frequency'),
                    func.count(Question.id).label('question_count')
                )
                .where(
                    and_(
                        Question.is_active == True,
                        Question.frequency_band.in_(['High', 'Medium'])
                    )
                )
                .group_by(Question.subcategory, Question.frequency_band)
                .order_by(func.avg(Question.frequency_score).desc())
                .limit(limit)
            )
            
            high_frequency_topics = []
            for row in result:
                high_frequency_topics.append({
                    'subcategory': row.subcategory,
                    'frequency_band': row.frequency_band,
                    'average_pyq_count': float(row.avg_frequency),
                    'total_questions': int(row.question_count)
                })
            
            return high_frequency_topics
            
        except Exception as e:
            logger.error(f"Error getting high frequency topics: {e}")
            return []