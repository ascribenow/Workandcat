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
                "user_id": user_id[:8],  # Truncated for privacy
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "session_context": session_id,
                
                # Core session data
                "sessions": self._get_all_sessions(db, user_id),
                "accuracy_trends": self._get_accuracy_trends(db, user_id),
                "concept_journey": self._get_concept_journey(db, user_id),
                "question_attempts": self._get_question_attempts(db, user_id),
                "pyq_performance": self._get_pyq_performance(db, user_id),
                "difficulty_patterns": self._get_difficulty_patterns(db, user_id),
                "coverage_analysis": self._get_coverage_analysis(db, user_id),
                "time_patterns": self._get_time_patterns(db, user_id),
                "recent_activity": self._get_recent_activity(db, user_id),
                
                # Context for current/upcoming session
                "upcoming_session": self._get_upcoming_session_context(db, session_id) if session_id else None
            }
            
            # Log data richness for debugging
            total_sessions = len(user_data.get("sessions", []))
            total_attempts = len(user_data.get("question_attempts", []))
            concept_count = len(user_data.get("concept_journey", []))
            
            self.logger.info(f"Extracted comprehensive data: {total_sessions} sessions, {total_attempts} attempts, {concept_count} concepts")
            
            return user_data
            
        except Exception as e:
            self.logger.error(f"Error extracting comprehensive data for user {user_id[:8]}: {e}")
            # Return minimal data structure if extraction fails
            return {
                "user_id": user_id[:8],
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
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
        """Get concept learning journey"""
        try:
            query = text("""
                SELECT 
                    ln.concept_norm,
                    ln.readiness,
                    ln.sessions_seen,
                    ln.total_attempts,
                    ln.correct_attempts,
                    ln.last_seen_at,
                    ln.first_seen_at
                FROM learner_notebook ln
                WHERE ln.user_id = :user_id
                ORDER BY ln.last_seen_at DESC
                LIMIT 50
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return [
                {
                    "concept": r.concept_norm,
                    "readiness": r.readiness,
                    "sessions_seen": int(r.sessions_seen or 0),
                    "total_attempts": int(r.total_attempts or 0),
                    "correct_attempts": int(r.correct_attempts or 0),
                    "accuracy": float(r.correct_attempts / r.total_attempts) if r.total_attempts > 0 else 0.0,
                    "last_seen": r.last_seen_at.isoformat() if r.last_seen_at else None,
                    "first_seen": r.first_seen_at.isoformat() if r.first_seen_at else None
                }
                for r in results
            ]
        except Exception as e:
            self.logger.warning(f"Error getting concept journey: {e}")
            return []
    
    def _get_question_attempts(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get recent question attempts with details"""
        try:
            query = text("""
                SELECT 
                    ae.question_id,
                    ae.was_correct,
                    ae.selected_option,
                    ae.time_taken_seconds,
                    ae.created_at,
                    q.category,
                    q.subcategory,
                    q.difficulty,
                    q.pyq_frequency_score
                FROM attempt_events ae
                JOIN questions q ON q.id = ae.question_id
                WHERE ae.user_id = :user_id
                ORDER BY ae.created_at DESC
                LIMIT 100
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return [
                {
                    "question_id": r.question_id,
                    "correct": bool(r.was_correct),
                    "selected_option": r.selected_option,
                    "time_taken": float(r.time_taken_seconds or 0.0),
                    "attempted_at": r.created_at.isoformat() if r.created_at else None,
                    "category": r.category,
                    "subcategory": r.subcategory,
                    "difficulty": r.difficulty,
                    "pyq_score": float(r.pyq_frequency_score or 0.0)
                }
                for r in results
            ]
        except Exception as e:
            self.logger.warning(f"Error getting question attempts: {e}")
            return []
    
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
                    q.difficulty,
                    COUNT(ae.id) as attempted,
                    COUNT(CASE WHEN ae.was_correct THEN 1 END) as correct,
                    AVG(ae.time_taken_seconds) as avg_time
                FROM attempt_events ae
                JOIN questions q ON q.id = ae.question_id
                WHERE ae.user_id = :user_id
                GROUP BY q.difficulty
            """)
            
            results = db.execute(query, {"user_id": user_id}).fetchall()
            return {
                r.difficulty or "Unknown": {
                    "attempted": int(r.attempted or 0),
                    "correct": int(r.correct or 0),
                    "accuracy": float(r.correct / r.attempted) if r.attempted > 0 else 0.0,
                    "avg_time_seconds": float(r.avg_time or 0.0)
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
    
    def _get_time_patterns(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get time-based patterns"""
        try:
            query = text("""
                SELECT 
                    AVG(ae.time_taken_seconds) as avg_time_per_question,
                    MIN(ae.time_taken_seconds) as fastest_time,
                    MAX(ae.time_taken_seconds) as slowest_time,
                    COUNT(CASE WHEN ae.time_taken_seconds < 60 THEN 1 END) as quick_answers,
                    COUNT(CASE WHEN ae.time_taken_seconds > 180 THEN 1 END) as slow_answers
                FROM attempt_events ae
                WHERE ae.user_id = :user_id AND ae.time_taken_seconds IS NOT NULL
            """)
            
            result = db.execute(query, {"user_id": user_id}).fetchone()
            if result:
                return {
                    "average_time_per_question": float(result.avg_time_per_question or 0.0),
                    "fastest_answer": float(result.fastest_time or 0.0),
                    "slowest_answer": float(result.slowest_time or 0.0),
                    "quick_answers_under_60s": int(result.quick_answers or 0),
                    "slow_answers_over_180s": int(result.slow_answers or 0)
                }
            return {}
        except Exception as e:
            self.logger.warning(f"Error getting time patterns: {e}")
            return {}
    
    def _get_recent_activity(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get recent activity summary"""
        try:
            # Last 7 days activity
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            query = text("""
                SELECT 
                    COUNT(DISTINCT s.session_id) as recent_sessions,
                    COUNT(ae.id) as recent_questions,
                    AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as recent_accuracy,
                    COUNT(DISTINCT DATE(ae.created_at)) as active_days
                FROM sessions s
                LEFT JOIN attempt_events ae ON ae.session_id = s.session_id
                WHERE s.user_id = :user_id AND s.started_at >= :week_ago
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
        """Get context about upcoming/current session"""
        if not session_id:
            return {}
            
        try:
            # Try to get session pack info if available
            query = text("""
                SELECT 
                    sp.session_id,
                    sp.pack_type,
                    sp.difficulty_distribution,
                    COUNT(spq.id) as question_count,
                    STRING_AGG(DISTINCT q.subcategory, ', ') as topics_covered
                FROM session_packs sp
                LEFT JOIN session_pack_questions spq ON spq.session_id = sp.session_id
                LEFT JOIN questions q ON q.id = spq.question_id
                WHERE sp.session_id = :session_id
                GROUP BY sp.session_id, sp.pack_type, sp.difficulty_distribution
            """)
            
            result = db.execute(query, {"session_id": session_id}).fetchone()
            if result:
                return {
                    "session_id": result.session_id,
                    "pack_type": result.pack_type,
                    "difficulty_distribution": result.difficulty_distribution,
                    "question_count": int(result.question_count or 0),
                    "topics_covered": result.topics_covered.split(', ') if result.topics_covered else []
                }
            return {"session_id": session_id, "status": "pack_not_ready"}
        except Exception as e:
            self.logger.warning(f"Error getting upcoming session context: {e}")
            return {"session_id": session_id, "error": str(e)}

# Global instance
comprehensive_data_extractor = ComprehensiveDataExtractor()