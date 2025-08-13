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
from sqlalchemy import select, func, and_, or_, text, desc
from database import (
    Question, User, Attempt, Mastery, Topic, Session,
    PYQQuestion, PYQPaper, PYQIngestion
)
from time_weighted_frequency_analyzer import TimeWeightedFrequencyAnalyzer, CAT_ANALYSIS_CONFIG

logger = logging.getLogger(__name__)

class EnhancedNightlyEngine:
    """
    Enhanced nightly processing engine with comprehensive frequency analysis
    Uses time-weighted frequency calculation for better accuracy
    """
    
    def __init__(self):
        self.time_analyzer = TimeWeightedFrequencyAnalyzer(CAT_ANALYSIS_CONFIG)
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
    
    async def refresh_simple_frequencies(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Refresh PYQ frequencies using simple calculation method
        """
        try:
            logger.info("Starting simple PYQ frequency refresh...")
            
            # Use the simple PYQ frequency calculator
            result = await self.pyq_calculator.calculate_simple_frequencies(db)
            
            if result.get('status') == 'completed':
                logger.info(f"Simple frequency refresh completed successfully")
                logger.info(f"Updated {result.get('updated_questions', 0)} questions")
                logger.info(f"Frequency distribution: {result.get('frequency_distribution', {})}")
                
                return {
                    'status': 'completed',
                    'updated_questions': result.get('updated_questions', 0),
                    'distribution': result.get('frequency_distribution', {}),
                    'method': 'simple_subcategory_count'
                }
            else:
                logger.error(f"Simple frequency refresh failed: {result.get('error', 'Unknown error')}")
                return {
                    'status': 'error',
                    'updated_questions': 0,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error in simple frequency refresh: {e}")
            return {
                'status': 'error',
                'updated_questions': 0,
                'error': str(e)
            }
    
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
            
            # Get frequency distribution
            freq_dist = await db.execute(
                select(
                    Question.frequency_band,
                    func.count(Question.id).label('count')
                )
                .where(Question.is_active == True)
                .group_by(Question.frequency_band)
            )
            
            frequency_distribution = {}
            for row in freq_dist:
                band = row.frequency_band or 'None'
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
            # Get simple frequency summary
            frequency_summary = await self.pyq_calculator.get_frequency_summary(db)
            
            # Get recent processing stats
            return {
                'last_processing': self.processing_stats,
                'frequency_analysis': frequency_summary,
                'system_status': 'simplified_processing_active'
            }
            
        except Exception as e:
            logger.error(f"Error getting processing summary: {e}")
            return {
                'error': str(e),
                'system_status': 'error'
            }