#!/usr/bin/env python3
"""
Spaced Repetition Engine - "Repeat Until Mastery" Logic
Implements proper spaced review and mastery-based retry logic
"""

import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from database import get_database, Question, Topic, Mastery, Attempt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
import logging
from formulas import (
    get_mastery_category,
    can_attempt_question,
    get_next_attempt_time,
    calculate_ewma_mastery
)

logger = logging.getLogger(__name__)

class SpacedRepetitionEngine:
    """
    Implements spaced repetition algorithm for optimal learning retention
    """
    
    def __init__(self):
        # Spaced repetition intervals (in hours)
        self.spaced_intervals = {
            "first_review": 4,      # 4 hours after first attempt
            "second_review": 24,    # 1 day after second attempt
            "third_review": 72,     # 3 days after third attempt
            "fourth_review": 168,   # 1 week after fourth attempt
            "fifth_review": 720,    # 1 month after fifth attempt
            "mastered": 8760        # 1 year (essentially mastered)
        }
        
        # Mastery thresholds for progression
        self.mastery_thresholds = {
            "needs_immediate_retry": 0.3,     # <30% mastery - immediate retry
            "needs_regular_review": 0.6,      # 30-60% mastery - regular spaced review
            "needs_spaced_review": 0.85,      # 60-85% mastery - longer intervals  
            "mastered": 0.85                  # >85% mastery - minimal review
        }
    
    async def get_due_questions_for_review(self, db: AsyncSession, user_id: str) -> List[Dict]:
        """
        Get questions that are due for spaced repetition review
        """
        try:
            # Get questions with attempt history for spaced review scheduling
            due_questions_query = text("""
                SELECT DISTINCT
                    q.id,
                    q.topic_id,
                    q.stem,
                    q.subcategory,
                    q.difficulty_band,
                    t.name as topic_name,
                    t.category,
                    m.mastery_pct,
                    last_attempts.last_attempt_date,
                    last_attempts.correct as last_correct,
                    attempt_stats.total_attempts,
                    attempt_stats.correct_attempts,
                    attempt_stats.incorrect_count,
                    attempt_stats.avg_accuracy
                FROM questions q
                JOIN topics t ON q.topic_id = t.id
                LEFT JOIN mastery m ON t.id = m.topic_id AND m.user_id = :user_id
                LEFT JOIN (
                    SELECT 
                        question_id,
                        MAX(created_at) as last_attempt_date,
                        BOOL_AND(correct) as correct
                    FROM attempts 
                    WHERE user_id = :user_id
                    GROUP BY question_id
                ) last_attempts ON q.id = last_attempts.question_id
                LEFT JOIN (
                    SELECT 
                        question_id,
                        COUNT(*) as total_attempts,
                        SUM(CASE WHEN correct = true THEN 1 ELSE 0 END) as correct_attempts,
                        SUM(CASE WHEN correct = false THEN 1 ELSE 0 END) as incorrect_count,
                        AVG(CASE WHEN correct = true THEN 1.0 ELSE 0.0 END) as avg_accuracy
                    FROM attempts 
                    WHERE user_id = :user_id
                    GROUP BY question_id
                ) attempt_stats ON q.id = attempt_stats.question_id
                WHERE q.is_active = true
                AND last_attempts.last_attempt_date IS NOT NULL
                ORDER BY last_attempts.last_attempt_date ASC
            """)
            
            result = await db.execute(due_questions_query, {"user_id": user_id})
            question_records = result.fetchall()
            
            due_questions = []
            now = datetime.utcnow()
            
            for record in question_records:
                mastery_score = float(record.mastery_pct or 0)
                last_attempt_date = datetime.fromisoformat(str(record.last_attempt_date))
                total_attempts = record.total_attempts or 0
                correct_attempts = record.correct_attempts or 0
                incorrect_count = record.incorrect_count or 0
                
                # Determine review urgency based on mastery and performance
                review_urgency = self.calculate_review_urgency(
                    mastery_score, total_attempts, correct_attempts, record.last_correct
                )
                
                # Calculate next review time based on spaced repetition
                next_review_time = self.calculate_next_review_time(
                    last_attempt_date, total_attempts, mastery_score, record.last_correct
                )
                
                # Check if question is due for review
                is_due = now >= next_review_time
                
                # Special cases for immediate retry
                if mastery_score < self.mastery_thresholds["needs_immediate_retry"]:
                    is_due = True  # Always due if very low mastery
                
                if incorrect_count >= 2:
                    is_due = True  # Always due if failed twice
                
                if is_due:
                    due_questions.append({
                        "id": str(record.id),
                        "topic_id": str(record.topic_id),
                        "topic_name": record.topic_name,
                        "category": record.category,
                        "subcategory": record.subcategory,
                        "difficulty_band": record.difficulty_band,
                        "mastery_score": mastery_score,
                        "mastery_category": get_mastery_category(mastery_score),
                        "review_urgency": review_urgency,
                        "total_attempts": total_attempts,
                        "correct_attempts": correct_attempts,
                        "incorrect_count": incorrect_count,
                        "last_attempt_date": last_attempt_date,
                        "next_review_time": next_review_time,
                        "last_correct": record.last_correct,
                        "days_since_last_attempt": (now - last_attempt_date).days,
                        "review_reason": self.get_review_reason(mastery_score, incorrect_count, total_attempts)
                    })
            
            # Sort by review urgency (highest first)
            due_questions.sort(key=lambda x: x["review_urgency"], reverse=True)
            
            logger.info(f"Found {len(due_questions)} questions due for spaced review")
            return due_questions
            
        except Exception as e:
            logger.error(f"Error getting due questions for review: {e}")
            return []
    
    def calculate_review_urgency(self, mastery_score: float, total_attempts: int, 
                               correct_attempts: int, last_correct: bool) -> float:
        """
        Calculate urgency score for review (0.0-1.0, higher = more urgent)
        """
        try:
            urgency = 0.0
            
            # 1. Mastery-based urgency (lower mastery = higher urgency)
            mastery_urgency = 1.0 - mastery_score
            urgency += mastery_urgency * 0.4
            
            # 2. Attempt history urgency
            if total_attempts > 0:
                accuracy = correct_attempts / total_attempts
                accuracy_urgency = 1.0 - accuracy
                urgency += accuracy_urgency * 0.3
            
            # 3. Recent performance urgency
            if not last_correct:
                urgency += 0.2  # Boost urgency if last attempt was wrong
            
            # 4. Forgetting curve urgency (more attempts = less urgency)
            attempt_factor = min(total_attempts / 10.0, 1.0)
            urgency += (1.0 - attempt_factor) * 0.1
            
            return min(urgency, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating review urgency: {e}")
            return 0.5
    
    def calculate_next_review_time(self, last_attempt_date: datetime, total_attempts: int,
                                 mastery_score: float, last_correct: bool) -> datetime:
        """
        Calculate when question should next be reviewed based on spaced repetition
        """
        try:
            # Determine interval based on attempt count and performance
            if total_attempts <= 1:
                interval_hours = self.spaced_intervals["first_review"]
            elif total_attempts <= 2:
                interval_hours = self.spaced_intervals["second_review"]
            elif total_attempts <= 3:
                interval_hours = self.spaced_intervals["third_review"]
            elif total_attempts <= 5:
                interval_hours = self.spaced_intervals["fourth_review"]
            elif mastery_score >= self.mastery_thresholds["mastered"]:
                interval_hours = self.spaced_intervals["mastered"]
            else:
                interval_hours = self.spaced_intervals["fifth_review"]
            
            # Adjust interval based on performance
            if not last_correct:
                interval_hours = max(4, interval_hours // 4)  # Much sooner if incorrect
            elif mastery_score < 0.3:
                interval_hours = max(4, interval_hours // 2)  # Sooner if low mastery
            elif mastery_score >= 0.85:
                interval_hours = interval_hours * 2  # Later if high mastery
            
            return last_attempt_date + timedelta(hours=interval_hours)
            
        except Exception as e:
            logger.error(f"Error calculating next review time: {e}")
            return last_attempt_date + timedelta(hours=24)  # Default to 1 day
    
    def get_review_reason(self, mastery_score: float, incorrect_count: int, 
                         total_attempts: int) -> str:
        """
        Get human-readable reason for why question is due for review
        """
        if mastery_score < 0.3:
            return "Low mastery - needs immediate attention"
        elif incorrect_count >= 2:
            return "Multiple incorrect attempts - retry needed"
        elif total_attempts == 1:
            return "First review - reinforce learning"
        elif mastery_score < 0.6:
            return "Building proficiency - regular review"
        elif mastery_score < 0.85:
            return "Spaced review - maintain retention"
        else:
            return "Maintenance review - prevent forgetting"
    
    async def should_retry_question(self, db: AsyncSession, user_id: str, 
                                  question_id: str) -> Tuple[bool, str]:
        """
        Determine if a question should be retried based on mastery and spacing rules
        """
        try:
            # Get question attempt history
            attempts_query = text("""
                SELECT 
                    a.correct,
                    a.created_at,
                    a.attempt_no,
                    m.mastery_pct
                FROM attempts a
                JOIN questions q ON a.question_id = q.id
                JOIN mastery m ON q.topic_id = m.topic_id AND m.user_id = a.user_id
                WHERE a.user_id = :user_id AND a.question_id = :question_id
                ORDER BY a.created_at DESC
                LIMIT 5
            """)
            
            result = await db.execute(attempts_query, {
                "user_id": user_id,
                "question_id": question_id
            })
            attempts = result.fetchall()
            
            if not attempts:
                return True, "No previous attempts - can attempt"
            
            latest_attempt = attempts[0]
            mastery_score = float(latest_attempt.mastery_pct or 0)
            
            # Count recent incorrect attempts
            recent_incorrect = sum(1 for attempt in attempts if not attempt.correct)
            
            # Apply retry logic
            if mastery_score < self.mastery_thresholds["needs_immediate_retry"]:
                return True, "Low mastery - immediate retry allowed"
            
            if recent_incorrect >= 2:
                return True, "Multiple incorrect attempts - retry until mastery"
            
            if not latest_attempt.correct:
                # Check spacing rules for incorrect attempts
                last_attempt_time = latest_attempt.created_at
                hours_since = (datetime.utcnow() - last_attempt_time).total_seconds() / 3600
                
                if hours_since >= 4:  # 4-hour spacing for incorrect attempts
                    return True, "Spacing interval met - retry available"
                else:
                    return False, f"Wait {4 - int(hours_since)} more hours before retry"
            
            # For correct attempts, check if spaced review is due
            next_review = self.calculate_next_review_time(
                latest_attempt.created_at, len(attempts), mastery_score, latest_attempt.correct
            )
            
            if datetime.utcnow() >= next_review:
                return True, "Spaced review interval reached"
            else:
                time_until_review = next_review - datetime.utcnow()
                return False, f"Next review in {time_until_review.days} days"
                
        except Exception as e:
            logger.error(f"Error checking retry eligibility: {e}")
            return True, "Error checking - retry allowed"
    
    async def get_mastery_focused_questions(self, db: AsyncSession, user_id: str, 
                                          target_count: int = 10) -> List[Dict]:
        """
        Get questions focused on achieving mastery through spaced repetition
        """
        try:
            # Get questions that need mastery work
            mastery_questions_query = text("""
                SELECT DISTINCT
                    q.id,
                    q.topic_id,
                    q.stem,
                    q.subcategory,
                    q.difficulty_band,
                    t.name as topic_name,
                    COALESCE(m.mastery_pct, 0) as mastery_score,
                    COALESCE(attempt_stats.total_attempts, 0) as total_attempts,
                    COALESCE(attempt_stats.correct_attempts, 0) as correct_attempts
                FROM questions q
                JOIN topics t ON q.topic_id = t.id
                LEFT JOIN mastery m ON t.id = m.topic_id AND m.user_id = :user_id
                LEFT JOIN (
                    SELECT 
                        question_id,
                        COUNT(*) as total_attempts,
                        SUM(CASE WHEN correct = true THEN 1 ELSE 0 END) as correct_attempts
                    FROM attempts 
                    WHERE user_id = :user_id
                    GROUP BY question_id
                ) attempt_stats ON q.id = attempt_stats.question_id
                WHERE q.is_active = true
                AND COALESCE(m.mastery_pct, 0) < 0.85  -- Not yet mastered
                ORDER BY COALESCE(m.mastery_pct, 0) ASC, attempt_stats.total_attempts ASC
                LIMIT :target_count
            """)
            
            result = await db.execute(mastery_questions_query, {
                "user_id": user_id,
                "target_count": target_count * 2  # Get extra to filter
            })
            question_records = result.fetchall()
            
            mastery_questions = []
            
            for record in question_records:
                mastery_score = float(record.mastery_score)
                
                # Check if question should be retried based on spacing
                should_retry, reason = await self.should_retry_question(
                    db, user_id, str(record.id)
                )
                
                if should_retry:
                    mastery_questions.append({
                        "id": str(record.id),
                        "topic_id": str(record.topic_id),
                        "topic_name": record.topic_name,
                        "subcategory": record.subcategory,
                        "difficulty_band": record.difficulty_band,
                        "mastery_score": mastery_score,
                        "mastery_category": get_mastery_category(mastery_score),
                        "total_attempts": record.total_attempts,
                        "correct_attempts": record.correct_attempts,
                        "retry_reason": reason,
                        "mastery_priority": 1.0 - mastery_score  # Higher priority for lower mastery
                    })
            
            # Sort by mastery priority and limit to target count
            mastery_questions.sort(key=lambda x: x["mastery_priority"], reverse=True)
            
            return mastery_questions[:target_count]
            
        except Exception as e:
            logger.error(f"Error getting mastery focused questions: {e}")
            return []