"""
Mastery Tracking System for CAT Preparation Platform
Implements EWMA-based mastery calculation with time decay as per specification
"""

import uuid
from typing import Dict, List, Optional, Any
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

    async def update_type_mastery_after_attempt(self, db: AsyncSession, attempt: Attempt):
        """Update type-level mastery after a question attempt (for three-phase adaptive system)"""
        try:
            # Get question to determine type information
            question_result = await db.execute(select(Question).where(Question.id == attempt.question_id))
            question = question_result.scalar_one_or_none()
            
            if not question:
                logger.warning(f"No question found for attempt {attempt.id}")
                return
            
            # Extract taxonomy triple
            category = self.get_category_from_subcategory(question.subcategory or 'Unknown')
            subcategory = question.subcategory or 'Unknown'
            type_of_question = question.type_of_question or 'General'
            
            from database import TypeMastery
            
            # Get or create type mastery record
            type_mastery_result = await db.execute(
                select(TypeMastery).where(
                    TypeMastery.user_id == attempt.user_id,
                    TypeMastery.category == category,
                    TypeMastery.subcategory == subcategory,
                    TypeMastery.type_of_question == type_of_question
                )
            )
            type_mastery = type_mastery_result.scalar_one_or_none()
            
            if not type_mastery:
                type_mastery = TypeMastery(
                    user_id=attempt.user_id,
                    category=category,
                    subcategory=subcategory,
                    type_of_question=type_of_question,
                    total_attempts=0,
                    correct_attempts=0,
                    accuracy_rate=0,
                    avg_time_taken=0,
                    mastery_score=0,
                    first_attempt_date=datetime.utcnow(),
                    last_attempt_date=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                db.add(type_mastery)
                await db.flush()
            
            # Update type mastery with this attempt
            await self.update_type_mastery_scores(db, type_mastery, attempt)
            
            await db.commit()
            logger.info(f"Updated type mastery for user {attempt.user_id}: {category}>{subcategory}>{type_of_question}")
            
        except Exception as e:
            logger.error(f"Error updating type mastery after attempt: {e}")
            await db.rollback()

    async def update_type_mastery_scores(self, db: AsyncSession, type_mastery, attempt: Attempt):
        """Update type-level mastery scores based on attempt"""
        try:
            # Update attempt counts
            type_mastery.total_attempts += 1
            if attempt.is_correct:
                type_mastery.correct_attempts += 1
            
            # Calculate new accuracy rate
            type_mastery.accuracy_rate = type_mastery.correct_attempts / type_mastery.total_attempts if type_mastery.total_attempts > 0 else 0
            
            # Update average time (EWMA with alpha=0.3)
            if attempt.time_taken:
                if type_mastery.avg_time_taken > 0:
                    type_mastery.avg_time_taken = 0.3 * attempt.time_taken + 0.7 * type_mastery.avg_time_taken
                else:
                    type_mastery.avg_time_taken = attempt.time_taken
            
            # Calculate mastery score (combination of accuracy and efficiency)
            accuracy_component = float(type_mastery.accuracy_rate)
            
            # Efficiency component based on time
            efficiency_component = 1.0  # Default to full efficiency
            if type_mastery.avg_time_taken > 0:
                # Assume target time is 120 seconds
                target_time = 120
                if type_mastery.avg_time_taken <= target_time:
                    efficiency_component = 1.0
                else:
                    efficiency_component = max(0.3, target_time / type_mastery.avg_time_taken)
            
            # Combined mastery score (70% accuracy, 30% efficiency)
            type_mastery.mastery_score = 0.7 * accuracy_component + 0.3 * efficiency_component
            
            # Update timestamps
            type_mastery.last_attempt_date = datetime.utcnow()
            type_mastery.last_updated = datetime.utcnow()
            
            logger.debug(f"Type mastery updated: Accuracy={type_mastery.accuracy_rate:.2f}, Mastery={type_mastery.mastery_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating type mastery scores: {e}")

    def get_category_from_subcategory(self, subcategory: str) -> str:
        """Map subcategory to canonical category for type mastery tracking"""
        try:
            # Canonical mapping based on the taxonomy
            canonical_mapping = {
                # Arithmetic
                "Time-Speed-Distance": "Arithmetic",
                "Time-Work": "Arithmetic", 
                "Ratios and Proportions": "Arithmetic",
                "Percentages": "Arithmetic",
                "Averages and Alligation": "Arithmetic",
                "Profit-Loss-Discount": "Arithmetic",
                "Simple and Compound Interest": "Arithmetic",
                "Mixtures and Solutions": "Arithmetic",
                "Partnerships": "Arithmetic",
                
                # Algebra
                "Linear Equations": "Algebra",
                "Quadratic Equations": "Algebra", 
                "Inequalities": "Algebra",
                "Progressions": "Algebra",
                "Functions and Graphs": "Algebra",
                "Logarithms and Exponents": "Algebra",
                "Special Algebraic Identities": "Algebra",
                "Maxima and Minima": "Algebra",
                "Special Polynomials": "Algebra",
                
                # Geometry and Mensuration
                "Triangles": "Geometry and Mensuration",
                "Circles": "Geometry and Mensuration",
                "Polygons": "Geometry and Mensuration",
                "Lines and Angles": "Geometry and Mensuration",
                "Coordinate Geometry": "Geometry and Mensuration",
                "Mensuration 2D": "Geometry and Mensuration", 
                "Mensuration 3D": "Geometry and Mensuration",
                
                # Number System
                "Divisibility": "Number System",
                "HCF-LCM": "Number System",
                "Remainders": "Number System",
                "Base Systems": "Number System",
                "Digit Properties": "Number System",
                "Number Properties": "Number System",
                "Number Series": "Number System", 
                "Factorials": "Number System",
                
                # Modern Math
                "Permutation-Combination": "Modern Math",
                "Probability": "Modern Math",
                "Set Theory and Venn Diagram": "Modern Math"
            }
            
            return canonical_mapping.get(subcategory, "Arithmetic")  # Default to Arithmetic
            
        except Exception as e:
            logger.error(f"Error mapping subcategory to category: {e}")
            return "Arithmetic"

    async def get_type_mastery_breakdown(self, db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Get detailed type-level mastery breakdown for user"""
        try:
            from database import TypeMastery
            
            result = await db.execute(
                select(TypeMastery).where(TypeMastery.user_id == user_id)
                .order_by(TypeMastery.category, TypeMastery.subcategory, TypeMastery.type_of_question)
            )
            type_masteries = result.scalars().all()
            
            breakdown = []
            for tm in type_masteries:
                breakdown.append({
                    'category': tm.category,
                    'subcategory': tm.subcategory, 
                    'type_of_question': tm.type_of_question,
                    'total_attempts': tm.total_attempts,
                    'correct_attempts': tm.correct_attempts,
                    'accuracy_rate': float(tm.accuracy_rate) if tm.accuracy_rate else 0,
                    'mastery_score': float(tm.mastery_score) if tm.mastery_score else 0,
                    'mastery_percentage': float(tm.mastery_score * 100) if tm.mastery_score else 0,
                    'avg_time_taken': float(tm.avg_time_taken) if tm.avg_time_taken else 0,
                    'last_attempt_date': tm.last_attempt_date.isoformat() if tm.last_attempt_date else None
                })
            
            logger.info(f"Retrieved {len(breakdown)} type mastery records for user {user_id}")
            return breakdown
            
        except Exception as e:
            logger.error(f"Error getting type mastery breakdown: {e}")
            return []
    
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
    
    # =====================================================
    # v1.3 COMPLIANCE METHODS
    # =====================================================
    
    def get_mastery_category_v13(self, mastery_score: float) -> str:
        """
        Categorize mastery score based on v1.3 feedback thresholds
        Mastered (≥85%), On track (60–84%), Needs focus (<60%)
        """
        from formulas import get_mastery_category
        return get_mastery_category(mastery_score)
    
    async def create_mastery_history_entry(self, db: AsyncSession, user_id: str, subcategory: str, mastery_score: float):
        """
        Store daily mastery history as per v1.3 requirements
        """
        try:
            from database import MasteryHistory
            from datetime import date
            
            # Create new history entry
            history_entry = MasteryHistory(
                user_id=user_id,
                subcategory=subcategory,
                mastery_score=mastery_score,
                recorded_date=date.today()
            )
            
            db.add(history_entry)
            await db.flush()
            
            logger.info(f"Created mastery history entry for user {user_id}, subcategory {subcategory}: {mastery_score}")
            
        except Exception as e:
            logger.error(f"Error creating mastery history entry: {e}")
    
    async def calculate_preparedness_ambition_v13(self, db: AsyncSession, user_id: str, plan_start_date: datetime, target_date: datetime) -> float:
        """
        Calculate preparedness ambition from t-1 to t+90 as per v1.3 feedback
        """
        try:
            # Get current mastery levels for all topics
            mastery_query = select(Mastery).where(Mastery.user_id == user_id)
            mastery_result = await db.execute(mastery_query)
            masteries = mastery_result.scalars().all()
            
            if not masteries:
                return 0.0  # No mastery data available
            
            # Calculate current average mastery (t-1)
            current_avg_mastery = sum(float(m.mastery_pct or 0) for m in masteries) / len(masteries)
            
            # Target mastery by day 90 (aspirational - e.g., 85% across all topics)
            target_mastery = 0.85
            
            # Calculate days from plan start to target
            days_to_target = (target_date - plan_start_date).days
            days_to_target = max(days_to_target, 90)  # At least 90 days
            
            # Preparedness ambition = improvement needed from current to target
            improvement_needed = target_mastery - current_avg_mastery
            preparedness_ambition = max(0.0, improvement_needed)
            
            # Normalize based on timeline (more ambition if less time)
            time_pressure_factor = 90.0 / days_to_target  # More pressure if less than 90 days
            preparedness_ambition *= time_pressure_factor
            
            return min(preparedness_ambition, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Error calculating preparedness ambition: {e}")
            return 0.0
    
    async def apply_v13_mastery_thresholds(self, db: AsyncSession, user_id: str) -> Dict[str, List[str]]:
        """
        Apply v1.3 mastery thresholds to categorize topics
        Returns dict with 'mastered', 'on_track', 'needs_focus' lists
        """
        try:
            # Get all mastery records for user
            mastery_query = select(Mastery, Topic.name).join(Topic, Mastery.topic_id == Topic.id).where(Mastery.user_id == user_id)
            mastery_result = await db.execute(mastery_query)
            mastery_records = mastery_result.all()
            
            categorized = {
                "mastered": [],    # ≥85%
                "on_track": [],    # 60-84%
                "needs_focus": []  # <60%
            }
            
            for mastery, topic_name in mastery_records:
                mastery_score = float(mastery.mastery_pct or 0)
                category = self.get_mastery_category_v13(mastery_score)
                
                topic_info = {
                    "name": topic_name,
                    "mastery_percentage": round(mastery_score * 100, 1),
                    "category": category
                }
                
                if category == "Mastered":
                    categorized["mastered"].append(topic_info)
                elif category == "On track":
                    categorized["on_track"].append(topic_info)
                else:
                    categorized["needs_focus"].append(topic_info)
            
            return categorized
            
        except Exception as e:
            logger.error(f"Error applying v1.3 mastery thresholds: {e}")
            return {"mastered": [], "on_track": [], "needs_focus": []}
    
    async def update_mastery_with_v13_formulas(self, db: AsyncSession, user_id: str, question_id: str, attempt: Attempt):
        """
        Update mastery using v1.3 compliant formulas and store history
        """
        try:
            from formulas import calculate_ewma_mastery
            
            # Get question details
            question_result = await db.execute(select(Question, Topic.name).join(Topic).where(Question.id == question_id))
            question, topic_name = question_result.first()
            
            if not question:
                return
            
            # Get current mastery
            mastery_query = select(Mastery).where(
                and_(Mastery.user_id == user_id, Mastery.topic_id == question.topic_id)
            )
            mastery_result = await db.execute(mastery_query)
            mastery = mastery_result.scalar_one_or_none()
            
            # Calculate new performance score
            performance_score = 1.0 if attempt.correct else 0.0
            
            # Time efficiency factor
            expected_time = self.target_times.get(question.difficulty_band, 150)
            time_efficiency = min(expected_time / max(attempt.time_sec, 1), 1.0)
            performance_score *= time_efficiency
            
            if mastery:
                # Update existing mastery using v1.3 EWMA (α=0.6)
                current_mastery = float(mastery.mastery_pct or 0)
                new_mastery = calculate_ewma_mastery(
                    current_mastery, 
                    performance_score, 
                    alpha=0.6  # v1.3 specification
                )
                mastery.mastery_pct = new_mastery
            else:
                # Create new mastery record
                from database import Mastery
                mastery = Mastery(
                    user_id=user_id,
                    topic_id=question.topic_id,
                    mastery_pct=performance_score,
                    exposure_score=1.0,
                    accuracy_easy=1.0 if question.difficulty_band == "Easy" and attempt.correct else 0.0,
                    accuracy_med=1.0 if question.difficulty_band == "Medium" and attempt.correct else 0.0,
                    accuracy_hard=1.0 if question.difficulty_band == "Hard" and attempt.correct else 0.0,
                    efficiency_score=time_efficiency
                )
                db.add(mastery)
                new_mastery = performance_score
            
            await db.flush()
            
            # Store mastery history entry
            await self.create_mastery_history_entry(
                db, user_id, question.subcategory, new_mastery
            )
            
            logger.info(f"Updated mastery for user {user_id}, topic {topic_name}: {new_mastery:.3f}")
            
        except Exception as e:
            logger.error(f"Error updating mastery with v1.3 formulas: {e}")