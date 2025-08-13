"""
Sophisticated 12-Question Session Logic
Adaptive, personalized question selection based on user learning profile
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
from database import Question, Attempt, Mastery, Topic, User, AsyncSession

logger = logging.getLogger(__name__)

class AdaptiveSessionLogic:
    """
    Sophisticated session logic that creates personalized 12-question sessions
    based on user's learning profile, mastery levels, and performance patterns
    """
    
    def __init__(self):
        # CAT Canonical Taxonomy Distribution
        self.category_distribution = {
            "A-Arithmetic": 4,           # 33% - Most important for CAT
            "B-Algebra": 3,              # 25% - Core mathematical concepts
            "C-Geometry & Mensuration": 2, # 17% - Spatial reasoning
            "D-Number System": 2,        # 17% - Fundamental concepts
            "E-Modern Math": 1           # 8% - Advanced topics
        }
        
        # Subcategory mapping
        self.canonical_subcategories = {
            "A-Arithmetic": [
                "Time–Speed–Distance (TSD)", "Time & Work", "Ratio–Proportion–Variation",
                "Percentages", "Averages & Alligation", "Profit–Loss–Discount (PLD)",
                "Simple & Compound Interest (SI–CI)", "Mixtures & Solutions"
            ],
            "B-Algebra": [
                "Linear Equations", "Quadratic Equations", "Inequalities", "Progressions",
                "Functions & Graphs", "Logarithms & Exponents", "Special Algebraic Identities"
            ],
            "C-Geometry & Mensuration": [
                "Triangles", "Circles", "Polygons", "Coordinate Geometry",
                "Mensuration (2D & 3D)", "Trigonometry in Geometry"
            ],
            "D-Number System": [
                "Divisibility", "HCF–LCM", "Remainders & Modular Arithmetic",
                "Base Systems", "Digit Properties"
            ],
            "E-Modern Math": [
                "Permutation–Combination (P&C)", "Probability", "Set Theory & Venn Diagrams"
            ]
        }

    async def create_personalized_session(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Create a sophisticated 12-question session tailored to the user's learning profile
        """
        try:
            logger.info(f"Creating personalized session for user {user_id}")
            
            # Step 1: Analyze user's learning profile
            user_profile = await self.analyze_user_learning_profile(user_id, db)
            logger.info(f"User profile: {user_profile}")
            
            # Step 2: Get personalized question pool
            question_pool = await self.get_personalized_question_pool(user_id, user_profile, db)
            
            if len(question_pool) < 12:
                logger.warning(f"Limited question pool ({len(question_pool)}), falling back to simple selection")
                return await self.create_simple_fallback_session(user_id, db)
            
            # Step 3: Apply intelligent selection strategies
            selected_questions = await self.apply_selection_strategies(
                user_id, user_profile, question_pool, db
            )
            
            # Step 4: Order questions by difficulty progression
            ordered_questions = self.order_by_difficulty_progression(selected_questions, user_profile)
            
            # Step 5: Generate session metadata
            session_metadata = self.generate_session_metadata(ordered_questions, user_profile)
            
            return {
                "questions": ordered_questions,
                "metadata": session_metadata,
                "personalization_applied": True
            }
            
        except Exception as e:
            logger.error(f"Error creating personalized session: {e}")
            return await self.create_simple_fallback_session(user_id, db)

    async def analyze_user_learning_profile(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Comprehensive analysis of user's learning patterns and performance
        """
        try:
            # Recent performance (last 7 days)
            recent_accuracy = await self.calculate_recent_accuracy(user_id, db, days=7)
            
            # Overall performance (last 30 days)
            overall_accuracy = await self.calculate_recent_accuracy(user_id, db, days=30)
            
            # Mastery levels by subcategory
            mastery_data = await self.get_user_mastery_breakdown(user_id, db)
            
            # Categorize subcategories by mastery level
            weak_subcategories = [
                item['subcategory'] for item in mastery_data 
                if item['mastery_percentage'] < 60
            ]
            
            moderate_subcategories = [
                item['subcategory'] for item in mastery_data 
                if 60 <= item['mastery_percentage'] < 85
            ]
            
            strong_subcategories = [
                item['subcategory'] for item in mastery_data 
                if item['mastery_percentage'] >= 85
            ]
            
            # Question attempt frequency
            attempt_frequency = await self.get_attempt_frequency_by_subcategory(user_id, db)
            
            # Determine learning stage
            learning_stage = self.determine_learning_stage(recent_accuracy, len(weak_subcategories))
            
            # Get difficulty preferences based on recent performance
            difficulty_preferences = self.get_difficulty_preferences(recent_accuracy, learning_stage)
            
            return {
                'recent_accuracy': recent_accuracy,
                'overall_accuracy': overall_accuracy,
                'weak_subcategories': weak_subcategories,
                'moderate_subcategories': moderate_subcategories,
                'strong_subcategories': strong_subcategories,
                'attempt_frequency': attempt_frequency,
                'learning_stage': learning_stage,
                'difficulty_preferences': difficulty_preferences,
                'total_attempts': len(attempt_frequency)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user profile: {e}")
            return {
                'recent_accuracy': 50.0,
                'overall_accuracy': 50.0,
                'weak_subcategories': [],
                'moderate_subcategories': [],
                'strong_subcategories': [],
                'attempt_frequency': {},
                'learning_stage': 'intermediate',
                'difficulty_preferences': {'Easy': 3, 'Medium': 6, 'Hard': 3},
                'total_attempts': 0
            }

    async def calculate_recent_accuracy(self, user_id: str, db: AsyncSession, days: int = 7) -> float:
        """Calculate user's accuracy over the last N days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db.execute(
                select(
                    func.count(Attempt.id).label('total'),
                    func.sum(func.cast(Attempt.correct, func.Integer)).label('correct')
                )
                .where(
                    and_(
                        Attempt.user_id == user_id,
                        Attempt.created_at >= cutoff_date
                    )
                )
            )
            
            row = result.first()
            if row and row.total > 0:
                return (row.correct / row.total) * 100
            
            return 50.0  # Default for new users
            
        except Exception as e:
            logger.error(f"Error calculating recent accuracy: {e}")
            return 50.0

    async def get_user_mastery_breakdown(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get detailed mastery breakdown by subcategory"""
        try:
            # Get all attempts with question details
            result = await db.execute(
                select(
                    Question.subcategory,
                    func.count(Attempt.id).label('total_attempts'),
                    func.sum(func.cast(Attempt.correct, func.Integer)).label('correct_attempts'),
                    func.avg(func.cast(Attempt.correct, func.Float)).label('accuracy')
                )
                .join(Question, Attempt.question_id == Question.id)
                .where(Attempt.user_id == user_id)
                .group_by(Question.subcategory)
            )
            
            mastery_data = []
            for row in result:
                accuracy = row.accuracy * 100 if row.accuracy else 0
                mastery_data.append({
                    'subcategory': row.subcategory,
                    'total_attempts': row.total_attempts,
                    'correct_attempts': row.correct_attempts,
                    'mastery_percentage': accuracy
                })
            
            return mastery_data
            
        except Exception as e:
            logger.error(f"Error getting mastery breakdown: {e}")
            return []

    async def get_attempt_frequency_by_subcategory(self, user_id: str, db: Session) -> Dict[str, int]:
        """Get attempt frequency by subcategory for spaced repetition"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            result = await db.execute(
                select(
                    Question.subcategory,
                    func.count(Attempt.id).label('recent_attempts')
                )
                .join(Question, Attempt.question_id == Question.id)
                .where(
                    and_(
                        Attempt.user_id == user_id,
                        Attempt.created_at >= cutoff_date
                    )
                )
                .group_by(Question.subcategory)
            )
            
            frequency = {}
            for row in result:
                frequency[row.subcategory] = row.recent_attempts
            
            return frequency
            
        except Exception as e:
            logger.error(f"Error getting attempt frequency: {e}")
            return {}

    def determine_learning_stage(self, accuracy: float, weak_count: int) -> str:
        """Determine student's learning stage for adaptive content"""
        if accuracy < 40 or weak_count > 20:
            return "beginner"           # Focus on fundamentals
        elif accuracy < 70 or weak_count > 10:
            return "intermediate"       # Balanced practice
        else:
            return "advanced"          # Challenge and refinement

    def get_difficulty_preferences(self, accuracy: float, learning_stage: str) -> Dict[str, int]:
        """Get difficulty distribution based on performance"""
        if learning_stage == "beginner":
            return {"Easy": 6, "Medium": 4, "Hard": 2}  # Confidence building
        elif learning_stage == "intermediate":
            return {"Easy": 3, "Medium": 6, "Hard": 3}  # Balanced growth
        else:  # advanced
            return {"Easy": 2, "Medium": 4, "Hard": 6}  # Challenge focused

    async def get_personalized_question_pool(self, user_id: str, user_profile: Dict, db: Session) -> List[Question]:
        """Get a personalized pool of questions based on user profile"""
        try:
            question_pool = []
            
            # Priority 1: Questions from weak areas (60% of pool)
            if user_profile['weak_subcategories']:
                weak_questions = await db.execute(
                    select(Question)
                    .where(
                        and_(
                            Question.is_active == True,
                            Question.subcategory.in_(user_profile['weak_subcategories'])
                        )
                    )
                    .order_by(func.random())
                    .limit(20)
                )
                question_pool.extend(weak_questions.scalars().all())
            
            # Priority 2: Questions from moderate areas (30% of pool)
            if user_profile['moderate_subcategories']:
                moderate_questions = await db.execute(
                    select(Question)
                    .where(
                        and_(
                            Question.is_active == True,
                            Question.subcategory.in_(user_profile['moderate_subcategories'])
                        )
                    )
                    .order_by(func.random())
                    .limit(10)
                )
                question_pool.extend(moderate_questions.scalars().all())
            
            # Priority 3: Questions from strong areas for retention (10% of pool)
            if user_profile['strong_subcategories']:
                strong_questions = await db.execute(
                    select(Question)
                    .where(
                        and_(
                            Question.is_active == True,
                            Question.subcategory.in_(user_profile['strong_subcategories'])
                        )
                    )
                    .order_by(func.random())
                    .limit(5)
                )
                question_pool.extend(strong_questions.scalars().all())
            
            # If not enough personalized questions, add random questions
            if len(question_pool) < 25:
                additional_questions = await db.execute(
                    select(Question)
                    .where(Question.is_active == True)
                    .order_by(func.random())
                    .limit(30 - len(question_pool))
                )
                question_pool.extend(additional_questions.scalars().all())
            
            return question_pool
            
        except Exception as e:
            logger.error(f"Error getting personalized question pool: {e}")
            return []

    async def apply_selection_strategies(self, user_id: str, user_profile: Dict, 
                                       question_pool: List[Question], db: Session) -> List[Question]:
        """Apply intelligent selection strategies to choose 12 questions"""
        try:
            selected_questions = []
            
            # Strategy 1: Category-balanced selection
            category_questions = self.select_by_category_distribution(question_pool, user_profile)
            
            # Strategy 2: Difficulty-balanced selection
            difficulty_questions = self.select_by_difficulty_distribution(category_questions, user_profile)
            
            # Strategy 3: Spaced repetition filter
            spaced_questions = await self.apply_spaced_repetition_filter(
                user_id, difficulty_questions, db
            )
            
            # Strategy 4: Ensure variety in question types
            final_questions = self.ensure_question_variety(spaced_questions)
            
            return final_questions[:12]
            
        except Exception as e:
            logger.error(f"Error applying selection strategies: {e}")
            return question_pool[:12]

    def select_by_category_distribution(self, questions: List[Question], 
                                      user_profile: Dict) -> List[Question]:
        """Select questions ensuring balanced category distribution"""
        try:
            selected = []
            
            # Group questions by category
            category_groups = {}
            for question in questions:
                # Determine category from subcategory
                category = self.get_category_from_subcategory(question.subcategory)
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(question)
            
            # Select questions according to distribution
            for category, target_count in self.category_distribution.items():
                if category in category_groups:
                    # Prioritize weak areas within category
                    category_questions = category_groups[category]
                    
                    # Sort by weakness (questions from weak subcategories first)
                    weak_first = sorted(
                        category_questions,
                        key=lambda q: (
                            0 if q.subcategory in user_profile['weak_subcategories'] else
                            1 if q.subcategory in user_profile['moderate_subcategories'] else 2
                        )
                    )
                    
                    selected.extend(weak_first[:target_count])
            
            return selected
            
        except Exception as e:
            logger.error(f"Error in category distribution selection: {e}")
            return questions[:12]

    def select_by_difficulty_distribution(self, questions: List[Question], 
                                        user_profile: Dict) -> List[Question]:
        """Select questions with appropriate difficulty distribution"""
        try:
            difficulty_prefs = user_profile['difficulty_preferences']
            selected = []
            
            # Group by difficulty
            difficulty_groups = {'Easy': [], 'Medium': [], 'Hard': []}
            for question in questions:
                difficulty = question.difficulty_band or 'Medium'
                if difficulty in difficulty_groups:
                    difficulty_groups[difficulty].append(question)
            
            # Select according to difficulty preferences
            for difficulty, target_count in difficulty_prefs.items():
                if difficulty in difficulty_groups:
                    available = difficulty_groups[difficulty]
                    selected.extend(available[:target_count])
            
            return selected
            
        except Exception as e:
            logger.error(f"Error in difficulty distribution selection: {e}")
            return questions

    async def apply_spaced_repetition_filter(self, user_id: str, questions: List[Question], 
                                           db: Session) -> List[Question]:
        """Apply spaced repetition principles to avoid recently attempted questions"""
        try:
            # Get recently attempted questions (last 3 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=3)
            
            recent_attempts = await db.execute(
                select(Attempt.question_id)
                .where(
                    and_(
                        Attempt.user_id == user_id,
                        Attempt.created_at >= recent_cutoff
                    )
                )
            )
            
            recently_attempted = {row.question_id for row in recent_attempts}
            
            # Prioritize questions not attempted recently
            fresh_questions = [q for q in questions if q.id not in recently_attempted]
            recent_questions = [q for q in questions if q.id in recently_attempted]
            
            # Use fresh questions first, then recent if needed
            if len(fresh_questions) >= 12:
                return fresh_questions
            else:
                return fresh_questions + recent_questions[:12 - len(fresh_questions)]
                
        except Exception as e:
            logger.error(f"Error applying spaced repetition filter: {e}")
            return questions

    def ensure_question_variety(self, questions: List[Question]) -> List[Question]:
        """Ensure variety in question types and avoid repetition"""
        try:
            # Group by type_of_question to ensure variety
            type_groups = {}
            for question in questions:
                q_type = question.type_of_question or 'General'
                if q_type not in type_groups:
                    type_groups[q_type] = []
                type_groups[q_type].append(question)
            
            # Select variety ensuring no more than 3 questions of same type
            selected = []
            remaining = list(questions)
            
            for q_type, type_questions in type_groups.items():
                # Take max 3 questions of each type
                selected.extend(type_questions[:3])
                for q in type_questions[:3]:
                    if q in remaining:
                        remaining.remove(q)
            
            # Fill remaining slots
            selected.extend(remaining[:12 - len(selected)])
            
            return selected[:12]
            
        except Exception as e:
            logger.error(f"Error ensuring question variety: {e}")
            return questions[:12]

    def order_by_difficulty_progression(self, questions: List[Question], 
                                      user_profile: Dict) -> List[Question]:
        """Order questions by difficulty progression for optimal learning flow"""
        try:
            learning_stage = user_profile['learning_stage']
            
            # Separate by difficulty
            easy = [q for q in questions if q.difficulty_band == 'Easy']
            medium = [q for q in questions if q.difficulty_band == 'Medium']
            hard = [q for q in questions if q.difficulty_band == 'Hard']
            
            if learning_stage == 'beginner':
                # Start easy, gradually increase
                return easy[:4] + medium[:4] + hard[:2] + easy[4:] + medium[4:]
            elif learning_stage == 'intermediate':
                # Mixed progression with confidence building
                return easy[:2] + medium[:3] + hard[:1] + medium[3:] + hard[1:] + easy[2:]
            else:  # advanced
                # Challenge early, maintain intensity
                return easy[:1] + medium[:2] + hard[:3] + medium[2:] + hard[3:] + easy[1:]
                
        except Exception as e:
            logger.error(f"Error ordering by difficulty progression: {e}")
            return questions

    def generate_session_metadata(self, questions: List[Question], 
                                 user_profile: Dict) -> Dict[str, Any]:
        """Generate metadata about the session composition"""
        try:
            # Difficulty breakdown
            difficulty_count = {'Easy': 0, 'Medium': 0, 'Hard': 0}
            category_count = {}
            subcategory_count = {}
            
            for question in questions:
                # Count difficulties
                difficulty = question.difficulty_band or 'Medium'
                difficulty_count[difficulty] += 1
                
                # Count categories
                category = self.get_category_from_subcategory(question.subcategory)
                category_count[category] = category_count.get(category, 0) + 1
                
                # Count subcategories
                subcategory_count[question.subcategory] = subcategory_count.get(question.subcategory, 0) + 1
            
            return {
                'learning_stage': user_profile['learning_stage'],
                'recent_accuracy': user_profile['recent_accuracy'],
                'difficulty_distribution': difficulty_count,
                'category_distribution': category_count,
                'subcategory_distribution': subcategory_count,
                'weak_areas_targeted': len([q for q in questions if q.subcategory in user_profile['weak_subcategories']]),
                'session_type': 'adaptive_personalized',
                'total_questions': len(questions)
            }
            
        except Exception as e:
            logger.error(f"Error generating session metadata: {e}")
            return {'session_type': 'adaptive_personalized', 'total_questions': len(questions)}

    def get_category_from_subcategory(self, subcategory: str) -> str:
        """Map subcategory to main category"""
        for category, subcategories in self.canonical_subcategories.items():
            if subcategory in subcategories:
                return category
        return "A-Arithmetic"  # Default fallback

    async def create_simple_fallback_session(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Fallback to simple random selection if sophisticated logic fails"""
        try:
            logger.info(f"Creating simple fallback session for user {user_id}")
            
            result = await db.execute(
                select(Question)
                .where(Question.is_active == True)
                .order_by(func.random())
                .limit(12)
            )
            
            questions = result.scalars().all()
            
            return {
                "questions": questions,
                "metadata": {
                    "session_type": "simple_random",
                    "total_questions": len(questions),
                    "personalization_applied": False
                },
                "personalization_applied": False
            }
            
        except Exception as e:
            logger.error(f"Error creating fallback session: {e}")
            return {
                "questions": [],
                "metadata": {"session_type": "error", "total_questions": 0},
                "personalization_applied": False
            }