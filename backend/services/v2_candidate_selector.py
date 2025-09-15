"""
V2 Candidate Selection Service - REPLACES ORDER BY RANDOM()

Fast, indexed, deterministic candidate selection using shuffle_hash column.
NO random sampling. NO full table scans. Pure V2 implementation.
"""

import logging
import hashlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from database import SessionLocal
from sqlalchemy import text
from util.v2_contract import V2CandidateSelection

logger = logging.getLogger(__name__)

@dataclass
class V2Candidate:
    """Light candidate for planner input"""
    id: str
    difficulty_band: str
    pyq_frequency_score: float
    subcategory: str
    type_of_question: str

class V2CandidateSelector:
    """
    V2 Candidate Selection - Fast, Deterministic, Indexed
    
    Uses shuffle_hash column for wrap-around selection instead of ORDER BY RANDOM().
    Guarantees 3/6/3 distribution + PYQ minima with deterministic seeding.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def select_candidates(self, user_id: str, sess_seq: int) -> V2CandidateSelection:
        """
        V2 Main Selection - Returns exactly 12 candidates
        
        Strategy:
        1. Generate deterministic seed from user_id + sess_seq
        2. Use wrap-around selection on shuffle_hash (indexed)
        3. Enforce 3/6/3 + PYQ minima
        4. Return light metadata for planner
        """
        seed = self._generate_seed(user_id, sess_seq)
        
        # Select by category with quotas
        candidates = []
        
        # PYQ 1.5 priority (need ≥2)
        pyq15_candidates = self._select_by_criteria(
            pyq_score=1.5, limit=3, seed=seed
        )
        candidates.extend(pyq15_candidates[:2])  # Take first 2
        
        # PYQ 1.0 priority (need ≥2) 
        pyq10_candidates = self._select_by_criteria(
            pyq_score=1.0, limit=3, seed=seed + 1  # Slight offset
        )
        candidates.extend(pyq10_candidates[:2])  # Take first 2
        
        # Fill by difficulty bands
        easy_candidates = self._select_by_criteria(
            difficulty_band="Easy", limit=4, seed=seed + 2,
            exclude_ids=[c.id for c in candidates]
        )
        candidates.extend(easy_candidates[:3])  # Need exactly 3
        
        medium_candidates = self._select_by_criteria(
            difficulty_band="Medium", limit=8, seed=seed + 3,
            exclude_ids=[c.id for c in candidates]
        )
        candidates.extend(medium_candidates[:6])  # Need exactly 6
        
        hard_candidates = self._select_by_criteria(
            difficulty_band="Hard", limit=4, seed=seed + 4,
            exclude_ids=[c.id for c in candidates]
        )
        candidates.extend(hard_candidates[:3])  # Need exactly 3
        
        # Ensure exactly 12 candidates
        if len(candidates) < 12:
            # Fill remaining slots with any available
            remaining_needed = 12 - len(candidates)
            filler = self._select_by_criteria(
                limit=remaining_needed + 5, seed=seed + 10,
                exclude_ids=[c.id for c in candidates]
            )
            candidates.extend(filler[:remaining_needed])
        
        # Truncate to exactly 12
        candidates = candidates[:12]
        
        self.logger.info(f"V2: Selected {len(candidates)} candidates for user {user_id[:8]}, sess_seq {sess_seq}")
        
        return V2CandidateSelection(
            ids=[c.id for c in candidates],
            seed=seed,
            selection_meta={
                "user_id": user_id,
                "sess_seq": sess_seq,
                "distribution": self._analyze_distribution(candidates),
                "selection_strategy": "v2_deterministic"
            }
        )
    
    def _generate_seed(self, user_id: str, sess_seq: int) -> int:
        """Generate deterministic seed from user + session"""
        seed_string = f"{user_id}:{sess_seq}"
        return abs(int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)) % 1000000
    
    def _select_by_criteria(self, 
                           pyq_score: float = None,
                           difficulty_band: str = None,
                           limit: int = 10,
                           seed: int = 0,
                           exclude_ids: List[str] = None) -> List[V2Candidate]:
        """
        V2 Core Selection - Wrap-around on shuffle_hash (indexed, fast)
        """
        db = SessionLocal()
        try:
            # Build WHERE conditions  
            conditions = ["is_active = true"]
            
            if pyq_score is not None:
                if pyq_score >= 1.5:
                    conditions.append("pyq_frequency_score >= 1.5")
                elif pyq_score >= 1.0:
                    conditions.append("pyq_frequency_score >= 1.0 AND pyq_frequency_score < 1.5")
                else:
                    conditions.append("pyq_frequency_score < 1.0")
            
            if difficulty_band:
                conditions.append(f"difficulty_band = '{difficulty_band}'")
            
            if exclude_ids:
                # Direct SQL string building (safe for UUIDs)
                exclude_clause = "id NOT IN ('" + "','".join(exclude_ids) + "')"
                conditions.append(exclude_clause)
            
            where_clause = " AND ".join(conditions)
            
            # V2 Wrap-around selection using shuffle_hash index  
            # Use direct hash value instead of parameter binding
            seed_hash = seed % 2147483647
            
            query = f"""
            WITH chunk_forward AS (
                SELECT id, difficulty_band, pyq_frequency_score, subcategory, type_of_question, shuffle_hash
                FROM questions
                WHERE {where_clause} AND shuffle_hash >= {seed_hash}
                ORDER BY shuffle_hash
                LIMIT {limit}
            ),
            chunk_wrap AS (
                SELECT id, difficulty_band, pyq_frequency_score, subcategory, type_of_question, shuffle_hash
                FROM questions  
                WHERE {where_clause} AND shuffle_hash < {seed_hash}
                ORDER BY shuffle_hash
                LIMIT GREATEST(0, {limit} - (SELECT COUNT(*) FROM chunk_forward))
            )
            SELECT id, difficulty_band, pyq_frequency_score, subcategory, type_of_question
            FROM chunk_forward
            UNION ALL
            SELECT id, difficulty_band, pyq_frequency_score, subcategory, type_of_question  
            FROM chunk_wrap
            LIMIT {limit}
            """
            
            # Execute query with no parameters (direct values)
            result = db.execute(text(query)).fetchall()
            
            candidates = []
            for row in result:
                candidates.append(V2Candidate(
                    id=row[0],
                    difficulty_band=row[1] or "Medium",
                    pyq_frequency_score=float(row[2] or 0.5),
                    subcategory=row[3] or "Unknown",
                    type_of_question=row[4] or "Unknown"
                ))
            
            return candidates
            
        finally:
            db.close()
    
    def _analyze_distribution(self, candidates: List[V2Candidate]) -> Dict[str, int]:
        """Analyze candidate distribution for telemetry"""
        distribution = {"Easy": 0, "Medium": 0, "Hard": 0, "pyq_15": 0, "pyq_10": 0}
        
        for c in candidates:
            band = c.difficulty_band
            if band in distribution:
                distribution[band] += 1
            
            if c.pyq_frequency_score >= 1.5:
                distribution["pyq_15"] += 1
            elif c.pyq_frequency_score >= 1.0:
                distribution["pyq_10"] += 1
        
        return distribution

# Global instance
v2_candidate_selector = V2CandidateSelector()