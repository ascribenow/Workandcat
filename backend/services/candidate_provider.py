#!/usr/bin/env python3
"""
Candidate Provider for Adaptive Logic
Manages question pool selection with normal and cold start modes
"""

import logging
import random
from typing import Dict, List, Any, Optional, Set, Tuple
from database import SessionLocal, Question
from sqlalchemy import select, and_, text
from services.deterministic_kernels import QuestionCandidate

logger = logging.getLogger(__name__)

class CandidateProvider:
    """Manages question candidate pools for session planning"""
    
    def __init__(self):
        self.valid_pairs: Set[str] = set()
        self.known_concepts: Set[str] = set()
        self._load_taxonomy()
    
    def _load_taxonomy(self):
        """Load canonical taxonomy and known concepts on service start"""
        db = SessionLocal()
        try:
            # Load valid subcategory:type_of_question pairs
            pairs = db.execute(text("""
                SELECT DISTINCT subcategory || ':' || type_of_question as pair
                FROM questions 
                WHERE is_active = true 
                AND subcategory IS NOT NULL 
                AND type_of_question IS NOT NULL
            """)).fetchall()
            
            self.valid_pairs = {pair[0] for pair in pairs}
            logger.info(f"Loaded {len(self.valid_pairs)} valid taxonomy pairs")
            
            # Load known concepts - handle both JSONB and TEXT core_concepts
            try:
                # Try JSONB first
                concepts = db.execute(text("""
                    SELECT DISTINCT jsonb_array_elements_text(core_concepts::jsonb) as concept
                    FROM questions
                    WHERE is_active = true 
                    AND core_concepts IS NOT NULL
                """)).fetchall()
            except:
                # Fallback: parse JSON strings manually
                concept_rows = db.execute(text("""
                    SELECT DISTINCT core_concepts
                    FROM questions
                    WHERE is_active = true 
                    AND core_concepts IS NOT NULL
                """)).fetchall()
                
                concepts = []
                for row in concept_rows:
                    try:
                        import json
                        if isinstance(row[0], str):
                            concept_list = json.loads(row[0])
                        else:
                            concept_list = row[0]
                        
                        for concept in concept_list:
                            concepts.append((concept,))
                    except:
                        continue
            
            self.known_concepts = {concept[0] for concept in concepts}
            logger.info(f"Loaded {len(self.known_concepts)} known concepts")
            
        except Exception as e:
            logger.error(f"Error loading taxonomy: {e}")
            # Use empty sets as fallback
            self.valid_pairs = set()
            self.known_concepts = set()
        finally:
            db.close()
    
    def _fetch_active_questions(self, excluded_question_ids: Optional[Set[str]] = None) -> List[QuestionCandidate]:
        """Fetch all active questions as candidates"""
        db = SessionLocal()
        try:
            query = select(Question).where(Question.is_active == True)
            
            if excluded_question_ids:
                query = query.where(~Question.id.in_(excluded_question_ids))
            
            questions = db.execute(query).scalars().all()
            
            candidates = []
            for q in questions:
                try:
                    # Parse core concepts
                    if isinstance(q.core_concepts, list):
                        concepts = q.core_concepts
                    elif isinstance(q.core_concepts, str):
                        import json
                        concepts = json.loads(q.core_concepts)
                    else:
                        concepts = []
                    
                    candidate = QuestionCandidate(
                        question_id=q.id,
                        difficulty_band=q.difficulty_band or 'Medium',
                        subcategory=q.subcategory or 'Unknown',
                        type_of_question=q.type_of_question or 'Unknown',
                        core_concepts=tuple(concepts),  # Convert to tuple
                        pyq_frequency_score=float(q.pyq_frequency_score) if q.pyq_frequency_score else 0.5,
                        pair=f"{q.subcategory}:{q.type_of_question}" if q.subcategory and q.type_of_question else "Unknown:Unknown"
                    )
                    candidates.append(candidate)
                    
                except Exception as e:
                    logger.warning(f"Error processing question {q.id}: {e}")
                    continue
            
            logger.debug(f"Fetched {len(candidates)} active question candidates")
            return candidates
            
        finally:
            db.close()
    
    def _group_by_difficulty(self, candidates: List[QuestionCandidate]) -> Dict[str, List[QuestionCandidate]]:
        """Group candidates by difficulty band"""
        groups = {"Easy": [], "Medium": [], "Hard": []}
        
        for candidate in candidates:
            band = candidate.difficulty_band
            if band in groups:
                groups[band].append(candidate)
            else:
                logger.warning(f"Unknown difficulty band: {band}")
                groups["Medium"].append(candidate)  # Default to Medium
        
        return groups
    
    def preflight_feasible(self, candidates: List[QuestionCandidate]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if candidate pool can satisfy basic constraints
        
        Args:
            candidates: List of question candidates
            
        Returns:
            (is_feasible, feasibility_details)
        """
        # Group by difficulty band
        by_band = {"Easy": [], "Medium": [], "Hard": []}
        for candidate in candidates:
            band = candidate.difficulty_band
            if band in by_band:
                by_band[band].append(candidate)
        
        # Check difficulty distribution feasibility
        target_distribution = {"Easy": 3, "Medium": 6, "Hard": 3}
        feasible = True
        issues = []
        
        for band, target_count in target_distribution.items():
            available = len(by_band[band])
            if available < target_count:
                feasible = False
                issues.append(f"Insufficient {band} questions: need {target_count}, have {available}")
        
        # Check PYQ score requirements
        pyq_1_0_count = sum(1 for c in candidates if c.pyq_frequency_score >= 1.0)
        pyq_1_5_count = sum(1 for c in candidates if c.pyq_frequency_score >= 1.5)
        
        if pyq_1_0_count < 2:
            feasible = False
            issues.append(f"Insufficient PYQ ≥1.0 questions: need 2, have {pyq_1_0_count}")
        
        if pyq_1_5_count < 2:
            feasible = False
            issues.append(f"Insufficient PYQ ≥1.5 questions: need 2, have {pyq_1_5_count}")
        
        details = {
            "feasible": feasible,
            "issues": issues,
            "band_counts": {band: len(questions) for band, questions in by_band.items()},
            "pyq_counts": {">=1.0": pyq_1_0_count, ">=1.5": pyq_1_5_count},
            "total_candidates": len(candidates)
        }
        
        if feasible:
            logger.debug(f"Preflight feasible: {len(candidates)} candidates")
        else:
            logger.warning(f"Preflight infeasible: {issues}")
        
        return feasible, details
    
    def build_candidate_pool(self, 
                           user_id: str,
                           readiness_levels: Optional[Dict[str, str]] = None,
                           coverage_debt: Optional[Dict[str, float]] = None,
                           k_pool_per_band: int = None) -> Tuple[List[QuestionCandidate], Dict[str, Any]]:
        """
        Build adaptive candidate pool based on readiness and coverage
        
        Args:
            user_id: User identifier
            readiness_levels: Map of semantic_id -> readiness level  
            coverage_debt: Map of pair -> debt score
            k_pool_per_band: Pool size per difficulty band (defaults to config value)
            
        Returns:
            (candidates, metadata) where candidates is the filtered pool
        """
        # Import config and set default
        from .pipeline import AdaptiveConfig
        if k_pool_per_band is None:
            k_pool_per_band = AdaptiveConfig.K_POOL_PER_BAND
            
        logger.info(f"Building adaptive candidate pool for user {user_id[:8]}... (K={k_pool_per_band})")
        
        # Get user's recent question history to avoid repetition
        excluded_questions = self._get_recent_questions(user_id, sessions_lookback=3)
        
        # Fetch all available candidates
        all_candidates = self._fetch_active_questions(excluded_questions)
        
        # TELEMETRY: Log data source and PYQ availability  
        pyq_15_available = sum(1 for c in all_candidates if c.pyq_frequency_score >= 1.5)
        pyq_10_available = sum(1 for c in all_candidates if c.pyq_frequency_score >= 1.0)
        logger.info(f"📊 TELEMETRY: provider_source=questions available_pyq15_in_pool={pyq_15_available} available_pyq10_in_pool={pyq_10_available} total_active={len(all_candidates)}")
        
        if not all_candidates:
            logger.warning("No active questions available")
            return [], {"error": "no_active_questions"}
        
        # Group by difficulty
        grouped = self._group_by_difficulty(all_candidates)
        
        # Select candidates per difficulty band using adaptive criteria
        selected_candidates = []
        
        for band in ["Easy", "Medium", "Hard"]:
            band_candidates = grouped[band]
            
            if not band_candidates:
                logger.warning(f"No {band} questions available")
                continue
            
            # Apply adaptive selection logic
            if readiness_levels and coverage_debt:
                band_selected = self._adaptive_selection(
                    band_candidates, readiness_levels, coverage_debt, k_pool_per_band
                )
            else:
                # Fallback to random selection if no adaptive data
                band_selected = random.sample(
                    band_candidates, 
                    min(k_pool_per_band, len(band_candidates))
                )
            
            selected_candidates.extend(band_selected)
            logger.debug(f"Selected {len(band_selected)} {band} questions")
        
        # Check feasibility and expand if needed
        feasible, feasibility_details = self.preflight_feasible(selected_candidates)
        
        # TELEMETRY: Log selected PYQ counts
        selected_pyq_15 = sum(1 for c in selected_candidates if c.pyq_frequency_score >= 1.5)
        selected_pyq_10 = sum(1 for c in selected_candidates if c.pyq_frequency_score >= 1.0)
        logger.info(f"📊 TELEMETRY: selected_pyq15_in_pool={selected_pyq_15} selected_pyq10_in_pool={selected_pyq_10} pool_feasible={feasible}")
        
        if not feasible:
            logger.warning("Initial pool not feasible, attempting expansion")
            expanded_candidates, expansion_details = self.adaptively_expand_pool(
                selected_candidates, k_pool_per_band
            )
            
            metadata = {
                "selection_strategy": "adaptive",
                "initial_size": len(selected_candidates),
                "expanded_size": len(expanded_candidates),
                "pool_expanded": True,
                "feasibility": feasibility_details,
                "expansion": expansion_details
            }
            
            return expanded_candidates, metadata
        
        metadata = {
            "selection_strategy": "adaptive",
            "pool_size": len(selected_candidates),
            "pool_expanded": False,
            "feasibility": feasibility_details,
            "excluded_questions": len(excluded_questions) if excluded_questions else 0
        }
        
        return selected_candidates, metadata
    
    def _adaptive_selection(self, 
                          candidates: List[QuestionCandidate],
                          readiness_levels: Dict[str, str],
                          coverage_debt: Dict[str, float],
                          k_pool: int) -> List[QuestionCandidate]:
        """Select candidates using adaptive criteria (readiness + coverage)"""
        
        # Score each candidate based on readiness and coverage
        scored_candidates = []
        
        for candidate in candidates:
            score = 0.0
            
            # Readiness scoring: prioritize Weak concepts for practice
            for concept in candidate.core_concepts:
                # This would need semantic_id mapping in real implementation
                # For now, use concept directly as placeholder
                readiness = readiness_levels.get(concept, "Moderate")
                
                if readiness == "Weak":
                    score += 1.0  # High priority for weak concepts
                elif readiness == "Moderate":
                    score += 0.6
                else:  # Strong
                    score += 0.3
            
            # Coverage scoring: prioritize high-debt pairs
            pair_debt = coverage_debt.get(candidate.pair, 0.5)  # Default moderate debt
            score += pair_debt
            
            scored_candidates.append((candidate, score))
        
        # Sort by score (highest first) and select top K
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        selected = [candidate for candidate, score in scored_candidates[:k_pool]]
        
        logger.debug(f"Adaptive selection: scored {len(candidates)}, selected {len(selected)}")
        return selected
    
    def adaptively_expand_pool(self, 
                             initial_pool: List[QuestionCandidate],
                             k_pool_per_band: int) -> Tuple[List[QuestionCandidate], Dict[str, Any]]:
        """
        Expand pool with backoff strategy: K→2K→4K until feasible
        
        Args:
            initial_pool: Initial candidate pool
            k_pool_per_band: Base pool size per band
            
        Returns:
            (expanded_pool, expansion_details)
        """
        logger.info("Attempting pool expansion with backoff strategy")
        
        expansion_attempts = []
        current_pool = initial_pool
        
        # Try K→2K→4K expansion
        for multiplier in [2, 4]:
            expanded_k = k_pool_per_band * multiplier
            logger.debug(f"Trying expansion with K={expanded_k}")
            
            # Fetch larger pool
            all_candidates = self._fetch_active_questions()
            grouped = self._group_by_difficulty(all_candidates)
            
            expanded_pool = []
            for band in ["Easy", "Medium", "Hard"]:
                band_candidates = grouped[band]
                selected_count = min(expanded_k, len(band_candidates))
                selected = random.sample(band_candidates, selected_count)
                expanded_pool.extend(selected)
            
            # Check feasibility
            feasible, details = self.preflight_feasible(expanded_pool)
            
            attempt_info = {
                "multiplier": multiplier,
                "k_value": expanded_k,
                "pool_size": len(expanded_pool),
                "feasible": feasible,
                "details": details
            }
            expansion_attempts.append(attempt_info)
            
            if feasible:
                logger.info(f"Pool expansion successful with K={expanded_k}")
                return expanded_pool, {
                    "success": True,
                    "final_multiplier": multiplier,
                    "final_k": expanded_k,
                    "final_size": len(expanded_pool),
                    "attempts": expansion_attempts
                }
            
            current_pool = expanded_pool
        
        # If still not feasible, return best attempt
        logger.warning("Pool expansion failed to achieve feasibility")
        return current_pool, {
            "success": False,
            "final_size": len(current_pool),
            "attempts": expansion_attempts
        }
    
    def build_coldstart_pool(self, 
                           user_id: str,
                           diversity_pool_size: int = 100) -> Tuple[List[QuestionCandidate], Dict[str, Any]]:
        """
        Build diversity-first candidate pool for cold start users
        
        Prioritizes:
        - Unseen concept/pair combinations
        - Broad exposure across taxonomy
        - Meeting basic constraints (3/6/3, PYQ minima)
        
        Args:
            user_id: User identifier (new user)
            diversity_pool_size: Size of diversity pool
            
        Returns:
            (candidates, metadata) for cold start selection
        """
        logger.info(f"Building cold start diversity pool for user {user_id[:8]}... (size={diversity_pool_size})")
        
        # For new users, no exclusions needed
        all_candidates = self._fetch_active_questions()
        
        # TELEMETRY: Log data source and PYQ availability for cold start
        pyq_15_available = sum(1 for c in all_candidates if c.pyq_frequency_score >= 1.5)
        pyq_10_available = sum(1 for c in all_candidates if c.pyq_frequency_score >= 1.0)
        logger.info(f"📊 TELEMETRY COLDSTART: provider_source=questions available_pyq15_in_pool={pyq_15_available} available_pyq10_in_pool={pyq_10_available} total_active={len(all_candidates)}")
        
        if not all_candidates:
            return [], {"error": "no_active_questions"}
        
        # Group by pair for diversity
        pair_groups = {}
        for candidate in all_candidates:
            pair = candidate.pair
            if pair not in pair_groups:
                pair_groups[pair] = []
            pair_groups[pair].append(candidate)
        
        # Select diverse candidates: aim for 5+ distinct pairs minimum
        diverse_candidates = []
        pairs_included = set()
        
        # First pass: one question from each pair (up to diversity_pool_size)
        pair_list = list(pair_groups.keys())
        random.shuffle(pair_list)
        
        for pair in pair_list:
            if len(diverse_candidates) >= diversity_pool_size:
                break
                
            # Select one random question from this pair
            candidate = random.choice(pair_groups[pair])
            diverse_candidates.append(candidate)
            pairs_included.add(pair)
        
        # Second pass: fill remaining slots randomly from all candidates
        remaining_candidates = [c for c in all_candidates if c not in diverse_candidates]
        remaining_slots = diversity_pool_size - len(diverse_candidates)
        
        if remaining_slots > 0 and remaining_candidates:
            additional = random.sample(
                remaining_candidates, 
                min(remaining_slots, len(remaining_candidates))
            )
            diverse_candidates.extend(additional)
        
        # Check feasibility
        feasible, feasibility_details = self.preflight_feasible(diverse_candidates)
        
        # TELEMETRY: Log cold start selection results
        selected_pyq_15 = sum(1 for c in diverse_candidates if c.pyq_frequency_score >= 1.5)
        selected_pyq_10 = sum(1 for c in diverse_candidates if c.pyq_frequency_score >= 1.0)
        logger.info(f"📊 TELEMETRY COLDSTART: selected_pyq15_in_pool={selected_pyq_15} selected_pyq10_in_pool={selected_pyq_10} pool_feasible={feasible}")
        
        if not feasible:
            logger.warning("Cold start pool not feasible, expanding")
            # For cold start, expand aggressively
            expanded_pool, expansion_details = self.adaptively_expand_pool(
                diverse_candidates, diversity_pool_size // 3  # Use smaller base for expansion
            )
            
            metadata = {
                "selection_strategy": "cold_start_diversity",
                "initial_size": len(diverse_candidates),
                "expanded_size": len(expanded_pool),
                "distinct_pairs": len(pairs_included),
                "pool_expanded": True,
                "feasibility": feasibility_details,
                "expansion": expansion_details
            }
            
            return expanded_pool, metadata
        
        metadata = {
            "selection_strategy": "cold_start_diversity",
            "pool_size": len(diverse_candidates),
            "distinct_pairs": len(pairs_included),
            "pool_expanded": False,
            "feasibility": feasibility_details
        }
        
        logger.info(f"Cold start pool: {len(diverse_candidates)} candidates, {len(pairs_included)} distinct pairs")
        return diverse_candidates, metadata
    
    def _get_recent_questions(self, user_id: str, sessions_lookback: int = 3) -> Set[str]:
        """Get question IDs from user's recent sessions to avoid repetition"""
        db = SessionLocal()
        try:
            recent_questions = db.execute(text("""
                SELECT DISTINCT ON (ae.question_id) ae.question_id
                FROM attempt_events ae
                JOIN sessions s ON ae.session_id = s.session_id
                WHERE ae.user_id = :user_id
                AND s.sess_seq > (
                    SELECT COALESCE(MAX(sess_seq), 0) - :lookback
                    FROM sessions
                    WHERE user_id = :user_id
                )
                ORDER BY ae.question_id, ae.created_at DESC
            """), {
                "user_id": user_id,
                "lookback": sessions_lookback
            }).fetchall()
            
            question_ids = {row[0] for row in recent_questions}
            logger.debug(f"Excluding {len(question_ids)} recent questions for user {user_id[:8]}")
            return question_ids
            
        except Exception as e:
            logger.warning(f"Error fetching recent questions: {e}")
            return set()
        finally:
            db.close()

# Global instance
candidate_provider = CandidateProvider()