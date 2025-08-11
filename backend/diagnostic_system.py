"""
25-Question Diagnostic System for CAT Preparation Platform
Implements fixed blueprint diagnostic with capability scoring as per specification
"""

import json
import uuid
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging
from formulas import get_diagnostic_blueprint
from database import DiagnosticSet, DiagnosticSetQuestion, Diagnostic, User, Question, Topic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class DiagnosticSystem:
    def __init__(self):
        # Fixed 25-Question Blueprint as per specification
        self.diagnostic_blueprint = {
            "name": "CAT QA Day-0 Diagnostic",
            "total_questions": 25,
            "time_targets": {
                "Easy": 90,      # seconds
                "Medium": 150,   # seconds  
                "Difficult": 210 # seconds
            },
            "distribution": {
                "Arithmetic": {
                    "count": 7,
                    "questions": [
                        {"subcategory": "Time–Speed–Distance (TSD)", "difficulty": "Medium", "seq": 1},
                        {"subcategory": "Time–Speed–Distance (TSD)", "difficulty": "Difficult", "seq": 2, "note": "relative speed, multi-stage"},
                        {"subcategory": "Time & Work", "difficulty": "Easy", "seq": 3},
                        {"subcategory": "Ratio–Proportion–Variation", "difficulty": "Medium", "seq": 4},
                        {"subcategory": "Percentages", "difficulty": "Medium", "seq": 5, "note": "successive changes"},
                        {"subcategory": "Averages & Alligation", "difficulty": "Easy", "seq": 6},
                        {"subcategory": "Profit–Loss–Discount (PLD)", "difficulty": "Difficult", "seq": 7, "note": "compound/stacked"}
                    ]
                },
                "Algebra": {
                    "count": 6,
                    "questions": [
                        {"subcategory": "Linear Equations", "difficulty": "Easy", "seq": 8, "note": "Linear & Quadratic"},
                        {"subcategory": "Quadratic Equations", "difficulty": "Difficult", "seq": 9, "note": "parameterized system"},
                        {"subcategory": "Inequalities", "difficulty": "Medium", "seq": 10, "note": "Inequalities/Mod/Absolute"},
                        {"subcategory": "Progressions", "difficulty": "Medium", "seq": 11, "note": "AP/GP"},
                        {"subcategory": "Functions & Graphs", "difficulty": "Difficult", "seq": 12, "note": "domain/range trap"},
                        {"subcategory": "Logarithms & Exponents", "difficulty": "Medium", "seq": 13}
                    ]
                },
                "Geometry & Mensuration": {
                    "count": 6,
                    "questions": [
                        {"subcategory": "Triangles", "difficulty": "Medium", "seq": 14, "note": "ratio properties"},
                        {"subcategory": "Circles", "difficulty": "Medium", "seq": 15, "note": "algebra + geometry"},
                        {"subcategory": "Polygons", "difficulty": "Easy", "seq": 16},
                        {"subcategory": "Coordinate Geometry", "difficulty": "Difficult", "seq": 17, "note": "slope+distance combo"},
                        {"subcategory": "Mensuration (2D & 3D)", "difficulty": "Medium", "seq": 18},
                        {"subcategory": "Triangles", "difficulty": "Easy", "seq": 19, "note": "Similarity"}
                    ]
                },
                "Number System": {
                    "count": 3,
                    "questions": [
                        {"subcategory": "Divisibility", "difficulty": "Easy", "seq": 20, "note": "Divisibility–Factors"},
                        {"subcategory": "Remainders & Modular Arithmetic", "difficulty": "Medium", "seq": 21, "note": "Remainders/CRT"},
                        {"subcategory": "Digit Properties", "difficulty": "Difficult", "seq": 22}
                    ]
                },
                "Modern Math": {
                    "count": 3,
                    "questions": [
                        {"subcategory": "Permutation–Combination (P&C)", "difficulty": "Medium", "seq": 23},
                        {"subcategory": "Probability", "difficulty": "Medium", "seq": 24, "note": "conditional"},
                        {"subcategory": "Set Theory & Venn Diagrams", "difficulty": "Difficult", "seq": 25, "note": "3-set constrained"}
                    ]
                }
            }
        }
    
    async def create_diagnostic_set(self, db: AsyncSession) -> DiagnosticSet:
        """Create the fixed 25-question diagnostic set"""
        try:
            # Check if diagnostic set already exists
            result = await db.execute(
                select(DiagnosticSet).where(DiagnosticSet.name == self.diagnostic_blueprint["name"])
            )
            existing_set = result.scalar_one_or_none()
            
            if existing_set:
                logger.info("Diagnostic set already exists")
                return existing_set
            
            # Create new diagnostic set
            diagnostic_set = DiagnosticSet(
                name=self.diagnostic_blueprint["name"],
                meta={
                    "blueprint": self.diagnostic_blueprint,
                    "created_by": "system",
                    "version": "1.0"
                },
                is_active=True
            )
            
            db.add(diagnostic_set)
            await db.flush()  # Get the ID
            
            # Create diagnostic set questions
            question_count = 0
            used_question_ids = set()  # Track used questions to avoid duplicates
            
            for category, category_data in self.diagnostic_blueprint["distribution"].items():
                for question_spec in category_data["questions"]:
                    # Find a suitable question for this specification
                    question = await self._find_diagnostic_question(
                        db, category, question_spec["subcategory"], question_spec["difficulty"], used_question_ids
                    )
                    
                    if question:
                        diagnostic_set_question = DiagnosticSetQuestion(
                            set_id=diagnostic_set.id,
                            question_id=question.id,
                            seq=question_spec["seq"]
                        )
                        db.add(diagnostic_set_question)
                        used_question_ids.add(question.id)  # Mark question as used
                        question_count += 1
                    else:
                        logger.warning(f"No question found for {category} -> {question_spec['subcategory']} ({question_spec['difficulty']})")
            
            await db.commit()
            logger.info(f"Created diagnostic set with {question_count} questions")
            return diagnostic_set
            
        except Exception as e:
            logger.error(f"Error creating diagnostic set: {e}")
            await db.rollback()
            raise
    
    async def _find_diagnostic_question(self, db: AsyncSession, category: str, subcategory: str, difficulty: str, used_question_ids: set = None) -> Question:
        """Find a question matching the diagnostic criteria with fallback options"""
        try:
            if used_question_ids is None:
                used_question_ids = set()
            
            # First try exact match
            result = await db.execute(
                select(Question)
                .join(Question.topic)
                .where(
                    Question.subcategory == subcategory,
                    Question.difficulty_band == difficulty,
                    Question.is_active == True,
                    ~Question.id.in_(used_question_ids) if used_question_ids else True
                )
                .order_by(Question.importance_index.desc())
                .limit(1)
            )
            
            question = result.scalar_one_or_none()
            if question:
                return question
            
            # Fallback 1: Try with different difficulty (Difficult -> Medium -> Easy)
            fallback_difficulties = []
            if difficulty == "Difficult":
                fallback_difficulties = ["Medium", "Easy"]
            elif difficulty == "Medium":
                fallback_difficulties = ["Easy", "Difficult"]
            else:  # Easy
                fallback_difficulties = ["Medium", "Difficult"]
                
            for fallback_difficulty in fallback_difficulties:
                result = await db.execute(
                    select(Question)
                    .join(Question.topic)
                    .where(
                        Question.subcategory == subcategory,
                        Question.difficulty_band == fallback_difficulty,
                        Question.is_active == True,
                        ~Question.id.in_(used_question_ids) if used_question_ids else True
                    )
                    .order_by(Question.importance_index.desc())
                    .limit(1)
                )
                
                question = result.scalar_one_or_none()
                if question:
                    logger.warning(f"Using fallback difficulty {fallback_difficulty} for {subcategory} (wanted {difficulty})")
                    return question
            
            # Fallback 2: Try any question from the same category
            result = await db.execute(
                select(Question)
                .join(Question.topic)
                .where(
                    Topic.name == category,
                    Question.is_active == True,
                    ~Question.id.in_(used_question_ids) if used_question_ids else True
                )
                .order_by(Question.importance_index.desc())
                .limit(1)
            )
            
            question = result.scalar_one_or_none()
            if question:
                logger.warning(f"Using fallback question from category {category} for {subcategory} ({difficulty})")
                return question
            
            # Fallback 3: Any active question
            result = await db.execute(
                select(Question)
                .where(
                    Question.is_active == True,
                    ~Question.id.in_(used_question_ids) if used_question_ids else True
                )
                .order_by(Question.importance_index.desc())
                .limit(1)
            )
            
            question = result.scalar_one_or_none()
            if question:
                logger.warning(f"Using fallback question (any active) for {subcategory} ({difficulty})")
                return question
                
            return None
            
        except Exception as e:
            logger.error(f"Error finding diagnostic question: {e}")
            return None
    
    async def start_diagnostic(self, db: AsyncSession, user_id: str) -> Diagnostic:
        """Start a new diagnostic session for a user"""
        try:
            # Get the active diagnostic set
            result = await db.execute(
                select(DiagnosticSet).where(DiagnosticSet.is_active == True)
            )
            diagnostic_set = result.scalar_one_or_none()
            
            if not diagnostic_set:
                raise ValueError("No active diagnostic set found")
            
            # Check if user already has a completed diagnostic
            existing_result = await db.execute(
                select(Diagnostic).where(
                    Diagnostic.user_id == user_id,
                    Diagnostic.set_id == diagnostic_set.id,
                    Diagnostic.completed_at.isnot(None)
                )
            )
            existing_diagnostic = existing_result.scalar_one_or_none()
            
            if existing_diagnostic:
                logger.info(f"User {user_id} already has completed diagnostic")
                return existing_diagnostic
            
            # Create new diagnostic
            diagnostic = Diagnostic(
                user_id=user_id,
                set_id=diagnostic_set.id,
                started_at=datetime.utcnow(),
                result={},
                initial_capability={}
            )
            
            db.add(diagnostic)
            await db.commit()
            
            logger.info(f"Started diagnostic {diagnostic.id} for user {user_id}")
            return diagnostic
            
        except Exception as e:
            logger.error(f"Error starting diagnostic: {e}")
            await db.rollback()
            raise
    
    async def get_diagnostic_questions(self, db: AsyncSession, diagnostic_id: str) -> List[Dict[str, Any]]:
        """Get the 25 questions for a diagnostic in correct order"""
        try:
            # Get diagnostic
            result = await db.execute(
                select(Diagnostic).where(Diagnostic.id == diagnostic_id)
            )
            diagnostic = result.scalar_one_or_none()
            
            if not diagnostic:
                raise ValueError("Diagnostic not found")
            
            # Get questions in order with topic information
            questions_result = await db.execute(
                select(Question, DiagnosticSetQuestion.seq, Topic.name.label('topic_name'))
                .join(DiagnosticSetQuestion, Question.id == DiagnosticSetQuestion.question_id)
                .join(Topic, Question.topic_id == Topic.id)
                .where(DiagnosticSetQuestion.set_id == diagnostic.set_id)
                .order_by(DiagnosticSetQuestion.seq)
            )
            
            questions_data = []
            for question, seq, topic_name in questions_result.fetchall():
                # Get expected time for this difficulty
                expected_time = self.diagnostic_blueprint["time_targets"].get(question.difficulty_band, 150)
                
                questions_data.append({
                    "id": str(question.id),
                    "sequence": seq,
                    "stem": question.stem,
                    "category": topic_name or "Unknown",
                    "subcategory": question.subcategory,
                    "difficulty_band": question.difficulty_band,
                    "expected_time_sec": expected_time,
                    "importance_index": float(question.importance_index) if question.importance_index else 0,
                    # Don't include answer or solution during diagnostic
                })
            
            logger.info(f"Retrieved {len(questions_data)} diagnostic questions")
            return questions_data
            
        except Exception as e:
            logger.error(f"Error getting diagnostic questions: {e}")
            raise
    
    def compute_capability_score(self, attempts: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Compute capability score using the formula:
        Capability = 0.55 × Accuracy + 0.25 × SpeedScore + 0.20 × Stability
        """
        try:
            if not attempts:
                return 0.0, {}
            
            # Calculate accuracy
            correct_count = sum(1 for attempt in attempts if attempt.get("correct", False))
            total_count = len(attempts)
            accuracy = correct_count / total_count if total_count > 0 else 0
            
            # Calculate speed score
            speed_score = self._calculate_speed_score(attempts)
            
            # Calculate stability score
            stability_score = self._calculate_stability_score(attempts)
            
            # Apply capability formula
            capability = 0.55 * accuracy + 0.25 * speed_score + 0.20 * stability_score
            
            capability_details = {
                "accuracy": round(accuracy, 3),
                "speed_score": round(speed_score, 3),
                "stability_score": round(stability_score, 3),
                "total_questions": total_count,
                "correct_answers": correct_count,
                "accuracy_percentage": round(accuracy * 100, 1)
            }
            
            return round(capability, 3), capability_details
            
        except Exception as e:
            logger.error(f"Error computing capability score: {e}")
            return 0.0, {}
    
    def _calculate_speed_score(self, attempts: List[Dict[str, Any]]) -> float:
        """Calculate speed score normalized vs target times"""
        try:
            speed_scores = []
            
            for attempt in attempts:
                difficulty = attempt.get("difficulty_band", "Medium")
                target_time = self.diagnostic_blueprint["time_targets"].get(difficulty, 150)
                actual_time = attempt.get("time_sec", target_time)
                
                # Speed score: 1.0 if at or under target, decreasing as time increases
                if actual_time <= target_time:
                    speed_score = 1.0
                else:
                    # Penalty for exceeding target time
                    speed_score = max(0.1, target_time / actual_time)
                
                speed_scores.append(speed_score)
            
            return sum(speed_scores) / len(speed_scores) if speed_scores else 0
            
        except Exception as e:
            logger.error(f"Error calculating speed score: {e}")
            return 0.5
    
    def _calculate_stability_score(self, attempts: List[Dict[str, Any]]) -> float:
        """Calculate stability from internal consistency across related items"""
        try:
            # Group attempts by subcategory
            subcategory_performance = {}
            
            for attempt in attempts:
                subcategory = attempt.get("subcategory", "Unknown")
                if subcategory not in subcategory_performance:
                    subcategory_performance[subcategory] = []
                
                subcategory_performance[subcategory].append({
                    "correct": attempt.get("correct", False),
                    "time_ratio": self._get_time_ratio(attempt)
                })
            
            # Calculate consistency within each subcategory
            consistency_scores = []
            
            for subcategory, performances in subcategory_performance.items():
                if len(performances) > 1:  # Need at least 2 questions for consistency
                    # Calculate variance in performance
                    accuracies = [1 if p["correct"] else 0 for p in performances]
                    time_ratios = [p["time_ratio"] for p in performances]
                    
                    # Lower variance = higher stability
                    accuracy_variance = self._calculate_variance(accuracies)
                    time_variance = self._calculate_variance(time_ratios)
                    
                    # Convert variance to stability score (lower variance = higher stability)
                    consistency_score = 1.0 - min(1.0, (accuracy_variance + time_variance) / 2)
                    consistency_scores.append(consistency_score)
            
            # If no consistency can be calculated, use overall performance as stability
            if not consistency_scores:
                accuracy = sum(1 for attempt in attempts if attempt.get("correct", False)) / len(attempts)
                return accuracy  # Use accuracy as fallback stability measure
            
            return sum(consistency_scores) / len(consistency_scores)
            
        except Exception as e:
            logger.error(f"Error calculating stability score: {e}")
            return 0.5
    
    def _get_time_ratio(self, attempt: Dict[str, Any]) -> float:
        """Get time ratio (actual time / target time)"""
        difficulty = attempt.get("difficulty_band", "Medium")
        target_time = self.diagnostic_blueprint["time_targets"].get(difficulty, 150)
        actual_time = attempt.get("time_sec", target_time)
        return actual_time / target_time
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        squared_diffs = [(x - mean) ** 2 for x in values]
        variance = sum(squared_diffs) / len(squared_diffs)
        return variance
    
    def compute_initial_capability_by_subcategory(self, attempts: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Compute initial capability per sub-category & difficulty"""
        try:
            subcategory_capabilities = {}
            
            # Group attempts by subcategory and difficulty
            grouped_attempts = {}
            
            for attempt in attempts:
                subcategory = attempt.get("subcategory", "Unknown")
                difficulty = attempt.get("difficulty_band", "Medium")
                key = f"{subcategory}_{difficulty}"
                
                if key not in grouped_attempts:
                    grouped_attempts[key] = []
                
                grouped_attempts[key].append(attempt)
            
            # Calculate capability for each group
            for key, group_attempts in grouped_attempts.items():
                subcategory, difficulty = key.rsplit("_", 1)
                
                if subcategory not in subcategory_capabilities:
                    subcategory_capabilities[subcategory] = {}
                
                capability, _ = self.compute_capability_score(group_attempts)
                subcategory_capabilities[subcategory][difficulty.lower()] = capability
            
            return subcategory_capabilities
            
        except Exception as e:
            logger.error(f"Error computing subcategory capabilities: {e}")
            return {}
    
    def determine_track(self, overall_capability: float, category_performance: Dict[str, float]) -> str:
        """
        Determine user track based on diagnostic results
        Tracks: Beginner | Intermediate | Good
        """
        try:
            # Track determination based on overall capability
            if overall_capability >= 0.75:
                return "Good"
            elif overall_capability >= 0.50:
                return "Intermediate" 
            else:
                return "Beginner"
                
        except Exception as e:
            logger.error(f"Error determining track: {e}")
            return "Beginner"
    
    async def complete_diagnostic(self, db: AsyncSession, diagnostic_id: str, attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Complete diagnostic and compute final results"""
        try:
            # Get diagnostic
            result = await db.execute(
                select(Diagnostic).where(Diagnostic.id == diagnostic_id)
            )
            diagnostic = result.scalar_one_or_none()
            
            if not diagnostic:
                raise ValueError("Diagnostic not found")
            
            if diagnostic.completed_at:
                raise ValueError("Diagnostic already completed")
            
            # Compute overall capability
            overall_capability, capability_details = self.compute_capability_score(attempts)
            
            # Compute per-subcategory capabilities
            subcategory_capabilities = self.compute_initial_capability_by_subcategory(attempts)
            
            # Compute category-wise performance
            category_performance = self._compute_category_performance(attempts)
            
            # Determine track
            track = self.determine_track(overall_capability, category_performance)
            
            # Create diagnostic result
            diagnostic_result = {
                "overall_capability": overall_capability,
                "capability_details": capability_details,
                "category_performance": category_performance,
                "readiness_band": self._determine_readiness_band(overall_capability),
                "track_recommendation": track,
                "completion_time": datetime.utcnow().isoformat(),
                "total_attempts": len(attempts)
            }
            
            # Update diagnostic
            diagnostic.completed_at = datetime.utcnow()
            diagnostic.result = diagnostic_result
            diagnostic.initial_capability = subcategory_capabilities
            
            await db.commit()
            
            logger.info(f"Completed diagnostic {diagnostic_id} with capability {overall_capability}")
            return diagnostic_result
            
        except Exception as e:
            logger.error(f"Error completing diagnostic: {e}")
            await db.rollback()
            raise
    
    def _compute_category_performance(self, attempts: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute accuracy by category"""
        category_performance = {}
        
        for attempt in attempts:
            category = attempt.get("category", "Unknown")
            if category not in category_performance:
                category_performance[category] = {"correct": 0, "total": 0}
            
            category_performance[category]["total"] += 1
            if attempt.get("correct", False):
                category_performance[category]["correct"] += 1
        
        # Convert to accuracy percentages
        for category in category_performance:
            total = category_performance[category]["total"]
            correct = category_performance[category]["correct"]
            category_performance[category] = round((correct / total) * 100, 1) if total > 0 else 0
        
        return category_performance
    
    def _determine_readiness_band(self, capability: float) -> str:
        """Determine readiness band based on capability score"""
        if capability >= 0.80:
            return "Excellent"
        elif capability >= 0.65:
            return "Good"
        elif capability >= 0.45:
            return "Average"
        else:
            return "Needs Improvement"


# Usage example
async def test_diagnostic_system():
    """Test the diagnostic system"""
    diagnostic_system = DiagnosticSystem()
    
    # Print the blueprint
    print(json.dumps(diagnostic_system.diagnostic_blueprint, indent=2))
    
    # Test capability computation
    test_attempts = [
        {"correct": True, "time_sec": 90, "difficulty_band": "Easy", "subcategory": "Basic TSD", "category": "Arithmetic"},
        {"correct": False, "time_sec": 180, "difficulty_band": "Medium", "subcategory": "Percentages", "category": "Arithmetic"},
        {"correct": True, "time_sec": 150, "difficulty_band": "Medium", "subcategory": "Linear Equations", "category": "Algebra"},
    ]
    
    capability, details = diagnostic_system.compute_capability_score(test_attempts)
    print(f"Capability: {capability}")
    print(f"Details: {json.dumps(details, indent=2)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_diagnostic_system())