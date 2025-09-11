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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, case, text
from database import Question, Attempt, Mastery, Topic, User, StudentCoverageTracking

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
        THREE-PHASE ADAPTIVE: Create a sophisticated 12-question session with phase-based progression
        Phase A (1-30): Coverage & Calibration
        Phase B (31-60): Strengthen & Stretch  
        Phase C (61+): Fully Adaptive
        """
        try:
            # Step 1: Determine user's current phase
            phase_info = self.determine_user_phase(user_id, db)
            logger.info(f"Creating {phase_info['phase_name']} session for user {user_id} (Session {phase_info['current_session']})")
            
            # Step 2: Analyze user's learning profile
            user_profile = self.analyze_user_learning_profile(user_id, db)
            logger.info(f"User profile: {user_profile}")
            
            # Step 3: Phase-specific session creation
            if phase_info['is_coverage_phase']:
                # Phase A: Coverage & Calibration
                return self.create_coverage_phase_session(user_id, user_profile, phase_info, db)
            elif phase_info['is_strengthen_phase']:
                # Phase B: Strengthen & Stretch
                return self.create_strengthen_phase_session(user_id, user_profile, phase_info, db)
            else:
                # Phase C: Fully Adaptive
                return self.create_adaptive_phase_session(user_id, user_profile, phase_info, db)
            
        except Exception as e:
            logger.error(f"Error creating three-phase adaptive session: {e}")
            return self.create_simple_fallback_session(user_id, db)

    def get_student_seen_combinations(self, user_id: str, db: Session) -> set:
        """
        Get all subcategory::type combinations this student has already seen
        Only used for Phase A (Sessions 1-30) to ensure coverage
        """
        try:
            result = db.execute(
                select(StudentCoverageTracking.subcategory_type_combination)
                .where(StudentCoverageTracking.user_id == user_id)
            )
            return {row[0] for row in result.fetchall()}
        except Exception as e:
            logger.error(f"Error getting student seen combinations: {e}")
            return set()
    
    def get_student_coverage_progress(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Get coverage progress metrics for a student in Phase A
        Returns coverage statistics and progress information
        """
        try:
            # Get total unique combinations available
            result = db.execute(
                select(func.concat(Question.subcategory, '::', Question.type_of_question))
                .where(Question.is_active == True)
                .distinct()
            )
            all_combinations = set(row[0] for row in result.fetchall())
            total_combinations = len(all_combinations)
            
            # Get combinations this student has seen
            result = db.execute(
                select(StudentCoverageTracking.subcategory_type_combination,
                       StudentCoverageTracking.sessions_seen,
                       StudentCoverageTracking.first_seen_session)
                .where(StudentCoverageTracking.user_id == user_id)
            )
            coverage_records = result.fetchall()
            
            seen_combinations = set(record[0] for record in coverage_records)
            coverage_count = len(seen_combinations)
            
            # Calculate progress percentage
            coverage_percentage = (coverage_count / total_combinations * 100) if total_combinations > 0 else 0
            
            # Find uncovered combinations
            uncovered_combinations = all_combinations - seen_combinations
            
            return {
                "total_combinations_available": total_combinations,
                "combinations_covered": coverage_count,
                "coverage_percentage": round(coverage_percentage, 1),
                "uncovered_combinations": list(uncovered_combinations)[:10],  # First 10 for display
                "uncovered_count": len(uncovered_combinations),
                "coverage_details": [
                    {
                        "combination": record[0],
                        "sessions_seen": record[1], 
                        "first_seen_session": record[2]
                    }
                    for record in coverage_records
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting student coverage progress: {e}")
            return {
                "total_combinations_available": 0,
                "combinations_covered": 0,
                "coverage_percentage": 0.0,
                "uncovered_combinations": [],
                "uncovered_count": 0,
                "coverage_details": []
            }

    def update_student_coverage_tracking(self, user_id: str, questions: List[Question], session_num: int, db: Session):
        """
        Update coverage tracking after a session is completed
        Records which subcategory::type combinations were seen
        """
        try:
            for question in questions:
                # Create combination key
                combination = f"{question.subcategory}::{question.type_of_question}"
                
                # Upsert coverage record using raw SQL for PostgreSQL compatibility
                db.execute(text("""
                    INSERT INTO student_coverage_tracking 
                    (user_id, subcategory_type_combination, sessions_seen, first_seen_session, last_seen_session, created_at, updated_at)
                    VALUES (:user_id, :combination, 1, :session_num, :session_num, NOW(), NOW())
                    ON CONFLICT (user_id, subcategory_type_combination) 
                    DO UPDATE SET 
                        sessions_seen = student_coverage_tracking.sessions_seen + 1,
                        last_seen_session = :session_num,
                        updated_at = NOW()
                """), {
                    "user_id": user_id, 
                    "combination": combination, 
                    "session_num": session_num
                })
            
            db.commit()
            logger.info(f"✅ Updated coverage tracking for user {user_id}, session {session_num}")
            
        except Exception as e:
            logger.error(f"❌ Error updating student coverage tracking: {e}")
            db.rollback()

    def get_coverage_weighted_question_pool(self, user_id: str, user_profile: Dict[str, Any], phase_info: Dict[str, Any], db: Session) -> List[Question]:
        """Get question pool optimized for coverage phase - prioritizes unseen subcategory-type combinations per student"""
        try:
            # Get all active questions
            result = db.execute(
                select(Question)
                .where(Question.is_active == True)
                .order_by(func.random())
            )
            all_questions = result.scalars().all()
            
            # Group by subcategory-type combinations for coverage
            coverage_groups = {}
            for question in all_questions:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'
                coverage_key = f"{subcategory}::{question_type}"
                
                if coverage_key not in coverage_groups:
                    coverage_groups[coverage_key] = []
                coverage_groups[coverage_key].append(question)
            
            # PHASE A ENHANCEMENT: Prioritize unseen combinations for this student
            if phase_info.get('phase') == 'A':
                seen_combinations = self.get_student_seen_combinations(user_id, db)
                logger.info(f"User {user_id} has seen {len(seen_combinations)} combinations in Phase A")
                
                # Priority 1: Unseen combinations (NEW combinations for this student)
                unseen_pool = []
                # Priority 2: Seen combinations (fallback)
                seen_pool = []
                
                for coverage_key, questions in coverage_groups.items():
                    # Take top 2 questions from each combination
                    sorted_questions = sorted(questions, key=lambda q: (
                        q.difficulty_score or 0.5,  # Medium difficulty preference
                        q.pyq_frequency_score or 0.5
                    ))[:2]
                    
                    if coverage_key not in seen_combinations:
                        unseen_pool.extend(sorted_questions)  # NEW combinations first
                    else:
                        seen_pool.extend(sorted_questions)    # Seen combinations as fallback
                
                # Combine with unseen combinations prioritized
                coverage_pool = unseen_pool + seen_pool
                logger.info(f"Phase A coverage: {len(unseen_pool)} from unseen combinations, {len(seen_pool)} from seen combinations")
                
            else:
                # Phase B/C: Use existing logic (no per-student prioritization needed)
                coverage_pool = []
                for coverage_key, questions in coverage_groups.items():
                    sorted_questions = sorted(questions, key=lambda q: (
                        q.difficulty_score or 0.5,
                        q.pyq_frequency_score or 0.5
                    ))[:2]
                    coverage_pool.extend(sorted_questions)
            
            logger.info(f"Coverage pool: {len(coverage_pool)} questions from {len(coverage_groups)} combinations")
            return coverage_pool
            
        except Exception as e:
            logger.error(f"Error getting coverage weighted question pool: {e}")
            return self.get_fallback_question_pool(db)

    def apply_coverage_selection_strategies(self, user_id: str, user_profile: Dict[str, Any], 
                                           question_pool: List[Question], balanced_distribution: Dict[str, int], 
                                           phase_info: Dict[str, Any], db: Session) -> List[Question]:
        """Apply QUOTA-BASED difficulty distribution for coverage phase - superior approach"""
        try:
            difficulty_dist = phase_info['difficulty_distribution']
            
            # Step 1: Set quotas upfront, but ADAPT to actual LLM difficulty distribution
            target_easy = int(12 * difficulty_dist.get('Easy', 0.2))      # 20% = 2 questions
            target_medium = int(12 * difficulty_dist.get('Medium', 0.75)) # 75% = 9 questions  
            target_hard = int(12 * difficulty_dist.get('Hard', 0.05))     # 5% = 1 question
            
            # Ensure exactly 12 questions
            total_target = target_easy + target_medium + target_hard
            if total_target != 12:
                target_medium = 12 - target_easy - target_hard
            
            logger.info(f"QUOTA-BASED targets (ideal): Easy={target_easy}, Medium={target_medium}, Hard={target_hard}")
            
            # Step 2: Check actual availability from LLM difficulty_band 
            hard_pool = []
            easy_pool = []
            medium_pool = []
            
            for question in question_pool:
                difficulty = self.determine_question_difficulty(question)
                if difficulty == "Hard":
                    hard_pool.append(question)
                elif difficulty == "Easy":
                    easy_pool.append(question)
                else:
                    medium_pool.append(question)
            
            logger.info(f"ACTUAL LLM distribution: Hard={len(hard_pool)}, Easy={len(easy_pool)}, Medium={len(medium_pool)}")
            
            # Step 3: ADAPT targets to respect LLM intelligence
            # If LLM says all questions are Medium, respect that assessment
            if len(easy_pool) == 0 and len(hard_pool) == 0:
                logger.info("LLM classified all questions as Medium - adapting Phase A to respect LLM assessment")
                adapted_targets = {
                    'Easy': 0,
                    'Medium': 12,  # Use all Medium as LLM determined
                    'Hard': 0
                }
                backfill_notes = ["LLM assessment: All questions classified as Medium difficulty - Phase A adapted accordingly"]
            else:
                # Use original targets if diversity exists
                adapted_targets = {
                    'Easy': min(target_easy, len(easy_pool)),
                    'Medium': target_medium,  
                    'Hard': min(target_hard, len(hard_pool))
                }
                backfill_notes = []
            
            # Step 4: Fill based on adapted targets that respect LLM assessment
            selected_questions = []
            used_combinations = set()
            
            # Fill Hard quota (if any available)
            hard_selected = self.fill_difficulty_quota(
                hard_pool, adapted_targets['Hard'], "Hard", used_combinations, 
                balanced_distribution, selected_questions
            )
            selected_questions.extend(hard_selected)
            
            # Fill Easy quota (if any available)
            easy_selected = self.fill_difficulty_quota(
                easy_pool, adapted_targets['Easy'], "Easy", used_combinations,
                balanced_distribution, selected_questions
            )
            selected_questions.extend(easy_selected)
            
            # Fill remaining slots with Medium (respecting LLM assessment)
            remaining_needed = 12 - len(selected_questions)
            medium_selected = self.fill_difficulty_quota(
                medium_pool, remaining_needed, "Medium", used_combinations,
                balanced_distribution, selected_questions
            )
            selected_questions.extend(medium_selected)
            
            # Step 5: Generate telemetry that explains LLM-based adaptation
            difficulty_actual = self.calculate_actual_difficulty_distribution(selected_questions)
            
            telemetry = {
                'difficulty_targets': adapted_targets,  # Show adapted targets that respect LLM
                'difficulty_actual': difficulty_actual,
                'backfill_notes': backfill_notes,
                'quota_system_used': True,
                'llm_assessment_respected': True,
                'original_phase_a_targets': {'Easy': target_easy, 'Medium': target_medium, 'Hard': target_hard}
            }
            
            logger.info(f"LLM-RESPECTING QUOTA: Targets={adapted_targets} vs Actual={difficulty_actual}")
            if backfill_notes:
                logger.info(f"LLM adaptation notes: {backfill_notes}")
            
            result_data = {
                'selected_questions': selected_questions[:12],
                'quota_telemetry': telemetry
            }
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error in LLM-respecting quota-based selection: {e}")
            return {'selected_questions': question_pool[:12], 'quota_telemetry': {}}
    
    def fill_difficulty_quota(self, pool: List[Question], quota: int, difficulty: str, 
                             used_combinations: set, category_distribution: Dict[str, int],
                             already_selected: List[Question]) -> List[Question]:
        """Fill quota for specific difficulty with existing category/coverage filters"""
        try:
            if quota <= 0 or not pool:
                return []
            
            import random
            selected = []
            
            # Apply coverage priority within this difficulty pool
            coverage_prioritized = []
            fallback_questions = []
            
            for question in pool:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'  
                combination = f"{subcategory}::{question_type}"
                
                # Check if this question would exceed category quotas
                category = self.get_category_from_subcategory(subcategory)
                category_count = sum(1 for q in already_selected + selected 
                                   if self.get_category_from_subcategory(q.subcategory or '') == category)
                category_limit = category_distribution.get(category, 99)
                
                if category_count >= category_limit:
                    continue  # Skip if would exceed category quota
                
                # Prioritize new combinations for coverage
                if combination not in used_combinations:
                    coverage_prioritized.append(question)
                else:
                    fallback_questions.append(question)
            
            # Sample from coverage_prioritized first, then fallback
            available_coverage = min(len(coverage_prioritized), quota)
            if available_coverage > 0:
                selected.extend(random.sample(coverage_prioritized, available_coverage))
            
            # Fill remaining from fallback if needed
            remaining_needed = quota - len(selected)
            if remaining_needed > 0 and fallback_questions:
                available_fallback = min(len(fallback_questions), remaining_needed)
                selected.extend(random.sample(fallback_questions, available_fallback))
            
            # Update used combinations
            for question in selected:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'
                combination = f"{subcategory}::{question_type}"
                used_combinations.add(combination)
            
            logger.info(f"Filled {difficulty} quota: {len(selected)}/{quota} questions")
            return selected
            
        except Exception as e:
            logger.error(f"Error filling {difficulty} quota: {e}")
            return []
    
    def perform_backfill(self, selected_questions: List[Question], hard_pool: List[Question], 
                        easy_pool: List[Question], medium_pool: List[Question],
                        difficulty_targets: Dict[str, int], used_combinations: set, 
                        backfill_notes: List[str]) -> List[Question]:
        """Single-pass backfill with clear logging"""
        try:
            needed = 12 - len(selected_questions)
            if needed <= 0:
                return []
            
            import random
            backfilled = []
            
            # Determine which pools were short
            actual_counts = self.calculate_actual_difficulty_distribution(selected_questions)
            
            # Backfill logic: H short → M, E short → M, M short → E then H
            if actual_counts.get('Hard', 0) < difficulty_targets.get('Hard', 0):
                # Hard was short, backfill from Medium
                available_medium = [q for q in medium_pool if q not in selected_questions]
                if available_medium and len(backfilled) < needed:
                    backfill_q = random.choice(available_medium)
                    backfilled.append(backfill_q)
                    backfill_notes.append(f"Hard short by 1 → filled from Medium")
            
            if actual_counts.get('Easy', 0) < difficulty_targets.get('Easy', 0) and len(backfilled) < needed:
                # Easy was short, backfill from Medium
                available_medium = [q for q in medium_pool if q not in selected_questions + backfilled]
                shortage = difficulty_targets.get('Easy', 0) - actual_counts.get('Easy', 0)
                for _ in range(min(shortage, len(available_medium), needed - len(backfilled))):
                    backfill_q = random.choice(available_medium)
                    backfilled.append(backfill_q) 
                    available_medium.remove(backfill_q)
                if shortage > 0:
                    backfill_notes.append(f"Easy short by {shortage} → filled from Medium")
            
            if len(backfilled) < needed:
                # Still need more, Medium was short - backfill from Easy first, then Hard
                remaining_needed = needed - len(backfilled)
                
                # Try Easy first
                available_easy = [q for q in easy_pool if q not in selected_questions + backfilled]
                easy_backfill = min(len(available_easy), remaining_needed)
                if easy_backfill > 0:
                    backfilled.extend(random.sample(available_easy, easy_backfill))
                    backfill_notes.append(f"Medium short → filled {easy_backfill} from Easy")
                
                # Then Hard if still needed
                if len(backfilled) < needed:
                    available_hard = [q for q in hard_pool if q not in selected_questions + backfilled]
                    hard_backfill = min(len(available_hard), needed - len(backfilled))
                    if hard_backfill > 0:
                        backfilled.extend(random.sample(available_hard, hard_backfill))
                        backfill_notes.append(f"Medium short → filled {hard_backfill} from Hard")
            
            logger.info(f"Backfilled {len(backfilled)} questions: {backfill_notes}")
            return backfilled
            
        except Exception as e:
            logger.error(f"Error in backfill: {e}")
            return []
    
    def calculate_actual_difficulty_distribution(self, questions: List[Question]) -> Dict[str, int]:
        """Calculate actual difficulty distribution of selected questions"""
        try:
            actual = {'Easy': 0, 'Medium': 0, 'Hard': 0}
            
            for question in questions:
                difficulty = self.determine_question_difficulty(question)
                if difficulty in actual:
                    actual[difficulty] += 1
            
            return actual
            
        except Exception as e:
            logger.error(f"Error calculating actual difficulty distribution: {e}")
            return {'Easy': 0, 'Medium': 0, 'Hard': 0}

    def order_by_coverage_progression(self, questions: List[Question], phase_info: Dict[str, Any]) -> List[Question]:
        """Order questions for coverage phase - Easy to Medium progression"""
        try:
            # Sort by difficulty (Easy → Medium → Hard) and subcategory diversity
            ordered = sorted(questions, key=lambda q: (
                self.get_difficulty_order(q),      # Easy=0, Medium=1, Hard=2
                q.subcategory or 'ZZZ',            # Subcategory alphabetically
                q.pyq_frequency_score or 0.5       # PYQ frequency
            ))
            
            logger.info(f"Coverage progression: {len(ordered)} questions ordered Easy→Medium→Hard")
            return ordered
            
        except Exception as e:
            logger.error(f"Error ordering coverage progression: {e}")
            return questions

    def identify_weak_type_combinations(self, user_profile: Dict[str, Any]) -> List[str]:
        """Identify weak subcategory-type combinations for strengthen phase"""
        try:
            weak_combinations = []
            mastery_data = user_profile.get('mastery_breakdown', [])
            
            for item in mastery_data:
                if item.get('mastery_percentage', 0) < 60:  # Consider <60% as weak
                    subcategory = item.get('subcategory', 'Unknown')
                    # For now, we'll identify weak subcategories and pair with common types
                    for question_type in ['Basics', 'Advanced']:  # Common types
                        weak_combinations.append(f"{subcategory}::{question_type}")
            
            # If no weak areas identified, target some default areas for strengthening
            if not weak_combinations:
                weak_combinations = [
                    "HCF-LCM::Euclidean Algorithm",
                    "Remainders::Chinese Remainder Theorem", 
                    "Divisibility::Basic Divisibility Rules"
                ]
            
            logger.info(f"Identified {len(weak_combinations)} weak type combinations")
            return weak_combinations[:10]  # Limit to top 10
            
        except Exception as e:
            logger.error(f"Error identifying weak type combinations: {e}")
            return ["HCF-LCM::Basics", "Remainders::Basics"]

    def identify_strong_type_combinations(self, user_profile: Dict[str, Any]) -> List[str]:
        """Identify strong subcategory-type combinations for stretch goals"""
        try:
            strong_combinations = []
            mastery_data = user_profile.get('mastery_breakdown', [])
            
            for item in mastery_data:
                if item.get('mastery_percentage', 0) > 75:  # Consider >75% as strong
                    subcategory = item.get('subcategory', 'Unknown')
                    # For strong areas, pair with advanced types
                    for question_type in ['Advanced', 'Complex']:
                        strong_combinations.append(f"{subcategory}::{question_type}")
            
            # If no strong areas identified, use some default strong patterns
            if not strong_combinations:
                strong_combinations = [
                    "Divisibility::Factorisation of Integers",
                    "HCF-LCM::Product of HCF and LCM",
                    "Number Properties::Perfect Squares"
                ]
            
            logger.info(f"Identified {len(strong_combinations)} strong type combinations")
            return strong_combinations[:8]  # Limit to top 8
            
        except Exception as e:
            logger.error(f"Error identifying strong type combinations: {e}")
            return ["Divisibility::Factorisation of Integers"]

    def calculate_strengthen_distribution(self, user_profile: Dict[str, Any], weak_areas: List[str], strong_areas: List[str]) -> Dict[str, int]:
        """Calculate category distribution for strengthen phase"""
        try:
            # Start with base distribution
            strengthen_dist = self.base_category_distribution.copy()
            
            # Extract categories from weak and strong areas
            weak_categories = []
            for area in weak_areas:
                subcategory = area.split('::')[0] if '::' in area else area
                category = self.get_category_from_subcategory(subcategory)
                if category:
                    weak_categories.append(category)
            
            strong_categories = []
            for area in strong_areas:
                subcategory = area.split('::')[0] if '::' in area else area
                category = self.get_category_from_subcategory(subcategory)
                if category:
                    strong_categories.append(category)
            
            # Adjust distribution to emphasize weak categories
            for category in set(weak_categories):
                if category in strengthen_dist:
                    strengthen_dist[category] += 1  # Add 1 extra question for weak categories
            
            # Normalize to 12 questions
            total = sum(strengthen_dist.values())
            if total > 12:
                # Scale down proportionally
                factor = 12 / total
                for category in strengthen_dist:
                    strengthen_dist[category] = max(1, int(strengthen_dist[category] * factor))
            
            logger.info(f"Strengthen distribution: {strengthen_dist}")
            return strengthen_dist
            
        except Exception as e:
            logger.error(f"Error calculating strengthen distribution: {e}")
            return self.base_category_distribution.copy()

    def get_strengthen_weighted_question_pool(self, user_id: str, user_profile: Dict[str, Any], 
                                            phase_info: Dict[str, Any], weak_areas: List[str], 
                                            strong_areas: List[str], db: Session) -> List[Question]:
        """Get question pool optimized for strengthen phase"""
        try:
            # Get all active questions
            result = db.execute(
                select(Question)
                .where(Question.is_active == True)
                .order_by(func.random())
            )
            all_questions = result.scalars().all()
            
            # Categorize questions by weak/strong/neutral
            weak_questions = []
            strong_questions = []
            neutral_questions = []
            
            for question in all_questions:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'
                combination = f"{subcategory}::{question_type}"
                
                if any(weak_area in combination or combination in weak_area for weak_area in weak_areas):
                    weak_questions.append(question)
                elif any(strong_area in combination or combination in strong_area for strong_area in strong_areas):
                    strong_questions.append(question)
                else:
                    neutral_questions.append(question)
            
            # Build strengthen pool: 50% weak, 30% strong, 20% neutral (approximations)
            strengthen_pool = []
            
            # Add weak area questions (for Easy→Medium targeting)
            weak_sorted = sorted(weak_questions, key=lambda q: q.difficulty_score or 0.5)
            strengthen_pool.extend(weak_sorted[:30])  # Up to 30 weak questions
            
            # Add strong area questions (for Hard targeting)  
            strong_sorted = sorted(strong_questions, key=lambda q: -(q.difficulty_score or 0.5))  # Harder first
            strengthen_pool.extend(strong_sorted[:20])  # Up to 20 strong questions
            
            # Add neutral questions
            strengthen_pool.extend(neutral_questions[:15])  # Up to 15 neutral questions
            
            logger.info(f"Strengthen pool: {len(strengthen_pool)} questions ({len(weak_questions)} weak, {len(strong_questions)} strong, {len(neutral_questions)} neutral)")
            return strengthen_pool
            
        except Exception as e:
            logger.error(f"Error getting strengthen weighted question pool: {e}")
            return self.get_fallback_question_pool(db)

    def apply_strengthen_selection_strategies(self, user_id: str, user_profile: Dict[str, Any], 
                                           question_pool: List[Question], strengthen_distribution: Dict[str, int], 
                                           weak_areas: List[str], strong_areas: List[str], 
                                           phase_info: Dict[str, Any], db: Session) -> List[Question]:
        """Apply selection strategies for strengthen phase: 45% weak, 35% strong, 20% authentic"""
        try:
            selected_questions = []
            difficulty_dist = phase_info['difficulty_distribution']
            
            # Allocation targets based on strengthen phase requirements
            weak_target = int(12 * 0.45)   # 45% = ~5 questions targeting weak areas
            strong_target = int(12 * 0.35) # 35% = ~4 questions targeting strong areas  
            authentic_target = int(12 * 0.2) # 20% = ~3 questions for authentic distribution
            
            # Separate questions by weak/strong/neutral
            weak_questions = []
            strong_questions = []
            neutral_questions = []
            
            for question in question_pool:
                subcategory = question.subcategory or 'Unknown'
                question_type = question.type_of_question or 'General'
                combination = f"{subcategory}::{question_type}"
                
                if any(weak_area in combination for weak_area in weak_areas):
                    weak_questions.append(question)
                elif any(strong_area in combination for strong_area in strong_areas):
                    strong_questions.append(question)
                else:
                    neutral_questions.append(question)
            
            # Select weak area questions (Easy→Medium preference)
            weak_sorted = sorted(weak_questions, key=lambda q: q.difficulty_score or 0.5)
            selected_questions.extend(weak_sorted[:weak_target])
            
            # Select strong area questions (Hard preference)
            strong_sorted = sorted(strong_questions, key=lambda q: -(q.difficulty_score or 0.5))
            selected_questions.extend(strong_sorted[:strong_target])
            
            # Fill remaining with neutral questions
            selected_questions.extend(neutral_questions[:authentic_target])
            
            # If we don't have enough, fill from any remaining pool
            while len(selected_questions) < 12:
                remaining_pool = [q for q in question_pool if q not in selected_questions]
                if not remaining_pool:
                    break
                selected_questions.append(remaining_pool[0])
            
            logger.info(f"Strengthen selection: {len(selected_questions)} questions ({weak_target} weak, {strong_target} strong, {authentic_target} authentic)")
            return selected_questions[:12]
            
        except Exception as e:
            logger.error(f"Error applying strengthen selection strategies: {e}")
            return question_pool[:12]

    def order_by_strengthen_progression(self, questions: List[Question], phase_info: Dict[str, Any]) -> List[Question]:
        """Order questions for strengthen phase - Easy → Medium → Hard progression"""
        try:
            # Sort by difficulty progression with some randomization within difficulty levels
            ordered = sorted(questions, key=lambda q: (
                self.get_difficulty_order(q),      # Easy=0, Medium=1, Hard=2
                q.pyq_frequency_score or 0.5       # Secondary sort by frequency
            ))
            
            logger.info(f"Strengthen progression: {len(ordered)} questions ordered with difficulty progression")
            return ordered
            
        except Exception as e:
            logger.error(f"Error ordering strengthen progression: {e}")
            return questions

    def create_coverage_phase_session(self, user_id: str, user_profile: Dict[str, Any], phase_info: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Phase A (Sessions 1-30): Coverage & Calibration
        Objective: Broad exposure across entire taxonomy, build initial mastery signals
        Difficulty: 75% Medium, 20% Easy, 5% Hard
        """
        try:
            logger.info(f"Creating Coverage Phase session (Session {phase_info['current_session']}/30)")
            
            # Coverage-focused category distribution (more balanced)
            balanced_distribution = {
                "Arithmetic": 3,                    # 25%
                "Algebra": 3,                       # 25%
                "Geometry and Mensuration": 2,      # 17%
                "Number System": 2,                 # 17%
                "Modern Math": 2                    # 17%
            }
            
            # Get diverse question pool focusing on coverage
            question_pool = self.get_coverage_weighted_question_pool(user_id, user_profile, phase_info, db)
            
            if len(question_pool) < 12:
                logger.warning(f"Limited question pool for coverage phase, falling back")
                return self.create_simple_fallback_session(user_id, db)
            
            # Apply coverage-focused selection (returns data with telemetry)
            selection_result = self.apply_coverage_selection_strategies(
                user_id, user_profile, question_pool, balanced_distribution, phase_info, db
            )
            
            # Extract questions and telemetry
            if isinstance(selection_result, dict) and 'selected_questions' in selection_result:
                selected_questions = selection_result['selected_questions']
                quota_telemetry = selection_result.get('quota_telemetry', {})
            else:
                # Fallback for legacy return format
                selected_questions = selection_result
                quota_telemetry = {}
            
            # Order by easy-to-medium progression
            ordered_questions = self.order_by_coverage_progression(selected_questions, phase_info)
            
            # Generate coverage phase metadata with quota telemetry
            session_metadata = self.generate_phase_metadata(
                ordered_questions, user_profile, balanced_distribution, phase_info,
                quota_telemetry=quota_telemetry
            )
            
            return {
                "questions": ordered_questions,
                "metadata": session_metadata,
                "personalization_applied": True,
                "enhancement_level": "three_phase_adaptive",
                "session_type": "intelligent_12_question_set",
                "phase_info": phase_info
            }
            
        except Exception as e:
            logger.error(f"Error creating coverage phase session: {e}")
            return self.create_simple_fallback_session(user_id, db)

    def create_strengthen_phase_session(self, user_id: str, user_profile: Dict[str, Any], phase_info: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Phase B (Sessions 31-60): Strengthen & Stretch
        Objective: Target weak areas + introduce Hard questions in strong areas
        Allocation: 45% weak areas (Easy→Medium), 35% strong areas (Hard), 20% authentic
        """
        try:
            logger.info(f"Creating Strengthen Phase session (Session {phase_info['current_session']}/60)")
            
            # Identify weak and strong areas at type level
            weak_areas = self.identify_weak_type_combinations(user_profile)
            strong_areas = self.identify_strong_type_combinations(user_profile)
            
            # Calculate strengthen-focused distribution
            strengthen_distribution = self.calculate_strengthen_distribution(
                user_profile, weak_areas, strong_areas
            )
            
            # Get targeted question pool for strengthen phase
            question_pool = self.get_strengthen_weighted_question_pool(
                user_id, user_profile, phase_info, weak_areas, strong_areas, db
            )
            
            if len(question_pool) < 12:
                logger.warning(f"Limited question pool for strengthen phase, falling back")
                return self.create_simple_fallback_session(user_id, db)
            
            # Apply strengthen-focused selection (45% weak, 35% strong, 20% authentic)
            selected_questions = self.apply_strengthen_selection_strategies(
                user_id, user_profile, question_pool, strengthen_distribution, 
                weak_areas, strong_areas, phase_info, db
            )
            
            # Order by difficulty progression (Easy → Medium → Hard)
            ordered_questions = self.order_by_strengthen_progression(selected_questions, phase_info)
            
            # Generate strengthen phase metadata
            session_metadata = self.generate_phase_metadata(
                ordered_questions, user_profile, strengthen_distribution, phase_info,
                weak_areas_targeted=len(weak_areas), strong_areas_targeted=len(strong_areas)
            )
            
            return {
                "questions": ordered_questions,
                "metadata": session_metadata,
                "personalization_applied": True,
                "enhancement_level": "three_phase_adaptive",
                "session_type": "intelligent_12_question_set",
                "phase_info": phase_info,
                "weak_areas_targeted": weak_areas,
                "strong_areas_targeted": strong_areas
            }
            
        except Exception as e:
            logger.error(f"Error creating strengthen phase session: {e}")
            return self.create_simple_fallback_session(user_id, db)

    def create_adaptive_phase_session(self, user_id: str, user_profile: Dict[str, Any], phase_info: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Phase C (Sessions 61+): Fully Adaptive
        Objective: Full adaptive logic with type-level granularity
        Uses existing enhanced logic but with type-aware selection
        """
        try:
            logger.info(f"Creating Fully Adaptive session (Session {phase_info['current_session']})")
            
            # Use dynamic category distribution (existing logic)
            dynamic_distribution = self.calculate_dynamic_category_distribution(user_profile, db)
            
            # Get PYQ frequency-weighted question pool with type-level awareness
            question_pool = self.get_pyq_weighted_question_pool(user_id, user_profile, db)
            
            if len(question_pool) < 12:
                logger.warning(f"Limited question pool for adaptive phase, falling back")
                return self.create_simple_fallback_session(user_id, db)
            
            # Apply enhanced selection strategies with type-level focus
            selected_questions = self.apply_enhanced_selection_strategies(
                user_id, user_profile, question_pool, dynamic_distribution, db
            )
            
            # Order by difficulty progression
            ordered_questions = self.order_by_difficulty_progression(selected_questions, user_profile)
            
            # Generate enhanced metadata with phase info
            session_metadata = self.generate_phase_metadata(
                ordered_questions, user_profile, dynamic_distribution, phase_info
            )
            
            return {
                "questions": ordered_questions,
                "metadata": session_metadata,
                "personalization_applied": True,
                "enhancement_level": "three_phase_adaptive",
                "session_type": "intelligent_12_question_set",
                "phase_info": phase_info
            }
            
        except Exception as e:
            logger.error(f"Error creating adaptive phase session: {e}")
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

    def generate_phase_metadata(self, questions: List[Question], user_profile: Dict[str, Any], 
                               distribution: Dict[str, int], phase_info: Dict[str, Any], 
                               weak_areas_targeted: int = 0, strong_areas_targeted: int = 0,
                               quota_telemetry: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate enhanced metadata for phase-based sessions with direct quota telemetry"""
        try:
            # Base metadata generation
            base_metadata = self.generate_enhanced_session_metadata(questions, user_profile, distribution)
            
            # Use provided quota telemetry (preferred) or try to extract from questions (legacy)
            if quota_telemetry is None:
                quota_telemetry = {}
                if questions:
                    first_question = questions[0]
                    if hasattr(first_question, '_quota_telemetry'):
                        quota_telemetry = getattr(first_question, '_quota_telemetry')
            
            # Add phase-specific metadata
            phase_metadata = {
                # Phase information
                "phase": phase_info.get("phase"),
                "phase_name": phase_info.get("phase_name"),  
                "phase_description": phase_info.get("phase_description"),
                "session_range": phase_info.get("session_range"),
                "current_session": phase_info.get("current_session"),
                "session_count": phase_info.get("session_count"),
                
                # Phase-specific targeting
                "weak_areas_targeted": weak_areas_targeted,
                "strong_areas_targeted": strong_areas_targeted,
                "is_coverage_phase": phase_info.get("is_coverage_phase", False),
                "is_strengthen_phase": phase_info.get("is_strengthen_phase", False), 
                "is_adaptive_phase": phase_info.get("is_adaptive_phase", False),
                
                # Phase difficulty distribution
                "phase_difficulty_distribution": phase_info.get("difficulty_distribution", {}),
                
                # QUOTA TELEMETRY - Superior difficulty tracking
                **quota_telemetry,  # Includes difficulty_targets, difficulty_actual, backfill_notes
                
                # Enhanced type-level tracking
                "enhancement_level": "three_phase_adaptive_quota_system"
            }
            
            # Merge base and phase metadata
            enhanced_metadata = {**base_metadata, **phase_metadata}
            
            # Add quota system indicator
            if quota_telemetry:
                logger.info(f"Generated phase metadata with DIRECT QUOTA TELEMETRY: {quota_telemetry}")
            
            logger.info(f"Generated phase metadata for {phase_info.get('phase_name', 'Unknown')} phase")
            return enhanced_metadata
            
        except Exception as e:
            logger.error(f"Error generating phase metadata: {e}")
            # Return base metadata as fallback
            try:
                return self.generate_enhanced_session_metadata(questions, user_profile, distribution)
            except:
                return {"enhancement_level": "error", "total_questions": len(questions)}

    def get_difficulty_order(self, question: Question) -> int:
        """Get difficulty order for sorting: Easy=0, Medium=1, Hard=2"""
        try:
            difficulty = self.determine_question_difficulty(question)
            order_map = {"Easy": 0, "Medium": 1, "Hard": 2}
            return order_map.get(difficulty, 1)  # Default to Medium
            
        except Exception as e:
            logger.error(f"Error getting difficulty order: {e}")
            return 1  # Default to Medium order

    def determine_question_difficulty(self, question: Question) -> str:
        """Determine question difficulty - RESPECTING LLM intelligence first"""
        try:
            # PRIORITY 1: Check if question has FORCED difficulty from stratified sampling
            if hasattr(question, '_forced_difficulty'):
                forced_difficulty = getattr(question, '_forced_difficulty')
                logger.debug(f"Using FORCED difficulty: {forced_difficulty} (stratified sampling)")
                return forced_difficulty
            
            # PRIORITY 2: ALWAYS RESPECT LLM difficulty_band when available (CORE LOGIC)
            if hasattr(question, 'difficulty_band') and question.difficulty_band:
                band = question.difficulty_band.strip()
                if band in ['Easy', 'Medium', 'Hard']:
                    return band
            
            # PRIORITY 3: Use difficulty_score as intelligent fallback
            difficulty_score = question.difficulty_score or 0.5
            if difficulty_score < 0.35:
                return "Easy"
            elif difficulty_score < 0.75:
                return "Medium"
            else:
                return "Hard"
                
            # NOTE: Removed arbitrary hash-based classification - was wrong approach
                
        except Exception as e:
            logger.error(f"Error determining question difficulty: {e}")
            return "Medium"  # Safe default

    def enhance_question_pool_with_artificial_difficulty(self, questions: List[Question], target_easy: int, target_medium: int, target_hard: int) -> List[Question]:
        """Enhance question pool by artificially balancing difficulties using stratified sampling"""
        try:
            logger.info(f"Applying stratified difficulty balancing: Easy={target_easy}, Medium={target_medium}, Hard={target_hard}")
            
            # Sort questions by their natural difficulty score for stratified selection
            sorted_questions = sorted(questions, key=lambda q: q.difficulty_score or 0.5)
            total_questions = len(sorted_questions)
            
            if total_questions < 12:
                logger.warning(f"Insufficient questions ({total_questions}) for stratified balancing")
                return sorted_questions
            
            # Implement proper stratified sampling based on research
            # Divide questions into strata based on their relative position
            strata_size = total_questions // 3
            
            # Create three strata
            easy_stratum = sorted_questions[:strata_size]  # Lowest 1/3 by difficulty score
            medium_stratum = sorted_questions[strata_size:2*strata_size]  # Middle 1/3
            hard_stratum = sorted_questions[2*strata_size:]  # Highest 1/3
            
            logger.info(f"Strata sizes: Easy={len(easy_stratum)}, Medium={len(medium_stratum)}, Hard={len(hard_stratum)}")
            
            # Apply stratified sampling to meet targets
            enhanced_pool = []
            
            # Sample from easy stratum (force these to be "Easy")
            easy_sample = self.sample_from_stratum(easy_stratum, target_easy, "Easy")
            enhanced_pool.extend(easy_sample)
            
            # Sample from medium stratum (force these to be "Medium")
            medium_sample = self.sample_from_stratum(medium_stratum, target_medium, "Medium")
            enhanced_pool.extend(medium_sample)
            
            # Sample from hard stratum (force these to be "Hard")
            hard_sample = self.sample_from_stratum(hard_stratum, target_hard, "Hard")
            enhanced_pool.extend(hard_sample)
            
            # Fill remaining slots if needed
            while len(enhanced_pool) < 12:
                remaining_questions = [q for q in sorted_questions if q not in enhanced_pool]
                if not remaining_questions:
                    break
                enhanced_pool.append(remaining_questions[0])
            
            logger.info(f"Stratified enhanced pool: {len(enhanced_pool)} questions created")
            return enhanced_pool[:12]
            
        except Exception as e:
            logger.error(f"Error in stratified difficulty balancing: {e}")
            return questions[:12]

    def sample_from_stratum(self, stratum: List[Question], target_count: int, forced_difficulty: str) -> List[Question]:
        """Sample questions from a stratum and assign forced difficulty for artificial balancing"""
        try:
            if not stratum or target_count <= 0:
                return []
            
            # If stratum has enough questions, randomly sample
            if len(stratum) >= target_count:
                import random
                sampled = random.sample(stratum, target_count)
            else:
                # If not enough, take all and repeat some if needed
                sampled = stratum.copy()
                while len(sampled) < target_count and stratum:
                    import random
                    sampled.append(random.choice(stratum))
            
            # Mark these questions with forced difficulty for tracking
            for question in sampled:
                # Add a temporary attribute for artificial difficulty tracking
                setattr(question, '_artificial_difficulty', forced_difficulty)
            
            logger.info(f"Sampled {len(sampled)} questions for {forced_difficulty} difficulty")
            return sampled[:target_count]
            
        except Exception as e:
            logger.error(f"Error sampling from stratum: {e}")
            return []

    def get_fallback_question_pool(self, db: Session) -> List[Question]:
        """Get fallback question pool when specialized pools fail"""
        try:
            result = db.execute(
                select(Question)
                .where(Question.is_active == True)
                .order_by(func.random())
                .limit(50)  # Get more questions for better selection
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting fallback question pool: {e}")
            return []

    def get_category_from_subcategory(self, subcategory: str) -> str:
        """Map subcategory to canonical category"""
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
            from database import Session as SessionModel
            session_count = db.query(SessionModel).filter(
                SessionModel.user_id == user_id,
                SessionModel.ended_at.isnot(None)  # Only count completed sessions
            ).count()
            
            logger.info(f"User {user_id} phase determination: Found {session_count} completed sessions")
            
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
            
            current_session = session_count + 1
            logger.info(f"User {user_id} assigned to {phase_name} (Session {current_session})")
            
            return {
                "phase": phase,
                "phase_name": phase_name,
                "phase_description": phase_description,
                "session_range": session_range,
                "session_count": session_count,
                "current_session": current_session,
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