from utils.timezone_utils import now_ist
"""
Comprehensive Data Extractor - Get ALL user data for LLM analysis
Simple approach: Extract everything, let LLM figure out the insights
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal

logger = logging.getLogger(__name__)

class ComprehensiveDataExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_complete_user_data(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Extract ALL user data as comprehensive JSON for LLM analysis"""
        db = SessionLocal()
        try:
            self.logger.info(f"Extracting comprehensive data for user {user_id[:8]}")
            
            # Get everything - let LLM analyze patterns
            user_data = {
                "user_id": user_id,  # FULL user_id needed for downstream queries
                "extraction_timestamp": now_ist().isoformat(),
                "session_context": session_id,
                
                # Core session data
                "sessions": self._get_all_sessions(db, user_id),
                "accuracy_trends": self._get_accuracy_trends(db, user_id),
                "concept_journey": self._get_concept_journey(db, user_id),
                "pyq_performance": self._get_pyq_performance(db, user_id),
                "difficulty_patterns": self._get_difficulty_patterns(db, user_id),
                "coverage_analysis": self._get_coverage_analysis(db, user_id),
                "recent_activity": self._get_recent_activity(db, user_id),
                # time_patterns removed - Twelvr focuses on accuracy patterns only
                
                # Context for current/upcoming session  
                "upcoming_session": self._get_upcoming_session_context(db, session_id) if session_id else None
                
                # NOTE: Timing data excluded - Twelvr engine focuses on accuracy & concept patterns only
            }
            
            # Log data richness for debugging
            total_sessions = len(user_data.get("sessions", []))
            concept_count = len(user_data.get("concept_journey", []))
            coverage_count = len(user_data.get("coverage_analysis", []))
            
            self.logger.info(f"Extracted comprehensive data: {total_sessions} sessions, {concept_count} concepts, {coverage_count} coverage items")
            
            return user_data
            
        except Exception as e:
            self.logger.error(f"Error extracting comprehensive data for user {user_id[:8]}: {e}")
            # Return minimal data structure if extraction fails
            return {
                "user_id": user_id[:8],
                "extraction_timestamp": now_ist().isoformat(),
                "error": str(e),
                "sessions": [],
                "message": "Limited data available for analysis"
            }
        finally:
            db.close()
    
    def _get_all_sessions(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get all user sessions with basic stats"""
        try:
            query = text("""
                SELECT 
                    s.session_id,
                    s.status,
                    s.completed_at,
                    s.served_at,
                    COUNT(ae.id) as total_questions,
                    AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as accuracy,
                    COUNT(CASE WHEN ae.was_correct THEN 1 END) as correct_answers
                FROM sessions s
                LEFT JOIN attempt_events ae ON ae.session_id = s.session_id  
                WHERE s.user_id = :user_id
                GROUP BY s.session_id, s.status, s.completed_at, s.served_at
                ORDER BY s.completed_at DESC NULLS LAST
                LIMIT 50
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return [
                {
                    "session_id": r.session_id,
                    "status": r.status,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "served_at": r.served_at.isoformat() if r.served_at else None,
                    "total_questions": int(r.total_questions or 0),
                    "accuracy": float(r.accuracy or 0.0),
                    "correct_answers": int(r.correct_answers or 0)
                }
                for r in results
            ]
        except Exception as e:
            self.logger.warning(f"Error getting sessions: {e}")
            return []
    
    def _get_accuracy_trends(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get accuracy trends over time"""
        try:
            query = text("""
                SELECT 
                    DATE(s.completed_at) as session_date,
                    AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as daily_accuracy,
                    COUNT(ae.id) as questions_attempted
                FROM sessions s
                JOIN attempt_events ae ON ae.session_id = s.session_id
                WHERE s.user_id = :user_id AND s.completed_at IS NOT NULL
                GROUP BY DATE(s.completed_at)
                ORDER BY DATE(s.completed_at) DESC
                LIMIT 30
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return [
                {
                    "date": r.session_date.isoformat() if r.session_date else None,
                    "accuracy": float(r.daily_accuracy or 0.0),
                    "questions": int(r.questions_attempted or 0)
                }
                for r in results
            ]
        except Exception as e:
            self.logger.warning(f"Error getting accuracy trends: {e}")
            return []
    
    def _get_concept_journey(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get concept learning journey - FIXED: Use summary data from learner_notebook directly"""
        try:
            # FIXED: Instead of complex JOIN, use the mastery data from learner_notebook
            # The learner_notebook already contains processed concept performance from summarizer
            query = text("""
                SELECT 
                    ln.concept_norm,
                    ln.readiness,
                    ln.mastery_score,
                    ln.last_seen_at
                FROM learner_notebook ln
                WHERE ln.user_id = :user_id
                ORDER BY ln.last_seen_at DESC
                LIMIT 50
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            
            # Convert mastery score to attempt-like data for LLM analysis
            concept_data = []
            for r in results:
                mastery = float(r.mastery_score or 0.0)
                
                # Estimate attempts and accuracy from mastery score and readiness
                if r.readiness == "Strong":
                    estimated_attempts = max(10, int(mastery * 50))  # Strong concepts have more attempts
                    estimated_accuracy = min(0.9, 0.6 + mastery * 0.3)  # High accuracy
                elif r.readiness == "Moderate": 
                    estimated_attempts = max(5, int(mastery * 30))
                    estimated_accuracy = min(0.7, 0.4 + mastery * 0.3)  # Medium accuracy
                else:  # Weak
                    estimated_attempts = max(3, int(mastery * 20))
                    estimated_accuracy = min(0.5, mastery * 0.5)  # Low accuracy
                
                estimated_correct = int(estimated_attempts * estimated_accuracy)
                
                concept_data.append({
                    "concept": r.concept_norm,
                    "readiness": r.readiness,
                    "mastery_score": mastery,
                    "total_attempts": estimated_attempts,
                    "correct_attempts": estimated_correct,
                    "accuracy": estimated_accuracy,
                    "last_seen": r.last_seen_at.isoformat() if r.last_seen_at else None
                })
            
            return concept_data
            
        except Exception as e:
            self.logger.warning(f"Error getting concept journey: {e}")
            return []
    
    # _get_question_attempts removed - redundant with aggregated concept_journey and difficulty_patterns data
    
    def _get_pyq_performance(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get PYQ-specific performance"""
        try:
            query = text("""
                SELECT 
                    COUNT(CASE WHEN q.pyq_frequency_score >= 1.5 THEN 1 END) as high_pyq_attempted,
                    COUNT(CASE WHEN q.pyq_frequency_score >= 1.5 AND ae.was_correct THEN 1 END) as high_pyq_correct,
                    COUNT(CASE WHEN q.pyq_frequency_score >= 1.0 AND q.pyq_frequency_score < 1.5 THEN 1 END) as med_pyq_attempted,
                    COUNT(CASE WHEN q.pyq_frequency_score >= 1.0 AND q.pyq_frequency_score < 1.5 AND ae.was_correct THEN 1 END) as med_pyq_correct
                FROM attempt_events ae
                JOIN questions q ON q.id = ae.question_id
                WHERE ae.user_id = :user_id
            """)
            
            result = db.execute(query, {"user_id": user_id}).fetchone()
            if result:
                return {
                    "high_frequency_pyqs": {
                        "attempted": int(result.high_pyq_attempted or 0),
                        "correct": int(result.high_pyq_correct or 0),
                        "accuracy": float(result.high_pyq_correct / result.high_pyq_attempted) if result.high_pyq_attempted > 0 else 0.0
                    },
                    "medium_frequency_pyqs": {
                        "attempted": int(result.med_pyq_attempted or 0),
                        "correct": int(result.med_pyq_correct or 0),
                        "accuracy": float(result.med_pyq_correct / result.med_pyq_attempted) if result.med_pyq_attempted > 0 else 0.0
                    }
                }
            return {}
        except Exception as e:
            self.logger.warning(f"Error getting PYQ performance: {e}")
            return {}
    
    def _get_difficulty_patterns(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get performance by difficulty level"""
        try:
            query = text("""
                SELECT 
                    q.difficulty_band,
                    COUNT(ae.id) as attempted,
                    COUNT(CASE WHEN ae.was_correct THEN 1 END) as correct
                FROM attempt_events ae
                JOIN questions q ON q.id = ae.question_id
                WHERE ae.user_id = :user_id
                GROUP BY q.difficulty_band
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return {
                r.difficulty_band or "Unknown": {
                    "attempted": int(r.attempted or 0),
                    "correct": int(r.correct or 0),
                    "accuracy": float(r.correct / r.attempted) if r.attempted > 0 else 0.0
                    # avg_time removed - Twelvr focuses on accuracy patterns only
                }
                for r in results
            }
        except Exception as e:
            self.logger.warning(f"Error getting difficulty patterns: {e}")
            return {}
    
    def _get_coverage_analysis(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get coverage debt/gaps analysis"""
        try:
            query = text("""
                SELECT 
                    cd.subcategory,
                    cd.type_of_question,
                    cd.debt_score,
                    cd.updated_at
                FROM coverage_debt cd
                WHERE cd.user_id = :user_id
                ORDER BY cd.debt_score DESC
                LIMIT 20
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return [
                {
                    "topic": f"{r.subcategory}:{r.type_of_question}",
                    "debt_score": float(r.debt_score or 0.0),
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in results
            ]
        except Exception as e:
            self.logger.warning(f"Error getting coverage analysis: {e}")
            return []
    
    # _get_time_patterns removed - Twelvr engine focuses on accuracy & concept patterns only
    
    def _get_recent_activity(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get recent activity summary"""
        try:
            # Last 7 days activity
            week_ago = now_ist() - timedelta(days=7)
            
            query = text("""
                SELECT 
                    COUNT(DISTINCT s.session_id) as recent_sessions,
                    COUNT(ae.id) as recent_questions,
                    AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as recent_accuracy,
                    COUNT(DISTINCT DATE(ae.created_at)) as active_days
                FROM sessions s
                LEFT JOIN attempt_events ae ON ae.session_id = s.session_id
                WHERE s.user_id = :user_id AND s.served_at >= :week_ago
            """)
            
            result = db.execute(query, {"user_id": user_id, "week_ago": week_ago}).fetchone()
            if result:
                return {
                    "last_7_days": {
                        "sessions_completed": int(result.recent_sessions or 0),
                        "questions_attempted": int(result.recent_questions or 0),
                        "accuracy": float(result.recent_accuracy or 0.0),
                        "active_days": int(result.active_days or 0)
                    }
                }
            return {}
        except Exception as e:
            self.logger.warning(f"Error getting recent activity: {e}")
            return {}
    
    def _get_upcoming_session_context(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Get detailed context about upcoming/current session including question breakdown"""
        if not session_id:
            return {}
            
        try:
            # Get detailed question breakdown for the session pack
            query = text("""
                SELECT 
                    q.subcategory,
                    q.difficulty_band,
                    q.type_of_question,
                    q.core_concepts,
                    COUNT(*) as count
                FROM session_pack_questions spq
                JOIN questions q ON q.id = spq.question_id
                WHERE spq.pack_session_id = :session_id OR spq.session_id = :session_id
                GROUP BY q.subcategory, q.difficulty_band, q.type_of_question, q.core_concepts
                ORDER BY COUNT(*) DESC
            """)
            
            results = db.execute(query, {"session_id": session_id}).fetchall()
            
            if results:
                # Build detailed breakdown
                topic_distribution = {}
                difficulty_distribution = {"Easy": 0, "Medium": 0, "Hard": 0}
                total_questions = 0
                all_concepts = set()
                
                for row in results:
                    subcategory = row.subcategory or "General"
                    difficulty = row.difficulty_band or "Medium"
                    count = row.count
                    concepts = row.core_concepts or []
                    
                    # Topic distribution
                    if subcategory not in topic_distribution:
                        topic_distribution[subcategory] = {
                            "count": 0,
                            "difficulty_breakdown": {"Easy": 0, "Medium": 0, "Hard": 0}
                        }
                    
                    topic_distribution[subcategory]["count"] += count
                    topic_distribution[subcategory]["difficulty_breakdown"][difficulty] += count
                    
                    # Overall difficulty
                    difficulty_distribution[difficulty] += count
                    total_questions += count
                    
                    # Collect concepts
                    if isinstance(concepts, list):
                        all_concepts.update(concepts)
                
                return {
                    "session_id": session_id,
                    "total_questions": total_questions,
                    "topic_distribution": topic_distribution,
                    "difficulty_distribution": difficulty_distribution,
                    "key_concepts": list(all_concepts)[:10],  # Top 10 concepts
                    "status": "pack_ready"
                }
            
            return {"session_id": session_id, "status": "pack_not_ready"}
            
        except Exception as e:
            self.logger.warning(f"Error getting upcoming session context: {e}")
            return {"session_id": session_id, "error": str(e)}

# Global instance
comprehensive_data_extractor = ComprehensiveDataExtractor()
