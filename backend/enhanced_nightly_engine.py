#!/usr/bin/env python3
"""
Enhanced Nightly Processing Engine for CAT Preparation Platform
Comprehensive processing with LLM-powered conceptual frequency analysis
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, desc, case
from database import (
    Question, User, Attempt, Mastery, Topic, Session,
    PYQQuestion, PYQPaper, PYQIngestion
)
from conceptual_frequency_analyzer import ConceptualFrequencyAnalyzer
from time_weighted_frequency_analyzer import TimeWeightedFrequencyAnalyzer, CAT_ANALYSIS_CONFIG

logger = logging.getLogger(__name__)

class EnhancedNightlyEngine:
    """
    Enhanced nightly processing engine with comprehensive frequency analysis
    Uses time-weighted frequency calculation for better accuracy
    """
    
    def __init__(self, llm_pipeline=None):
        self.time_analyzer = TimeWeightedFrequencyAnalyzer(CAT_ANALYSIS_CONFIG)
        self.conceptual_analyzer = ConceptualFrequencyAnalyzer(llm_pipeline) if llm_pipeline else None
        self.processing_stats = {
            'start_time': None,
            'end_time': None,
            'mastery_updates': 0,
            'frequency_updates': 0,
            'inactive_questions': 0,
            'errors': []
        }
    
    async def run_nightly_processing(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Run enhanced nightly processing tasks
        """
        self.processing_stats['start_time'] = datetime.utcnow()
        logger.info("🌙 Starting enhanced nightly processing...")
        
        try:
            # Task 1: Update mastery calculations
            logger.info("📊 Updating mastery calculations...")
            mastery_result = await self.update_mastery_calculations(db)
            self.processing_stats['mastery_updates'] = mastery_result.get('updated_count', 0)
            
            # Task 2: Enhanced PYQ frequency refresh
            logger.info("📈 Refreshing enhanced PYQ frequencies...")
            frequency_result = await self.refresh_enhanced_frequencies(db)
            self.processing_stats['frequency_updates'] = frequency_result.get('updated_questions', 0)
            
            # Task 3: Cleanup inactive questions
            logger.info("🧹 Cleaning up inactive questions...")
            cleanup_result = await self.cleanup_inactive_questions(db)
            self.processing_stats['inactive_questions'] = cleanup_result.get('cleaned_count', 0)
            
            # Task 4: Update question statistics
            logger.info("📋 Updating question statistics...")
            await self.update_question_statistics(db)
            
            self.processing_stats['end_time'] = datetime.utcnow()
            duration = self.processing_stats['end_time'] - self.processing_stats['start_time']
            
            logger.info(f"✅ Enhanced nightly processing completed in {duration.total_seconds():.1f} seconds")
            logger.info(f"   - Mastery updates: {self.processing_stats['mastery_updates']}")
            logger.info(f"   - Frequency updates: {self.processing_stats['frequency_updates']}")
            logger.info(f"   - Inactive questions handled: {self.processing_stats['inactive_questions']}")
            
            return {
                'status': 'completed',
                'duration_seconds': duration.total_seconds(),
                'stats': self.processing_stats
            }
            
        except Exception as e:
            logger.error(f"❌ Nightly processing failed: {e}")
            self.processing_stats['errors'].append(str(e))
            self.processing_stats['end_time'] = datetime.utcnow()
            
            return {
                'status': 'error',
                'error': str(e),
                'stats': self.processing_stats
            }
    
    async def update_mastery_calculations(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Update mastery calculations based on recent attempts
        """
        try:
            # Get users with recent attempts (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            recent_attempts = await db.execute(
                select(Attempt.user_id)
                .where(Attempt.created_at >= cutoff_time)
                .distinct()
            )
            
            active_users = [row.user_id for row in recent_attempts]
            
            if not active_users:
                logger.info("No users with recent attempts found")
                return {'updated_count': 0}
            
            updated_count = 0
            
            for user_id in active_users:
                try:
                    # Get user's attempt history by topic
                    user_attempts = await db.execute(
                        select(
                            Topic.id.label('topic_id'),
                            Topic.subcategory,
                            func.count(Attempt.id).label('total_attempts'),
                            func.sum(func.cast(Attempt.correct, func.Integer)).label('correct_attempts'),
                            func.avg(func.cast(Attempt.correct, func.Float)).label('accuracy')
                        )
                        .join(Question, Attempt.question_id == Question.id)
                        .join(Topic, Question.topic_id == Topic.id)
                        .where(Attempt.user_id == user_id)
                        .group_by(Topic.id, Topic.subcategory)
                    )
                    
                    for row in user_attempts:
                        accuracy = row.accuracy or 0.0
                        
                        # Update or create mastery record
                        existing_mastery = await db.execute(
                            select(Mastery)
                            .where(
                                and_(
                                    Mastery.user_id == user_id,
                                    Mastery.topic_id == row.topic_id
                                )
                            )
                        )
                        
                        mastery_record = existing_mastery.scalar_one_or_none()
                        
                        if mastery_record:
                            # Update existing record
                            mastery_record.mastery_pct = accuracy
                            mastery_record.total_attempts = row.total_attempts
                            mastery_record.correct_attempts = row.correct_attempts
                            mastery_record.last_updated = datetime.utcnow()
                        else:
                            # Create new record
                            mastery_record = Mastery(
                                user_id=user_id,
                                topic_id=row.topic_id,
                                mastery_pct=accuracy,
                                total_attempts=row.total_attempts,
                                correct_attempts=row.correct_attempts,
                                last_updated=datetime.utcnow()
                            )
                            db.add(mastery_record)
                        
                        updated_count += 1
                
                except Exception as user_error:
                    logger.error(f"Error updating mastery for user {user_id}: {user_error}")
                    continue
            
            await db.commit()
            logger.info(f"Updated mastery for {updated_count} topic-user combinations")
            
            return {'updated_count': updated_count}
            
        except Exception as e:
            logger.error(f"Error in mastery calculations: {e}")
            return {'updated_count': 0, 'error': str(e)}
    
    async def refresh_enhanced_frequencies(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Refresh PYQ frequencies using enhanced time-weighted analysis
        """
        try:
            logger.info("Starting enhanced PYQ frequency refresh...")
            
            # Get all active questions that need frequency analysis
            questions_query = await db.execute(
                select(Question)
                .where(Question.is_active == True)
                .order_by(Question.id)
            )
            
            questions = questions_query.scalars().all()
            updated_count = 0
            frequency_distribution = {}
            
            for question in questions:
                try:
                    # Get PYQ data for this subcategory
                    pyq_data = await self.get_pyq_temporal_data(db, question.subcategory)
                    
                    if pyq_data['yearly_occurrences']:
                        # Calculate time-weighted frequency
                        frequency_result = self.time_analyzer.calculate_time_weighted_frequency(
                            pyq_data['yearly_occurrences'],
                            pyq_data['total_pyq_per_year']
                        )
                        
                        # Update question with PYQ frequency data only (other frequency fields removed)
                        question.pyq_frequency_score = frequency_result.get('weighted_frequency', 0.0)
                        # frequency_score, frequency_band, frequency_notes removed as per requirements
                        question.last_frequency_update = datetime.utcnow()
                        
                        # Track frequency distribution using pyq_frequency_score ranges
                        pyq_score = question.pyq_frequency_score or 0.0
                        if pyq_score >= 0.7:
                            band = "High"
                        elif pyq_score >= 0.4:
                            band = "Medium"
                        else:
                            band = "Low"
                        frequency_distribution[band] = frequency_distribution.get(band, 0) + 1
                        updated_count += 1
                    
                except Exception as q_error:
                    logger.error(f"Error processing question {question.id}: {q_error}")
                    continue
            
            await db.commit()
            
            logger.info(f"Enhanced frequency refresh completed successfully")
            logger.info(f"Updated {updated_count} questions")
            logger.info(f"Frequency distribution: {frequency_distribution}")
            
            return {
                'status': 'completed',
                'updated_questions': updated_count,
                'distribution': frequency_distribution,
                'method': 'time_weighted_analysis'
            }
                
        except Exception as e:
            logger.error(f"Error in enhanced frequency refresh: {e}")
            return {
                'status': 'error',
                'updated_questions': 0,
                'error': str(e)
            }
    
    async def get_pyq_temporal_data(self, db: AsyncSession, subcategory: str) -> Dict[str, Any]:
        """
        Get temporal PYQ data for a subcategory
        """
        try:
            # Get PYQ questions for this subcategory with year information
            pyq_query = await db.execute(
                select(
                    PYQPaper.year,
                    func.count(PYQQuestion.id).label('question_count')
                )
                .join(PYQQuestion, PYQPaper.id == PYQQuestion.paper_id)
                .where(PYQQuestion.subcategory == subcategory)
                .group_by(PYQPaper.year)
                .order_by(PYQPaper.year)
            )
            
            yearly_occurrences = {}
            for row in pyq_query:
                yearly_occurrences[row.year] = row.question_count
            
            # Get total PYQ questions per year for normalization
            total_query = await db.execute(
                select(
                    PYQPaper.year,
                    func.count(PYQQuestion.id).label('total_count')
                )
                .join(PYQQuestion, PYQPaper.id == PYQQuestion.paper_id)
                .group_by(PYQPaper.year)
                .order_by(PYQPaper.year)
            )
            
            total_pyq_per_year = {}
            for row in total_query:
                total_pyq_per_year[row.year] = row.total_count
            
            return {
                'yearly_occurrences': yearly_occurrences,
                'total_pyq_per_year': total_pyq_per_year
            }
            
        except Exception as e:
            logger.error(f"Error getting PYQ temporal data for {subcategory}: {e}")
            return {
                'yearly_occurrences': {},
                'total_pyq_per_year': {}
            }
    
    # determine_frequency_band method removed as frequency_band field was deleted
    
    async def cleanup_inactive_questions(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Clean up questions that should be inactive or have issues
        """
        try:
            cleaned_count = 0
            
            # Find questions with missing required data
            problematic_questions = await db.execute(
                select(Question)
                .where(
                    or_(
                        Question.stem.is_(None),
                        Question.stem == '',
                        Question.answer.is_(None),
                        Question.answer == '',
                        Question.subcategory.is_(None),
                        Question.subcategory == ''
                    )
                )
            )
            
            for question in problematic_questions.scalars():
                if question.is_active:
                    question.is_active = False
                    question.frequency_notes = "Deactivated: Missing required data"
                    cleaned_count += 1
            
            # Find questions with broken images
            broken_image_questions = await db.execute(
                select(Question)
                .where(
                    and_(
                        Question.has_image == True,
                        or_(
                            Question.image_url.is_(None),
                            Question.image_url == ''
                        )
                    )
                )
            )
            
            for question in broken_image_questions.scalars():
                question.has_image = False
                question.image_url = None
                question.image_alt_text = None
                cleaned_count += 1
            
            await db.commit()
            
            logger.info(f"Cleaned up {cleaned_count} problematic questions")
            
            return {'cleaned_count': cleaned_count}
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
            return {'cleaned_count': 0, 'error': str(e)}
    
    async def update_question_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Update overall question statistics and counts
        """
        try:
            # Get overall statistics
            stats_query = await db.execute(
                select(
                    func.count(Question.id).label('total_questions'),
                    func.sum(func.cast(Question.is_active, func.Integer)).label('active_questions'),
                    func.count(func.distinct(Question.subcategory)).label('unique_subcategories'),
                    func.count(func.distinct(Question.difficulty_band)).label('difficulty_levels')
                )
            )
            
            stats = stats_query.first()
            
            # Get frequency distribution using pyq_frequency_score ranges  
            freq_dist = await db.execute(
                select(
                    case(
                        (Question.pyq_frequency_score >= 0.7, 'High'),
                        (Question.pyq_frequency_score >= 0.4, 'Medium'),
                        else_='Low'
                    ).label('freq_band'),
                    func.count(Question.id).label('count')
                ).where(Question.is_active == True)
                .group_by(
                    case(
                        (Question.pyq_frequency_score >= 0.7, 'High'),
                        (Question.pyq_frequency_score >= 0.4, 'Medium'),
                        else_='Low'
                    )
                )
            )
            
            frequency_distribution = {}
            for row in freq_dist:
                band = row.freq_band or 'None'
                frequency_distribution[band] = row.count
            
            logger.info(f"Question statistics updated:")
            logger.info(f"  - Total questions: {stats.total_questions}")
            logger.info(f"  - Active questions: {stats.active_questions}")
            logger.info(f"  - Unique subcategories: {stats.unique_subcategories}")
            logger.info(f"  - Frequency distribution: {frequency_distribution}")
            
            return {
                'total_questions': stats.total_questions,
                'active_questions': stats.active_questions,
                'unique_subcategories': stats.unique_subcategories,
                'frequency_distribution': frequency_distribution
            }
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return {'error': str(e)}
    
    async def get_processing_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get summary of the current processing status
        """
        try:
            # Get enhanced frequency summary
            frequency_summary = await self.get_enhanced_frequency_summary(db)
            
            # Get recent processing stats
            return {
                'last_processing': self.processing_stats,
                'frequency_analysis': frequency_summary,
                'system_status': 'enhanced_processing_active'
            }
            
        except Exception as e:
            logger.error(f"Error getting processing summary: {e}")
            return {
                'error': str(e),
                'system_status': 'error'
            }
    
    async def get_enhanced_frequency_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get summary of enhanced frequency analysis
        """
        try:
            # Get frequency band distribution
            freq_dist = await db.execute(
                select(
                    Question.frequency_band,
                    func.count(Question.id).label('count'),
                    func.avg(Question.frequency_score).label('avg_score')
                )
                .where(Question.is_active == True)
                .group_by(Question.frequency_band)
            )
            
            distribution = {}
            for row in freq_dist:
                band = row.frequency_band or 'Unanalyzed'
                distribution[band] = {
                    'count': row.count,
                    'avg_score': round(row.avg_score or 0.0, 3)
                }
            
            # Get recent updates
            recent_updates = await db.execute(
                select(func.count(Question.id))
                .where(
                    and_(
                        Question.is_active == True,
                        Question.last_frequency_update >= datetime.utcnow() - timedelta(days=1)
                    )
                )
            )
            
            recent_count = recent_updates.scalar() or 0
            
            return {
                'method': 'time_weighted_analysis',
                'frequency_distribution': distribution,
                'recent_updates_24h': recent_count,
                'analyzer_config': {
                    'total_data_years': self.time_analyzer.config.total_data_years,
                    'relevance_window_years': self.time_analyzer.config.relevance_window_years,
                    'decay_rate': self.time_analyzer.config.decay_rate
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced frequency summary: {e}")
            return {
                'error': str(e),
                'method': 'time_weighted_analysis'
            }