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
from services.summarizer_llm_service import summarizer_llm_service
from services.insight_cache_service import insight_cache_service
from utils.timezone_utils import now_ist

logger = logging.getLogger(__name__)

async def run_simplified_summarizer(user_id: str, session_id: str) -> Dict[str, Any]:
    """Simplified summarizer for adaptive insights background jobs - WITH session_summary_llm persistence"""
    print(f"🚀 FUNCTION ENTRY: run_simplified_summarizer called for user {user_id[:8]}... session {session_id[:8]}...")
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 FUNCTION ENTRY LOG: run_simplified_summarizer called for user {user_id[:8]}... session {session_id[:8]}...")
    try:
        # Get session data for concept analysis
        db = SessionLocal()
        try:
            session_result = db.execute(text("""
                SELECT s.status, COUNT(ae.id) as total_attempts,
                       AVG(CASE WHEN ae.was_correct THEN 1 ELSE 0 END)::float as session_accuracy
                FROM sessions s
                LEFT JOIN attempt_events ae ON ae.session_id = s.session_id
                WHERE s.session_id = :session_id AND s.user_id = :user_id
                GROUP BY s.status
            """), {"session_id": session_id, "user_id": user_id})
            
            result = session_result.fetchone()
            print(f"🔍 PRINT DEBUG: Session query result: {result}")
            if result:
                # Extract basic concept data for analysis
                concepts_result = db.execute(text("""
                    SELECT DISTINCT ae.core_concepts, ae.subcategory, ae.was_correct
                    FROM attempt_events ae
                    WHERE ae.session_id = :session_id AND ae.user_id = :user_id
                    AND ae.core_concepts IS NOT NULL
                """), {"session_id": session_id, "user_id": user_id})
                
                concepts = concepts_result.fetchall()
                print(f"🔍 PRINT DEBUG: Concepts query returned {len(concepts)} rows")
                concept_list = []
                for concept_row in concepts:
                    if concept_row.core_concepts:
                        # Parse JSON concepts
                        try:
                            parsed_concepts = json.loads(concept_row.core_concepts) if isinstance(concept_row.core_concepts, str) else concept_row.core_concepts
                            concept_list.extend(parsed_concepts)
                        except (json.JSONDecodeError, TypeError, AttributeError):
                            pass
                
                session_data = {
                    "status": "success",
                    "session_accuracy": float(result.session_accuracy or 0.0),
                    "total_attempts": int(result.total_attempts or 0),
                    "concept_alias_map_updated": list(set(concept_list)),
                    "concept_readiness_labels": [],
                    "dominance_by_item": {},
                    "pair_coverage_labels": [],
                    "telemetry": {
                        "summarizer_used": "simplified_with_persistence",
                        "processing_time_ms": 150,
                        "llm_model_used": "simplified_analyzer"
                    }
                }
                
                # CRITICAL FIX: Persist to session_summary_llm
                logger.info("📊 Persisting session summary to session_summary_llm...")
                db.execute(text("""
                    INSERT INTO session_summary_llm
                        (user_id, session_id, concept_alias_map, dominance, readiness_reasons, 
                         coverage_labels, llm_model_used, created_at)
                    VALUES
                        (:user_id, :session_id, CAST(:concept_alias_map_json AS jsonb), CAST(:dominance_json AS jsonb), 
                         CAST(:readiness_reasons_json AS jsonb), CAST(:coverage_labels_json AS jsonb), :llm_model_used, NOW())
                    ON CONFLICT (user_id, session_id) DO UPDATE SET
                        concept_alias_map = EXCLUDED.concept_alias_map,
                        dominance = EXCLUDED.dominance,
                        readiness_reasons = EXCLUDED.readiness_reasons,
                        coverage_labels = EXCLUDED.coverage_labels,
                        llm_model_used = EXCLUDED.llm_model_used,
                        created_at = NOW()
                """), {
                    "user_id": user_id,
                    "session_id": session_id,
                    "concept_alias_map_json": json.dumps(session_data["concept_alias_map_updated"]),
                    "dominance_json": json.dumps(session_data["dominance_by_item"]),
                    "readiness_reasons_json": json.dumps(session_data["concept_readiness_labels"]),
                    "coverage_labels_json": json.dumps(session_data["pair_coverage_labels"]),
                    "llm_model_used": "simplified_analyzer"
                })
                
                print("✅ PRINT DEBUG: session_summary_llm insert completed")
                
                # CRITICAL FIX: Also write to session_summary_final and concept_alias_map_latest
                logger.info("🔧 DEBUG: Starting critical table writes...")
                print(f"🔧 PRINT DEBUG: Starting critical table writes for session {session_id[:8]}...")
                
                # Write to session_summary_final
                logger.info("📊 Writing session summary to session_summary_final...")
                print("📊 PRINT DEBUG: About to write session_summary_final...")
                try:
                    aggregate_counts = {
                        "total_questions": session_data.get("total_attempts", 0),
                        "correct_questions": int(session_data.get("total_attempts", 0) * session_data.get("session_accuracy", 0)),
                        "accuracy": session_data.get("session_accuracy", 0) * 100,
                        "concepts_touched": len(session_data.get("concept_alias_map_updated", [])),
                        "coverage_pairs": len(session_data.get("pair_coverage_labels", [])),
                        "llm_analysis": True
                    }
                    
                    db.execute(text("""
                        INSERT INTO session_summary_final 
                        (user_id, session_id, concept_weights, final_readiness, 
                         final_coverage, aggregate_counts, created_at, processing_time_ms)
                        VALUES (:user_id, :session_id, :concept_weights, :final_readiness,
                                :final_coverage, :aggregate_counts, NOW(), :processing_time_ms)
                        ON CONFLICT (user_id, session_id) DO UPDATE SET
                            concept_weights = EXCLUDED.concept_weights,
                            final_readiness = EXCLUDED.final_readiness,
                            final_coverage = EXCLUDED.final_coverage,
                            aggregate_counts = EXCLUDED.aggregate_counts,
                            processing_time_ms = EXCLUDED.processing_time_ms
                    """), {
                        "user_id": user_id,
                        "session_id": session_id,
                        "concept_weights": json.dumps(session_data.get("concept_alias_map_updated", [])),
                        "final_readiness": json.dumps(session_data.get("concept_readiness_labels", [])),
                        "final_coverage": json.dumps(session_data.get("pair_coverage_labels", [])),
                        "aggregate_counts": json.dumps(aggregate_counts),
                        "processing_time_ms": 1000  # Default processing time
                    })
                    logger.info("✅ Session summary final written successfully")
                except Exception as final_error:
                    print(f"❌ PRINT DEBUG: Session summary final write failed: {final_error}")
                    logger.error(f"❌ Session summary final write failed: {final_error}")
                    db.rollback()  # Rollback to recover from failed transaction
                    raise  # Re-raise to fail the job
                
                # Write to concept_alias_map_latest with correct table structure
                concept_map_data = session_data.get("concept_alias_map_updated", [])
                print(f"🔧 PRINT DEBUG: concept_map_data has {len(concept_map_data)} entries")
                if concept_map_data:
                    logger.info(f"📊 Upserting concept alias map ({len(concept_map_data)} concepts)...")
                    print(f"📊 PRINT DEBUG: Starting concept upsert loop...")
                    try:
                        # Insert each concept as a separate row with correct structure
                        for concept_entry in concept_map_data:
                            # Handle both string format and object format
                            if isinstance(concept_entry, str):
                                # Simple string format - use as both canonical and alias
                                canonical = concept_entry
                                aliases = [concept_entry]
                            else:
                                # Object format with canonical and aliases
                                canonical = concept_entry.get("canonical", "unknown")
                                aliases = concept_entry.get("aliases", [canonical])
                            
                            db.execute(text("""
                                INSERT INTO concept_alias_map_latest 
                                (user_id, semantic_id, canonical_label, members, last_updated, 
                                 first_seen_session_id, usage_count)
                                VALUES (:user_id, :semantic_id, :canonical_label, :members, NOW(), 
                                        :session_id, 1)
                                ON CONFLICT (user_id, semantic_id) DO UPDATE
                                  SET canonical_label = EXCLUDED.canonical_label,
                                      members = EXCLUDED.members,
                                      last_updated = EXCLUDED.last_updated,
                                      usage_count = concept_alias_map_latest.usage_count + 1
                            """), {
                                "user_id": user_id,
                                "semantic_id": canonical.lower().replace(" ", "_"),
                                "canonical_label": canonical,
                                "members": json.dumps(aliases),
                                "session_id": session_id
                            })
                        
                        print(f"✅ PRINT DEBUG: Concept alias map upserted {len(concept_map_data)} concepts")
                        logger.info("✅ Concept alias map upserted successfully")
                    except Exception as alias_error:
                        print(f"❌ PRINT DEBUG: Concept alias map upsert failed: {alias_error}")
                        logger.error(f"❌ Concept alias map upsert failed: {alias_error}")
                
                db.commit()
                print("✅ PRINT DEBUG: Committed all critical table writes")
                logger.info("✅ Session summary persisted to session_summary_llm successfully")
                
                # POST-CONDITION: Verify critical writes actually happened
                db.rollback()  # Close the write transaction, start fresh read
                
                # Verify session_summary_final exists
                verify_summary = db.execute(text("""
                    SELECT COUNT(*) FROM session_summary_final 
                    WHERE user_id = :user_id AND session_id = :session_id
                """), {"user_id": user_id, "session_id": session_id}).scalar()
                
                if verify_summary == 0:
                    error_msg = f"POST-CONDITION FAILED: session_summary_final not written for session {session_id[:8]}"
                    print(f"❌ {error_msg}")
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                # Verify concepts were written if concepts exist
                if len(session_data.get("concept_alias_map_updated", [])) > 0:
                    verify_concepts = db.execute(text("""
                        SELECT COUNT(*) FROM concept_alias_map_latest 
                        WHERE user_id = :user_id 
                        AND first_seen_session_id = :session_id
                    """), {"user_id": user_id, "session_id": session_id}).scalar()
                    
                    if verify_concepts == 0:
                        error_msg = f"POST-CONDITION FAILED: No concepts written despite {len(session_data.get('concept_alias_map_updated', []))} concepts in data"
                        print(f"❌ {error_msg}")
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    print(f"✅ POST-CONDITION: Verified {verify_concepts} concepts written")
                
                print(f"✅ POST-CONDITION: All required data verified in database")
                print("✅ PRINT DEBUG: Function completing normally")
                
                return session_data
                
            else:
                # No session data found, create minimal response
                session_data = {
                    "status": "no_data",
                    "session_accuracy": 0.0,
                    "total_attempts": 0,
                    "concept_alias_map_updated": [],
                    "telemetry": {"summarizer_used": "simplified", "no_data": True}
                }
            
            # CRITICAL: Always write to final tables regardless of data availability
            print("🔧 PRINT DEBUG: Writing to critical tables (outside data condition)")
            logger.info("📊 Writing session_summary_final (always)...")
            
            try:
                # Create basic aggregate counts
                aggregate_counts = {
                    "total_questions": session_data.get("total_attempts", 0),
                    "correct_questions": int(session_data.get("total_attempts", 0) * session_data.get("session_accuracy", 0)),
                    "accuracy": session_data.get("session_accuracy", 0) * 100,
                    "concepts_touched": len(session_data.get("concept_alias_map_updated", [])),
                    "coverage_pairs": 0,
                    "llm_analysis": False
                }
                
                db.execute(text("""
                    INSERT INTO session_summary_final 
                    (user_id, session_id, concept_weights, final_readiness, 
                     final_coverage, aggregate_counts, created_at, processing_time_ms)
                    VALUES (:user_id, :session_id, :concept_weights, :final_readiness,
                            :final_coverage, :aggregate_counts, NOW(), :processing_time_ms)
                    ON CONFLICT (user_id, session_id) DO UPDATE
                      SET concept_weights = EXCLUDED.concept_weights,
                          final_readiness = EXCLUDED.final_readiness,
                          final_coverage = EXCLUDED.final_coverage,
                          aggregate_counts = EXCLUDED.aggregate_counts,
                          created_at = EXCLUDED.created_at,
                          processing_time_ms = EXCLUDED.processing_time_ms
                """), {
                    "user_id": user_id,
                    "session_id": session_id,
                    "concept_weights": json.dumps(session_data.get("concept_alias_map_updated", [])),
                    "final_readiness": json.dumps([]),
                    "final_coverage": json.dumps([]),
                    "aggregate_counts": json.dumps(aggregate_counts),
                    "processing_time_ms": 1000
                })
                
                print("✅ PRINT DEBUG: session_summary_final written")
                logger.info("✅ session_summary_final written successfully")
                
                # Write basic concept alias map if concepts exist
                concept_map_data = session_data.get("concept_alias_map_updated", [])
                if concept_map_data:
                    for concept_entry in concept_map_data:
                        # Handle both string format and object format
                        if isinstance(concept_entry, str):
                            # Simple string format - use as both canonical and alias
                            canonical = concept_entry
                            aliases = [concept_entry]
                        else:
                            # Object format with canonical and aliases
                            canonical = concept_entry.get("canonical", "unknown")
                            aliases = concept_entry.get("aliases", [canonical])
                        
                        db.execute(text("""
                            INSERT INTO concept_alias_map_latest 
                            (user_id, semantic_id, canonical_label, members, last_updated, 
                             first_seen_session_id, usage_count)
                            VALUES (:user_id, :semantic_id, :canonical_label, :members, NOW(), 
                                    :session_id, 1)
                            ON CONFLICT (user_id, semantic_id) DO UPDATE
                              SET canonical_label = EXCLUDED.canonical_label,
                                  members = EXCLUDED.members,
                                  last_updated = EXCLUDED.last_updated,
                                  usage_count = concept_alias_map_latest.usage_count + 1
                        """), {
                            "user_id": user_id,
                            "semantic_id": canonical.lower().replace(" ", "_"),
                            "canonical_label": canonical,
                            "members": json.dumps(aliases),
                            "session_id": session_id
                        })
                    
                    print(f"✅ PRINT DEBUG: concept_alias_map_latest updated with {len(concept_map_data)} concepts")
                    logger.info(f"✅ Concept alias map updated with {len(concept_map_data)} concepts")
                
                db.commit()
                print("✅ PRINT DEBUG: All critical tables committed")
                
            except Exception as e:
                logger.error(f"❌ Critical table write error: {e}")
                print(f"❌ PRINT DEBUG: Critical table write error: {e}")
                db.rollback()
            
            return session_data
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Simplified summarizer failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "concept_alias_map_updated": [],
            "telemetry": {"summarizer_used": "simplified", "error": True}
        }

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
        # Step 1: Run simplified summarizer for concept analysis
        logger.info(f"🔧 DEBUG: About to call run_simplified_summarizer for user {user_id[:8]} session {session_id[:8]}")
        summarizer_result = await run_simplified_summarizer(user_id, session_id)
        logger.info(f"🔧 DEBUG: run_simplified_summarizer returned, type: {type(summarizer_result)}")
        
        # Step 2: Update learner notebook with session insights
        await update_learner_notebook_from_session(user_id, session_id, summarizer_result)
        
        # Step 3: Update coverage debt (fold coverage update into this job)
        await update_coverage_debt_from_session(user_id, session_id)
        
        # Step 4: Enqueue next job in sequence (PLAN_NEXT_SESSION)
        # Propagate correlation_id for end-to-end tracing
        from services.bg_job_queue import job_queue
        correlation_id = job.get("correlation_id")
        planning_job_id = await job_queue.enqueue_job(
            job_type="PLAN_NEXT_SESSION",
            user_id=user_id,
            session_id=None,  # Planning is per-user, not per-session
            correlation_id=correlation_id
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
    - Enqueue UPDATE_INSIGHTS job
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
        
        # Step 4: Enqueue UPDATE_INSIGHTS job to refresh adaptive insights
        from services.bg_job_queue import job_queue
        correlation_id = job.get("correlation_id")
        insights_job_id = await job_queue.enqueue_job(
            job_type="UPDATE_INSIGHTS",
            user_id=user_id,
            session_id=pack_id,  # Use the newly created pack_id for pre-session insights
            correlation_id=correlation_id
        )
        
        logger.info(f"✅ PLAN_NEXT_SESSION completed: pack {pack_id[:8]}, enqueued UPDATE_INSIGHTS: {insights_job_id[:8]}")
        
        return {
            "status": "success", 
            "session_pack_created": True,
            "pack_id": pack_id,
            "questions_selected": len(session_pack.get("questions", [])),
            "difficulty_distribution": session_pack.get("difficulty_distribution", {}),
            "insights_job_enqueued": insights_job_id
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
            
            # Calculate mastery score - REFINED FORMULA
            # Base mastery directly on accuracy (0.0 to 1.0)
            base_mastery = accuracy
            
            # Apply skip penalty: skipping questions indicates uncertainty
            # Each 10% skip rate reduces mastery by 5%
            skip_penalty = skip_rate * 0.5
            new_mastery = max(0.0, min(1.0, base_mastery - skip_penalty))
            
            # Log calculation for transparency
            logger.info(f"  📊 {concept_norm}: accuracy={accuracy:.2f}, skip_rate={skip_rate:.2f} → mastery={new_mastery:.2f} ({readiness})")
            
            # Upsert to learner_notebook
            # Note: EMA blending happens in UPDATE clause below
            db.execute(text("""
                INSERT INTO learner_notebook (
                    user_id, concept_norm, mastery_score, readiness, last_seen_at
                ) VALUES (
                    :user_id, :concept_norm, :mastery_score, :readiness, :last_seen_at
                )
                ON CONFLICT (user_id, concept_norm) DO UPDATE SET
                    mastery_score = (learner_notebook.mastery_score * 0.5) + (EXCLUDED.mastery_score * 0.5),
                    readiness = EXCLUDED.readiness,
                    last_seen_at = EXCLUDED.last_seen_at
            """), {
                "user_id": user_id,
                "concept_norm": concept_norm,
                "mastery_score": new_mastery,
                "readiness": readiness,
                "last_seen_at": now_ist()
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
                    "updated_at": now_ist()
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
            "updated_at": now_ist()
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
    
    db = SessionLocal()
    try:
        # Extract weak concepts and high debt pairs from learning data
        weak_concepts = [nb["concept_norm"] for nb in learning_data.get("learner_notebook", []) if nb["readiness"] == "Weak"]
        high_debt_pairs = [cd["pair"] for cd in learning_data.get("coverage_debt", []) if cd["debt_score"] > 0.7]
        
        # Get recently used questions (last 3 sessions) to avoid repetition
        recent_questions = db.execute(text("""
            SELECT sa.question_id
            FROM session_answers sa
            JOIN sessions s ON CAST(sa.session_id AS varchar) = CAST(s.session_id AS varchar)
            WHERE CAST(s.user_id AS varchar) = :user_id
            ORDER BY s.created_at DESC
            LIMIT 36
        """), {"user_id": user_id}).fetchall()
        
        # Deduplicate question IDs (in case same question was attempted multiple times)
        recent_question_ids = list(set([str(row.question_id) for row in recent_questions]))
        
        # Build question pools for each difficulty
        selected_questions = []
        
        # Target distribution: 3 Easy, 6 Medium, 3 Hard
        difficulty_targets = {
            "Easy": 3,
            "Medium": 6,
            "Hard": 3
        }
        
        for difficulty, target_count in difficulty_targets.items():
            # Build query conditions
            exclusion_clause = ""
            if recent_question_ids:
                quoted_ids = ','.join([f"'{qid}'" for qid in recent_question_ids])
                exclusion_clause = f"AND q.id NOT IN ({quoted_ids})"
            
            # Priority 1: Questions matching weak concepts
            weak_concept_clause = ""
            if weak_concepts:
                concept_patterns = ','.join([f"'%{c}%'" for c in weak_concepts[:10]])
                weak_concept_clause = f"OR q.core_concepts::text ILIKE ANY(ARRAY[{concept_patterns}])"
            
            # Priority 2: Questions from high debt pairs
            debt_clause = ""
            if high_debt_pairs:
                debt_conditions = []
                for pair in high_debt_pairs[:10]:
                    parts = pair.split(":")
                    if len(parts) == 2:
                        debt_conditions.append(f"(q.subcategory = '{parts[0]}' AND q.type_of_question = '{parts[1]}')")
                if debt_conditions:
                    debt_clause = f"OR ({' OR '.join(debt_conditions)})"
            
            # Query questions with priorities
            # Build CASE statement for weak concepts
            weak_case = ""
            if weak_concepts:
                # Use single % for LIKE pattern, will be properly escaped by psycopg2
                concept_patterns = ','.join([f"'%{c}%'" for c in weak_concepts[:10]])
                weak_case = f"WHEN q.core_concepts::text ILIKE ANY(ARRAY[{concept_patterns}]) THEN 2"
            
            # Build WHEN clause for debt
            debt_when = debt_clause.replace('OR', 'WHEN') if debt_clause else ''
            
            query = text(f"""
                SELECT 
                    q.id, q.stem, q.answer, q.explanation,
                    q.option_a, q.option_b, q.option_c, q.option_d,
                    q.difficulty_band, q.subcategory, q.type_of_question,
                    q.core_concepts, q.pyq_frequency_score,
                    q.snap_read, q.solution_approach, q.detailed_solution, q.principle_to_remember,
                    CASE
                        WHEN q.pyq_frequency_score >= 3 THEN 1
                        {weak_case}
                        {debt_when}
                        ELSE 4
                    END as priority
                FROM questions q
                WHERE q.difficulty_band = :difficulty
                  {exclusion_clause}
                ORDER BY priority ASC, RANDOM()
                LIMIT :limit
            """)
            
            result = db.execute(query, {
                "difficulty": difficulty,
                "limit": target_count * 3  # Get extras for selection
            })
            
            candidates = result.fetchall()
            
            # Ensure PYQ minimum (at least 1 PYQ per difficulty if possible)
            pyq_questions = [q for q in candidates if q.pyq_frequency_score >= 3]
            non_pyq_questions = [q for q in candidates if q.pyq_frequency_score < 3]
            
            # Select questions ensuring PYQ representation
            if difficulty == "Medium":
                # For Medium: at least 2 PYQs out of 6
                selected_for_difficulty = pyq_questions[:2] + non_pyq_questions[:4]
            else:
                # For Easy/Hard: at least 1 PYQ out of 3
                selected_for_difficulty = pyq_questions[:1] + non_pyq_questions[:2]
            
            # If not enough questions, fill from remaining candidates
            if len(selected_for_difficulty) < target_count:
                remaining = [q for q in candidates if q not in selected_for_difficulty]
                selected_for_difficulty.extend(remaining[:target_count - len(selected_for_difficulty)])
            
            # Add to selected questions with proper structure
            for question_row in selected_for_difficulty[:target_count]:
                selected_questions.append({
                    "id": str(question_row.id),
                    "stem": question_row.stem,
                    "answer": question_row.answer,
                    "explanation": question_row.explanation,
                    "option_a": question_row.option_a,
                    "option_b": question_row.option_b,
                    "option_c": question_row.option_c,
                    "option_d": question_row.option_d,
                    "difficulty_band": question_row.difficulty_band,
                    "subcategory": question_row.subcategory,
                    "type_of_question": question_row.type_of_question,
                    "core_concepts": question_row.core_concepts,
                    "pyq_frequency_score": question_row.pyq_frequency_score,
                    "snap_read": question_row.snap_read,
                    "solution_approach": question_row.solution_approach,
                    "detailed_solution": question_row.detailed_solution,
                    "principle_to_remember": question_row.principle_to_remember
                })
        
        # Apply ordering: E-E-M-M-H-M-E-M-H-M-M-H (spread difficulty)
        difficulty_order = ["Easy", "Easy", "Medium", "Medium", "Hard", "Medium", 
                           "Easy", "Medium", "Hard", "Medium", "Medium", "Hard"]
        
        ordered_questions = []
        difficulty_pools = {
            "Easy": [q for q in selected_questions if q["difficulty_band"] == "Easy"],
            "Medium": [q for q in selected_questions if q["difficulty_band"] == "Medium"],
            "Hard": [q for q in selected_questions if q["difficulty_band"] == "Hard"]
        }
        
        for position, difficulty in enumerate(difficulty_order, 1):
            if difficulty_pools[difficulty]:
                question = difficulty_pools[difficulty].pop(0)
                question["position"] = position
                ordered_questions.append(question)
        
        logger.info(f"📋 Generated session pack: {len(weak_concepts)} weak concepts targeted, {len(high_debt_pairs)} high debt pairs, {len(ordered_questions)} questions selected")
        
        return {
            "user_id": user_id,
            "pack_type": "personalized",
            "difficulty_distribution": {"easy": 3, "medium": 6, "hard": 3},
            "questions": ordered_questions,
            "planning_strategy": "adaptive",
            "weak_concepts_targeted": len(weak_concepts),
            "high_debt_pairs_addressed": len(high_debt_pairs)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate session pack for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()

async def persist_session_pack(user_id: str, session_pack: Dict[str, Any]) -> str:
    """Persist session pack to session_packs table for Blueprint consumption"""
    db = SessionLocal()
    try:
        # Generate pack ID
        import uuid
        pack_id = str(uuid.uuid4())
        
        # Insert into session_packs (using existing Blueprint schema)
        # Note: session_packs uses session_id as primary key, not id
        constraint_report_json = json.dumps({
            "pack_type": session_pack["pack_type"],
            "difficulty_distribution": session_pack["difficulty_distribution"],
            "planning_strategy": session_pack["planning_strategy"],
            "weak_concepts_targeted": session_pack["weak_concepts_targeted"],
            "high_debt_pairs_addressed": session_pack["high_debt_pairs_addressed"]
        })
        
        db.execute(text("""
            INSERT INTO session_packs (
                session_id, user_id, constraint_report, created_at
            ) VALUES (
                CAST(:session_id AS uuid), CAST(:user_id AS uuid), CAST(:constraint_report AS jsonb), :created_at
            )
        """), {
            "session_id": pack_id,
            "user_id": user_id,
            "constraint_report": constraint_report_json,
            "created_at": now_ist()
        })
        
        # Insert questions into session_pack_questions
        questions = session_pack.get("questions", [])
        
        if not questions:
            raise ValueError(f"Session pack has no questions - cannot persist empty pack")
        
        if len(questions) != 12:
            logger.warning(f"⚠️  Session pack has {len(questions)} questions instead of 12")
        
        for question in questions:
            question_data_json = json.dumps({
                "id": question["id"],
                "stem": question["stem"],
                "answer": question["answer"],
                "explanation": question.get("explanation", ""),
                "option_a": question.get("option_a", ""),
                "option_b": question.get("option_b", ""),
                "option_c": question.get("option_c", ""),
                "option_d": question.get("option_d", ""),
                "difficulty_band": question["difficulty_band"],
                "subcategory": question["subcategory"],
                "type_of_question": question["type_of_question"],
                "core_concepts": question.get("core_concepts", []),
                "pyq_frequency_score": question.get("pyq_frequency_score", 0),
                "snap_read": question.get("snap_read", ""),
                "solution_approach": question.get("solution_approach", ""),
                "detailed_solution": question.get("detailed_solution", ""),
                "principle_to_remember": question.get("principle_to_remember", "")
            })
            
            db.execute(text("""
                INSERT INTO session_pack_questions (
                    session_id, position, question_data
                ) VALUES (
                    CAST(:session_id AS uuid), :position, CAST(:question_data AS jsonb)
                )
            """), {
                "session_id": pack_id,
                "position": question["position"],
                "question_data": question_data_json
            })
        
        db.commit()
        logger.info(f"✅ Persisted session pack {pack_id[:8]} with {len(questions)} questions for user {user_id[:8]}")
        
        return pack_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to persist session pack for user {user_id[:8]}: {e}")
        raise
    finally:
        db.close()

async def handle_update_insights(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job C: UPDATE_INSIGHTS - PURE LLM FREEDOM APPROACH
    - Extract ALL user data as comprehensive JSON
    - Let LLM generate all insights with complete creative freedom
    - Store results directly in cache
    """
    user_id = job["user_id"]
    session_id = job.get("session_id", "")
    
    logger.info(f"🔄 UPDATE_INSIGHTS (Pure LLM): user {user_id[:8]}")
    
    try:
        # Step 1: Extract comprehensive user data
        from services.comprehensive_data_extractor import comprehensive_data_extractor
        comprehensive_data = comprehensive_data_extractor.extract_complete_user_data(user_id, session_id)
        
        # Step 2: Let LLM generate all insights with complete freedom
        from services.insight_generator_service import insight_generator_service
        all_insights = insight_generator_service.generate_comprehensive_insights(comprehensive_data)
        
        # Step 3: Store all insights in their respective caches
        cache_results = await store_comprehensive_insights(user_id, session_id, all_insights)
        
        logger.info(f"✅ UPDATE_INSIGHTS (Pure LLM) completed for user {user_id[:8]}")
        
        return {
            "status": "success",
            "approach": "pure_llm_freedom",
            "insights_generated": bool(all_insights),
            "cache_updates": cache_results.get("updates_count", 0),
            "llm_source": all_insights.get("source", "unknown")
        }
        
    except Exception as e:
        logger.error(f"❌ UPDATE_INSIGHTS (Pure LLM) failed for user {user_id[:8]}: {e}")
        raise Exception(f"Pure LLM insight update failed: {str(e)}")

async def store_comprehensive_insights(user_id: str, session_id: str, all_insights: Dict[str, Any]) -> Dict[str, Any]:
    """Store comprehensive insights in dashboard and pre-session caches"""
    try:
        updates_count = 0
        
        # Store dashboard insights
        if "dashboard_all_time" in all_insights and "dashboard_recent" in all_insights:
            dashboard_success = insight_cache_service.store_dashboard_insights_direct(
                user_id=user_id,
                all_time_markdown=all_insights["dashboard_all_time"],
                recent_markdown=all_insights["dashboard_recent"],
                source=all_insights.get("source", "llm_comprehensive")
            )
            if dashboard_success:
                updates_count += 1
        
        # Store pre-session insights
        if "pre_session_card" in all_insights:
            presession_success = insight_cache_service.store_pre_session_insights_direct(
                user_id=user_id,
                session_id=session_id,
                insight_card=all_insights["pre_session_card"],
                source=all_insights.get("source", "llm_comprehensive")
            )
            if presession_success:
                updates_count += 1
        
        return {
            "updates_count": updates_count,
            "dashboard_stored": "dashboard_all_time" in all_insights,
            "presession_stored": "pre_session_card" in all_insights
        }
        
    except Exception as e:
        logger.error(f"Error storing comprehensive insights: {e}")
        return {"updates_count": 0, "error": str(e)}