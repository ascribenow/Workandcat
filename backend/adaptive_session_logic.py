"""
Sophisticated 12-Question Session Logic - THREE-PHASE ADAPTIVE ENHANCED
Adaptive, personalized question selection with:
- PYQ frequency integration
- Dynamic category quotas  
- Subcategory diversity caps
- Differential cooldowns
- THREE-PHASE ADAPTIVE PROGRESSION:
  * Phase A (Sessions 1-30): Coverage & Calibration
  * Phase B (Sessions 31-60): Strengthen & Stretch  
  * Phase C (Sessions 61+): Fully Adaptive
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc, case
from database import Question, Attempt, Mastery, Topic, User, AsyncSession

logger = logging.getLogger(__name__)

class AdaptiveSessionLogic:
    """
    THREE-PHASE ADAPTIVE ENHANCED: Sophisticated session logic with phase-based progression
    Phase A (1-30): Coverage & Calibration
    Phase B (31-60): Strengthen & Stretch
    Phase C (61+): Fully Adaptive
    """
    
    def __init__(self):
        # Base category distribution (updated for new canonical taxonomy)
        self.base_category_distribution = {
            "Arithmetic": 4,                    # 33% - Core calculation topics
            "Algebra": 3,                       # 25% - Algebraic manipulation
            "Geometry and Mensuration": 3,      # 25% - Spatial and geometric reasoning  
            "Number System": 1,                 # 8% - Number theory fundamentals
            "Modern Math": 1                    # 8% - Combinatorics and probability
        }
        
        # THREE-PHASE DIFFICULTY DISTRIBUTIONS
        self.phase_difficulty_distributions = {
            "phase_a": {  # Sessions 1-30: Coverage & Calibration
                "Easy": 0.2,      # 20%
                "Medium": 0.75,   # 75% 
                "Hard": 0.05      # 5%
            },
            "phase_b": {  # Sessions 31-60: Strengthen & Stretch
                "Easy": 0.2,      # 20%
                "Medium": 0.5,    # 50%
                "Hard": 0.3       # 30%
            },
            "phase_c": {  # Sessions 61+: Fully Adaptive
                "Easy": 0.15,     # 15%
                "Medium": 0.55,   # 55%
                "Hard": 0.3       # 30%
            }
        }
        
        # Phase allocation percentages for Phase B
        self.phase_b_allocation = {
            "weak_areas_easy_medium": 0.45,  # 45% target weak areas with Easy→Medium
            "strong_areas_hard": 0.35,       # 35% target strong areas with Hard
            "authentic_distribution": 0.2    # 20% maintain CAT-authentic distribution
        }
        
        # PHASE 1: Differential cooldown periods by difficulty (RELAXED FOR TESTING)
        self.cooldown_periods = {
            "Easy": 0,      # No cooldown for now
            "Medium": 0,    # No cooldown for now  
            "Hard": 0       # No cooldown for now
        }
        
        # PHASE 1: Subcategory diversity limits (RELAXED FOR LIMITED QUESTION POOL)
        self.max_questions_per_subcategory = 5  # Max 5 per subcategory for diversity
        self.min_subcategories_per_session = 3  # Target minimum 3 subcategories per session
        self.max_questions_per_type_in_subcategory = 3  # Max 3 per type within subcategory
        
        # Updated canonical taxonomy based on provided CSV document
        self.canonical_subcategories = {
            "Arithmetic": [
                "Time-Speed-Distance", "Time-Work", "Ratios and Proportions", 
                "Percentages", "Averages and Alligation", "Profit-Loss-Discount",
                "Simple and Compound Interest", "Mixtures and Solutions", "Partnerships"
            ],
            "Algebra": [
                "Linear Equations", "Quadratic Equations", "Inequalities", "Progressions",
                "Functions and Graphs", "Logarithms and Exponents", "Special Algebraic Identities",
                "Maxima and Minima", "Special Polynomials"
            ],
            "Geometry and Mensuration": [
                "Triangles", "Circles", "Polygons", "Coordinate Geometry",
                "Mensuration 2D", "Mensuration 3D", "Trigonometry"
            ],
            "Number System": [
                "Divisibility", "HCF-LCM", "Remainders", "Base Systems",
                "Digit Properties", "Number Properties", "Number Series", "Factorials"
            ],
            "Modern Math": [
                "Permutation-Combination", "Probability", "Set Theory and Venn Diagram"
            ]
        }

        # Detailed question types mapping based on canonical taxonomy CSV
        self.question_types_mapping = {
            # Arithmetic
            "Time-Speed-Distance": ["Basics", "Relative Speed", "Circular Track Motion", "Boats and Streams", "Trains", "Races"],
            "Time-Work": ["Work Time Effeciency", "Pipes and Cisterns", "Work Equivalence"],
            "Ratios and Proportions": ["Simple Rations", "Compound Ratios", "Direct and Inverse Variation", "Partnerships"],
            "Percentages": ["Basics", "Percentage Change", "Successive Percentage Change"],
            "Averages and Alligation": ["Basic Averages", "Weighted Averages", "Alligations & Mixtures", "Three Mixture Alligations"],
            "Profit-Loss-Discount": ["Basics", "Successive Profit/Loss/Discounts", "Marked Price and Cost Price Relations", "Discount Chains"],
            "Simple and Compound Interest": ["Basics", "Difference between Simple Interest and Compound Interests", "Fractional Time Period Compound Interest"],
            "Mixtures and Solutions": ["Replacements", "Concentration Change", "Solid-Liquid-Gas Mixtures"],
            "Partnerships": ["Profit share"],
            
            # Algebra
            "Linear Equations": ["Two variable systems", "Three variable systems", "Dependent and Inconsistent Systems"],
            "Quadratic Equations": ["Roots & Nature of Roots", "Sum and Product of Roots", "Maximum and Minimum Values"],
            "Inequalities": ["Linear Inequalities", "Quadratic Inequalities", "Modulus and Absolute Value", "Arithmetic Mean", "Geometric Mean", "Cauchy Schwarz"],
            "Progressions": ["Arithmetic Progression", "Geometric Progression", "Harmonic Progression", "Mixed Progressions"],
            "Functions and Graphs": ["Linear Functions", "Quadratic Functions", "Polynomial Functions", "Modulus Functions", "Step Functions", "Transformations", "Domain Range", "Composition and Inverse Functions"],
            "Logarithms and Exponents": ["Basics", "Change of Base Formula", "Soliving Log Equations", "Surds and Indices"],
            "Special Algebraic Identities": ["Expansion and Factorisation", "Cubes and Squares", "Binomial Theorem"],
            "Maxima and Minima": ["Optimsation with Algebraic Expressions"],
            "Special Polynomials": ["Remainder Theorem", "Factor Theorem"],
            
            # Geometry and Mensuration
            "Triangles": ["Properties (Angles, Sides, Medians, Bisectors)", "Congruence & Similarity", "Pythagoras & Converse", "Inradius, Circumradius, Orthocentre"],
            "Circles": ["Tangents & Chords", "Angles in a Circle", "Cyclic Quadrilaterals"],
            "Polygons": ["Regular Polygons", "Interior / Exterior Angles"],
            "Coordinate Geometry": ["Distance", "Section Formula", "Midpoint", "Equation of a line", "Slope & Intercepts", "Circles in Coordinate Plane", "Parabola", "Ellipse", "Hyperbola"],
            "Mensuration 2D": ["Area Triangle", "Area Rectangle", "Area Trapezium", "Area Circle", "Sector"],
            "Mensuration 3D": ["Volume Cubes", "Volume Cuboid", "Volume Cylinder", "Volume Cone", "Volume Sphere", "Volume Hemisphere", "Surface Areas"],
            "Trigonometry": ["Heights and Distances", "Basic Trigonometric Ratios"],
            
            # Number System
            "Divisibility": ["Basic Divisibility Rules", "Factorisation of Integers"],
            "HCF-LCM": ["Euclidean Algorithm", "Product of HCF and LCM"],
            "Remainders": ["Basic Remainder Theorem", "Chinese Remainder Theorem", "Cyclicity of Remainders (Last Digits)", "Cyclicity of Remainders (Last Two Digits)"],
            "Base Systems": ["Conversion between bases", "Arithmetic in different bases"],
            "Digit Properties": ["Sum of Digits", "Last Digit Patterns", "Palindromes", "Repetitive Digits"],
            "Number Properties": ["Perfect Squares", "Perfect Cubes"],
            "Number Series": ["Sum of Squares", "Sum of Cubes", "Telescopic Series"],
            "Factorials": ["Properties of Factorials"],
            
            # Modern Math
            "Permutation-Combination": ["Basics", "Circular Permutations", "Permutations with Repetitions", "Permutations with Restrictions", "Combinations with Repetitions", "Combinations with Restrictions"],
            "Probability": ["Classical Probability", "Conditional Probability", "Bayes' Theorem"],
            "Set Theory and Venn Diagram": ["Union and Intersection", "Complement and Difference of Sets", "Multi Set Problems"]
        }

    def create_personalized_session(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        PHASE 1 ENHANCED: Create a sophisticated 12-question session with PYQ frequency integration
        """
        try:
            logger.info(f"Creating PHASE 1 enhanced personalized session for user {user_id}")
            
            # Step 1: Analyze user's learning profile
            user_profile = self.analyze_user_learning_profile(user_id, db)
            logger.info(f"User profile: {user_profile}")
            
            # Step 2: PHASE 1 - Calculate dynamic category distribution
            dynamic_distribution = self.calculate_dynamic_category_distribution(
                user_profile, db
            )
            logger.info(f"Dynamic distribution: {dynamic_distribution}")
            
            # Step 3: Get PYQ frequency-weighted question pool
            question_pool = self.get_pyq_weighted_question_pool(user_id, user_profile, db)
            
            if len(question_pool) < 12:
                logger.warning(f"Limited question pool ({len(question_pool)}), falling back to simple selection")
                return self.create_simple_fallback_session(user_id, db)
            
            # Step 4: Apply PHASE 1 enhanced selection strategies
            selected_questions = self.apply_enhanced_selection_strategies(
                user_id, user_profile, question_pool, dynamic_distribution, db
            )
            
            # Step 5: Order questions by difficulty progression
            ordered_questions = self.order_by_difficulty_progression(selected_questions, user_profile)
            
            # Step 6: Generate enhanced session metadata
            session_metadata = self.generate_enhanced_session_metadata(
                ordered_questions, user_profile, dynamic_distribution
            )
            
            return {
                "questions": ordered_questions,
                "metadata": session_metadata,
                "personalization_applied": True,
                "enhancement_level": "phase_1_advanced",
                "session_type": "intelligent_12_question_set"  # Add session type for API compatibility
            }
            
        except Exception as e:
            logger.error(f"Error creating enhanced personalized session: {e}")
            return self.create_simple_fallback_session(user_id, db)

    def calculate_dynamic_category_distribution(
        self, 
        user_profile: Dict[str, Any], 
        db: Session
    ) -> Dict[str, int]:
        """
        PHASE 1: Calculate dynamic category distribution based on student's weakest areas
        """
        try:
            # Start with base CAT distribution
            dynamic_dist = self.base_category_distribution.copy()
            
            # Identify student's weakest category
            weakest_category = self.identify_weakest_category(user_profile, db)
            strongest_category = self.identify_strongest_category(user_profile, db)
            
            # PHASE 1: Dynamic adjustment (±1 question max to maintain exam authenticity)
            if (weakest_category and strongest_category and 
                weakest_category != strongest_category and
                dynamic_dist[strongest_category] > 1):  # Don't reduce below 1
                
                dynamic_dist[weakest_category] += 1
                dynamic_dist[strongest_category] -= 1
                
                logger.info(f"Dynamic adjustment: +1 to {weakest_category}, -1 to {strongest_category}")
            
            # Ensure total is still 12
            total = sum(dynamic_dist.values())
            if total != 12:
                logger.warning(f"Dynamic distribution total is {total}, adjusting to 12")
                # Reset to base if math doesn't work out
                dynamic_dist = self.base_category_distribution.copy()
            
            return dynamic_dist
            
        except Exception as e:
            logger.error(f"Error calculating dynamic distribution: {e}")
            return self.base_category_distribution.copy()

    def identify_weakest_category(self, user_profile: Dict[str, Any], db: Session) -> Optional[str]:
        """
        Identify the category with lowest average mastery
        """
        try:
            category_mastery = {}
            
            # Calculate average mastery per category
            for category, subcategories in self.canonical_subcategories.items():
                category_scores = []
                
                # Get mastery data for subcategories in this category
                mastery_data = user_profile.get('mastery_breakdown', [])
                for item in mastery_data:
                    if item['subcategory'] in subcategories:
                        category_scores.append(item['mastery_percentage'])
                
                # Calculate average mastery for category
                if category_scores:
                    category_mastery[category] = sum(category_scores) / len(category_scores)
                else:
                    category_mastery[category] = 0.0  # No data = weakest
            
            # Find weakest category
            if category_mastery:
                weakest = min(category_mastery.items(), key=lambda x: x[1])
                return weakest[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error identifying weakest category: {e}")
            return None

    def identify_strongest_category(self, user_profile: Dict[str, Any], db: Session) -> Optional[str]:
        """
        Identify the category with highest average mastery
        """
        try:
            category_mastery = {}
            
            # Calculate average mastery per category
            for category, subcategories in self.canonical_subcategories.items():
                category_scores = []
                
                # Get mastery data for subcategories in this category
                mastery_data = user_profile.get('mastery_breakdown', [])
                for item in mastery_data:
                    if item['subcategory'] in subcategories:
                        category_scores.append(item['mastery_percentage'])
                
                # Calculate average mastery for category
                if category_scores:
                    category_mastery[category] = sum(category_scores) / len(category_scores)
                else:
                    category_mastery[category] = 0.0
            
            # Find strongest category (but only if it has meaningful mastery)
            if category_mastery:
                strongest = max(category_mastery.items(), key=lambda x: x[1])
                if strongest[1] > 70:  # Only consider it strong if >70% mastery
                    return strongest[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error identifying strongest category: {e}")
            return None

    def analyze_user_learning_profile(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Comprehensive analysis of user's learning patterns and performance
        """
        try:
            # Recent performance (last 7 days)
            recent_accuracy = self.calculate_recent_accuracy(user_id, db, days=7)
            
            # Overall performance (last 30 days)
            overall_accuracy = self.calculate_recent_accuracy(user_id, db, days=30)
            
            # Mastery levels by subcategory
            mastery_data = self.get_user_mastery_breakdown(user_id, db)
            
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
            attempt_frequency = self.get_attempt_frequency_by_subcategory(user_id, db)
            
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
                'total_attempts': len(attempt_frequency),
                'mastery_breakdown': []  # PHASE 1: Empty but consistent structure
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

    def calculate_recent_accuracy(self, user_id: str, db: Session, days: int = 7) -> float:
        """Calculate user's accuracy over the last N days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = db.execute(
                select(
                    func.count(Attempt.id).label('total'),
                    func.sum(case((Attempt.correct == True, 1), else_=0)).label('correct')
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

    def get_user_mastery_breakdown(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get detailed mastery breakdown by subcategory"""
        try:
            # Get all attempts with question details
            result = db.execute(
                select(
                    Question.subcategory,
                    func.count(Attempt.id).label('total_attempts'),
                    func.sum(case((Attempt.correct == True, 1), else_=0)).label('correct_attempts'),
                    func.avg(case((Attempt.correct == True, 1.0), else_=0.0)).label('accuracy')
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

    def get_attempt_frequency_by_subcategory(self, user_id: str, db: Session) -> Dict[str, int]:
        """Get attempt frequency by subcategory for spaced repetition"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            result = db.execute(
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

    def get_pyq_weighted_question_pool(self, user_id: str, user_profile: Dict, db: Session, target_size: int = 50) -> List[Question]:
        """
        Get a diverse, weighted question pool for dual-dimension diversity enforcement
        Priority: Ensure subcategory diversity in pool FIRST, then PYQ weighting within subcategories
        """
        try:
            question_pool = []
            
            # PHASE 1: Get diverse subcategory representation in pool
            # Get all active subcategories first
            subcategory_result = db.execute(
                select(Question.subcategory).distinct()
                .where(Question.is_active == True)
            )
            available_subcategories = [row[0] for row in subcategory_result.all() if row[0]]
            
            logger.info(f"Available subcategories for diversity: {len(available_subcategories)}")
            
            # PHASE 2: Get questions from each subcategory (diversity-first pool selection)
            questions_per_subcategory = min(6, target_size // len(available_subcategories)) if available_subcategories else target_size
            
            for subcategory in available_subcategories:
                # Get questions from this subcategory with PYQ weighting
                subcategory_questions_result = db.execute(
                    select(Question)
                    .where(
                        and_(
                            Question.is_active == True,
                            Question.subcategory == subcategory
                        )
                    )
                    .order_by(desc(Question.pyq_frequency_score), func.random())
                    .limit(questions_per_subcategory)
                )
                subcategory_questions = subcategory_questions_result.scalars().all()
                question_pool.extend(subcategory_questions)
                
                logger.info(f"Added {len(subcategory_questions)} questions from {subcategory}")
            
            # PHASE 3: Fill remaining slots with high-priority questions if needed
            if len(question_pool) < target_size:
                # Priority 1: Questions from weak areas
                if user_profile['weak_subcategories']:
                    weak_questions_result = db.execute(
                        select(Question)
                        .where(
                            and_(
                                Question.is_active == True,
                                Question.subcategory.in_(user_profile['weak_subcategories'])
                            )
                        )
                        .order_by(desc(Question.pyq_frequency_score), func.random())
                        .limit(target_size - len(question_pool))
                    )
                    additional_questions = weak_questions_result.scalars().all()
                    # Add only questions not already in pool
                    existing_ids = {q.id for q in question_pool}
                    for q in additional_questions:
                        if q.id not in existing_ids:
                            question_pool.append(q)
                            if len(question_pool) >= target_size:
                                break
            
            # PHASE 4: Final quality check and reporting
            subcategory_distribution = {}
            type_distribution = {}
            
            for question in question_pool:
                subcat = question.subcategory or 'Unknown'
                qtype = question.type_of_question or 'Unknown'
                subcategory_distribution[subcat] = subcategory_distribution.get(subcat, 0) + 1
                type_distribution[qtype] = type_distribution.get(qtype, 0) + 1
            
            logger.info(f"Diverse question pool created: {len(question_pool)} questions")
            logger.info(f"Subcategory diversity in pool: {len(subcategory_distribution)} subcategories")
            logger.info(f"Type diversity in pool: {len(type_distribution)} types")
            logger.info(f"Pool subcategory distribution: {subcategory_distribution}")
            
            return question_pool
            
        except Exception as e:
            logger.error(f"Error getting diverse PYQ weighted question pool: {e}")
            return []

    def apply_enhanced_selection_strategies(
        self, 
        user_id: str, 
        user_profile: Dict, 
        question_pool: List[Question], 
        dynamic_distribution: Dict[str, int],
        db: Session
    ) -> List[Question]:
        """
        PHASE 1: Apply enhanced selection strategies with all improvements
        """
        try:
            selected_questions = []
            
            # Strategy 1: Dynamic category-balanced selection
            category_questions = self.select_by_dynamic_category_distribution(
                question_pool, user_profile, dynamic_distribution
            )
            
            # Strategy 2: Difficulty-balanced selection with PYQ weighting
            difficulty_questions = self.select_by_difficulty_with_pyq_weighting(
                category_questions, user_profile
            )
            
            # Strategy 3: PHASE 1 - Enhanced differential cooldown filter
            cooled_questions = self.apply_differential_cooldown_filter(
                user_id, difficulty_questions, db
            )
            
            # Strategy 4: PHASE 1 - Dual-dimension diversity enforcement (Subcategory + Type)
            diverse_questions = self.enforce_dual_dimension_diversity(cooled_questions)
            
            # Strategy 5: Ensure question type variety
            final_questions = self.ensure_question_variety(diverse_questions)
            
            return final_questions[:12]
            
        except Exception as e:
            logger.error(f"Error applying enhanced selection strategies: {e}")
            return question_pool[:12]

    def select_by_dynamic_category_distribution(
        self, 
        questions: List[Question], 
        user_profile: Dict,
        dynamic_distribution: Dict[str, int]
    ) -> List[Question]:
        """
        PHASE 1: Select questions using dynamic category distribution
        """
        try:
            selected = []
            
            # Debug logging
            logger.info(f"Starting dynamic category selection with {len(questions)} questions")
            logger.info(f"Dynamic distribution: {dynamic_distribution}")
            
            # Group questions by category
            category_groups = {}
            for question in questions:
                category = self.get_category_from_subcategory(question.subcategory)
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(question)
            
            logger.info(f"Category groups: {[(cat, len(qs)) for cat, qs in category_groups.items()]}")
            
            # CRITICAL FIX: Use base distribution if dynamic distribution is empty
            distribution_to_use = dynamic_distribution if dynamic_distribution else self.base_category_distribution
            
            # Select questions according to distribution
            for category, target_count in distribution_to_use.items():
                if category in category_groups:
                    category_questions = category_groups[category]
                    
                    # Sort by weakness first, then PYQ frequency, then Type diversity
                    prioritized = sorted(
                        category_questions,
                        key=lambda q: (
                            0 if q.subcategory in user_profile['weak_subcategories'] else
                            1 if q.subcategory in user_profile['moderate_subcategories'] else 2,
                            -(q.pyq_frequency_score or 0.5),  # Higher PYQ frequency first
                            q.type_of_question or 'ZZZ'  # Type diversity (alphabetical for consistency)
                        )
                    )
                    
                    selected.extend(prioritized[:target_count])
                    logger.info(f"Selected {min(target_count, len(prioritized))} questions from {category}")
                else:
                    logger.warning(f"No questions available for category {category}")
            
            # ULTIMATE FIX: Enhanced fallback logic to ensure 12 questions
            if len(selected) < 12:
                logger.warning(f"Only {len(selected)} questions selected from distribution, need 12")
                selected_ids = {q.id for q in selected}
                remaining_questions = [q for q in questions if q.id not in selected_ids]
                
                # Sort remaining by PYQ frequency and weakness priority
                remaining_sorted = sorted(
                    remaining_questions,
                    key=lambda q: (
                        0 if q.subcategory in user_profile['weak_subcategories'] else
                        1 if q.subcategory in user_profile['moderate_subcategories'] else 2,
                        -(q.pyq_frequency_score or 0.5)
                    )
                )
                
                needed = 12 - len(selected)
                selected.extend(remaining_sorted[:needed])
                logger.info(f"Added {min(needed, len(remaining_sorted))} additional questions to reach 12")
                
                # ULTIMATE FALLBACK: If still not enough, use any available questions
                if len(selected) < 12:
                    logger.warning(f"Still only {len(selected)} questions, using any available questions")
                    all_remaining = [q for q in questions if q.id not in {s.id for s in selected}]
                    final_needed = 12 - len(selected)
                    selected.extend(all_remaining[:final_needed])
                    logger.info(f"Final fallback: added {min(final_needed, len(all_remaining))} questions")
            
            final_count = len(selected)
            logger.info(f"Final selection: {final_count} questions")
            return selected[:12]  # Ensure exactly 12 questions
            
        except Exception as e:
            logger.error(f"Error in dynamic category selection: {e}")
            return questions[:12]

    def select_by_difficulty_with_pyq_weighting(
        self, 
        questions: List[Question], 
        user_profile: Dict
    ) -> List[Question]:
        """
        PHASE 1: Select questions with difficulty distribution and PYQ frequency weighting
        ULTIMATE FIX: Enhanced fallback logic to ensure 12 questions are always selected
        """
        try:
            difficulty_prefs = user_profile['difficulty_preferences']
            selected = []
            
            # Group by difficulty
            difficulty_groups = {'Easy': [], 'Medium': [], 'Hard': []}
            for question in questions:
                difficulty = question.difficulty_band or 'Medium'
                if difficulty in difficulty_groups:
                    difficulty_groups[difficulty].append(question)
            
            logger.info(f"Difficulty groups: Easy={len(difficulty_groups['Easy'])}, Medium={len(difficulty_groups['Medium'])}, Hard={len(difficulty_groups['Hard'])}")
            logger.info(f"Difficulty preferences: {difficulty_prefs}")
            
            # Select according to difficulty preferences, weighted by PYQ frequency
            for difficulty, target_count in difficulty_prefs.items():
                if difficulty in difficulty_groups:
                    available = difficulty_groups[difficulty]
                    
                    # Sort by PYQ frequency score (higher first)
                    pyq_weighted = sorted(
                        available, 
                        key=lambda q: -(q.pyq_frequency_score or 0.5)
                    )
                    
                    actual_selected = min(target_count, len(pyq_weighted))
                    selected.extend(pyq_weighted[:actual_selected])
                    logger.info(f"Selected {actual_selected}/{target_count} {difficulty} questions")
            
            # ULTIMATE FIX: Ensure we have 12 questions by filling from available pool
            if len(selected) < 12:
                logger.warning(f"Only {len(selected)} questions selected from difficulty preferences, need 12")
                selected_ids = {q.id for q in selected}
                remaining_questions = [q for q in questions if q.id not in selected_ids]
                
                # Sort remaining by PYQ frequency
                remaining_sorted = sorted(
                    remaining_questions,
                    key=lambda q: -(q.pyq_frequency_score or 0.5)
                )
                
                needed = 12 - len(selected)
                selected.extend(remaining_sorted[:needed])
                logger.info(f"Added {min(needed, len(remaining_sorted))} additional questions to reach 12")
            
            final_count = len(selected)
            logger.info(f"Final difficulty selection: {final_count} questions")
            return selected[:12]  # Ensure exactly 12 questions
            
        except Exception as e:
            logger.error(f"Error in PYQ-weighted difficulty selection: {e}")
            return questions[:12]  # Fallback to first 12 questions

    def apply_differential_cooldown_filter(
        self, 
        user_id: str, 
        questions: List[Question], 
        db: Session
    ) -> List[Question]:
        """
        PHASE 1: Apply differential cooldown periods based on difficulty
        """
        try:
            cooled_questions = []
            
            for question in questions:
                difficulty = question.difficulty_band or 'Medium'
                cooldown_days = self.cooldown_periods.get(difficulty, 2)
                
                # Check if question is within cooldown period
                recent_cutoff = datetime.utcnow() - timedelta(days=cooldown_days)
                
                recent_attempt_result = db.execute(
                    select(Attempt.id)
                    .where(
                        and_(
                            Attempt.user_id == user_id,
                            Attempt.question_id == question.id,
                            Attempt.created_at >= recent_cutoff
                        )
                    )
                    .limit(1)
                )
                
                recent_attempt = recent_attempt_result.scalar_one_or_none()
                
                if not recent_attempt:  # Question is outside cooldown period
                    cooled_questions.append(question)
            
            logger.info(f"After differential cooldown filter: {len(cooled_questions)} questions")
            
            # If not enough questions after cooldown, add some recent ones back
            if len(cooled_questions) < 12:
                remaining_needed = 12 - len(cooled_questions)
                recent_questions = [q for q in questions if q not in cooled_questions]
                cooled_questions.extend(recent_questions[:remaining_needed])
            
            return cooled_questions
                
        except Exception as e:
            logger.error(f"Error applying differential cooldown filter: {e}")
            return questions

    
    def enforce_dual_dimension_diversity(self, questions: List[Question]) -> List[Question]:
        """
        Enforce Dual-Dimension Diversity: Subcategory level first, then Type level within subcategories
        
        Priority Order:
        1. First: Maximize subcategory coverage across session (max 5 per subcategory)
        2. Second: Ensure type diversity within each chosen subcategory (max 2-3 per type)
        
        Caps:
        - Per Subcategory Cap: Max 5 questions from same subcategory per session
        - Per Type within Subcategory Cap: Max 2-3 questions of same type within subcategory
        """
        try:
            subcategory_counts = {}
            type_within_subcategory_counts = {}
            diverse_questions = []
            
            # Sort questions by PYQ frequency first for quality
            sorted_questions = sorted(
                questions, 
                key=lambda q: -(q.pyq_frequency_score or 0.5)
            )
            
            logger.info("Starting dual-dimension diversity enforcement...")
            
            # PHASE 1: Maximize subcategory coverage first
            for question in sorted_questions:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'
                
                # Check subcategory cap (max 3 per subcategory for better diversity)
                current_subcategory_count = subcategory_counts.get(subcategory, 0)
                if current_subcategory_count >= 3:  # Stricter cap for better diversity
                    logger.info(f"Skipping {subcategory} - subcategory cap reached ({current_subcategory_count}/3)")
                    continue  # Skip if subcategory cap reached
                
                # Check type within subcategory cap (max 2-3 per type within subcategory)
                type_within_subcategory_key = f"{subcategory}::{question_type}"
                current_type_count = type_within_subcategory_counts.get(type_within_subcategory_key, 0)
                
                # Use cap of 2 for "Basics" type (stricter), 1-2 for specific types
                type_cap = 2 if question_type == "Basics" else 1
                if current_type_count >= type_cap:
                    logger.info(f"Skipping {subcategory}::{question_type} - type cap reached ({current_type_count}/{type_cap})")
                    continue  # Skip if type within subcategory cap reached
                
                # Add question - satisfies both caps
                diverse_questions.append(question)
                subcategory_counts[subcategory] = current_subcategory_count + 1
                type_within_subcategory_counts[type_within_subcategory_key] = current_type_count + 1
                
                # Stop if we have enough questions
                if len(diverse_questions) >= 12:
                    break
            
            # PHASE 2: Analyze diversity achieved
            unique_subcategories = len(subcategory_counts)
            unique_types_overall = len(set(q.type_of_question or 'General' for q in diverse_questions))
            
            logger.info(f"Dual-dimension diversity achieved: {len(diverse_questions)} questions from {unique_subcategories} subcategories, {unique_types_overall} types")
            
            # Show subcategory distribution
            for subcategory, count in subcategory_counts.items():
                logger.info(f"  - {subcategory}: {count} questions")
            
            # PHASE 3: Quality check - ensure reasonable subcategory spread
            if unique_subcategories < 3 and len(diverse_questions) < 12:
                logger.info(f"Only {unique_subcategories} subcategories, attempting to improve subcategory diversity...")
                
                # Try to add questions from unused subcategories
                selected_subcategories = set(subcategory_counts.keys())
                remaining_questions = [q for q in questions if q not in diverse_questions]
                
                for question in remaining_questions:
                    question_subcategory = question.subcategory or 'Unknown'
                    
                    # Prefer questions from new subcategories
                    if question_subcategory not in selected_subcategories:
                        diverse_questions.append(question)
                        subcategory_counts[question_subcategory] = subcategory_counts.get(question_subcategory, 0) + 1
                        logger.info(f"Added question from new subcategory: {question_subcategory}")
                        
                        if len(diverse_questions) >= 12:
                            break
            
            # GUARANTEED: Always ensure exactly 12 questions (100% success rate)
            if len(diverse_questions) < 12:
                logger.info(f"Ensuring 12 questions: currently have {len(diverse_questions)}, need {12 - len(diverse_questions)} more")
                
                # Add remaining questions to reach 12, relaxing caps if necessary
                selected_ids = {q.id for q in diverse_questions}
                remaining_questions = [q for q in questions if q.id not in selected_ids]
                
                # Sort remaining by PYQ frequency for quality
                remaining_sorted = sorted(remaining_questions, key=lambda q: -(q.pyq_frequency_score or 0.5))
                
                for question in remaining_sorted:
                    if len(diverse_questions) >= 12:
                        break
                    
                    subcategory = question.subcategory or 'Unknown'
                    current_subcategory_count = subcategory_counts.get(subcategory, 0)
                    
                    # Prefer questions that don't exceed subcategory cap, but add anyway if needed for 12 questions
                    diverse_questions.append(question)
                    subcategory_counts[subcategory] = current_subcategory_count + 1
                    logger.info(f"Added question from {subcategory} to reach 12 questions (count now: {current_subcategory_count + 1})")
                
                logger.info(f"Successfully padded to {len(diverse_questions)} questions")
            
            # VALIDATION: Ensure exactly 12 questions
            if len(diverse_questions) > 12:
                logger.info(f"Truncating from {len(diverse_questions)} to 12 questions")
                diverse_questions = diverse_questions[:12]  # Truncate if over 12
            elif len(diverse_questions) < 12:
                logger.warning(f"Still only have {len(diverse_questions)} questions - using emergency fallback")
                # Emergency fallback: add any remaining questions to reach 12
                selected_ids = {q.id for q in diverse_questions}
                remaining_questions = [q for q in questions if q.id not in selected_ids]
                
                # Add remaining questions one by one
                for question in remaining_questions:
                    if len(diverse_questions) >= 12:
                        break
                    diverse_questions.append(question)
                    logger.info(f"Emergency: Added {question.subcategory}::{question.type_of_question}")
                
                # If still under 12, duplicate best questions
                while len(diverse_questions) < 12:
                    if questions:
                        best_question = questions[0]  # Take first (highest PYQ frequency)
                        diverse_questions.append(best_question)
                        logger.info(f"Emergency: Duplicated {best_question.subcategory}::{best_question.type_of_question}")
                    else:
                        break
                
                logger.info(f"Emergency fallback completed: {len(diverse_questions)} questions")
            
            # FINAL REPORTING
            final_subcategories = len(set(q.subcategory for q in diverse_questions[:12] if q.subcategory))
            final_types = len(set(q.type_of_question for q in diverse_questions[:12] if q.type_of_question))
            
            logger.info(f"Dual-dimension diversity enforcement complete:")
            logger.info(f"  - {len(diverse_questions)} questions selected")
            logger.info(f"  - {final_subcategories} unique subcategories")
            logger.info(f"  - {final_types} unique types")
            logger.info(f"  - Subcategory caps enforced (max 5 per subcategory)")
            logger.info(f"  - Type caps enforced (max 2-3 per type within subcategory)")
            
            return diverse_questions[:12]  # GUARANTEE exactly 12 questions
            
        except Exception as e:
            logger.error(f"Error enforcing dual-dimension diversity: {e}")
            return questions[:12]  # Fallback to first 12 questions
    

    def enforce_subcategory_diversity(self, questions: List[Question]) -> List[Question]:
        """
        PHASE 1: Enforce subcategory diversity caps to prevent domination
        """
        try:
            subcategory_counts = {}
            diverse_questions = []
            
            # Sort questions by PYQ frequency first to prioritize high-frequency questions
            sorted_questions = sorted(
                questions, 
                key=lambda q: -(q.pyq_frequency_score or 0.5)
            )
            
            for question in sorted_questions:
                subcategory = question.subcategory
                current_count = subcategory_counts.get(subcategory, 0)
                
                # Check if adding this question would exceed subcategory limit
                if current_count < self.max_questions_per_subcategory:
                    diverse_questions.append(question)
                    subcategory_counts[subcategory] = current_count + 1
                
                # Stop if we have enough questions
                if len(diverse_questions) >= 12:
                    break
            
            # Ensure minimum subcategory diversity
            unique_subcategories = len(set(q.subcategory for q in diverse_questions[:12]))
            
            if unique_subcategories < self.min_subcategories_per_session:
                logger.warning(f"Only {unique_subcategories} subcategories, below minimum {self.min_subcategories_per_session}")
                # Try to add more diverse questions if available
                remaining_questions = [q for q in questions if q not in diverse_questions]
                for question in remaining_questions:
                    if question.subcategory not in [q.subcategory for q in diverse_questions]:
                        diverse_questions.append(question)
                        if len(set(q.subcategory for q in diverse_questions[:12])) >= self.min_subcategories_per_session:
                            break
            
            logger.info(f"Enforced diversity: {len(diverse_questions)} questions from {unique_subcategories} subcategories")
            return diverse_questions
            
        except Exception as e:
            logger.error(f"Error enforcing subcategory diversity: {e}")
            return questions

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
            for category, target_count in self.base_category_distribution.items():
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
            
            # CRITICAL FIX: Ensure we always have 12 questions
            if len(selected) < 12:
                logger.warning(f"Category distribution only yielded {len(selected)} questions, filling to 12")
                # Get all remaining questions not already selected
                selected_ids = {q.id for q in selected}
                remaining_questions = [q for q in questions if q.id not in selected_ids]
                
                # Add remaining questions to reach 12
                needed = 12 - len(selected)
                selected.extend(remaining_questions[:needed])
                logger.info(f"Added {min(needed, len(remaining_questions))} additional questions for complete session")
            
            return selected[:12]  # Ensure exactly 12 questions
            
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

    def apply_spaced_repetition_filter(self, user_id: str, questions: List[Question], 
                                           db: Session) -> List[Question]:
        """Apply spaced repetition principles to avoid recently attempted questions"""
        try:
            # Get recently attempted questions (last 3 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=3)
            
            recent_attempts = db.execute(
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

    def generate_enhanced_session_metadata(
        self, 
        questions: List[Question], 
        user_profile: Dict[str, Any],
        dynamic_distribution: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        PHASE 1: Generate enhanced session metadata with all improvements
        """
        try:
            # Basic metadata
            difficulty_distribution = {}
            category_distribution = {}
            subcategory_distribution = {}
            pyq_frequency_stats = {
                'high_frequency': 0,
                'medium_frequency': 0, 
                'low_frequency': 0,
                'average_score': 0.0
            }
            
            total_pyq_score = 0.0
            
            for question in questions:
                # Difficulty distribution
                difficulty = question.difficulty_band or 'Medium'
                difficulty_distribution[difficulty] = difficulty_distribution.get(difficulty, 0) + 1
                
                # Category distribution
                category = self.get_category_from_subcategory(question.subcategory)
                if category:
                    category_distribution[category] = category_distribution.get(category, 0) + 1
                
                # Subcategory distribution
                subcategory = question.subcategory
                subcategory_distribution[subcategory] = subcategory_distribution.get(subcategory, 0) + 1
                
                # PYQ frequency analysis
                pyq_score = float(question.pyq_frequency_score or 0.5)  # Convert to float
                total_pyq_score += pyq_score
                
                if pyq_score >= 0.7:
                    pyq_frequency_stats['high_frequency'] += 1
                elif pyq_score >= 0.4:
                    pyq_frequency_stats['medium_frequency'] += 1
                else:
                    pyq_frequency_stats['low_frequency'] += 1
            
            # Calculate averages
            pyq_frequency_stats['average_score'] = total_pyq_score / len(questions) if questions else 0.0
            
            # Count weak areas targeted
            weak_areas_targeted = sum(
                1 for q in questions 
                if q.subcategory in user_profile.get('weak_subcategories', [])
            )
            
            # Type distribution analysis
            type_distribution = {}
            category_type_distribution = {}
            
            for question in questions:
                # Type distribution
                question_type = question.type_of_question or 'General'
                type_distribution[question_type] = type_distribution.get(question_type, 0) + 1
                
                # Category-Type combination analysis
                category = self.get_category_from_subcategory(question.subcategory)
                category_type_key = f"{category}::{question.subcategory}::{question_type}"
                category_type_distribution[category_type_key] = category_type_distribution.get(category_type_key, 0) + 1

            # Dual-dimension diversity analysis
            subcategory_type_distribution = {}
            subcategory_caps_analysis = {}
            type_within_subcategory_analysis = {}
            
            for question in questions:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'
                
                # Subcategory-Type combination analysis for dual-dimension tracking
                subcategory_type_key = f"{subcategory}::{question_type}"
                subcategory_type_distribution[subcategory_type_key] = subcategory_type_distribution.get(subcategory_type_key, 0) + 1
                
                # Subcategory caps analysis (max 5 per subcategory)
                subcategory_caps_analysis[subcategory] = subcategory_caps_analysis.get(subcategory, 0) + 1
                
                # Type within subcategory analysis
                if subcategory not in type_within_subcategory_analysis:
                    type_within_subcategory_analysis[subcategory] = {}
                type_within_subcategory_analysis[subcategory][question_type] = type_within_subcategory_analysis[subcategory].get(question_type, 0) + 1
            
            # Enhanced metadata
            metadata = {
                'learning_stage': user_profile.get('learning_stage', 'unknown'),
                'recent_accuracy': user_profile.get('recent_accuracy', 0),
                'difficulty_distribution': difficulty_distribution,
                'category_distribution': category_distribution,
                'subcategory_distribution': subcategory_distribution,
                'type_distribution': type_distribution,
                'category_type_distribution': category_type_distribution,
                'subcategory_type_distribution': subcategory_type_distribution,
                'subcategory_caps_analysis': subcategory_caps_analysis,
                'type_within_subcategory_analysis': type_within_subcategory_analysis,
                'weak_areas_targeted': weak_areas_targeted,
                'dynamic_adjustment_applied': dynamic_distribution != self.base_category_distribution,
                'base_distribution': self.base_category_distribution,
                'applied_distribution': dynamic_distribution,
                'pyq_frequency_analysis': pyq_frequency_stats,
                'subcategory_diversity': len(subcategory_distribution),
                'type_diversity': len(type_distribution),
                'category_type_diversity': len(category_type_distribution),
                'dual_dimension_diversity': len(subcategory_type_distribution),
                'cooldown_periods_used': self.cooldown_periods,
                'total_questions': len(questions),
                'enhancement_level': 'phase_1_advanced'
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error generating enhanced metadata: {e}")
            return {
                'learning_stage': 'unknown',
                'recent_accuracy': 0,
                'difficulty_distribution': {},
                'category_distribution': {},
                'weak_areas_targeted': 0,
                'enhancement_level': 'error'
            }

    def get_category_from_subcategory(self, subcategory: str) -> str:
        """Map subcategory to canonical category"""
        if not subcategory:
            return "Arithmetic"  # Default fallback
        
        # Direct mapping based on canonical taxonomy
        for category, subcategories in self.canonical_subcategories.items():
            if subcategory in subcategories:
                return category
        
        # Legacy compatibility mapping for old subcategory names
        legacy_mapping = {
            "Time–Speed–Distance (TSD)": "Arithmetic",
            "Time & Work": "Arithmetic", 
            "Speed-Time-Distance": "Arithmetic",
            "Basic Arithmetic": "Arithmetic",
            "Powers and Roots": "Algebra",
            "Perimeter and Area": "Geometry and Mensuration",
            "Basic Operations": "Number System",
            "HCF–LCM": "Number System",
            "Remainders & Modular Arithmetic": "Number System",
            "Permutation–Combination (P&C)": "Modern Math",
            "Set Theory & Venn Diagrams": "Modern Math"
        }
        
        if subcategory in legacy_mapping:
            return legacy_mapping[subcategory]
            
        return "Arithmetic"  # Default fallback

    def create_simple_fallback_session(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Fallback to simple random selection if sophisticated logic fails"""
        try:
            logger.info(f"Creating simple fallback session for user {user_id}")
            
            result = db.execute(
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

    def determine_user_phase(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Determine which adaptive phase the user is in based on completed sessions
        Returns phase info and metadata for session generation
        """
        try:
            # Count completed sessions for this user
            from sqlalchemy import Session as DBSession
            session_count = db.query(DBSession).filter(
                DBSession.user_id == user_id,
                DBSession.ended_at.isnot(None)  # Only count completed sessions
            ).count()
            
            # Determine phase
            if session_count < 30:
                phase = "phase_a"
                phase_name = "Coverage & Calibration"
                phase_description = "Building broad exposure across taxonomy, Easy/Medium bias"
                session_range = "1-30"
                difficulty_distribution = self.phase_difficulty_distributions["phase_a"]
            elif session_count < 60:
                phase = "phase_b" 
                phase_name = "Strengthen & Stretch"
                phase_description = "Targeting weak areas + Hard questions in strong areas"
                session_range = "31-60"
                difficulty_distribution = self.phase_difficulty_distributions["phase_b"]
            else:
                phase = "phase_c"
                phase_name = "Fully Adaptive"
                phase_description = "Dynamic adaptation with type-level granularity"
                session_range = "61+"
                difficulty_distribution = self.phase_difficulty_distributions["phase_c"]
            
            return {
                "phase": phase,
                "phase_name": phase_name,
                "phase_description": phase_description,
                "session_range": session_range,
                "session_count": session_count,
                "current_session": session_count + 1,
                "difficulty_distribution": difficulty_distribution,
                "is_coverage_phase": phase == "phase_a",
                "is_strengthen_phase": phase == "phase_b",
                "is_adaptive_phase": phase == "phase_c"
            }
            
        except Exception as e:
            logger.error(f"Error determining user phase: {e}")
            # Default to Phase A for new users
            return {
                "phase": "phase_a",
                "phase_name": "Coverage & Calibration",
                "phase_description": "Building broad exposure across taxonomy",
                "session_range": "1-30", 
                "session_count": 0,
                "current_session": 1,
                "difficulty_distribution": self.phase_difficulty_distributions["phase_a"],
                "is_coverage_phase": True,
                "is_strengthen_phase": False,
                "is_adaptive_phase": False
            }