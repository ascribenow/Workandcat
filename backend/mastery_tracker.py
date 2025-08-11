"""
Mastery Tracking System for CAT Preparation Platform
Implements EWMA-based mastery calculation with time decay as per specification
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database import Mastery, Attempt, User, Topic, Question
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
import logging
import math
from formulas import (
    calculate_ewma_mastery,
    calculate_learning_impact,
    calculate_preparedness_ambition,
    apply_mastery_decay,
    normalize_score
)

logger = logging.getLogger(__name__)

class MasteryTracker:
    def __init__(self):
        # EWMA (Exponentially Weighted Moving Average) parameters
        self.ewma_alpha = 0.6  # Updated to v1.3 spec (was 0.3)
        self.time_decay_factor = 0.95  # Daily decay factor for mastery
        self.min_attempts_for_stability = 3  # Minimum attempts for stable mastery
        
        # Efficiency scoring parameters
        self.target_times = {
            "Easy": 90,      # seconds
            "Medium": 150,   # seconds
            "Difficult": 210 # seconds
        }
    
    async def update_mastery_after_attempt(self, db: AsyncSession, attempt: Attempt):
        """Update mastery immediately after a question attempt"""
        try:
            # Get question to determine topic
            question_result = await db.execute(select(Question).where(Question.id == attempt.question_id))
            question = question_result.scalar_one_or_none()
            
            if not question or not question.topic_id:
                logger.warning(f"No topic found for question {attempt.question_id}")
                return
            
            # Get or create mastery record
            mastery_result = await db.execute(
                select(Mastery).where(
                    Mastery.user_id == attempt.user_id,
                    Mastery.topic_id == question.topic_id
                )
            )
            mastery = mastery_result.scalar_one_or_none()
            
            if not mastery:
                mastery = Mastery(
                    user_id=attempt.user_id,
                    topic_id=question.topic_id,
                    exposure_score=0,
                    accuracy_easy=0,
                    accuracy_med=0,
                    accuracy_hard=0,
                    efficiency_score=0,
                    mastery_pct=0,
                    last_updated=datetime.utcnow()
                )
                db.add(mastery)
                await db.flush()
            
            # Update mastery with this attempt
            await self.update_mastery_scores(db, mastery, attempt, question)
            
            await db.commit()
            logger.info(f"Updated mastery for user {attempt.user_id}, topic {question.topic_id}")
            
        except Exception as e:
            logger.error(f"Error updating mastery after attempt: {e}")
            await db.rollback()
    
    async def update_mastery_scores(self, db: AsyncSession, mastery: Mastery, 
                                  attempt: Attempt, question: Question):
        """Update all mastery component scores"""
        try:
            # Update exposure score (incremental)
            mastery.exposure_score = float(mastery.exposure_score) + 1.0
            
            # Update difficulty-specific accuracy using EWMA
            difficulty = question.difficulty_band
            current_accuracy = self.get_difficulty_accuracy(mastery, difficulty)
            new_accuracy_point = 1.0 if attempt.correct else 0.0
            
            # EWMA update: new_value = alpha * new_point + (1 - alpha) * old_value
            updated_accuracy = (self.ewma_alpha * new_accuracy_point + 
                              (1 - self.ewma_alpha) * current_accuracy)
            
            self.set_difficulty_accuracy(mastery, difficulty, updated_accuracy)
            
            # Update efficiency score
            efficiency_point = self.calculate_efficiency_point(attempt, question)
            current_efficiency = float(mastery.efficiency_score)
            updated_efficiency = (self.ewma_alpha * efficiency_point + 
                                (1 - self.ewma_alpha) * current_efficiency)
            mastery.efficiency_score = updated_efficiency
            
            # Calculate overall mastery percentage
            mastery.mastery_pct = self.calculate_overall_mastery(mastery)
            mastery.last_updated = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating mastery scores: {e}")
            raise
    
    def get_difficulty_accuracy(self, mastery: Mastery, difficulty: str) -> float:
        """Get accuracy for specific difficulty level"""
        if difficulty == "Easy":
            return float(mastery.accuracy_easy)
        elif difficulty == "Medium":
            return float(mastery.accuracy_med)
        elif difficulty == "Difficult":
            return float(mastery.accuracy_hard)
        else:
            return 0.0
    
    def set_difficulty_accuracy(self, mastery: Mastery, difficulty: str, value: float):
        """Set accuracy for specific difficulty level"""
        value = max(0.0, min(1.0, value))  # Clamp between 0 and 1
        
        if difficulty == "Easy":
            mastery.accuracy_easy = value
        elif difficulty == "Medium":
            mastery.accuracy_med = value
        elif difficulty == "Difficult":
            mastery.accuracy_hard = value
    
    def calculate_efficiency_point(self, attempt: Attempt, question: Question) -> float:
        """Calculate efficiency score for this attempt (0-1)"""
        try:
            target_time = self.target_times.get(question.difficulty_band, 150)
            actual_time = attempt.time_sec
            
            if actual_time <= 0:
                return 0.5  # Default if no time recorded
            
            # Efficiency score: 1.0 if at or under target, decreasing as time increases
            if actual_time <= target_time:
                efficiency = 1.0
            else:
                # Exponential decay for times over target
                efficiency = math.exp(-0.5 * (actual_time - target_time) / target_time)
            
            # Bonus for being well under target time
            if actual_time <= target_time * 0.7:
                efficiency = min(1.0, efficiency + 0.1)
            
            return max(0.0, min(1.0, efficiency))
            
        except Exception as e:
            logger.error(f"Error calculating efficiency: {e}")
            return 0.5
    
    def calculate_overall_mastery(self, mastery: Mastery) -> float:
        """
        Calculate overall mastery percentage
        Formula: weighted average of accuracy levels + efficiency bonus
        """
        try:
            # Weighted accuracy (easier questions count less)
            accuracy_easy = float(mastery.accuracy_easy)
            accuracy_med = float(mastery.accuracy_med)
            accuracy_hard = float(mastery.accuracy_hard)
            
            # Weights: Easy=0.2, Medium=0.4, Difficult=0.4
            weighted_accuracy = (0.2 * accuracy_easy + 0.4 * accuracy_med + 0.4 * accuracy_hard)
            
            # Efficiency bonus (up to 0.1 boost)
            efficiency_bonus = min(0.1, float(mastery.efficiency_score) * 0.1)
            
            # Exposure factor (gradually increase weight as exposure increases)
            exposure_factor = min(1.0, float(mastery.exposure_score) / 10.0)  # Full weight after 10 attempts
            
            # Calculate mastery with exposure weighting
            mastery_pct = (weighted_accuracy + efficiency_bonus) * exposure_factor
            
            return max(0.0, min(1.0, mastery_pct))
            
        except Exception as e:
            logger.error(f"Error calculating overall mastery: {e}")
            return 0.0
    
    async def apply_time_decay(self, db: AsyncSession, user_id: str, days_since_activity: int):
        """Apply time decay to mastery scores (called by nightly job)"""
        try:
            if days_since_activity == 0:
                return  # No decay for same day
            
            # Get all mastery records for user
            mastery_result = await db.execute(
                select(Mastery).where(Mastery.user_id == user_id)
            )
            mastery_records = mastery_result.scalars().all()
            
            # Apply decay to each mastery record
            decay_factor = self.time_decay_factor ** days_since_activity
            
            for mastery in mastery_records:
                # Apply decay to accuracy scores
                mastery.accuracy_easy = float(mastery.accuracy_easy) * decay_factor
                mastery.accuracy_med = float(mastery.accuracy_med) * decay_factor
                mastery.accuracy_hard = float(mastery.accuracy_hard) * decay_factor
                
                # Apply decay to efficiency
                mastery.efficiency_score = float(mastery.efficiency_score) * decay_factor
                
                # Recalculate overall mastery
                mastery.mastery_pct = self.calculate_overall_mastery(mastery)
                mastery.last_updated = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Applied time decay to {len(mastery_records)} mastery records for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error applying time decay: {e}")
            await db.rollback()
    
    async def get_mastery_trends(self, db: AsyncSession, user_id: str, days: int = 30) -> Dict:
        """Get mastery trends over time"""
        try:
            # Get mastery records updated in the last N days
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            mastery_result = await db.execute(
                select(Mastery, Topic.name)
                .join(Topic, Mastery.topic_id == Topic.id)
                .where(
                    Mastery.user_id == user_id,
                    Mastery.last_updated >= cutoff_date
                )
                .order_by(desc(Mastery.mastery_pct))
            )
            
            trends = []
            for mastery, topic_name in mastery_result.fetchall():
                trends.append({
                    "topic": topic_name,
                    "current_mastery": round(float(mastery.mastery_pct) * 100, 1),
                    "accuracy_easy": round(float(mastery.accuracy_easy) * 100, 1),
                    "accuracy_medium": round(float(mastery.accuracy_med) * 100, 1),
                    "accuracy_difficult": round(float(mastery.accuracy_hard) * 100, 1),
                    "efficiency_score": round(float(mastery.efficiency_score) * 100, 1),
                    "exposure_count": int(mastery.exposure_score),
                    "last_updated": mastery.last_updated.isoformat()
                })
            
            # Calculate overall stats
            if trends:
                avg_mastery = sum(t["current_mastery"] for t in trends) / len(trends)
                strong_topics = [t for t in trends if t["current_mastery"] >= 70]
                weak_topics = [t for t in trends if t["current_mastery"] < 40]
            else:
                avg_mastery = 0
                strong_topics = []
                weak_topics = []
            
            return {
                "trends": trends,
                "summary": {
                    "average_mastery": round(avg_mastery, 1),
                    "strong_topics_count": len(strong_topics),
                    "weak_topics_count": len(weak_topics),
                    "total_topics_practiced": len(trends)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting mastery trends: {e}")
            return {"trends": [], "summary": {}}
    
    async def identify_focus_areas(self, db: AsyncSession, user_id: str) -> List[Dict]:
        """Identify topics that need focus based on mastery and importance"""
        try:
            # Get mastery records with topic information
            mastery_result = await db.execute(
                select(Mastery, Topic.name, Topic.centrality)
                .join(Topic, Mastery.topic_id == Topic.id)
                .where(Mastery.user_id == user_id)
                .order_by(Mastery.mastery_pct.asc())  # Lowest mastery first
            )
            
            focus_areas = []
            for mastery, topic_name, centrality in mastery_result.fetchall():
                # Calculate focus priority (low mastery + high centrality = high priority)
                mastery_pct = float(mastery.mastery_pct)
                topic_centrality = float(centrality) if centrality else 0.5
                
                # Priority score: inverse of mastery * centrality
                priority_score = (1 - mastery_pct) * topic_centrality
                
                # Only include topics with low mastery or high priority
                if mastery_pct < 0.6 or priority_score > 0.3:
                    focus_areas.append({
                        "topic": topic_name,
                        "current_mastery": round(mastery_pct * 100, 1),
                        "priority_score": round(priority_score, 3),
                        "recommendation": self.get_focus_recommendation(mastery_pct, topic_centrality),
                        "weak_difficulties": self.identify_weak_difficulties(mastery)
                    })
            
            # Sort by priority score
            focus_areas.sort(key=lambda x: x["priority_score"], reverse=True)
            
            return focus_areas[:10]  # Top 10 focus areas
            
        except Exception as e:
            logger.error(f"Error identifying focus areas: {e}")
            return []
    
    def get_focus_recommendation(self, mastery_pct: float, centrality: float) -> str:
        """Get recommendation text for focus area"""
        if mastery_pct < 0.3:
            return "Urgent: Start with basic concepts and easy questions"
        elif mastery_pct < 0.5:
            return "Important: Focus on understanding and medium difficulty questions"
        elif mastery_pct < 0.7:
            return "Strengthen: Practice difficult questions and edge cases"
        else:
            return "Maintain: Regular practice to prevent decay"
    
    def identify_weak_difficulties(self, mastery: Mastery) -> List[str]:
        """Identify which difficulty levels are weak for this topic"""
        weak_difficulties = []
        
        if float(mastery.accuracy_easy) < 0.7:
            weak_difficulties.append("Easy")
        if float(mastery.accuracy_med) < 0.6:
            weak_difficulties.append("Medium")
        if float(mastery.accuracy_hard) < 0.4:
            weak_difficulties.append("Difficult")
        
        return weak_difficulties