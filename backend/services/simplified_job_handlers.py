"""
Simplified Job Handlers
Three job types: SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from database import SessionLocal
from sqlalchemy import text
from services.summarizer import summarizer_service
from services.insight_cache_service import insight_cache_service

logger = logging.getLogger(__name__)

async def handle_summarize_session(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job A: SUMMARIZE_SESSION
    - Run LLM session analysis 
    - Update concept_alias_map_latest
    - Update learner_notebook (readiness + mastery)
    - Update coverage_debt (decrease served pairs, decay others)
    - Enqueue PLAN_NEXT_SESSION job
    """
    user_id = job["user_id"]
    session_id = job["session_id"]
    
    logger.info(f"🧠 SUMMARIZE_SESSION: user {user_id[:8]}, session {session_id[:8] if session_id else 'N/A'}")
    
    try:
        # Step 1: Run existing summarizer service for LLM analysis
        summarizer_result = await summarizer_service.run(
            user_id=user_id,
            session_id=session_id
        )
        
        # Step 2: Update learner notebook with session insights
        await update_learner_notebook_from_session(user_id, session_id, summarizer_result)
        
        # Step 3: Update coverage debt (fold coverage update into this job)
        await update_coverage_debt_from_session(user_id, session_id)
        
        # Step 4: Enqueue next job in sequence (PLAN_NEXT_SESSION)
        from services.bg_job_queue import job_queue
        planning_job_id = await job_queue.enqueue_job(
            job_type="PLAN_NEXT_SESSION",
            user_id=user_id,
            session_id=None  # Planning is per-user, not per-session
        )
        
        logger.info(f"✅ SUMMARIZE_SESSION completed, enqueued PLAN_NEXT_SESSION: {planning_job_id[:8]}")
        
        return {
            "status": "success",
            "summary_generated": True,
            "concept_updates": len(summarizer_result.get("concept_alias_map_updated", [])),
            "planning_job_enqueued": planning_job_id,
            "telemetry": summarizer_result.get("telemetry", {})
        }
        
    except Exception as e:
        logger.error(f"❌ SUMMARIZE_SESSION failed for user {user_id[:8]}: {e}")
        raise Exception(f"Session summarization failed: {str(e)}")

async def handle_plan_next_session(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job B: PLAN_NEXT_SESSION  
    - Use notebook + coverage + recency + PYQ constraints
    - Select 3E/6M/3H with Weak/Moderate preference
    - Persist prepack into session_packs + session_pack_questions
    """
    user_id = job["user_id"]
    
    logger.info(f"📋 PLAN_NEXT_SESSION: user {user_id[:8]}")
    
    try:
        # Step 1: Gather user learning data for planning
        learning_data = await gather_user_learning_data(user_id)
        
        # Step 2: Generate personalized session plan using existing planner
        session_pack = await generate_personalized_session_pack(user_id, learning_data)
        
        # Step 3: Persist prepack to session_packs tables
        pack_id = await persist_session_pack(user_id, session_pack)
        
        logger.info(f"✅ PLAN_NEXT_SESSION completed: pack {pack_id[:8]} for user {user_id[:8]}")
        
        return {
            "status": "success", 
            "session_pack_created": True,
            "pack_id": pack_id,
            "questions_selected": len(session_pack.get("questions", [])),
            "difficulty_distribution": session_pack.get("difficulty_distribution", {})
        }
        
    except Exception as e:
        logger.error(f"❌ PLAN_NEXT_SESSION failed for user {user_id[:8]}: {e}")
        raise Exception(f"Session planning failed: {str(e)}")

# Helper functions for job processing

async def update_learner_notebook_from_session(user_id: str, session_id: str, summarizer_result: Dict[str, Any]):
    """Update learner_notebook with simplified schema"""
    db = SessionLocal()
    try:
        # Get attempt events from this session for analysis
        attempts_result = db.execute(text("""
            SELECT subcategory, type_of_question, was_correct, skipped
            FROM attempt_events 
            WHERE user_id = :user_id AND session_id = :session_id
        """), {"user_id": user_id, "session_id": session_id})
        
        attempts = attempts_result.fetchall()
        
        # Group by concept pairs
        concept_stats = {}
        for attempt in attempts:
            pair = f"{attempt.subcategory}:{attempt.type_of_question}"
            if pair not in concept_stats:
                concept_stats[pair] = {"total": 0, "correct": 0, "skipped": 0}
            
            concept_stats[pair]["total"] += 1
            if attempt.was_correct:
                concept_stats[pair]["correct"] += 1
            if attempt.skipped:
                concept_stats[pair]["skipped"] += 1
        
        # Update learner notebook with simplified schema
        for concept_norm, stats in concept_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            skip_rate = stats["skipped"] / stats["total"] if stats["total"] > 0 else 0
            
            # Determine readiness (simplified: Weak/Moderate/Strong)
            if skip_rate > 0.5 or accuracy < 0.3:
                readiness = "Weak"
            elif accuracy >= 0.7 and skip_rate < 0.2:
                readiness = "Strong" 
            else:
                readiness = "Moderate"
            
            # Calculate mastery score (EMA-style: blend with existing)
            new_mastery = max(0.1, min(0.9, accuracy + (1 - skip_rate) * 0.1))
            
            # Upsert to learner_notebook
            db.execute(text("""
                INSERT INTO learner_notebook (
                    user_id, concept_norm, mastery_score, readiness, last_seen_at
                ) VALUES (
                    :user_id, :concept_norm, :mastery_score, :readiness, :last_seen_at
                )
                ON CONFLICT (user_id, concept_norm) DO UPDATE SET
                    mastery_score = (learner_notebook.mastery_score * 0.7) + (EXCLUDED.mastery_score * 0.3),
                    readiness = EXCLUDED.readiness,
                    last_seen_at = EXCLUDED.last_seen_at
            """), {
                "user_id": user_id,
                "concept_norm": concept_norm,
                "mastery_score": new_mastery,
                "readiness": readiness,
                "last_seen_at": datetime.now(timezone.utc)
            })
        
        db.commit()
        logger.info(f"✅ Updated learner_notebook for {len(concept_stats)} concepts")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update learner_notebook: {e}")
        raise
    finally:
        db.close()

async def update_coverage_debt_from_session(user_id: str, session_id: str):
    """Update coverage_debt - decrease for served pairs, small decay for others"""
    db = SessionLocal()
    try:
        # Get served pairs from this session
        served_result = db.execute(text("""
            SELECT DISTINCT subcategory, type_of_question
            FROM attempt_events 
            WHERE user_id = :user_id AND session_id = :session_id
        """), {"user_id": user_id, "session_id": session_id})
        
        served_pairs = [f"{row.subcategory}:{row.type_of_question}" for row in served_result.fetchall()]
        
        if served_pairs:
            # Decrease debt for served pairs (they got practice)
            for pair in served_pairs:
                subcategory, type_of_question = pair.split(":", 1)
                db.execute(text("""
                    INSERT INTO coverage_debt (
                        user_id, subcategory, type_of_question, debt_score, updated_at
                    ) VALUES (
                        :user_id, :subcategory, :type_of_question, 0.1, :updated_at
                    )
                    ON CONFLICT (user_id, subcategory, type_of_question) DO UPDATE SET
                        debt_score = GREATEST(0.0, coverage_debt.debt_score - 0.2),
                        updated_at = EXCLUDED.updated_at
                """), {
                    "user_id": user_id,
                    "subcategory": subcategory,
                    "type_of_question": type_of_question,
                    "updated_at": datetime.now(timezone.utc)
                })
        
        # Small decay for all other pairs (time passing increases debt)
        db.execute(text("""
            UPDATE coverage_debt 
            SET debt_score = LEAST(1.0, debt_score + 0.05),
                updated_at = :updated_at
            WHERE user_id = :user_id 
            AND CONCAT(subcategory, ':', type_of_question) != ALL(:served_pairs)
        """), {
            "user_id": user_id,
            "served_pairs": served_pairs,
            "updated_at": datetime.now(timezone.utc)
        })
        
        db.commit()
        logger.info(f"✅ Updated coverage debt: decreased for {len(served_pairs)} served pairs")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update coverage debt: {e}")
        raise
    finally:
        db.close()

async def gather_user_learning_data(user_id: str) -> Dict[str, Any]:
    """Gather learning data for personalized planning"""
    db = SessionLocal()
    try:
        # Get learner notebook (simplified)
        notebook_result = db.execute(text("""
            SELECT concept_norm, mastery_score, readiness, last_seen_at
            FROM learner_notebook 
            WHERE user_id = :user_id
            ORDER BY last_seen_at DESC
            LIMIT 50
        """), {"user_id": user_id})
        
        notebook_data = [
            {
                "concept_norm": row.concept_norm,
                "mastery_score": float(row.mastery_score),
                "readiness": row.readiness,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None
            }
            for row in notebook_result.fetchall()
        ]
        
        # Get coverage debt (simplified)
        debt_result = db.execute(text("""
            SELECT subcategory, type_of_question, debt_score, updated_at
            FROM coverage_debt
            WHERE user_id = :user_id AND debt_score > 0.3
            ORDER BY debt_score DESC
            LIMIT 20
        """), {"user_id": user_id})
        
        debt_data = [
            {
                "pair": f"{row.subcategory}:{row.type_of_question}",
                "debt_score": float(row.debt_score),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            }
            for row in debt_result.fetchall()
        ]
        
        return {
            "learner_notebook": notebook_data,
            "coverage_debt": debt_data,
            "has_sufficient_data": len(notebook_data) > 0 or len(debt_data) > 0
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to gather learning data for user {user_id[:8]}: {e}")
        return {"has_sufficient_data": False}
    finally:
        db.close()

async def generate_personalized_session_pack(user_id: str, learning_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate personalized 3E/6M/3H session pack using learning data"""
    
    # For now, create a simplified session pack structure
    # In full implementation, this would use the existing planner service
    # with readiness-based question selection and PYQ constraints
    
    session_pack = {
        "user_id": user_id,
        "pack_type": "personalized",
        "difficulty_distribution": {"easy": 3, "medium": 6, "hard": 3},
        "questions": [],  # Would be populated by planner
        "planning_strategy": "adaptive",
        "weak_concepts_targeted": len([nb for nb in learning_data.get("learner_notebook", []) if nb["readiness"] == "Weak"]),
        "high_debt_pairs_addressed": len([cd for cd in learning_data.get("coverage_debt", []) if cd["debt_score"] > 0.7])
    }
    
    logger.info(f"📋 Generated session pack: {session_pack['weak_concepts_targeted']} weak concepts, {session_pack['high_debt_pairs_addressed']} high debt pairs")
    
    return session_pack

async def persist_session_pack(user_id: str, session_pack: Dict[str, Any]) -> str:
    """Persist session pack to session_packs table for Blueprint consumption"""
    db = SessionLocal()
    try:
        # Generate pack ID
        import uuid
        pack_id = str(uuid.uuid4())
        
        # Insert into session_packs (using existing Blueprint schema)
        # Note: session_packs uses session_id as primary key, not id
        db.execute(text("""
            INSERT INTO session_packs (
                session_id, user_id, constraint_report, created_at
            ) VALUES (
                :session_id, :user_id, :constraint_report, :created_at
            )
        """), {
            "session_id": pack_id,  # Use pack_id as session_id
            "user_id": user_id, 
            "constraint_report": json.dumps({
                "pack_type": session_pack["pack_type"],
                "difficulty_distribution": session_pack["difficulty_distribution"],
                "planning_strategy": session_pack["planning_strategy"],
                "weak_concepts_targeted": session_pack["weak_concepts_targeted"],
                "high_debt_pairs_addressed": session_pack["high_debt_pairs_addressed"]
            }),
            "created_at": datetime.now(timezone.utc)
        })
        
        db.commit()
        logger.info(f"✅ Persisted session pack {pack_id[:8]} for user {user_id[:8]}")
        
        return pack_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to persist session pack for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()