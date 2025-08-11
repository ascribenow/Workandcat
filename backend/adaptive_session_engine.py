#!/usr/bin/env python3
"""
Adaptive Session Engine - EWMA/Mastery-Based Question Selection
Ensures sessions are adaptively selected based on user capability and mastery levels
"""

import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from database import get_database, Question, Topic, Mastery, Attempt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
import logging
import random
from formulas import (
    get_mastery_category,
    can_attempt_question,
    calculate_ewma_mastery
)

logger = logging.getLogger(__name__)

class AdaptiveSessionEngine:
    """
    Adaptive question selection engine that uses EWMA mastery scores
    to provide optimal challenge level for each user session
    """
    
    def __init__(self):
        # Adaptive selection weights
        self.selection_weights = {
            "mastery_gap": 0.4,        # Prioritize areas with low mastery
            "learning_impact": 0.3,    # High-impact questions first  
            "difficulty_match": 0.2,   # Match user's capability level
            "spacing_compliance": 0.1   # Respect attempt spacing rules
        }
        
        # Difficulty progression thresholds based on mastery
        self.difficulty_thresholds = {
            "Easy": {"min_mastery": 0.0, "max_mastery": 0.6},      # <60% mastery
            "Medium": {"min_mastery": 0.4, "max_mastery": 0.85},   # 40-85% mastery  
            "Hard": {"min_mastery": 0.7, "max_mastery": 1.0}       # >70% mastery
        }
        
        # Session composition ratios based on user capability
        self.session_composition = {
            "beginner": {"easy": 0.6, "medium": 0.3, "hard": 0.1},
            "intermediate": {"easy": 0.3, "medium": 0.5, "hard": 0.2}, 
            "advanced": {"easy": 0.1, "medium": 0.4, "hard": 0.5}
        }
    
    async def get_adaptive_session_questions(self, db: AsyncSession, user_id: str, 
                                           target_count: int = 15) -> List[Dict]:
        """
        Get adaptively selected questions for user session based on EWMA mastery
        """
        try:
            logger.info(f"Getting adaptive session questions for user {user_id}, target: {target_count}")
            
            # 1. Analyze user's current mastery state
            mastery_profile = await self.get_user_mastery_profile(db, user_id)
            
            # 2. Determine user capability level
            capability_level = self.determine_capability_level(mastery_profile)
            
            # 3. Get candidate questions with adaptive scoring
            candidate_questions = await self.get_candidate_questions_with_scores(db, user_id, mastery_profile)
            
            # 4. Apply adaptive selection algorithm
            selected_questions = await self.apply_adaptive_selection(
                candidate_questions, mastery_profile, capability_level, target_count
            )
            
            logger.info(f"Selected {len(selected_questions)} adaptive questions for user {user_id}")
            return selected_questions
            
        except Exception as e:
            logger.error(f"Error getting adaptive session questions: {e}")
            return []
    
    async def get_user_mastery_profile(self, db: AsyncSession, user_id: str) -> Dict:
        """
        Get comprehensive mastery profile using EWMA scores
        """
        try:
            # Get all mastery records with topic info
            mastery_query = text("""
                SELECT 
                    m.topic_id,
                    t.name as topic_name,
                    t.category,
                    t.parent_id,
                    m.mastery_pct,
                    m.exposure_score,
                    m.accuracy_easy,
                    m.accuracy_med, 
                    m.accuracy_hard,
                    m.efficiency_score,
                    m.last_updated
                FROM mastery m
                JOIN topics t ON m.topic_id = t.id
                WHERE m.user_id = :user_id
                ORDER BY m.mastery_pct ASC
            """)
            
            result = await db.execute(mastery_query, {"user_id": user_id})
            mastery_records = result.fetchall()
            
            profile = {
                "topics": {},
                "categories": {},
                "overall_mastery": 0.0,
                "weakest_topics": [],
                "strongest_topics": [],
                "capability_distribution": {"Easy": 0, "Medium": 0, "Hard": 0}
            }
            
            total_mastery = 0.0
            count = 0
            
            for record in mastery_records:
                mastery_score = float(record.mastery_pct or 0)
                category = record.category or "Unknown"
                
                # Store topic-level mastery
                profile["topics"][record.topic_name] = {
                    "topic_id": str(record.topic_id),
                    "mastery_score": mastery_score,
                    "category": category,
                    "mastery_category": get_mastery_category(mastery_score),
                    "accuracy_by_difficulty": {
                        "Easy": float(record.accuracy_easy or 0),
                        "Medium": float(record.accuracy_med or 0),
                        "Hard": float(record.accuracy_hard or 0)
                    },
                    "efficiency_score": float(record.efficiency_score or 0),
                    "last_updated": record.last_updated
                }
                
                # Group by category
                if category not in profile["categories"]:
                    profile["categories"][category] = {
                        "topics": [],
                        "avg_mastery": 0.0,
                        "topic_count": 0
                    }
                
                profile["categories"][category]["topics"].append(record.topic_name)
                profile["categories"][category]["topic_count"] += 1
                
                # Categorize topics by strength
                if mastery_score < 0.6:  # Needs focus
                    profile["weakest_topics"].append({
                        "topic": record.topic_name,
                        "mastery": mastery_score,
                        "category": category
                    })
                elif mastery_score >= 0.85:  # Mastered
                    profile["strongest_topics"].append({
                        "topic": record.topic_name,
                        "mastery": mastery_score,  
                        "category": category
                    })
                
                # Determine appropriate difficulty levels
                for difficulty, thresholds in self.difficulty_thresholds.items():
                    if thresholds["min_mastery"] <= mastery_score <= thresholds["max_mastery"]:
                        profile["capability_distribution"][difficulty] += 1
                
                total_mastery += mastery_score
                count += 1
            
            # Calculate overall averages
            if count > 0:
                profile["overall_mastery"] = total_mastery / count
                
                # Calculate category averages
                for category in profile["categories"]:
                    category_masteries = [
                        profile["topics"][topic]["mastery_score"] 
                        for topic in profile["categories"][category]["topics"]
                    ]
                    if category_masteries:
                        profile["categories"][category]["avg_mastery"] = sum(category_masteries) / len(category_masteries)
            
            # Sort by priority
            profile["weakest_topics"].sort(key=lambda x: x["mastery"])
            profile["strongest_topics"].sort(key=lambda x: x["mastery"], reverse=True)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user mastery profile: {e}")
            return {"topics": {}, "categories": {}, "overall_mastery": 0.0, "weakest_topics": [], "strongest_topics": []}
    
    def determine_capability_level(self, mastery_profile: Dict) -> str:
        """
        Determine user's overall capability level based on mastery distribution
        """
        overall_mastery = mastery_profile.get("overall_mastery", 0.0)
        
        if overall_mastery < 0.4:
            return "beginner"
        elif overall_mastery < 0.75:
            return "intermediate" 
        else:
            return "advanced"
    
    async def get_candidate_questions_with_scores(self, db: AsyncSession, user_id: str, 
                                                 mastery_profile: Dict) -> List[Dict]:
        """
        Get all candidate questions with adaptive selection scores
        """
        try:
            # Get questions with attempt history and spacing compliance
            questions_query = text("""
                SELECT DISTINCT
                    q.id,
                    q.topic_id,
                    q.subcategory,
                    q.type_of_question,
                    q.stem,
                    q.difficulty_band,
                    q.difficulty_score,
                    q.learning_impact,
                    q.importance_index,
                    q.learning_impact_v13,
                    q.importance_score_v13,
                    t.name as topic_name,
                    t.category,
                    COALESCE(last_attempts.last_attempt_date, NULL) as last_attempt_date,
                    COALESCE(attempt_stats.incorrect_count, 0) as incorrect_count,
                    COALESCE(attempt_stats.total_attempts, 0) as total_attempts,
                    COALESCE(attempt_stats.avg_time, 0) as avg_time_taken
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
                        COUNT(*) as total_attempts,
                        AVG(time_sec) as avg_time
                    FROM attempts 
                    WHERE user_id = :user_id
                    GROUP BY question_id
                ) attempt_stats ON q.id = attempt_stats.question_id
                WHERE q.is_active = true
                ORDER BY t.category, q.subcategory, q.difficulty_band
            """)
            
            result = await db.execute(questions_query, {"user_id": user_id})
            question_records = result.fetchall()
            
            candidate_questions = []
            
            for record in question_records:
                topic_name = record.topic_name
                category = record.category or "Unknown"
                difficulty = record.difficulty_band or "Medium"
                
                # Get topic mastery for this question
                topic_mastery = mastery_profile["topics"].get(topic_name, {})
                topic_mastery_score = topic_mastery.get("mastery_score", 0.0)
                
                # Check attempt spacing compliance
                spacing_compliant = True
                if record.last_attempt_date:
                    from datetime import datetime
                    last_attempt = datetime.fromisoformat(str(record.last_attempt_date))
                    spacing_compliant = can_attempt_question(last_attempt, record.incorrect_count)
                
                # Calculate adaptive selection score
                adaptive_score = self.calculate_adaptive_score(
                    mastery_score=topic_mastery_score,
                    difficulty=difficulty,
                    learning_impact=float(record.learning_impact_v13 or record.learning_impact or 0),
                    importance=float(record.importance_score_v13 or record.importance_index or 0),
                    spacing_compliant=spacing_compliant,
                    attempt_count=record.total_attempts
                )
                
                candidate_questions.append({
                    "id": str(record.id),
                    "topic_id": str(record.topic_id),
                    "topic_name": topic_name,
                    "category": category,
                    "subcategory": record.subcategory,
                    "type_of_question": record.type_of_question,
                    "difficulty_band": difficulty,
                    "mastery_score": topic_mastery_score,
                    "mastery_category": get_mastery_category(topic_mastery_score),
                    "adaptive_score": adaptive_score,
                    "learning_impact": float(record.learning_impact_v13 or record.learning_impact or 0),
                    "importance": float(record.importance_score_v13 or record.importance_index or 0),
                    "spacing_compliant": spacing_compliant,
                    "attempt_count": record.total_attempts,
                    "last_attempt_date": record.last_attempt_date
                })
            
            # Sort by adaptive score (highest first)
            candidate_questions.sort(key=lambda x: x["adaptive_score"], reverse=True)
            
            return candidate_questions
            
        except Exception as e:
            logger.error(f"Error getting candidate questions: {e}")
            return []
    
    def calculate_adaptive_score(self, mastery_score: float, difficulty: str, 
                               learning_impact: float, importance: float,
                               spacing_compliant: bool, attempt_count: int) -> float:
        """
        Calculate adaptive selection score based on user mastery and question attributes
        """
        try:
            # 1. Mastery gap score (higher for lower mastery topics)
            mastery_gap_score = 1.0 - mastery_score
            
            # 2. Learning impact score (normalized)
            learning_impact_score = min(learning_impact / 10.0, 1.0)
            
            # 3. Difficulty match score (optimal challenge zone)
            difficulty_match_score = self.get_difficulty_match_score(mastery_score, difficulty)
            
            # 4. Spacing compliance bonus
            spacing_bonus = 1.0 if spacing_compliant else 0.3
            
            # 5. Attempt frequency penalty (avoid over-attempted questions)
            frequency_penalty = max(0.1, 1.0 - (attempt_count * 0.1))
            
            # 6. Importance weight
            importance_weight = min(importance / 5.0, 1.0) if importance > 0 else 0.5
            
            # Calculate weighted composite score
            adaptive_score = (
                mastery_gap_score * self.selection_weights["mastery_gap"] +
                learning_impact_score * self.selection_weights["learning_impact"] +
                difficulty_match_score * self.selection_weights["difficulty_match"] +
                spacing_bonus * self.selection_weights["spacing_compliance"]
            ) * importance_weight * frequency_penalty
            
            return round(adaptive_score, 4)
            
        except Exception as e:
            logger.error(f"Error calculating adaptive score: {e}")
            return 0.0
    
    def get_difficulty_match_score(self, mastery_score: float, difficulty: str) -> float:
        """
        Calculate how well question difficulty matches user's current mastery level
        """
        thresholds = self.difficulty_thresholds.get(difficulty, {"min_mastery": 0.0, "max_mastery": 1.0})
        
        # Perfect match gets score of 1.0
        if thresholds["min_mastery"] <= mastery_score <= thresholds["max_mastery"]:
            # Within optimal range - calculate how close to center
            center = (thresholds["min_mastery"] + thresholds["max_mastery"]) / 2
            distance_from_center = abs(mastery_score - center)
            range_size = thresholds["max_mastery"] - thresholds["min_mastery"]
            match_score = 1.0 - (distance_from_center / (range_size / 2))
            return max(0.5, match_score)  # Minimum 0.5 for optimal range
        
        # Outside optimal range - penalize based on distance
        if mastery_score < thresholds["min_mastery"]:
            # Too easy
            distance = thresholds["min_mastery"] - mastery_score
            return max(0.1, 0.5 - distance)
        else:
            # Too hard
            distance = mastery_score - thresholds["max_mastery"] 
            return max(0.1, 0.3 - (distance * 0.5))
    
    async def apply_adaptive_selection(self, candidate_questions: List[Dict], 
                                     mastery_profile: Dict, capability_level: str, 
                                     target_count: int) -> List[Dict]:
        """
        Apply adaptive selection algorithm to choose optimal questions
        """
        try:
            # Get session composition based on capability level
            composition = self.session_composition[capability_level]
            
            # Calculate target counts per difficulty
            easy_target = int(target_count * composition["easy"])
            medium_target = int(target_count * composition["medium"])
            hard_target = target_count - easy_target - medium_target
            
            selected_questions = []
            
            # Select questions by difficulty with adaptive prioritization
            difficulty_targets = {
                "Easy": easy_target,
                "Medium": medium_target, 
                "Hard": hard_target
            }
            
            for difficulty, target in difficulty_targets.items():
                if target == 0:
                    continue
                    
                # Filter questions by difficulty
                difficulty_questions = [
                    q for q in candidate_questions 
                    if q["difficulty_band"] == difficulty and q["spacing_compliant"]
                ]
                
                # Sort by adaptive score within difficulty
                difficulty_questions.sort(key=lambda x: x["adaptive_score"], reverse=True)
                
                # Prioritize weak topics (mastery gap)
                weak_topic_questions = [
                    q for q in difficulty_questions 
                    if q["mastery_category"] == "Needs focus"
                ]
                
                on_track_questions = [
                    q for q in difficulty_questions 
                    if q["mastery_category"] == "On track"
                ]
                
                mastered_questions = [
                    q for q in difficulty_questions 
                    if q["mastery_category"] == "Mastered"
                ]
                
                # Select with priority: Weak topics > On track > Mastered
                selected_from_difficulty = []
                
                # Allocate 70% to weak topics, 20% to on track, 10% to mastered
                weak_allocation = int(target * 0.7)
                track_allocation = int(target * 0.2)
                master_allocation = target - weak_allocation - track_allocation
                
                # Select from each category
                selected_from_difficulty.extend(weak_topic_questions[:weak_allocation])
                selected_from_difficulty.extend(on_track_questions[:track_allocation])
                selected_from_difficulty.extend(mastered_questions[:master_allocation])
                
                # Fill remaining slots if needed
                remaining_needed = target - len(selected_from_difficulty)
                if remaining_needed > 0:
                    remaining_questions = [
                        q for q in difficulty_questions 
                        if q not in selected_from_difficulty
                    ][:remaining_needed]
                    selected_from_difficulty.extend(remaining_questions)
                
                selected_questions.extend(selected_from_difficulty[:target])
            
            # Final randomization within selected set to avoid predictability
            random.shuffle(selected_questions)
            
            logger.info(f"Adaptive selection complete: {len(selected_questions)} questions")
            logger.info(f"Difficulty distribution: Easy={len([q for q in selected_questions if q['difficulty_band']=='Easy'])}, " +
                       f"Medium={len([q for q in selected_questions if q['difficulty_band']=='Medium'])}, " +
                       f"Hard={len([q for q in selected_questions if q['difficulty_band']=='Hard'])}")
            
            return selected_questions[:target_count]
            
        except Exception as e:
            logger.error(f"Error applying adaptive selection: {e}")
            return candidate_questions[:target_count]  # Fallback to top candidates