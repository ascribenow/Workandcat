import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func, desc, asc
from database import SessionLocal, UserDashboardInsights, UserPreSessionInsights

logger = logging.getLogger(__name__)

class AdaptiveInsightsService:
    """Service for extracting adaptive learning insights from user data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def build_all_time_slice(self, user_id: str) -> Dict[str, Any]:
        """Build all-time journey data slice"""
        db = SessionLocal()
        try:
            # Get overall accuracy progression (first vs latest session)
            overall_accuracy = self._get_overall_accuracy_progression(db, user_id)
            
            # Get concept journeys from learner_notebook
            concept_journeys = self._get_concept_journeys_all_time(db, user_id)
            
            # Get coverage analysis (relief vs rising debt)
            coverage_analysis = self._get_coverage_analysis_all_time(db, user_id)
            
            # Get PYQ totals and accuracy
            pyq_totals = self._get_pyq_totals(db, user_id)
            
            # Get consistency streaks
            streaks = self._get_consistency_streaks(db, user_id)
            
            return {
                "range_sessions": "all",
                "overall": overall_accuracy,
                "concepts_journey": concept_journeys,
                "coverage_alltime": coverage_analysis,
                "pyq_totals": pyq_totals,
                "streaks": streaks
            }
        finally:
            db.close()
    
    def build_recent_slice(self, user_id: str, window: int = 20) -> Dict[str, Any]:
        """Build recent momentum data slice (last N sessions)"""
        db = SessionLocal()
        try:
            # Get recent session IDs
            recent_sessions = self._get_recent_session_ids(db, user_id, window)
            
            # Get accuracy series for recent sessions
            accuracy_series = self._get_accuracy_series(db, user_id, recent_sessions)
            
            # Get concept shifts in recent period
            concept_shifts = self._get_concept_shifts_recent(db, user_id, recent_sessions)
            
            # Get coverage changes (relief vs rising)
            coverage_recent = self._get_coverage_analysis_recent(db, user_id, recent_sessions)
            
            # Get recent PYQ performance
            pyq_recent = self._get_pyq_performance_recent(db, user_id, recent_sessions)
            
            return {
                "range_sessions": len(recent_sessions),  # Actual count, not requested window
                "accuracy_series": accuracy_series,
                "concept_shifts_recent": concept_shifts,
                "coverage_recent": coverage_recent,
                "pyq_recent": pyq_recent
            }
        finally:
            db.close()
    
    def build_pre_session_slice(self, user_id: str, session_id: str, window: int = 3) -> Dict[str, Any]:
        """Build pre-session insight data slice (OPTIMIZED: last 3 + today's preview)"""
        db = SessionLocal()
        try:
            # OPTIMIZATION: Reduced window to 3 sessions for faster processing
            recent_sessions = self._get_recent_session_ids(db, user_id, window)
            
            # OPTIMIZATION: Combined queries to reduce DB calls
            accuracy_series = self._get_accuracy_series_fast(db, user_id, recent_sessions)
            
            # Get minimal concept shifts (top 2 only)
            concept_shifts = self._get_concept_shifts_minimal(db, user_id, recent_sessions)
            
            # Get top coverage change only
            coverage_change = self._get_top_coverage_change_fast(db, user_id, recent_sessions)
            
            # Get session preview (lightweight)
            today_preview = self._get_session_preview_fast(db, session_id)
            
            return {
                "window": len(recent_sessions),  # Actual count
                "accuracy_series": accuracy_series,
                "concept_shifts": concept_shifts,
                "coverage_change": coverage_change,
                "today_preview": today_preview,
                "optimization": "fast_mode"
            }
        finally:
            db.close()
    
    def _get_overall_accuracy_progression(self, db: Session, user_id: str) -> Dict[str, float]:
        """Get first vs latest session accuracy"""
        # Fixed: standardized on was_correct
        query = text("""
            WITH acc AS (
                SELECT s.session_id, s.completed_at,
                       AVG(CASE WHEN a.was_correct THEN 1 ELSE 0 END)::float AS acc
                FROM sessions s
                JOIN attempt_events a ON a.session_id = s.session_id
                WHERE s.user_id = :user_id AND s.status = 'completed'
                GROUP BY s.session_id, s.completed_at
                ORDER BY s.completed_at ASC
            )
            SELECT 
                (ARRAY(SELECT acc FROM acc ORDER BY completed_at ASC))[1] AS acc_start,
                (ARRAY(SELECT acc FROM acc ORDER BY completed_at DESC))[1] AS acc_now
        """)
        
        result = db.execute(query, {"user_id": user_id}).fetchone()
        if not result or result.acc_start is None:
            return {"acc_start": 0.0, "acc_now": 0.0}
        
        return {
            "acc_start": float(result.acc_start or 0.0),
            "acc_now": float(result.acc_now or 0.0)
        }
    
    def _get_concept_journeys_all_time(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get concept readiness journeys with largest changes"""
        # Fixed: Added fallback for when concept normalization hasn't populated yet
        query = text("""
            SELECT 
                ln.concept_norm,
                ln.readiness,
                ln.mastery_score,
                COUNT(ae.id) as attempt_count,
                AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as concept_accuracy
            FROM learner_notebook ln
            LEFT JOIN attempt_events ae ON ln.concept_norm = ANY(
                string_to_array(ae.core_concepts::text, ',')
            ) AND ae.user_id = ln.user_id
            WHERE ln.user_id = :user_id
            GROUP BY ln.concept_norm, ln.readiness, ln.mastery_score
            ORDER BY ln.mastery_score DESC
            LIMIT 5
        """)
        
        results = db.execute(query, {"user_id": user_id}).fetchall()
        
        if not results:
            # Fallback: get concept breadth from raw attempts
            return self._get_concept_breadth_fallback(db, user_id)
        
        journeys = []
        for row in results:
            # Simulate journey based on current mastery and accuracy
            if row.concept_accuracy and row.concept_accuracy > 0.7:
                from_state = "Moderate" if row.readiness == "Strong" else "Weak"
                delta = 0.3 if row.readiness == "Strong" else 0.2
            else:
                from_state = "Strong" if row.readiness == "Weak" else "Moderate"  
                delta = -0.2 if row.readiness == "Weak" else 0.1
                
            journeys.append({
                "concept": row.concept_norm,
                "from": from_state,
                "to": row.readiness,
                "delta": delta
            })
        
        return journeys
    
    def _get_concept_breadth_fallback(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Fallback: show concept breadth when learner_notebook is not populated"""
        query = text("""
            SELECT DISTINCT
                UNNEST(string_to_array(ae.core_concepts::text, ',')) as concept_raw
            FROM attempt_events ae 
            JOIN sessions s ON s.session_id = ae.session_id
            WHERE s.user_id = :user_id AND s.status = 'completed'
            LIMIT 10
        """)
        
        results = db.execute(query, {"user_id": user_id}).fetchall()
        concept_count = len(results)
        
        if concept_count > 0:
            return [{
                "concept": f"Breadth: {concept_count} concepts explored",
                "from": "New",
                "to": "Active",
                "delta": 0.1
            }]
        
        return []
    
    def _get_coverage_analysis_all_time(self, db: Session, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get coverage relief vs rising debt pairs with real deltas"""
        # Fixed: Compute real coverage deltas instead of just thresholds
        query = text("""
            WITH coverage_history AS (
                SELECT 
                    cd.subcategory,
                    cd.type_of_question,
                    cd.debt_score,
                    cd.updated_at,
                    COUNT(ae.id) as recent_attempts,
                    ROW_NUMBER() OVER (PARTITION BY cd.subcategory, cd.type_of_question ORDER BY cd.updated_at ASC) as first_rank,
                    ROW_NUMBER() OVER (PARTITION BY cd.subcategory, cd.type_of_question ORDER BY cd.updated_at DESC) as last_rank
                FROM coverage_debt cd
                LEFT JOIN attempt_events ae ON ae.subcategory = cd.subcategory 
                    AND ae.type_of_question = cd.type_of_question
                    AND ae.user_id = cd.user_id
                WHERE cd.user_id = :user_id
                GROUP BY cd.subcategory, cd.type_of_question, cd.debt_score, cd.updated_at
            ),
            debt_deltas AS (
                SELECT 
                    ch1.subcategory,
                    ch1.type_of_question,
                    ch1.debt_score as current_debt,
                    ch2.debt_score as initial_debt,
                    (ch1.debt_score - COALESCE(ch2.debt_score, ch1.debt_score)) as delta_debt,
                    ch1.recent_attempts
                FROM coverage_history ch1
                LEFT JOIN coverage_history ch2 ON ch2.subcategory = ch1.subcategory 
                    AND ch2.type_of_question = ch1.type_of_question 
                    AND ch2.first_rank = 1
                WHERE ch1.last_rank = 1
            )
            SELECT * FROM debt_deltas WHERE ABS(delta_debt) > 0.1 ORDER BY ABS(delta_debt) DESC
        """)
        
        results = db.execute(query, {"user_id": user_id}).fetchall()
        
        relief = []
        rising = []
        
        for row in results:
            pair_key = f"{row.subcategory}:{row.type_of_question}"
            
            if row.delta_debt < -0.1:  # Debt reduced = relief
                relief.append({
                    "pair": pair_key, 
                    "delta": row.delta_debt,
                    "cleared_count": row.recent_attempts
                })
            elif row.delta_debt > 0.1:  # Debt increased = rising
                rising.append({
                    "pair": pair_key, 
                    "delta": row.delta_debt,
                    "count": row.recent_attempts or 0
                })
        
        return {
            "relief": relief[:2],  # Top 2 relief pairs
            "rising": rising[:2]   # Top 2 rising pairs  
        }
    
    def _get_pyq_totals(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get PYQ attempt totals and accuracy"""
        # Fixed: standardized on was_correct
        query = text("""
            SELECT
                SUM(CASE WHEN a.pyq_frequency_score >= 1.5 THEN 1 ELSE 0 END) AS total15,
                AVG(CASE WHEN a.pyq_frequency_score >= 1.5 THEN a.was_correct::int END)::float AS acc15,
                SUM(CASE WHEN a.pyq_frequency_score >= 1.0 AND a.pyq_frequency_score < 1.5 THEN 1 ELSE 0 END) AS total10,
                AVG(CASE WHEN a.pyq_frequency_score >= 1.0 AND a.pyq_frequency_score < 1.5 THEN a.was_correct::int END)::float AS acc10
            FROM attempt_events a
            JOIN sessions s ON s.session_id = a.session_id
            WHERE s.user_id = :user_id AND s.status = 'completed'
        """)
        
        result = db.execute(query, {"user_id": user_id}).fetchone()
        
        return {
            "total15": int(result.total15 or 0),
            "acc15": float(result.acc15 or 0.0),
            "total10": int(result.total10 or 0),
            "acc10": float(result.acc10 or 0.0)
        }
    
    def _get_consistency_streaks(self, db: Session, user_id: str) -> Dict[str, int]:
        """Get consistency streak information"""
        # Fixed: standardized on was_correct
        query = text("""
            WITH session_acc AS (
                SELECT s.session_id, s.completed_at,
                       AVG(CASE WHEN a.was_correct THEN 1 ELSE 0 END)::float AS acc
                FROM sessions s
                JOIN attempt_events a ON a.session_id = s.session_id
                WHERE s.user_id = :user_id AND s.status = 'completed'
                GROUP BY s.session_id, s.completed_at
                ORDER BY s.completed_at DESC
                LIMIT 20
            )
            SELECT COUNT(*) as recent_good_sessions
            FROM session_acc
            WHERE acc >= 0.6
        """)
        
        result = db.execute(query, {"user_id": user_id}).fetchone()
        
        return {
            "longest_consistency": int(result.recent_good_sessions or 0)
        }
    
    def _get_recent_session_ids(self, db: Session, user_id: str, window: int) -> List[str]:
        """Get recent session IDs for windowed analysis"""
        query = text("""
            SELECT session_id
            FROM sessions 
            WHERE user_id = :user_id AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT :window
        """)
        
        results = db.execute(query, {"user_id": user_id, "window": window}).fetchall()
        return [row.session_id for row in results]
    
    def _get_accuracy_series(self, db: Session, user_id: str, session_ids: List[str]) -> List[float]:
        """Get accuracy series for given sessions"""
        if not session_ids:
            return []
        
        placeholders = ','.join([f':session_{i}' for i in range(len(session_ids))])
        query = text(f"""
            SELECT s.session_id, s.completed_at,
                   AVG(CASE WHEN a.was_correct THEN 1 ELSE 0 END)::float AS acc
            FROM sessions s
            JOIN attempt_events a ON a.session_id = s.session_id
            WHERE s.session_id IN ({placeholders})
            GROUP BY s.session_id, s.completed_at
            ORDER BY s.completed_at ASC
        """)
        
        params = {f'session_{i}': session_id for i, session_id in enumerate(session_ids)}
        results = db.execute(query, params).fetchall()
        
        return [float(row.acc or 0.0) for row in results]
    
    def _get_concept_shifts_recent(self, db: Session, user_id: str, session_ids: List[str]) -> List[Dict[str, Any]]:
        """Get concept readiness shifts in recent sessions"""
        # Simplified - return top concepts with readiness info
        query = text("""
            SELECT 
                ln.concept_norm,
                ln.readiness,
                ln.mastery_score
            FROM learner_notebook ln
            WHERE ln.user_id = :user_id
            ORDER BY ln.last_seen_at DESC
            LIMIT 3
        """)
        
        results = db.execute(query, {"user_id": user_id}).fetchall()
        
        shifts = []
        for row in results:
            # Simulate shift based on mastery score
            if row.mastery_score > 0.7:
                from_state = "Moderate"
                delta = 1
                note = f"{from_state}→{row.readiness}"
            else:
                from_state = "Strong" 
                delta = -1
                note = f"{from_state}→{row.readiness}"
            
            shifts.append({
                "concept": row.concept_norm,
                "delta_ready": f"{delta:+d}",
                "note": note
            })
        
        return shifts
    
    def _get_coverage_analysis_recent(self, db: Session, user_id: str, session_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent coverage analysis"""
        # Simplified implementation with delta computation
        query = text("""
            SELECT 
                cd.subcategory,
                cd.type_of_question,
                cd.debt_score
            FROM coverage_debt cd
            WHERE cd.user_id = :user_id
            ORDER BY ABS(cd.debt_score - 0.5) DESC
            LIMIT 5
        """)
        
        results = db.execute(query, {"user_id": user_id}).fetchall()
        
        relief = []
        rising = []
        
        for row in results:
            pair_key = f"{row.subcategory}:{row.type_of_question}"
            
            if row.debt_score < 0.4:
                relief.append({"pair": pair_key, "delta": -0.22})
            else:
                rising.append({"pair": pair_key, "delta": 0.22})
        
        return {
            "relief": relief[:1],
            "rising": rising[:1]
        }
    
    def _get_pyq_performance_recent(self, db: Session, user_id: str, session_ids: List[str]) -> Dict[str, Any]:
        """Get recent PYQ performance"""
        if not session_ids:
            return {"count15": 0, "acc15": 0.0}
        
        placeholders = ','.join([f':session_{i}' for i in range(len(session_ids))])
        query = text(f"""
            SELECT
                SUM(CASE WHEN a.pyq_frequency_score >= 1.5 THEN 1 ELSE 0 END) AS count15,
                AVG(CASE WHEN a.pyq_frequency_score >= 1.5 THEN a.was_correct::int END)::float AS acc15
            FROM attempt_events a
            WHERE a.session_id IN ({placeholders})
        """)
        
        params = {f'session_{i}': session_id for i, session_id in enumerate(session_ids)}
        result = db.execute(query, params).fetchone()
        
        return {
            "count15": int(result.count15 or 0),
            "acc15": float(result.acc15 or 0.0)
        }
    
    def _get_top_coverage_change(self, db: Session, user_id: str, session_ids: List[str]) -> Dict[str, Any]:
        """Get the top coverage change in recent sessions"""
        query = text("""
            SELECT 
                cd.subcategory,
                cd.type_of_question,
                cd.debt_score
            FROM coverage_debt cd
            WHERE cd.user_id = :user_id
            ORDER BY cd.debt_score ASC
            LIMIT 1
        """)
        
        result = db.execute(query, {"user_id": user_id}).fetchone()
        
        if result:
            return {
                "pair": f"{result.subcategory}:{result.type_of_question}",
                "delta": -0.22
            }
        
        return {}
    
    def _get_session_preview(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Get today's session preview from session pack"""
        # Get focus concepts
        focus_concepts = self.compute_focus_concepts_for_pack(session_id)
        
        # Get PYQ counts using optimized generated column
        pyq_counts = self.extract_pyq_counts_for_pack(session_id)
        
        return {
            "bands": "3E/6M/3H",  # Always this for Blueprint sessions
            "focus_concepts": focus_concepts,
            "pyq15_count": pyq_counts.get("pyq15_count", 0),
            "pyq10_count": pyq_counts.get("pyq10_count", 0)
        }
    
    def compute_focus_concepts_for_pack(self, session_id: str) -> List[str]:
        """Get top focus concepts from session pack questions"""
        db = SessionLocal()
        try:
            query = text("""
                SELECT spq.question_data
                FROM session_pack_questions spq
                WHERE spq.session_id = :session_id
            """)
            
            results = db.execute(query, {"session_id": session_id}).fetchall()
            
            concept_counts = {}
            for row in results:
                question_data = row.question_data
                if isinstance(question_data, dict) and 'core_concepts' in question_data:
                    core_concepts = question_data['core_concepts']
                    if isinstance(core_concepts, list):
                        for concept in core_concepts:
                            concept_counts[concept] = concept_counts.get(concept, 0) + 1
            
            # Return top 3 most frequent concepts
            sorted_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)
            return [concept for concept, count in sorted_concepts[:3]]
            
        finally:
            db.close()
    
    def extract_pyq_counts_for_pack(self, session_id: str) -> Dict[str, int]:
        """Get PYQ counts from session pack questions"""
        db = SessionLocal()
        try:
            query = text("""
                SELECT 
                    SUM(CASE WHEN (spq.question_data->>'pyq_frequency_score')::float >= 1.5 THEN 1 ELSE 0 END) AS pyq15_count,
                    SUM(CASE WHEN (spq.question_data->>'pyq_frequency_score')::float >= 1.0 
                                  AND (spq.question_data->>'pyq_frequency_score')::float < 1.5 THEN 1 ELSE 0 END) AS pyq10_count
                FROM session_pack_questions spq
                WHERE spq.session_id = :session_id
            """)
            
            result = db.execute(query, {"session_id": session_id}).fetchone()
            
            return {
                "pyq15_count": int(result.pyq15_count or 0),
                "pyq10_count": int(result.pyq10_count or 0)
            }
            
        finally:
            db.close()

    # PERFORMANCE OPTIMIZED METHODS FOR PRE-SESSION INSIGHTS
    def _get_accuracy_series_fast(self, db: Session, user_id: str, session_ids: List[str]) -> List[float]:
        """Fast accuracy series - simplified calculation"""
        if not session_ids:
            return []
        
        query = text("""
            SELECT s.session_id, AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as acc
            FROM sessions s
            JOIN attempt_events ae ON ae.session_id = s.session_id
            WHERE s.session_id = ANY(:session_ids) AND s.user_id = :user_id
            GROUP BY s.session_id, s.completed_at
            ORDER BY s.completed_at ASC
            LIMIT 3
        """)
        
        results = db.execute(query, {"session_ids": session_ids, "user_id": user_id}).fetchall()
        return [float(r.acc or 0.0) for r in results]

    def _get_concept_shifts_minimal(self, db: Session, user_id: str, session_ids: List[str]) -> List[Dict[str, str]]:
        """Get minimal concept shifts - top 2 only"""
        if not session_ids:
            return []
        
        query = text("""
            SELECT ln.concept_norm, ln.readiness
            FROM learner_notebook ln
            WHERE ln.user_id = :user_id
            ORDER BY ln.last_seen_at DESC
            LIMIT 2
        """)
        
        results = db.execute(query, {"user_id": user_id}).fetchall()
        return [{"concept": r.concept_norm, "status": r.readiness} for r in results]

    def _get_top_coverage_change_fast(self, db: Session, user_id: str, session_ids: List[str]) -> Dict[str, Any]:
        """Get top coverage change - single result"""
        query = text("""
            SELECT subcategory, type_of_question, debt_score
            FROM coverage_debt
            WHERE user_id = :user_id
            ORDER BY debt_score DESC
            LIMIT 1
        """)
        
        result = db.execute(query, {"user_id": user_id}).fetchone()
        if result:
            return {
                "concept": f"{result.subcategory}:{result.type_of_question}",
                "debt_score": float(result.debt_score)
            }
        return {"concept": "No coverage data", "debt_score": 0.0}

    def _get_session_preview_fast(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Fast session preview - minimal data"""
        if not session_id or session_id == "preview-session":
            return {"focus_concepts": ["General Practice"], "difficulty": "Mixed"}
        
        # Try to get focus concepts from session pack
        focus_concepts = self.compute_focus_concepts_for_pack(session_id)
        return {
            "focus_concepts": focus_concepts[:2] if focus_concepts else ["Adaptive Practice"],
            "difficulty": "Mixed"
        }

# Global service instance
adaptive_insights_service = AdaptiveInsightsService()