"""
Background Jobs and Nightly Processing for CAT Preparation Platform
Implements scheduled tasks for mastery updates, plan extensions, and LI computation
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

# Import database and services
from database import (
    get_database, User, Mastery, Plan, Question, Attempt, 
    Topic, Session, PlanUnit
)
from mastery_tracker import MasteryTracker
from study_planner import StudyPlanner
from llm_enrichment import LLMEnrichmentPipeline

logger = logging.getLogger(__name__)

class BackgroundJobProcessor:
    def __init__(self, llm_api_key: str):
        self.scheduler = AsyncIOScheduler()
        self.mastery_tracker = MasteryTracker()
        self.study_planner = StudyPlanner()
        self.llm_pipeline = LLMEnrichmentPipeline(llm_api_key)
        
    def start_scheduler(self):
        """Start the background job scheduler"""
        try:
            # Schedule nightly jobs at 2 AM
            self.scheduler.add_job(
                self.nightly_processing_job,
                CronTrigger(hour=2, minute=0),
                id='nightly_processing',
                name='Nightly Processing Job'
            )
            
            # Schedule mastery decay calculation every 6 hours
            self.scheduler.add_job(
                self.mastery_decay_job,
                CronTrigger(hour='*/6'),
                id='mastery_decay',
                name='Mastery Decay Job'
            )
            
            # Schedule plan extension every day at 1 AM
            self.scheduler.add_job(
                self.plan_extension_job,
                CronTrigger(hour=1, minute=0),
                id='plan_extension',
                name='Plan Extension Job'
            )
            
            # Schedule learning impact recomputation weekly
            self.scheduler.add_job(
                self.learning_impact_job,
                CronTrigger(day_of_week='sun', hour=3, minute=0),
                id='learning_impact_update',
                name='Learning Impact Update Job'
            )
            
            self.scheduler.start()
            logger.info("Background job scheduler started")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    def stop_scheduler(self):
        """Stop the background job scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Background job scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def nightly_processing_job(self):
        """Main nightly processing job - runs all maintenance tasks"""
        logger.info("Starting nightly processing job")
        
        try:
            async for db in get_database():
                # 1. Update mastery scores with time decay
                await self.update_all_mastery_scores(db)
                
                # 2. Recompute dynamic learning impact
                await self.recompute_dynamic_learning_impact(db)
                
                # 3. Update importance indices based on new LI
                await self.update_importance_indices(db)
                
                # 4. Clean up old data
                await self.cleanup_old_data(db)
                
                # 5. Generate usage statistics
                await self.generate_usage_stats(db)
                
                logger.info("Nightly processing job completed successfully")
                break
                
        except Exception as e:
            logger.error(f"Error in nightly processing job: {e}")
    
    async def mastery_decay_job(self):
        """Job to apply time decay to mastery scores"""
        logger.info("Starting mastery decay job")
        
        try:
            async for db in get_database():
                # Get all users who haven't been active recently
                cutoff_time = datetime.utcnow() - timedelta(hours=6)
                
                inactive_users_result = await db.execute(
                    select(User.id).where(
                        ~User.id.in_(
                            select(Session.user_id).where(
                                Session.started_at > cutoff_time
                            )
                        )
                    )
                )
                
                inactive_user_ids = [str(uid) for uid in inactive_users_result.scalars().all()]
                
                # Apply decay to inactive users
                for user_id in inactive_user_ids:
                    # Calculate days since last activity
                    last_activity_result = await db.execute(
                        select(Session.started_at)
                        .where(Session.user_id == user_id)
                        .order_by(desc(Session.started_at))
                        .limit(1)
                    )
                    last_activity = last_activity_result.scalar_one_or_none()
                    
                    if last_activity:
                        days_inactive = (datetime.utcnow() - last_activity).days
                        if days_inactive > 0:
                            await self.mastery_tracker.apply_time_decay(db, user_id, days_inactive)
                
                logger.info(f"Applied mastery decay to {len(inactive_user_ids)} inactive users")
                break
                
        except Exception as e:
            logger.error(f"Error in mastery decay job: {e}")
    
    async def plan_extension_job(self):
        """Job to extend study plans with new plan units"""
        logger.info("Starting plan extension job")
        
        try:
            async for db in get_database():
                # Get all active plans
                active_plans_result = await db.execute(
                    select(Plan).where(Plan.status == "active")
                )
                active_plans = active_plans_result.scalars().all()
                
                # Extend each plan by 3-5 days
                for plan in active_plans:
                    await self.study_planner.extend_plan_units(db, str(plan.id), 5)
                
                logger.info(f"Extended {len(active_plans)} active study plans")
                break
                
        except Exception as e:
            logger.error(f"Error in plan extension job: {e}")
    
    async def learning_impact_job(self):
        """Weekly job to recompute learning impact with dynamic factors"""
        logger.info("Starting learning impact update job")
        
        try:
            async for db in get_database():
                await self.recompute_dynamic_learning_impact(db)
                await self.update_importance_indices(db)
                
                logger.info("Learning impact update job completed")
                break
                
        except Exception as e:
            logger.error(f"Error in learning impact job: {e}")
    
    async def update_all_mastery_scores(self, db: AsyncSession):
        """Update mastery scores for all users"""
        try:
            # Get all mastery records that haven't been updated today
            today = datetime.utcnow().date()
            stale_mastery_result = await db.execute(
                select(Mastery).where(
                    or_(
                        Mastery.last_updated < datetime.combine(today, datetime.min.time()),
                        Mastery.last_updated.is_(None)
                    )
                )
            )
            stale_mastery_records = stale_mastery_result.scalars().all()
            
            # Recalculate mastery for each record
            for mastery in stale_mastery_records:
                # Get recent attempts for this user-topic combination
                recent_attempts_result = await db.execute(
                    select(Attempt)
                    .join(Question, Attempt.question_id == Question.id)
                    .where(
                        Attempt.user_id == mastery.user_id,
                        Question.topic_id == mastery.topic_id,
                        Attempt.created_at > datetime.utcnow() - timedelta(days=30)
                    )
                    .order_by(desc(Attempt.created_at))
                )
                recent_attempts = recent_attempts_result.scalars().all()
                
                if recent_attempts:
                    # Recalculate mastery based on recent attempts
                    total_attempts = len(recent_attempts)
                    correct_attempts = sum(1 for attempt in recent_attempts if attempt.correct)
                    
                    # Update mastery percentage with new calculation
                    new_mastery_pct = self.mastery_tracker.calculate_overall_mastery(mastery)
                    mastery.mastery_pct = new_mastery_pct
                    mastery.last_updated = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Updated {len(stale_mastery_records)} mastery records")
            
        except Exception as e:
            logger.error(f"Error updating mastery scores: {e}")
            await db.rollback()
    
    async def recompute_dynamic_learning_impact(self, db: AsyncSession):
        """Recompute dynamic learning impact for all questions"""
        try:
            # Get all active questions
            questions_result = await db.execute(
                select(Question).where(Question.is_active == True)
            )
            questions = questions_result.scalars().all()
            
            updated_count = 0
            
            for question in questions:
                try:
                    # Calculate dynamic components
                    dynamic_li = await self.calculate_dynamic_learning_impact(db, question)
                    
                    # Blend with static LI: 0.60 * Static + 0.40 * Dynamic
                    static_li = float(question.learning_impact) if question.learning_impact else 50.0
                    blended_li = 0.60 * static_li + 0.40 * dynamic_li
                    
                    # Update question
                    question.learning_impact = round(blended_li, 2)
                    
                    # Update learning impact band
                    if blended_li >= 70:
                        question.learning_impact_band = "High"
                    elif blended_li >= 45:
                        question.learning_impact_band = "Medium"
                    else:
                        question.learning_impact_band = "Low"
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error updating LI for question {question.id}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Updated dynamic learning impact for {updated_count} questions")
            
        except Exception as e:
            logger.error(f"Error recomputing dynamic learning impact: {e}")
            await db.rollback()
    
    async def calculate_dynamic_learning_impact(self, db: AsyncSession, question: Question) -> float:
        """
        Calculate dynamic learning impact components:
        - CTU (Cross-Topic Uplift)
        - Misconception richness 
        - Retention stickiness
        - Time-to-skill
        """
        try:
            # Get attempts for this question
            attempts_result = await db.execute(
                select(Attempt).where(
                    Attempt.question_id == question.id,
                    Attempt.created_at > datetime.utcnow() - timedelta(days=90)
                )
            )
            attempts = attempts_result.scalars().all()
            
            if not attempts:
                return 50.0  # Default if no attempt data
            
            # Calculate components
            ctu_score = await self.calculate_cross_topic_uplift(db, question, attempts)
            misconception_score = self.calculate_misconception_richness(attempts)
            retention_score = await self.calculate_retention_stickiness(db, question, attempts)
            time_to_skill_score = self.calculate_time_to_skill(attempts)
            
            # Weighted combination
            dynamic_li = (
                0.30 * ctu_score +
                0.25 * misconception_score +
                0.25 * retention_score +
                0.20 * time_to_skill_score
            )
            
            return max(0.0, min(100.0, dynamic_li))
            
        except Exception as e:
            logger.error(f"Error calculating dynamic LI: {e}")
            return 50.0
    
    async def calculate_cross_topic_uplift(self, db: AsyncSession, question: Question, attempts: List[Attempt]) -> float:
        """Calculate how much this question helps with other topics"""
        try:
            # Get users who attempted this question
            user_ids = [attempt.user_id for attempt in attempts if attempt.correct]
            
            if not user_ids:
                return 30.0  # Default low score
            
            # Check improvement in related topics after attempting this question
            related_topics_result = await db.execute(
                select(Topic).where(
                    or_(
                        Topic.parent_id == question.topic.parent_id,
                        Topic.id == question.topic.parent_id
                    )
                )
            )
            related_topics = related_topics_result.scalars().all()
            
            uplift_scores = []
            
            for user_id in user_ids[:10]:  # Sample to avoid performance issues
                # Measure performance improvement in related topics
                # (Simplified calculation)
                recent_mastery_result = await db.execute(
                    select(Mastery.mastery_pct).where(
                        Mastery.user_id == user_id,
                        Mastery.topic_id.in_([t.id for t in related_topics])
                    )
                )
                mastery_scores = [float(score) for score in recent_mastery_result.scalars().all()]
                
                if mastery_scores:
                    avg_mastery = sum(mastery_scores) / len(mastery_scores)
                    uplift_scores.append(avg_mastery)
            
            if uplift_scores:
                return sum(uplift_scores) / len(uplift_scores)
            else:
                return 40.0
                
        except Exception as e:
            logger.error(f"Error calculating CTU: {e}")
            return 40.0
    
    def calculate_misconception_richness(self, attempts: List[Attempt]) -> float:
        """Calculate how rich this question is in revealing misconceptions"""
        try:
            if not attempts:
                return 30.0
            
            # Count different types of incorrect answers
            incorrect_answers = [attempt.user_answer for attempt in attempts if not attempt.correct]
            unique_incorrect = len(set(incorrect_answers))
            total_incorrect = len(incorrect_answers)
            
            if total_incorrect == 0:
                return 20.0  # Easy question, low misconception value
            
            # Higher diversity of wrong answers = higher misconception richness
            diversity_ratio = unique_incorrect / total_incorrect if total_incorrect > 0 else 0
            
            # Scale to 0-100
            richness_score = 30 + (diversity_ratio * 50)
            
            return min(100.0, richness_score)
            
        except Exception as e:
            logger.error(f"Error calculating misconception richness: {e}")
            return 40.0
    
    async def calculate_retention_stickiness(self, db: AsyncSession, question: Question, attempts: List[Attempt]) -> float:
        """Calculate how well students retain knowledge from this question"""
        try:
            # Look at users who got this question correct initially
            correct_users = [attempt.user_id for attempt in attempts if attempt.correct and attempt.attempt_no == 1]
            
            if not correct_users:
                return 30.0
            
            retention_scores = []
            
            for user_id in correct_users[:10]:  # Sample for performance
                # Check if they got similar questions correct later
                later_attempts_result = await db.execute(
                    select(Attempt)
                    .join(Question, Attempt.question_id == Question.id)
                    .where(
                        Attempt.user_id == user_id,
                        Question.subcategory == question.subcategory,
                        Question.difficulty_band == question.difficulty_band,
                        Attempt.created_at > max(attempt.created_at for attempt in attempts if attempt.user_id == user_id),
                        Attempt.question_id != question.id
                    )
                )
                later_attempts = later_attempts_result.scalars().all()
                
                if later_attempts:
                    later_accuracy = sum(1 for attempt in later_attempts if attempt.correct) / len(later_attempts)
                    retention_scores.append(later_accuracy * 100)
            
            if retention_scores:
                return sum(retention_scores) / len(retention_scores)
            else:
                return 50.0
                
        except Exception as e:
            logger.error(f"Error calculating retention stickiness: {e}")
            return 50.0
    
    def calculate_time_to_skill(self, attempts: List[Attempt]) -> float:
        """Calculate how quickly students develop skill from this question"""
        try:
            # Group attempts by user and look at improvement over attempts
            user_attempts = {}
            for attempt in attempts:
                if attempt.user_id not in user_attempts:
                    user_attempts[attempt.user_id] = []
                user_attempts[attempt.user_id].append(attempt)
            
            improvement_scores = []
            
            for user_id, user_attempt_list in user_attempts.items():
                if len(user_attempt_list) > 1:
                    # Sort by attempt number
                    sorted_attempts = sorted(user_attempt_list, key=lambda x: x.attempt_no)
                    
                    # Check for improvement (incorrect -> correct)
                    if not sorted_attempts[0].correct and any(attempt.correct for attempt in sorted_attempts[1:]):
                        # Found improvement - calculate time to skill
                        first_correct = next(attempt for attempt in sorted_attempts if attempt.correct)
                        attempts_to_correct = first_correct.attempt_no
                        
                        # Lower attempts to correct = higher time-to-skill score
                        skill_score = max(20, 100 - (attempts_to_correct - 1) * 30)
                        improvement_scores.append(skill_score)
            
            if improvement_scores:
                return sum(improvement_scores) / len(improvement_scores)
            else:
                return 60.0  # Default if no improvement data
                
        except Exception as e:
            logger.error(f"Error calculating time to skill: {e}")
            return 60.0
    
    async def update_importance_indices(self, db: AsyncSession):
        """Update importance indices based on new learning impact scores"""
        try:
            questions_result = await db.execute(
                select(Question).where(Question.is_active == True)
            )
            questions = questions_result.scalars().all()
            
            updated_count = 0
            
            for question in questions:
                # Recalculate importance using the formula:
                # 0.50×Frequency + 0.25×DifficultyNorm + 0.25×LearningImpact
                
                frequency_scores = {"High": 100, "Medium": 60, "Low": 30}
                frequency_score = frequency_scores.get(question.frequency_band, 60)
                
                difficulty_norm = 20 + ((float(question.difficulty_score or 3) - 1) / 4) * 80
                learning_impact = float(question.learning_impact) if question.learning_impact else 50
                
                importance = (
                    0.50 * frequency_score +
                    0.25 * difficulty_norm +
                    0.25 * learning_impact
                )
                
                question.importance_index = round(importance, 2)
                
                # Update importance band
                if importance >= 70:
                    question.importance_band = "High"
                elif importance >= 45:
                    question.importance_band = "Medium"
                else:
                    question.importance_band = "Low"
                
                updated_count += 1
            
            await db.commit()
            logger.info(f"Updated importance indices for {updated_count} questions")
            
        except Exception as e:
            logger.error(f"Error updating importance indices: {e}")
            await db.rollback()
    
    async def cleanup_old_data(self, db: AsyncSession):
        """Clean up old data to maintain performance"""
        try:
            # Remove old sessions (older than 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            old_sessions_result = await db.execute(
                select(Session).where(Session.started_at < cutoff_date)
            )
            old_sessions = old_sessions_result.scalars().all()
            
            for session in old_sessions:
                await db.delete(session)
            
            await db.commit()
            logger.info(f"Cleaned up {len(old_sessions)} old sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            await db.rollback()
    
    async def generate_usage_stats(self, db: AsyncSession):
        """Generate daily usage statistics"""
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            # Count various metrics for yesterday
            daily_stats = {}
            
            # Active users
            active_users_result = await db.execute(
                select(func.count(func.distinct(Session.user_id))).where(
                    Session.started_at >= datetime.combine(yesterday, datetime.min.time()),
                    Session.started_at < datetime.combine(today, datetime.min.time())
                )
            )
            daily_stats['active_users'] = active_users_result.scalar() or 0
            
            # Questions attempted
            questions_attempted_result = await db.execute(
                select(func.count(Attempt.id)).where(
                    Attempt.created_at >= datetime.combine(yesterday, datetime.min.time()),
                    Attempt.created_at < datetime.combine(today, datetime.min.time())
                )
            )
            daily_stats['questions_attempted'] = questions_attempted_result.scalar() or 0
            
            # Average session duration
            avg_duration_result = await db.execute(
                select(func.avg(Session.duration_sec)).where(
                    Session.started_at >= datetime.combine(yesterday, datetime.min.time()),
                    Session.started_at < datetime.combine(today, datetime.min.time()),
                    Session.duration_sec.isnot(None)
                )
            )
            avg_duration = avg_duration_result.scalar()
            daily_stats['avg_session_minutes'] = round(avg_duration / 60, 1) if avg_duration else 0
            
            logger.info(f"Daily stats for {yesterday}: {daily_stats}")
            
        except Exception as e:
            logger.error(f"Error generating usage stats: {e}")

# Global instance
job_processor = None

def start_background_processing(llm_api_key: str):
    """Start background job processing"""
    global job_processor
    try:
        job_processor = BackgroundJobProcessor(llm_api_key)
        job_processor.start_scheduler()
        logger.info("Background processing started")
    except Exception as e:
        logger.error(f"Error starting background processing: {e}")

def stop_background_processing():
    """Stop background job processing"""
    global job_processor
    try:
        if job_processor:
            job_processor.stop_scheduler()
            job_processor = None
        logger.info("Background processing stopped")
    except Exception as e:
        logger.error(f"Error stopping background processing: {e}")