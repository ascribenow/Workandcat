"""
Advanced Study Planning System for CAT Preparation Platform
Implements 90-day planning with serving algorithms as per specification
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from database import Plan, PlanUnit, User, Question, Topic, Mastery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
import logging

logger = logging.getLogger(__name__)

class StudyPlanner:
    def __init__(self):
        self.track_configs = {
            "Beginner": {
                "daily_minutes_weekday": 30,
                "daily_minutes_weekend": 60,
                "difficulty_distribution": {"Easy": 0.5, "Medium": 0.4, "Difficult": 0.1},
                "questions_per_session": 3
            },
            "Intermediate": {
                "daily_minutes_weekday": 45,
                "daily_minutes_weekend": 90,
                "difficulty_distribution": {"Easy": 0.3, "Medium": 0.5, "Difficult": 0.2},
                "questions_per_session": 5
            },
            "Good": {
                "daily_minutes_weekday": 60,
                "daily_minutes_weekend": 120,
                "difficulty_distribution": {"Easy": 0.2, "Medium": 0.4, "Difficult": 0.4},
                "questions_per_session": 7
            }
        }
        
        self.retry_intervals = {
            1: {"correct": 3, "incorrect": 1},   # 1st attempt: 3 days if correct, 1-2 days if incorrect
            2: {"correct": 7, "incorrect": 3},   # 2nd attempt: 7 days if correct, 3-5 days if incorrect  
            3: {"correct": 14, "incorrect": 10}  # 3rd attempt: 14 days if correct, 7-10 days if incorrect
        }
    
    async def create_plan(self, db: AsyncSession, user_id: str, track: str, 
                         daily_minutes_weekday: int, daily_minutes_weekend: int) -> Plan:
        """Create 90-day study plan for user"""
        try:
            # Create plan
            plan = Plan(
                user_id=user_id,
                track=track,
                daily_minutes_weekday=daily_minutes_weekday,
                daily_minutes_weekend=daily_minutes_weekend,
                start_date=date.today(),
                status="active"
            )
            
            db.add(plan)
            await db.flush()  # Get ID
            
            # Generate initial plan units (7-10 days ahead)
            await self.generate_plan_units(db, plan, 10)
            
            await db.commit()
            logger.info(f"Created {track} plan for user {user_id}")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating study plan: {e}")
            await db.rollback()
            raise
    
    async def generate_plan_units(self, db: AsyncSession, plan: Plan, days_ahead: int):
        """Generate plan units for the next N days"""
        try:
            config = self.track_configs[plan.track]
            
            for day_offset in range(days_ahead):
                plan_date = plan.start_date + timedelta(days=day_offset)
                
                # Skip if units already exist for this date
                existing_result = await db.execute(
                    select(PlanUnit).where(
                        PlanUnit.plan_id == plan.id,
                        PlanUnit.planned_for == plan_date
                    )
                )
                if existing_result.scalar_one_or_none():
                    continue
                
                # Determine daily time budget
                is_weekend = plan_date.weekday() >= 5
                daily_minutes = plan.daily_minutes_weekend if is_weekend else plan.daily_minutes_weekday
                
                # Generate units for this day
                await self.generate_daily_units(db, plan, plan_date, daily_minutes, config)
            
        except Exception as e:
            logger.error(f"Error generating plan units: {e}")
            raise
    
    async def generate_daily_units(self, db: AsyncSession, plan: Plan, plan_date: date, 
                                 daily_minutes: int, config: Dict[str, Any]):
        """Generate plan units for a specific day"""
        try:
            # Get topics that need coverage
            topics_result = await db.execute(select(Topic).where(Topic.parent_id.isnot(None)))
            topics = topics_result.scalars().all()
            
            # Simple algorithm: rotate through topics with different unit kinds
            day_number = (plan_date - plan.start_date).days
            topic_index = day_number % len(topics)
            selected_topic = topics[topic_index]
            
            # Determine unit kind based on day pattern
            unit_kinds = ["practice", "examples", "practice", "review", "practice"]
            unit_kind = unit_kinds[day_number % len(unit_kinds)]
            
            # Calculate target count based on time budget
            avg_time_per_question = 3  # minutes
            target_count = max(1, daily_minutes // avg_time_per_question)
            
            # Get questions for payload
            questions_payload = await self.select_questions_for_unit(
                db, plan.user_id, selected_topic.id, unit_kind, target_count, config
            )
            
            # Create plan unit
            plan_unit = PlanUnit(
                plan_id=plan.id,
                planned_for=plan_date,
                topic_id=selected_topic.id,
                unit_kind=unit_kind,
                target_count=target_count,
                generated_payload={"question_ids": questions_payload},
                status="pending"
            )
            
            db.add(plan_unit)
            
        except Exception as e:
            logger.error(f"Error generating daily units: {e}")
            raise
    
    async def select_questions_for_unit(self, db: AsyncSession, user_id: str, topic_id: str,
                                      unit_kind: str, target_count: int, config: Dict[str, Any]) -> List[str]:
        """
        Select questions for a plan unit using serving algorithm
        Balances: Importance + Fit + Coverage + Retries
        """
        try:
            # Get user's mastery for this topic
            mastery_result = await db.execute(
                select(Mastery).where(
                    Mastery.user_id == user_id,
                    Mastery.topic_id == topic_id
                )
            )
            mastery = mastery_result.scalar_one_or_none()
            
            # Determine difficulty distribution based on mastery and track
            difficulty_dist = config["difficulty_distribution"]
            
            if mastery:
                # Adjust distribution based on mastery level
                if mastery.mastery_pct < 0.3:  # Low mastery - more easy questions
                    difficulty_dist = {"Easy": 0.6, "Medium": 0.3, "Difficult": 0.1}
                elif mastery.mastery_pct > 0.7:  # High mastery - more difficult questions
                    difficulty_dist = {"Easy": 0.2, "Medium": 0.3, "Difficult": 0.5}
            
            # Select questions by difficulty
            selected_questions = []
            
            for difficulty, ratio in difficulty_dist.items():
                needed_count = int(target_count * ratio)
                if needed_count == 0:
                    continue
                
                # Get questions of this difficulty for the topic
                questions_result = await db.execute(
                    select(Question).where(
                        Question.topic_id == topic_id,
                        Question.difficulty_band == difficulty,
                        Question.is_active == True
                    ).order_by(desc(Question.importance_index)).limit(needed_count * 2)  # Get extras for filtering
                )
                questions = questions_result.scalars().all()
                
                # Filter based on retry intervals and select best
                filtered_questions = await self.filter_questions_by_attempts(
                    db, user_id, questions, needed_count
                )
                
                selected_questions.extend([str(q.id) for q in filtered_questions[:needed_count]])
            
            # Fill remaining slots if needed
            while len(selected_questions) < target_count:
                # Get any available questions (excluding broken images)
                remaining_result = await db.execute(
                    select(Question).where(
                        Question.topic_id == topic_id,
                        Question.is_active == True,
                        # Exclude questions with broken images
                        ~Question.tags.any("broken_image"),
                        ~Question.id.in_([uuid.UUID(qid) for qid in selected_questions])
                    ).order_by(desc(Question.importance_index)).limit(1)
                )
                remaining_q = remaining_result.scalar_one_or_none()
                if remaining_q:
                    selected_questions.append(str(remaining_q.id))
                else:
                    break
            
            return selected_questions[:target_count]
            
        except Exception as e:
            logger.error(f"Error selecting questions: {e}")
            return []
    
    async def filter_questions_by_attempts(self, db: AsyncSession, user_id: str, 
                                         questions: List[Question], needed_count: int) -> List[Question]:
        """Filter questions based on attempt history and retry intervals"""
        try:
            from database import Attempt
            
            available_questions = []
            
            for question in questions:
                # Check user's attempt history for this question
                attempts_result = await db.execute(
                    select(Attempt).where(
                        Attempt.user_id == user_id,
                        Attempt.question_id == question.id
                    ).order_by(desc(Attempt.created_at))
                )
                attempts = attempts_result.scalars().all()
                
                if not attempts:
                    # Never attempted - always available
                    available_questions.append(question)
                    continue
                
                last_attempt = attempts[0]
                days_since_attempt = (datetime.utcnow() - last_attempt.created_at).days
                
                # Check if enough time has passed for retry
                retry_interval = self.get_retry_interval(last_attempt.attempt_no, last_attempt.correct)
                
                if days_since_attempt >= retry_interval:
                    available_questions.append(question)
                
                if len(available_questions) >= needed_count * 2:  # Have enough options
                    break
            
            return available_questions
            
        except Exception as e:
            logger.error(f"Error filtering questions by attempts: {e}")
            return questions  # Return all if error
    
    def get_retry_interval(self, attempt_no: int, was_correct: bool) -> int:
        """Get retry interval based on attempt number and correctness"""
        if attempt_no > 3:
            return 14  # Long cooldown after 3 attempts
        
        interval_config = self.retry_intervals.get(attempt_no, self.retry_intervals[3])
        return interval_config["correct"] if was_correct else interval_config["incorrect"]
    
    def get_next_retry_interval(self, attempt_no: int, is_correct: bool) -> int:
        """Get next retry interval for displaying to user"""
        if attempt_no >= 3 and not is_correct:
            return 10  # Lock and cooldown
        
        next_attempt = attempt_no + 1
        if next_attempt > 3:
            return 14 if is_correct else 10
        
        interval_config = self.retry_intervals.get(next_attempt, self.retry_intervals[3])
        return interval_config["correct"] if is_correct else interval_config["incorrect"]
    
    async def get_next_question(self, db: AsyncSession, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get next question for a study session"""
        try:
            # Get today's plan units for the user
            today = date.today()
            
            units_result = await db.execute(
                select(PlanUnit)
                .join(Plan, PlanUnit.plan_id == Plan.id)
                .where(
                    Plan.user_id == user_id,
                    Plan.status == "active",
                    PlanUnit.planned_for == today,
                    PlanUnit.status.in_(["pending", "in_progress"])
                )
                .order_by(PlanUnit.created_at)
            )
            units = units_result.scalars().all()
            
            if not units:
                return None  # No plan units for today
            
            # Get first available unit
            current_unit = units[0]
            question_ids = current_unit.generated_payload.get("question_ids", [])
            
            if not question_ids:
                return None
            
            # Get first question that hasn't been used in this session yet
            # (In a real implementation, you'd track session progress)
            question_result = await db.execute(
                select(Question).where(Question.id == question_ids[0])
            )
            question = question_result.scalar_one_or_none()
            
            if not question:
                return None
            
            return {
                "id": str(question.id),
                "stem": question.stem,
                "subcategory": question.subcategory,
                "difficulty_band": question.difficulty_band,
                "importance_index": float(question.importance_index) if question.importance_index else 0,
                "unit_id": str(current_unit.id),
                "unit_kind": current_unit.unit_kind
            }
            
        except Exception as e:
            logger.error(f"Error getting next question: {e}")
            return None
    
    async def extend_plan_units(self, db: AsyncSession, plan_id: str, days_to_extend: int = 5):
        """Extend plan units for the next N days (called by nightly job)"""
        try:
            # Get plan
            plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
            plan = plan_result.scalar_one_or_none()
            
            if not plan or plan.status != "active":
                return
            
            # Generate additional plan units
            await self.generate_plan_units(db, plan, days_to_extend)
            await db.commit()
            
            logger.info(f"Extended plan {plan_id} by {days_to_extend} days")
            
        except Exception as e:
            logger.error(f"Error extending plan units: {e}")