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
    
    def _fetch_candidates_with_seeded_hash(self, user_id: str, session_seq: int, 
                                         pyq_score: float = None, difficulty_band: str = None, 
                                         limit: int = 50) -> List[QuestionCandidate]:
        """P0 FIX: Replace ORDER BY RANDOM() with seeded hash ordering"""
        db = SessionLocal()
        try:
            # Create deterministic seed from user_id and session_seq
            seed = f"{user_id}:{session_seq}"
            
            # Build base query with light columns first (performance optimization)
            base_conditions = ["is_active = true"]
            params = {"seed": seed}
            
            if pyq_score is not None:
                if pyq_score >= 1.5:
                    base_conditions.append("pyq_frequency_score >= 1.5")
                elif pyq_score >= 1.0:
                    base_conditions.append("pyq_frequency_score >= 1.0 AND pyq_frequency_score < 1.5")
                else:
                    base_conditions.append("pyq_frequency_score < 1.0")
            
            if difficulty_band:
                base_conditions.append(f"difficulty_band = '{difficulty_band}'")
                
            where_clause = " AND ".join(base_conditions)
            
            # P0 FIX: Use seeded hash ordering instead of RANDOM()
            light_query = f"""
            SELECT id, difficulty_band, pyq_frequency_score
            FROM questions
            WHERE {where_clause}
            ORDER BY (abs(hashtext(id::text) # hashtext(%(seed)s::text)))
            LIMIT {limit}
            """
            
            # Get light results first
            light_results = db.execute(text(light_query), params).fetchall()
            question_ids = [row[0] for row in light_results]
            
            if not question_ids:
                return []
            
            # Then fetch full question data for selected IDs
            full_query = select(Question).where(Question.id.in_(question_ids))
            questions = db.execute(full_query).scalars().all()
            
            # Convert to QuestionCandidate objects
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
                        core_concepts=tuple(concepts),
                        pyq_frequency_score=float(q.pyq_frequency_score) if q.pyq_frequency_score else 0.5,
                        pair=f"{q.subcategory}:{q.type_of_question}" if q.subcategory and q.type_of_question else "Unknown:Unknown"
                    )
                    candidates.append(candidate)
                    
                except Exception as e:
                    logger.warning(f"Error processing question {q.id}: {e}")
                    continue
            
            return candidates
            
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
                           diversity_pool_size: int = 100,
                           session_seq: int = 1) -> Tuple[List[QuestionCandidate], Dict[str, Any]]:
        """
        P0 FIX: Build diversity-first candidate pool with seeded hash sampling
        
        Prioritizes:
        - Unseen concept/pair combinations
        - Broad exposure across taxonomy  
        - Meeting basic constraints (3/6/3, PYQ minima)
        - Deterministic seeded ordering (no ORDER BY RANDOM())
        
        Args:
            user_id: User identifier (new user)
            diversity_pool_size: Size of diversity pool
            session_seq: Session sequence for deterministic seeding
            
        Returns:
            (candidates, metadata) for cold start selection
        """
        logger.info(f"Building cold start diversity pool for user {user_id[:8]}... (size={diversity_pool_size})")
        
        # P0 FIX: Use seeded hash sampling for PYQ requirements first
        # This avoids the ORDER BY RANDOM() performance issue
        
        # Step 1: Get PYQ 1.5 candidates (deterministic)
        pyq15_candidates = self._fetch_candidates_with_seeded_hash(
            user_id=user_id, session_seq=session_seq, 
            pyq_score=1.5, limit=10
        )
        
        # Step 2: Get PYQ 1.0 candidates (deterministic)  
        pyq10_candidates = self._fetch_candidates_with_seeded_hash(
            user_id=user_id, session_seq=session_seq,
            pyq_score=1.0, limit=20
        )
        
        # Step 3: Get fill candidates by band (deterministic)
        easy_candidates = self._fetch_candidates_with_seeded_hash(
            user_id=user_id, session_seq=session_seq,
            difficulty_band="Easy", limit=30
        )
        
        medium_candidates = self._fetch_candidates_with_seeded_hash(
            user_id=user_id, session_seq=session_seq,
            difficulty_band="Medium", limit=40
        )
        
        hard_candidates = self._fetch_candidates_with_seeded_hash(
            user_id=user_id, session_seq=session_seq,
            difficulty_band="Hard", limit=30
        )
        
        # Combine all candidates with preference for PYQ
        all_candidates = []
        all_candidates.extend(pyq15_candidates[:2])  # Ensure at least 2 PYQ 1.5
        all_candidates.extend(pyq10_candidates[:2])  # Ensure at least 2 PYQ 1.0  
        
        # Add remaining candidates to reach diversity_pool_size
        remaining_candidates = []
        remaining_candidates.extend(pyq15_candidates[2:])
        remaining_candidates.extend(pyq10_candidates[2:])
        remaining_candidates.extend(easy_candidates)
        remaining_candidates.extend(medium_candidates) 
        remaining_candidates.extend(hard_candidates)
        
        # Remove duplicates and add to pool
        seen_ids = {c.question_id for c in all_candidates}
        for candidate in remaining_candidates:
            if candidate.question_id not in seen_ids and len(all_candidates) < diversity_pool_size:
                all_candidates.append(candidate)
                seen_ids.add(candidate.question_id)
        
        # TELEMETRY: Log data source and PYQ availability for cold start
        pyq_15_available = len(pyq15_candidates)
        pyq_10_available = len(pyq10_candidates)
        logger.info(f"📊 TELEMETRY COLDSTART: provider_source=seeded_hash available_pyq15_in_pool={pyq_15_available} available_pyq10_in_pool={pyq_10_available} total_active={len(all_candidates)}")
        
        # Check feasibility
        feasible, feasibility_details = self.preflight_feasible(all_candidates)
        
        # TELEMETRY: Log cold start selection results
        selected_pyq_15 = sum(1 for c in all_candidates if c.pyq_frequency_score >= 1.5)
        selected_pyq_10 = sum(1 for c in all_candidates if c.pyq_frequency_score >= 1.0)
        logger.info(f"📊 TELEMETRY COLDSTART: selected_pyq15_in_pool={selected_pyq_15} selected_pyq10_in_pool={selected_pyq_10} pool_feasible={feasible}")
        
        if not feasible:
            logger.warning("Cold start pool not feasible, expanding with seeded sampling")
            return self._expand_pool_deterministic(all_candidates, diversity_pool_size, user_id, session_seq)
        
        # Group by pair for diversity check
        pairs_included = set()
        for candidate in all_candidates:
            pairs_included.add(candidate.pair)
        
        logger.info(f"Cold start pool: {len(all_candidates)} candidates, {len(pairs_included)} distinct pairs")
        
        return all_candidates, {
            "pool_size": len(all_candidates),
            "distinct_pairs": len(pairs_included),
            "pyq_15_count": selected_pyq_15,
            "pyq_10_count": selected_pyq_10,
            "feasible": feasible,
            "strategy": "seeded_hash_sampling",
            "feasibility_details": feasibility_details
        }
    
    def _expand_pool_deterministic(self, initial_pool, target_size, user_id, session_seq):
        """P0 FIX: Deterministic pool expansion using seeded hash sampling"""
        logger.info("Expanding pool deterministically with seeded hash sampling")
        
        # Try to fetch more candidates with higher limits
        expanded_candidates = []
        expanded_candidates.extend(initial_pool)
        
        # Get more candidates per category with higher limits
        categories = [
            (1.5, 20),  # PYQ 1.5 - more limit
            (1.0, 40),  # PYQ 1.0 - more limit 
            ("Easy", 50),
            ("Medium", 60),
            ("Hard", 50)
        ]
        
        seen_ids = {c.question_id for c in initial_pool}
        
        for category, limit in categories:
            if len(expanded_candidates) >= target_size:
                break
                
            if isinstance(category, float):
                # PYQ score category
                candidates = self._fetch_candidates_with_seeded_hash(
                    user_id=user_id, session_seq=session_seq + 1,  # Slight offset for variety
                    pyq_score=category, limit=limit
                )
            else:
                # Difficulty band category
                candidates = self._fetch_candidates_with_seeded_hash(
                    user_id=user_id, session_seq=session_seq + 1,
                    difficulty_band=category, limit=limit
                )
            
            # Add unseen candidates
            for candidate in candidates:
                if (candidate.question_id not in seen_ids and 
                    len(expanded_candidates) < target_size):
                    expanded_candidates.append(candidate)
                    seen_ids.add(candidate.question_id)
        
        # Check final feasibility
        feasible, feasibility_details = self.preflight_feasible(expanded_candidates)
        
        return expanded_candidates, {
            "success": feasible,
            "final_size": len(expanded_candidates),
            "strategy": "deterministic_expansion",
            "feasible": feasible,
            "feasibility_details": feasibility_details
        }
    
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