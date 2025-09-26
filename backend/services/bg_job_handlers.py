"""
Background Job Handlers
Implements specific job processing logic for different job types
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from datetime import datetime, timezone

from database import SessionLocal
from sqlalchemy import text
from services.summarizer import summarizer_service
from services.planner import planner_service
from services.telemetry import telemetry_service

logger = logging.getLogger(__name__)

async def handle_session_summarization(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle post-session LLM summarization job
    
    Job data should contain:
    - user_id: User identifier
    - session_id: Session identifier
    - attempt_data: List of attempt records
    """
    job_data = job["job_data"]
    user_id = job["user_id"]
    session_id = job["session_id"]
    
    logger.info(f"🧠 Processing session summarization for user {user_id[:8]}, session {session_id[:8]}")
    
    try:
        # Run the summarizer service
        result = await summarizer_service.run(
            user_id=user_id,
            session_id=session_id
        )
        
        # Emit telemetry
        telemetry_service.emit_metric("bg_job.session_summarization.success", 1, {
            "user_id": user_id,
            "session_id": session_id,
            "llm_model": result.get("telemetry", {}).get("llm_model_used", "unknown")
        })
        
        logger.info(f"✅ Session summarization completed for session {session_id[:8]}")
        
        return {
            "status": "success",
            "summary_generated": True,
            "concepts_processed": len(result.get("concept_alias_map_updated", [])),
            "dominance_items": len(result.get("dominance_by_item", {})),
            "telemetry": result.get("telemetry", {})
        }
        
    except Exception as e:
        logger.error(f"❌ Session summarization failed for session {session_id[:8]}: {e}")
        
        # Emit failure telemetry
        telemetry_service.emit_metric("bg_job.session_summarization.failed", 1, {
            "user_id": user_id,
            "session_id": session_id,
            "error": str(e)[:100]
        })
        
        raise Exception(f"Session summarization failed: {str(e)}")

async def handle_personalized_planning(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle personalized next-session planning job
    
    Job data should contain:
    - user_id: User identifier
    - planning_context: Context for planning (user history, preferences)
    """
    job_data = job["job_data"]
    user_id = job["user_id"]
    
    logger.info(f"📋 Processing personalized planning for user {user_id[:8]}")
    
    try:
        # Get user's learning context
        planning_context = job_data.get("planning_context", {})
        
        # Run the planner service for next session using existing planner
        from services.planner import planner_service as existing_planner
        
        # Use the existing planner but with planning context
        result = await existing_planner.run(
            user_id=user_id,
            planning_context=planning_context
        )
        
        # Update learner notebook with planning insights
        await update_learner_notebook(user_id, result)
        
        # Emit telemetry
        telemetry_service.emit_metric("bg_job.personalized_planning.success", 1, {
            "user_id": user_id,
            "recommendations_generated": len(result.get("recommendations", []))
        })
        
        logger.info(f"✅ Personalized planning completed for user {user_id[:8]}")
        
        return {
            "status": "success",
            "planning_completed": True,
            "recommendations": result.get("recommendations", []),
            "focus_areas": result.get("focus_areas", [])
        }
        
    except Exception as e:
        logger.error(f"❌ Personalized planning failed for user {user_id[:8]}: {e}")
        
        # Emit failure telemetry
        telemetry_service.emit_metric("bg_job.personalized_planning.failed", 1, {
            "user_id": user_id,
            "error": str(e)[:100]
        })
        
        raise Exception(f"Personalized planning failed: {str(e)}")

async def handle_concept_analysis(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle concept mastery analysis job
    
    Job data should contain:
    - user_id: User identifier
    - analysis_scope: Scope of analysis (recent_sessions, full_history)
    """
    job_data = job["job_data"]
    user_id = job["user_id"]
    analysis_scope = job_data.get("analysis_scope", "recent_sessions")
    
    logger.info(f"🔍 Processing concept analysis for user {user_id[:8]} (scope: {analysis_scope})")
    
    try:
        # Get user's attempt history based on scope
        db = SessionLocal()
        try:
            if analysis_scope == "recent_sessions":
                # Analyze last 5 sessions
                query = text("""
                    SELECT ae.* FROM attempt_events ae
                    JOIN sessions s ON ae.session_id = s.session_id
                    WHERE ae.user_id = :user_id AND s.status = 'completed'
                    ORDER BY s.completed_at DESC, ae.created_at ASC
                    LIMIT 60  -- Roughly 5 sessions * 12 questions
                """)
            else:
                # Analyze full history
                query = text("""
                    SELECT ae.* FROM attempt_events ae
                    WHERE ae.user_id = :user_id
                    ORDER BY ae.created_at ASC
                """)
            
            attempts = db.execute(query, {"user_id": user_id}).fetchall()
            
        finally:
            db.close()
        
        if not attempts:
            logger.warning(f"⚠️ No attempt data found for concept analysis, user {user_id[:8]}")
            return {
                "status": "success",
                "analysis_completed": False,
                "reason": "no_attempt_data"
            }
        
        # Analyze concept patterns
        concept_insights = await analyze_concept_patterns(user_id, attempts)
        
        # Update learner notebook with insights
        await update_learner_notebook_from_analysis(user_id, concept_insights)
        
        # Emit telemetry
        telemetry_service.emit_metric("bg_job.concept_analysis.success", 1, {
            "user_id": user_id,
            "attempts_analyzed": len(attempts),
            "concepts_identified": len(concept_insights.get("concepts", {}))
        })
        
        logger.info(f"✅ Concept analysis completed for user {user_id[:8]} ({len(attempts)} attempts)")
        
        return {
            "status": "success",
            "analysis_completed": True,
            "attempts_analyzed": len(attempts),
            "concept_insights": concept_insights
        }
        
    except Exception as e:
        logger.error(f"❌ Concept analysis failed for user {user_id[:8]}: {e}")
        
        # Emit failure telemetry
        telemetry_service.emit_metric("bg_job.concept_analysis.failed", 1, {
            "user_id": user_id,
            "error": str(e)[:100]
        })
        
        raise Exception(f"Concept analysis failed: {str(e)}")

async def handle_coverage_update(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle coverage debt and learning gap analysis job
    
    Job data should contain:
    - user_id: User identifier
    - update_scope: Scope of update (session_based, periodic_full)
    """
    job_data = job["job_data"]
    user_id = job["user_id"]
    update_scope = job_data.get("update_scope", "session_based")
    
    logger.info(f"📊 Processing coverage update for user {user_id[:8]} (scope: {update_scope})")
    
    try:
        # Calculate coverage debt based on user's performance patterns
        coverage_analysis = await analyze_coverage_patterns(user_id, update_scope)
        
        # Update coverage debt table
        await update_coverage_debt_table(user_id, coverage_analysis)
        
        # Emit telemetry
        telemetry_service.emit_metric("bg_job.coverage_update.success", 1, {
            "user_id": user_id,
            "debt_items_updated": len(coverage_analysis.get("debt_updates", [])),
            "high_priority_gaps": coverage_analysis.get("high_priority_count", 0)
        })
        
        logger.info(f"✅ Coverage update completed for user {user_id[:8]}")
        
        return {
            "status": "success",
            "coverage_updated": True,
            "debt_analysis": coverage_analysis
        }
        
    except Exception as e:
        logger.error(f"❌ Coverage update failed for user {user_id[:8]}: {e}")
        
        # Emit failure telemetry
        telemetry_service.emit_metric("bg_job.coverage_update.failed", 1, {
            "user_id": user_id,
            "error": str(e)[:100]
        })
        
        raise Exception(f"Coverage update failed: {str(e)}")

# Helper functions for job processing

async def update_learner_notebook(user_id: str, planning_result: Dict[str, Any]):
    """Update learner notebook with planning insights"""
    db = SessionLocal()
    try:
        # Extract insights from planning result
        recommendations = planning_result.get("recommendations", [])
        
        for rec in recommendations:
            concept_id = rec.get("concept_semantic_id")
            if not concept_id:
                continue
            
            # Upsert learner notebook entry
            db.execute(text("""
                INSERT INTO learner_notebook (
                    user_id, concept_semantic_id, canonical_label,
                    readiness_labels, last_updated_at
                ) VALUES (
                    :user_id, :concept_id, :label, :readiness_labels::jsonb, :updated_at
                )
                ON CONFLICT (user_id, concept_semantic_id) DO UPDATE SET
                    readiness_labels = EXCLUDED.readiness_labels,
                    last_updated_at = EXCLUDED.last_updated_at
            """), {
                "user_id": user_id,
                "concept_id": concept_id,
                "label": rec.get("canonical_label", "Unknown Concept"),
                "readiness_labels": json.dumps(rec.get("readiness_labels", [])),
                "updated_at": datetime.now(timezone.utc)
            })
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update learner notebook for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()

async def analyze_concept_patterns(user_id: str, attempts: list) -> Dict[str, Any]:
    """Analyze concept mastery patterns from attempt data"""
    # Simplified concept analysis - can be enhanced with LLM processing
    concepts = {}
    
    for attempt in attempts:
        # Extract concept information
        pair_id = f"{attempt.subcategory}:{attempt.type_of_question}"
        
        if pair_id not in concepts:
            concepts[pair_id] = {
                "total_attempts": 0,
                "correct_attempts": 0,
                "skip_count": 0,
                "last_attempt": None
            }
        
        concepts[pair_id]["total_attempts"] += 1
        if attempt.was_correct:
            concepts[pair_id]["correct_attempts"] += 1
        if attempt.skipped:
            concepts[pair_id]["skip_count"] += 1
        concepts[pair_id]["last_attempt"] = attempt.created_at
    
    # Calculate mastery metrics
    for pair_id, data in concepts.items():
        total = data["total_attempts"]
        correct = data["correct_attempts"]
        accuracy = correct / total if total > 0 else 0
        
        # Determine mastery level
        if accuracy >= 0.8 and total >= 5:
            mastery_level = "proficient"
        elif accuracy >= 0.6 and total >= 3:
            mastery_level = "developing"
        else:
            mastery_level = "novice"
        
        data["accuracy"] = accuracy
        data["mastery_level"] = mastery_level
        data["confidence_score"] = min(accuracy + (total * 0.05), 1.0)  # Confidence grows with attempts
    
    return {"concepts": concepts}

async def update_learner_notebook_from_analysis(user_id: str, concept_insights: Dict[str, Any]):
    """Update learner notebook from concept analysis"""
    db = SessionLocal()
    try:
        concepts = concept_insights.get("concepts", {})
        
        for pair_id, data in concepts.items():
            # Convert pair_id to semantic_id (simplified)
            concept_semantic_id = pair_id.replace(":", "_").lower()
            
            # Determine readiness labels
            readiness_labels = []
            if data["skip_count"] / data["total_attempts"] > 0.3:
                readiness_labels.append("skipped")
            if data["accuracy"] < 0.4:
                readiness_labels.append("wrong_gt_3")
            elif data["accuracy"] < 0.6:
                readiness_labels.append("wrong_1_to_3")
            
            # Upsert learner notebook
            db.execute(text("""
                INSERT INTO learner_notebook (
                    user_id, concept_semantic_id, canonical_label,
                    mastery_level, confidence_score, total_attempts, 
                    correct_attempts, readiness_labels, last_updated_at,
                    last_attempt_at
                ) VALUES (
                    :user_id, :concept_id, :label, :mastery_level,
                    :confidence_score, :total_attempts, :correct_attempts,
                    :readiness_labels::jsonb, :updated_at, :last_attempt_at
                )
                ON CONFLICT (user_id, concept_semantic_id) DO UPDATE SET
                    mastery_level = EXCLUDED.mastery_level,
                    confidence_score = EXCLUDED.confidence_score,
                    total_attempts = EXCLUDED.total_attempts,
                    correct_attempts = EXCLUDED.correct_attempts,
                    readiness_labels = EXCLUDED.readiness_labels,
                    last_updated_at = EXCLUDED.last_updated_at,
                    last_attempt_at = EXCLUDED.last_attempt_at
            """), {
                "user_id": user_id,
                "concept_id": concept_semantic_id,
                "label": pair_id.replace(":", " - "),
                "mastery_level": data["mastery_level"],
                "confidence_score": data["confidence_score"],
                "total_attempts": data["total_attempts"],
                "correct_attempts": data["correct_attempts"],
                "readiness_labels": json.dumps(readiness_labels),
                "updated_at": datetime.now(timezone.utc),
                "last_attempt_at": data["last_attempt"]
            })
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update learner notebook from analysis for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()

async def analyze_coverage_patterns(user_id: str, scope: str) -> Dict[str, Any]:
    """Analyze coverage patterns and identify learning gaps"""
    # Simplified coverage analysis - can be enhanced with more sophisticated logic
    db = SessionLocal()
    try:
        # Get subcategory/type pairs with poor performance or insufficient exposure
        result = db.execute(text("""
            SELECT 
                CONCAT(subcategory, ':', type_of_question) as pair_identifier,
                COUNT(*) as total_attempts,
                COUNT(CASE WHEN was_correct THEN 1 END) as correct_attempts,
                COUNT(CASE WHEN skipped THEN 1 END) as skip_attempts,
                MAX(created_at) as last_attempt_at,
                EXTRACT(DAYS FROM NOW() - MAX(created_at)) as days_since_practice
            FROM attempt_events 
            WHERE user_id = :user_id
            GROUP BY subcategory, type_of_question
            HAVING COUNT(*) >= 2  -- Only consider pairs with multiple attempts
            ORDER BY (COUNT(CASE WHEN was_correct THEN 1 END)::float / COUNT(*)) ASC,
                     EXTRACT(DAYS FROM NOW() - MAX(created_at)) DESC
        """), {"user_id": user_id})
        
        pairs = result.fetchall()
        debt_updates = []
        high_priority_count = 0
        
        for pair in pairs:
            accuracy = pair.correct_attempts / pair.total_attempts if pair.total_attempts > 0 else 0
            skip_rate = pair.skip_attempts / pair.total_attempts
            days_since = int(pair.days_since_practice or 0)
            
            # Calculate debt score
            debt_score = 0.0
            debt_type = "insufficient_exposure"
            reason_codes = []
            
            # Performance-based debt
            if accuracy < 0.4:
                debt_score += 0.4
                debt_type = "performance_decline"
                reason_codes.append("low_accuracy")
            
            # Avoidance-based debt
            if skip_rate > 0.3:
                debt_score += 0.3
                debt_type = "avoidance_pattern"
                reason_codes.append("high_skip_rate")
            
            # Recency-based debt
            if days_since > 7:
                debt_score += min(days_since * 0.02, 0.3)
                reason_codes.append("insufficient_recent_practice")
            
            debt_score = min(debt_score, 1.0)
            
            if debt_score > 0.3:  # Only track significant debt
                priority_score = debt_score * (1 + (pair.total_attempts * 0.1))  # More attempts = higher priority
                
                if priority_score > 0.7:
                    high_priority_count += 1
                
                debt_updates.append({
                    "pair_identifier": pair.pair_identifier,
                    "debt_score": debt_score,
                    "debt_type": debt_type,
                    "reason_codes": reason_codes,
                    "priority_score": min(priority_score, 1.0),
                    "days_since_practice": days_since
                })
        
        return {
            "debt_updates": debt_updates,
            "high_priority_count": high_priority_count,
            "total_pairs_analyzed": len(pairs)
        }
        
    except Exception as e:
        logger.error(f"❌ Coverage pattern analysis failed for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()

async def update_coverage_debt_table(user_id: str, analysis: Dict[str, Any]):
    """Update coverage debt table with analysis results"""
    db = SessionLocal()
    try:
        debt_updates = analysis.get("debt_updates", [])
        
        for debt in debt_updates:
            db.execute(text("""
                INSERT INTO coverage_debt (
                    user_id, pair_identifier, debt_score, debt_type,
                    reason_codes, priority_score, days_since_practice,
                    updated_at
                ) VALUES (
                    :user_id, :pair_identifier, :debt_score, :debt_type,
                    :reason_codes::jsonb, :priority_score, :days_since_practice,
                    :updated_at
                )
                ON CONFLICT (user_id, pair_identifier) DO UPDATE SET
                    debt_score = EXCLUDED.debt_score,
                    debt_type = EXCLUDED.debt_type,
                    reason_codes = EXCLUDED.reason_codes,
                    priority_score = EXCLUDED.priority_score,
                    days_since_practice = EXCLUDED.days_since_practice,
                    updated_at = EXCLUDED.updated_at,
                    resolved_at = NULL  -- Reset resolution when debt recurs
            """), {
                "user_id": user_id,
                "pair_identifier": debt["pair_identifier"],
                "debt_score": debt["debt_score"],
                "debt_type": debt["debt_type"],
                "reason_codes": json.dumps(debt["reason_codes"]),
                "priority_score": debt["priority_score"],
                "days_since_practice": debt["days_since_practice"],
                "updated_at": datetime.now(timezone.utc)
            })
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update coverage debt table for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()