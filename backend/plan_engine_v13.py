#!/usr/bin/env python3
"""
Enhanced Plan Engine v1.3 - Intelligent Daily Allocation
Implements feedback requirements for smart study planning
"""

import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from database import get_database, Plan, PlanUnit, Question, Topic, Mastery, Attempt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
import logging
import random
from formulas import (
    calculate_frequency_score,
    calculate_importance_score_v13, 
    calculate_learning_impact_v13,
    get_mastery_category,
    can_attempt_question,
    get_next_attempt_time
)

logger = logging.getLogger(__name__)

class IntelligentPlanEngine:
    """
    Enhanced plan engine that allocates daily question sets based on:
    1. Preparedness ambition
    2. Current mastery levels
    3. v1.3 formula-based question prioritization
    4. Attempt spacing rules
    """
    
    def __init__(self):
        self.daily_question_targets = {
            "Beginner": {"weekday": 15, "weekend": 25},
            "Intermediate": {"weekday": 20, "weekend": 30}, 
            "Advanced": {"weekday": 25, "weekend": 40}
        }
        
        # Priority weights for question selection
        self.priority_weights = {
            "importance_score": 0.4,
            "mastery_gap": 0.3,
            "learning_impact": 0.2,
            "recency": 0.1
        }
    
    async def create_intelligent_plan(self, db: AsyncSession, user_id: str, track: str, 
                                    daily_minutes_weekday: int, daily_minutes_weekend: int,
                                    start_date: date = None) -> Plan:
        """
        Create an intelligent 90-day study plan with daily allocations
        """
        try:
            if start_date is None:
                start_date = date.today()
            
            # Calculate preparedness ambition
            preparedness_target = await self.calculate_preparedness_ambition(
                db, user_id, start_date, start_date + timedelta(days=90)
            )
            
            # Create the plan
            plan = Plan(
                user_id=user_id,
                track=track,
                daily_minutes_weekday=daily_minutes_weekday,
                daily_minutes_weekend=daily_minutes_weekend,
                start_date=start_date,
                preparedness_target=preparedness_target,  # v1.3 requirement
                status="active"
            )
            
            db.add(plan)
            await db.flush()
            
            # Generate daily plan units for 90 days
            await self.generate_daily_plan_units(db, plan, user_id, track)
            
            await db.commit()
            
            logger.info(f"Created intelligent plan for user {user_id}, track {track}, target: {preparedness_target:.3f}")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating intelligent plan: {e}")
            await db.rollback()
            raise
    
    async def generate_daily_plan_units(self, db: AsyncSession, plan: Plan, user_id: str, track: str):
        """
        Generate intelligent daily plan units for 90 days
        """
        try:
            # Get user's current mastery state
            mastery_data = await self.get_user_mastery_state(db, user_id)
            
            # Get available questions with v1.3 scores
            questions_pool = await self.get_prioritized_questions_pool(db, user_id)
            
            target_counts = self.daily_question_targets[track]
            
            for day_offset in range(90):
                current_date = plan.start_date + timedelta(days=day_offset)
                is_weekend = current_date.weekday() >= 5  # Saturday=5, Sunday=6
                
                daily_target = target_counts["weekend"] if is_weekend else target_counts["weekday"]
                
                # Select questions for this day based on intelligence
                selected_questions = await self.select_daily_questions(
                    db, user_id, questions_pool, mastery_data, daily_target, current_date
                )
                
                # Create plan unit
                plan_unit = PlanUnit(
                    plan_id=plan.id,
                    planned_for=current_date,
                    topic_id=None,  # Multi-topic daily units
                    unit_kind="practice",
                    target_count=daily_target,
                    generated_payload={
                        "questions": selected_questions,
                        "focus_areas": self.get_daily_focus_areas(mastery_data, day_offset),
                        "intelligence_applied": True,
                        "v13_compliant": True
                    },
                    status="pending"
                )
                
                db.add(plan_unit)
            
            await db.flush()
            logger.info(f"Generated 90 intelligent daily plan units for plan {plan.id}")
            
        except Exception as e:
            logger.error(f"Error generating daily plan units: {e}")
            raise
    
    async def get_user_mastery_state(self, db: AsyncSession, user_id: str) -> Dict:
        """
        Get comprehensive mastery state for planning decisions
        """
        try:
            # Get all mastery records with topic info
            mastery_query = select(Mastery, Topic.name, Topic.category).join(
                Topic, Mastery.topic_id == Topic.id
            ).where(Mastery.user_id == user_id)
            
            mastery_result = await db.execute(mastery_query)
            mastery_records = mastery_result.all()
            
            mastery_state = {
                "by_topic": {},
                "by_category": {},
                "overall_average": 0.0,
                "needs_focus": [],
                "on_track": [],
                "mastered": []
            }
            
            total_mastery = 0.0
            count = 0
            
            for mastery, topic_name, category in mastery_records:
                mastery_score = float(mastery.mastery_pct or 0)
                mastery_category = get_mastery_category(mastery_score)
                
                mastery_state["by_topic"][topic_name] = {
                    "score": mastery_score,
                    "category": mastery_category,
                    "topic_category": category
                }
                
                # Group by category (A, B, C, D, E)
                if category not in mastery_state["by_category"]:
                    mastery_state["by_category"][category] = []
                mastery_state["by_category"][category].append({
                    "topic": topic_name,
                    "score": mastery_score,
                    "category": mastery_category
                })
                
                # Categorize for focus
                if mastery_category == "Needs focus":
                    mastery_state["needs_focus"].append(topic_name)
                elif mastery_category == "On track":
                    mastery_state["on_track"].append(topic_name)
                else:
                    mastery_state["mastered"].append(topic_name)
                
                total_mastery += mastery_score
                count += 1
            
            mastery_state["overall_average"] = total_mastery / count if count > 0 else 0.0
            
            return mastery_state
            
        except Exception as e:
            logger.error(f"Error getting user mastery state: {e}")
            return {"by_topic": {}, "by_category": {}, "overall_average": 0.0, 
                   "needs_focus": [], "on_track": [], "mastered": []}
    
    async def get_prioritized_questions_pool(self, db: AsyncSession, user_id: str) -> List[Dict]:
        """
        Get questions prioritized by v1.3 formulas and user mastery gaps
        """
        try:
            # Get questions with their v1.3 scores and attempt history
            questions_query = text("""
                SELECT 
                    q.id,
                    q.topic_id,
                    q.subcategory,
                    q.difficulty_band,
                    q.importance_score_v13,
                    q.learning_impact_v13,
                    q.frequency_score,
                    t.name as topic_name,
                    t.category,
                    COALESCE(last_attempts.last_attempt_date, NULL) as last_attempt_date,
                    COALESCE(attempt_stats.incorrect_count, 0) as incorrect_count,
                    COALESCE(attempt_stats.total_attempts, 0) as total_attempts
                FROM questions q
                JOIN topics t ON q.topic_id = t.id
                LEFT JOIN (
                    SELECT 
                        question_id,
                        MAX(created_at) as last_attempt_date
                    FROM attempts 
                    WHERE user_id = :user_id
                    GROUP BY question_id
                ) last_attempts ON q.id = last_attempts.question_id
                LEFT JOIN (
                    SELECT 
                        question_id,
                        SUM(CASE WHEN correct = false THEN 1 ELSE 0 END) as incorrect_count,
                        COUNT(*) as total_attempts
                    FROM attempts 
                    WHERE user_id = :user_id
                    GROUP BY question_id
                ) attempt_stats ON q.id = attempt_stats.question_id
                WHERE q.is_active = true
                ORDER BY 
                    COALESCE(q.importance_score_v13, 0) DESC,
                    COALESCE(q.learning_impact_v13, 0) DESC
            """)
            
            result = await db.execute(questions_query, {"user_id": user_id})
            questions_data = result.fetchall()
            
            prioritized_questions = []
            
            for row in questions_data:
                # Calculate priority score based on multiple factors
                importance_score = float(row.importance_score_v13 or 0)
                learning_impact = float(row.learning_impact_v13 or 0)
                frequency_score = float(row.frequency_score or 0)
                
                # Check attempt spacing eligibility
                can_attempt = True
                if row.last_attempt_date:
                    from datetime import datetime
                    last_attempt = datetime.fromisoformat(str(row.last_attempt_date))
                    can_attempt = can_attempt_question(last_attempt, row.incorrect_count)
                
                # Calculate composite priority
                priority_score = (
                    importance_score * self.priority_weights["importance_score"] +
                    learning_impact * self.priority_weights["learning_impact"] +
                    frequency_score * self.priority_weights["recency"]
                )
                
                prioritized_questions.append({
                    "id": str(row.id),
                    "topic_id": str(row.topic_id),
                    "topic_name": row.topic_name,
                    "subcategory": row.subcategory,
                    "category": row.category,
                    "difficulty_band": row.difficulty_band,
                    "importance_score": importance_score,
                    "learning_impact": learning_impact,
                    "frequency_score": frequency_score,
                    "priority_score": priority_score,
                    "can_attempt": can_attempt,
                    "last_attempt_date": row.last_attempt_date,
                    "total_attempts": row.total_attempts
                })
            
            # Sort by priority score
            prioritized_questions.sort(key=lambda x: x["priority_score"], reverse=True)
            
            logger.info(f"Retrieved {len(prioritized_questions)} prioritized questions for user {user_id}")
            return prioritized_questions
            
        except Exception as e:
            logger.error(f"Error getting prioritized questions pool: {e}")
            return []
    
    async def select_daily_questions(self, db: AsyncSession, user_id: str, questions_pool: List[Dict], 
                                   mastery_data: Dict, daily_target: int, current_date: date) -> List[str]:
        """
        Intelligently select questions for a specific day based on mastery gaps and priorities
        """
        try:
            selected_questions = []
            used_questions = set()
            
            # Focus on topics that need attention first
            needs_focus_topics = mastery_data.get("needs_focus", [])
            on_track_topics = mastery_data.get("on_track", [])
            
            # Allocate questions by priority
            focus_allocation = int(daily_target * 0.6)  # 60% to needs focus
            review_allocation = int(daily_target * 0.3)  # 30% to on track  
            challenge_allocation = daily_target - focus_allocation - review_allocation  # 10% to mastered
            
            # Select questions for "needs focus" topics
            for question in questions_pool:
                if (len(selected_questions) < focus_allocation and 
                    question["topic_name"] in needs_focus_topics and
                    question["can_attempt"] and
                    question["id"] not in used_questions):
                    
                    selected_questions.append(question["id"])
                    used_questions.add(question["id"])
            
            # Select questions for "on track" topics
            for question in questions_pool:
                if (len(selected_questions) < focus_allocation + review_allocation and 
                    question["topic_name"] in on_track_topics and
                    question["can_attempt"] and
                    question["id"] not in used_questions):
                    
                    selected_questions.append(question["id"])
                    used_questions.add(question["id"])
            
            # Fill remaining slots with high-priority questions
            for question in questions_pool:
                if (len(selected_questions) < daily_target and
                    question["can_attempt"] and
                    question["id"] not in used_questions):
                    
                    selected_questions.append(question["id"])
                    used_questions.add(question["id"])
            
            # If still not enough, relax spacing constraints for incorrect attempts >= 2
            if len(selected_questions) < daily_target:
                for question in questions_pool:
                    if (len(selected_questions) < daily_target and
                        question["id"] not in used_questions):
                        
                        selected_questions.append(question["id"])
                        used_questions.add(question["id"])
            
            logger.info(f"Selected {len(selected_questions)} questions for {current_date}")
            return selected_questions
            
        except Exception as e:
            logger.error(f"Error selecting daily questions: {e}")
            return []
    
    def get_daily_focus_areas(self, mastery_data: Dict, day_offset: int) -> List[str]:
        """
        Determine focus areas for the day based on mastery data and progression
        """
        focus_areas = []
        
        # Early days: Focus on foundation topics
        if day_offset < 30:
            focus_areas.extend(mastery_data.get("needs_focus", [])[:3])
        # Mid period: Balance weak and improving topics
        elif day_offset < 60:
            focus_areas.extend(mastery_data.get("needs_focus", [])[:2])
            focus_areas.extend(mastery_data.get("on_track", [])[:2])
        # Final stretch: Challenge and consolidation
        else:
            focus_areas.extend(mastery_data.get("on_track", [])[:2])
            focus_areas.extend(mastery_data.get("mastered", [])[:2])
        
        return focus_areas[:4]  # Max 4 focus areas per day
    
    async def calculate_preparedness_ambition(self, db: AsyncSession, user_id: str, 
                                            start_date: date, target_date: date) -> float:
        """
        Calculate preparedness ambition from current state to target (v1.3 requirement)
        """
        try:
            # Get current mastery levels
            mastery_query = select(Mastery.mastery_pct).where(Mastery.user_id == user_id)
            mastery_result = await db.execute(mastery_query)
            mastery_scores = [float(score[0] or 0) for score in mastery_result.fetchall()]
            
            if not mastery_scores:
                return 0.5  # Default ambition for new users
            
            # Current average mastery (t-1)
            current_avg = sum(mastery_scores) / len(mastery_scores)
            
            # Target mastery at day 90 (aspirational but realistic)
            target_avg = min(current_avg + 0.3, 0.85)  # Improve by 30% or reach 85%, whichever is lower
            
            # Calculate days available
            days_available = (target_date - start_date).days
            
            # Preparedness ambition = improvement needed / time available
            improvement_needed = target_avg - current_avg
            preparedness_ambition = improvement_needed * (90.0 / max(days_available, 1))
            
            return max(0.0, min(preparedness_ambition, 1.0))  # Bound between 0 and 1
            
        except Exception as e:
            logger.error(f"Error calculating preparedness ambition: {e}")
            return 0.5
    
    async def adjust_plan_nightly(self, db: AsyncSession, plan_id: str):
        """
        Nightly adjustment of plan based on performance (v1.3 requirement)
        """
        try:
            # Get plan details
            plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
            plan = plan_result.scalar_one_or_none()
            
            if not plan or plan.status != "active":
                return
            
            # Get updated mastery state
            mastery_data = await self.get_user_mastery_state(db, plan.user_id)
            
            # Get upcoming plan units (next 7 days)
            upcoming_date = date.today() + timedelta(days=1)
            future_units_query = select(PlanUnit).where(
                and_(
                    PlanUnit.plan_id == plan_id,
                    PlanUnit.planned_for >= upcoming_date,
                    PlanUnit.planned_for <= upcoming_date + timedelta(days=7),
                    PlanUnit.status == "pending"
                )
            )
            
            future_units_result = await db.execute(future_units_query)
            future_units = future_units_result.scalars().all()
            
            # Re-prioritize questions for upcoming units
            questions_pool = await self.get_prioritized_questions_pool(db, plan.user_id)
            
            for unit in future_units:
                # Regenerate question selection based on current mastery
                new_questions = await self.select_daily_questions(
                    db, plan.user_id, questions_pool, mastery_data, 
                    unit.target_count, unit.planned_for
                )
                
                # Update the plan unit
                unit.generated_payload.update({
                    "questions": new_questions,
                    "focus_areas": self.get_daily_focus_areas(mastery_data, 
                                                            (unit.planned_for - plan.start_date).days),
                    "last_adjusted": datetime.utcnow().isoformat(),
                    "adjustment_reason": "nightly_intelligence_update"
                })
            
            await db.commit()
            logger.info(f"Adjusted plan {plan_id} based on current performance")
            
        except Exception as e:
            logger.error(f"Error adjusting plan nightly: {e}")
            await db.rollback()