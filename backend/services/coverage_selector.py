"""
Coverage Selector Service
Deterministic service that selects exactly 12 questions based on Coverage Planner recipe
Implements PYQ-first, 4-tier priority, band-aware backfill, and caps
"""

import asyncio
import hashlib
import json
import logging
import random
from typing import Dict, List, Tuple, Set, Optional, Iterable
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Constants for backfill logic
PRIMARY_VIEW = {"easy": "weak", "medium": "moderate", "hard": "strong"}
BORROW = {
    "easy":   [("moderate","medium"), ("strong","hard")],
    "medium": [("weak","easy"), ("strong","hard")],
    "hard":   [("moderate","medium"), ("weak","easy")]
}

class CoverageSelector:
    """
    Deterministic service that selects questions using Coverage recipe
    Implements all priority logic, caps, and backfill mechanisms
    """
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        self._served_map = {}  # Cache for served counts during selection
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def select_pack(self, user_id: str, session_id: str, notebook: Dict, recipe: Dict) -> Tuple[List[Dict], Dict]:
        """
        Deterministic selection with all fixes and performance optimizations
        
        Args:
            user_id: User identifier
            session_id: Session identifier for stable seeding
            notebook: Learner notebook with skill statuses
            recipe: Selection recipe from Coverage Planner
            
        Returns:
            Tuple of (selected_pack, audit_dict)
        """
        try:
            logger.info(f"🎯 Coverage Selector starting for user {user_id[:8]}, session {session_id[:8]}")
            
            # Preload served counts to avoid N+1 queries
            self._served_map = await self._preload_served_counts(user_id)
            logger.debug(f"📊 Preloaded {len(self._served_map)} served count entries")
            
            # Get eligible questions with anchors
            eligible_questions = await self._get_eligible_questions_with_anchors()
            logger.info(f"📋 Found {len(eligible_questions)} eligible questions")
            
            if len(eligible_questions) < 12:
                logger.warning(f"⚠️ Only {len(eligible_questions)} eligible questions available")
            
            # Tag questions with skill views
            tagged_questions = self._tag_questions_with_views(eligible_questions, notebook)
            
            # Initialize pack-level PYQ counters and audit
            pack_pyq_counters = {"1_5": 0, "1_0": 0}  # Pack-level tracking
            audit = {
                "shape": {"easy": 0, "medium": 0, "hard": 0},
                "pyq": {},
                "borrow": {"easy": 0, "medium": 0, "hard": 0}
            }
            
            # Fill buckets with PYQ-first logic and borrowing
            easy_selected = self._fill_bucket("easy", 3, tagged_questions, recipe, 
                                            pack_pyq_counters, audit, session_id)
            medium_selected = self._fill_bucket("medium", 6, tagged_questions, recipe,
                                              pack_pyq_counters, audit, session_id)
            hard_selected = self._fill_bucket("hard", 3, tagged_questions, recipe,
                                            pack_pyq_counters, audit, session_id)
            
            all_selected = easy_selected + medium_selected + hard_selected
            logger.info(f"📦 Initial selection: {len(all_selected)} questions")
            
            # Apply caps with smart band-aware backfill preserving bucket intent
            capped_pack = await self._apply_caps_with_smart_band_aware_backfill(
                all_selected, eligible_questions, recipe, notebook, user_id, session_id
            )
            
            # Pack-level PYQ top-up after caps/backfill
            final_pack = self._pack_level_pyq_topup(capped_pack, eligible_questions,
                                                  pack_pyq_counters, user_id, session_id)
            
            # Recompute audit from final pack to ensure accuracy
            audit["shape"] = self._shape_from_pack(final_pack)
            audit["pyq"] = self._pyq_from_pack(final_pack)
            
            # NEW: merge per-caps audit
            if hasattr(self, "_last_caps_backfill_audit"):
                audit.update(self._last_caps_backfill_audit)
            
            logger.info(f"✅ Coverage Selector completed: {len(final_pack)} questions selected")
            logger.info(f"📊 Final shape: {audit['shape']}")
            
            return final_pack, audit
            
        except Exception as e:
            logger.error(f"❌ Coverage Selector failed: {e}")
            # Return safe fallback
            return [], {"error": str(e), "shape": {"easy": 0, "medium": 0, "hard": 0}, "pyq": {}}
    
    async def _get_eligible_questions_with_anchors(self) -> List[Dict]:
        """Get eligible questions with anchors and optimize for selection"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, anchors, difficulty_band, subcategory, type_of_question,
                       pyq_frequency_score, core_concepts, stem
                FROM questions
                WHERE is_active = TRUE 
                AND quality_verified = TRUE 
                AND difficulty_band IS NOT NULL
                AND anchors IS NOT NULL
                AND anchors != '[]'::jsonb
                ORDER BY pyq_frequency_score DESC, id
            """)
            
            results = cur.fetchall()
            cur.close()
            conn.close()
            
            questions = []
            for row in results:
                try:
                    # Parse anchors safely
                    anchors = row[1]
                    if isinstance(anchors, str):
                        anchors = json.loads(anchors)
                    if not isinstance(anchors, list):
                        anchors = []
                    
                    # Parse core_concepts safely
                    core_concepts = row[6]
                    if isinstance(core_concepts, str):
                        core_concepts = json.loads(core_concepts)
                    if not isinstance(core_concepts, list):
                        core_concepts = []
                    
                    questions.append({
                        "id": row[0],
                        "anchors": anchors,
                        "difficulty_band": row[2].lower() if row[2] else 'medium',
                        "subcategory": row[3] or 'Unknown',
                        "type_of_question": row[4] or 'Unknown', 
                        "pyq_frequency_score": float(row[5]) if row[5] else 0.0,
                        "core_concepts": core_concepts,
                        "stem": row[7] or 'No stem available'
                    })
                    
                except Exception as parse_error:
                    logger.warning(f"Failed to parse question {row[0]}: {parse_error}")
                    continue
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to get eligible questions: {e}")
            return []
    
    async def _preload_served_counts(self, user_id: str) -> Dict[str, int]:
        """Preload all served counts to avoid N+1 queries"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT subcategory_type, served_count
                FROM coverage_ledger 
                WHERE user_id = %s
            """, (user_id,))
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            return {row[0]: row[1] for row in rows}
            
        except Exception as e:
            logger.warning(f"Failed to preload served counts: {e}")
            return {}
    
    def _get_served_count(self, user_id: str, subcat_type: str) -> int:
        """Get served count from preloaded cache"""
        return self._served_map.get(subcat_type, 0)
    
    def _tag_questions_with_views(self, questions: List[Dict], notebook: Dict) -> List[Dict]:
        """Tag questions with skill view membership"""
        # Extract skill sets from notebook
        skill_sets = {"weak": set(), "moderate": set(), "strong": set()}
        for skill in notebook.get("skills", []):
            label = skill.get("label", "").strip().lower()
            status = skill.get("status", "moderate")
            if label and status in skill_sets:
                skill_sets[status].add(label)
        
        tagged = []
        for question in questions:
            question_anchors = set(anchor.lower() for anchor in question.get('anchors', []))
            
            # Tag with view membership (multi-label allowed)
            question['hits_weak'] = bool(question_anchors & skill_sets["weak"])
            question['hits_moderate'] = bool(question_anchors & skill_sets["moderate"])
            question['hits_strong'] = bool(question_anchors & skill_sets["strong"])
            
            # If no hits and empty notebook, everything hits moderate
            if not any([question['hits_weak'], question['hits_moderate'], question['hits_strong']]):
                if not any(skill_sets.values()):  # Empty notebook
                    question['hits_moderate'] = True
            
            tagged.append(question)
        
        return tagged
    
    def _fill_bucket(self, band: str, target_count: int, tagged_questions: List[Dict],
                    recipe: Dict, pack_pyq_counters: Dict, audit: Dict, session_id: str) -> List[Dict]:
        """Fill a difficulty band bucket with PYQ-first selection"""
        
        # Filter questions for this band
        band_questions = [q for q in tagged_questions if q["difficulty_band"] == band]
        
        # Get priority skills for this band from recipe
        priority_skills = set()
        band_recipe = recipe.get(band, {})
        for skill in band_recipe.get("priority_skills", []):
            priority_skills.add(skill.lower())
        
        # Sort questions by 4-tier priority with session-stable seeding
        def priority_key(q):
            # Tier 1: Skill match (0 = match, 1 = no match)
            skill_match = 0 if any(anchor.lower() in priority_skills for anchor in q.get("anchors", [])) else 1
            
            # Tier 2: PYQ score (negative for descending order)
            pyq_score = -q.get("pyq_frequency_score", 0.0)
            
            # Tier 3: Served count (ascending order - prefer less served)
            subcat_type = f"{q.get('subcategory', 'Unknown')}|{q.get('type_of_question', 'Unknown')}"
            served_count = self._get_served_count("user", subcat_type)  # Use cached value
            
            # Tier 4: Seeded hash for stable randomization
            question_hash = hashlib.md5(f"{q['id']}_{session_id}".encode()).hexdigest()[:8]
            hash_value = int(question_hash, 16)
            
            return (skill_match, pyq_score, served_count, hash_value)
        
        sorted_questions = sorted(band_questions, key=priority_key)
        
        # Select up to target_count questions
        selected = sorted_questions[:target_count]
        
        # Update audit
        audit["shape"][band] = len(selected)
        
        return selected
    
    async def _apply_caps_with_smart_band_aware_backfill(
        self,
        selected_questions: List[Dict],
        eligible_pool: List[Dict],
        recipe: Dict,
        notebook: Dict,
        user_id: str,
        session_id: str,
    ) -> List[Dict]:
        """
        Enforce ≤2 per subtype cap, then deterministically backfill to restore 3/6/3 and total=12.
        If inventory under same-band/borrow cannot satisfy, allow a *soft* cap relax to 3 (audited).
        As last resort, force-fill to 12 while flagging audit.
        """
        subtype_counts: Dict[str, int] = {}
        used_ids: set = set()

        # split by band
        easy = [q for q in selected_questions if q.get("difficulty_band") == "easy"]
        med  = [q for q in selected_questions if q.get("difficulty_band") == "medium"]
        hard = [q for q in selected_questions if q.get("difficulty_band") == "hard"]

        # enforce ≤2 cap inside each band
        easy_c = self._apply_cap_to_band(easy,  subtype_counts, used_ids)
        med_c  = self._apply_cap_to_band(med,   subtype_counts, used_ids)
        hard_c = self._apply_cap_to_band(hard,  subtype_counts, used_ids)

        # init audit holders if caller didn't
        audit = {"cap_relaxations": {"easy":0,"medium":0,"hard":0}, "force_fill": 0, "shape_compromised_due_to_inventory": False}

        # compute deficits
        need_easy = max(0, 3 - len(easy_c))
        need_med  = max(0, 6 - len(med_c))
        need_hard = max(0, 3 - len(hard_c))

        # fill deficits in priority order easy→medium→hard to stabilize ties
        easy_c += self._backfill_band("easy", need_easy,  eligible_pool, recipe, notebook,
                                      subtype_counts, used_ids, user_id, session_id, audit)
        med_c  += self._backfill_band("medium", need_med, eligible_pool, recipe, notebook,
                                      subtype_counts, used_ids, user_id, session_id, audit)
        hard_c += self._backfill_band("hard", need_hard,  eligible_pool, recipe, notebook,
                                      subtype_counts, used_ids, user_id, session_id, audit)

        # assemble & enforce 3/6/3 slice and total <= 12
        pack = (easy_c[:3] + med_c[:6] + hard_c[:3])[:12]

        # If still short due to inventory, force-fill to 12 and flag audit
        if len(pack) < 12:
            pack = self._force_fill_to_twelve(pack, eligible_pool, used_ids, user_id, session_id, audit)
            # If force-filled from other bands, shape might be off; mark it
            shape = self._shape_from_pack(pack)
            if not (shape.get("easy")==3 and shape.get("medium")==6 and shape.get("hard")==3):
                audit["shape_compromised_due_to_inventory"] = True

        # store audit on self so caller (select_pack) can merge it in its audit
        self._last_caps_backfill_audit = audit
        return pack
    
    def _backfill_band(
        self,
        target_band: str,
        need: int,
        pool: List[Dict],
        recipe: Dict,
        notebook: Dict,
        subtype_counts: Dict[str,int],
        used_ids: set,
        user_id: str,
        session_id: str,
        audit: Dict
    ) -> List[Dict]:
        if need <= 0:
            return []

        bucket = recipe.get(target_band, {})
        priority = set(bucket.get("priority_skills", []))
        skill_sets = self._extract_skill_sets(notebook)
        primary_view = PRIMARY_VIEW[target_band]

        picked: List[Dict] = []

        # Phase A: same-band + primary view (weak/moderate/strong)
        picked += self._take_from_stream(
            self._candidate_stream(pool, band=target_band, view=primary_view,
                                   skill_sets=skill_sets, priority=priority,
                                   user_id=user_id, session_id=session_id),
            need - len(picked), subtype_counts, used_ids
        )

        # Phase B: borrow chain
        for view_name, source_band in BORROW[target_band]:
            if len(picked) >= need:
                break
            picked += self._take_from_stream(
                self._candidate_stream(pool, band=source_band, view=view_name,
                                       skill_sets=skill_sets, priority=priority,
                                       user_id=user_id, session_id=session_id),
                need - len(picked), subtype_counts, used_ids
            )

        # Phase C: same-band, any view
        if len(picked) < need:
            picked += self._take_from_stream(
                self._candidate_stream(pool, band=target_band, view=None,
                                       skill_sets=skill_sets, priority=priority,
                                       user_id=user_id, session_id=session_id),
                need - len(picked), subtype_counts, used_ids
            )

        # Phase D: soft cap relax (raise subtype cap to 3) as last resort
        while len(picked) < need:
            extra = self._take_from_stream(
                self._candidate_stream(pool, band=target_band, view=None,
                                       skill_sets=skill_sets, priority=priority,
                                       user_id=user_id, session_id=session_id),
                1, subtype_counts, used_ids, allow_soft_cap_relax=True
            )
            if not extra:
                break
            picked += extra
            audit["cap_relaxations"][target_band] += 1

        return picked[:need]

    def _candidate_stream(
        self,
        pool: List[Dict],
        band: str,
        view: Optional[str],
        skill_sets: Dict[str,set],
        priority: set,
        user_id: str,
        session_id: str
    ):
        target_labels = skill_sets.get(view, set()) if view else None

        # Filter
        candidates = []
        for q in pool:
            qid = q.get("id")
            if not qid:  # safety
                continue
            if q.get("difficulty_band") != band:
                continue
            if target_labels is not None and not (set(q.get("anchors", [])) & target_labels):
                continue
            candidates.append(q)

        # Sort by our 4-tier priority (priority-hit, -pyq, served_count, stable hash)
        def sort_key(c):
            priority_hit = bool(set(c.get('anchors', [])) & priority)
            pyq = float(c.get('pyq_frequency_score', 0.0))
            subcat_type = f"{c.get('subcategory','')}|{c.get('type_of_question','')}"
            served = self._get_served_count(user_id, subcat_type)
            stable_hash = int(hashlib.md5(f"{user_id}|{session_id}|{c['id']}".encode('utf-8')).hexdigest()[:8], 16)
            return (not priority_hit, -pyq, served, stable_hash)

        candidates.sort(key=sort_key)
        for c in candidates:
            yield c

    def _take_from_stream(
        self,
        stream: Iterable[Dict],
        need: int,
        subtype_counts: Dict[str,int],
        used_ids: set,
        allow_soft_cap_relax: bool = False
    ) -> List[Dict]:
        out = []
        cap = 3 if allow_soft_cap_relax else 2

        for c in stream:
            if len(out) >= need:
                break
            qid = c.get("id")
            if qid in used_ids:
                continue
            subtype = f"{c.get('subcategory','Unknown')}|{c.get('type_of_question','Unknown')}"
            if subtype_counts.get(subtype, 0) < cap:
                out.append(c)
                used_ids.add(qid)
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1

        return out

    def _force_fill_to_twelve(
        self,
        pack: List[Dict],
        pool: List[Dict],
        used_ids: set,
        user_id: str,
        session_id: str,
        audit: Dict
    ) -> List[Dict]:
        remaining = 12 - len(pack)
        if remaining <= 0:
            return pack

        unused = [q for q in pool if q.get("id") not in used_ids]
        # Favor PYQ, then coverage variety, then stable
        def sort_key(q):
            pyq = float(q.get('pyq_frequency_score', 0.0))
            subcat_type = f"{q.get('subcategory','')}|{q.get('type_of_question','')}"
            served = self._get_served_count(user_id, subcat_type)
            stable_hash = int(hashlib.md5(f"{user_id}|{session_id}|{q['id']}".encode('utf-8')).hexdigest()[:8], 16)
            return (-pyq, served, stable_hash)

        unused.sort(key=sort_key)
        fill = unused[:remaining]
        used_ids.update(q["id"] for q in fill)
        audit["force_fill"] = remaining
        return pack + fill

    def _extract_skill_sets(self, notebook: Dict) -> Dict[str, Set[str]]:
        """Extract weak/moderate/strong skill sets from notebook"""
        skill_sets = {"weak": set(), "moderate": set(), "strong": set()}
        for skill in notebook.get("skills", []):
            label = skill.get("label", "").strip().lower()
            status = skill.get("status", "moderate")
            if label and status in skill_sets:
                skill_sets[status].add(label)
        return skill_sets

    def _apply_cap_to_band(self, band_questions: List[Dict], subtype_counts: Dict, used_question_ids: set) -> List[Dict]:
        """Apply ≤2 cap per subcategory|type within a band"""
        capped = []
        
        for question in band_questions:
            subtype = f"{question.get('subcategory', 'Unknown')}|{question.get('type_of_question', 'Unknown')}"
            
            # ENFORCE CAP: ≤2 per subcategory|type
            if subtype_counts.get(subtype, 0) < 2:
                capped.append(question)
                used_question_ids.add(question['id'])
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
        
        return capped
    
    def _pack_level_pyq_topup(self, pack: List[Dict], eligible_questions: List[Dict],
                            pack_pyq_counters: Dict, user_id: str, session_id: str) -> List[Dict]:
        """Perform pack-level PYQ top-up if targets not met"""
        
        # Check current PYQ counts in pack
        current_1_5 = sum(1 for q in pack if q.get("pyq_frequency_score", 0) >= 1.5)
        current_1_0 = sum(1 for q in pack if 1.0 <= q.get("pyq_frequency_score", 0) < 1.5)
        
        # If targets already met, return as-is
        if current_1_5 >= 2 and (current_1_5 + current_1_0) >= 4:
            return pack
        
        # Find high-PYQ candidates not already in pack
        used_ids = {q["id"] for q in pack}
        high_pyq_candidates = [
            q for q in eligible_questions 
            if q["id"] not in used_ids and q.get("pyq_frequency_score", 0) >= 1.5
        ]
        
        # Stable selection for PYQ top-up
        random.seed(hashlib.md5(f"pyq_topup_{session_id}".encode()).hexdigest()[:8])
        random.shuffle(high_pyq_candidates)
        
        # Replace lowest PYQ questions with high PYQ ones if beneficial
        pack_with_pyq_scores = [(q, q.get("pyq_frequency_score", 0)) for q in pack]
        pack_with_pyq_scores.sort(key=lambda x: x[1])  # Sort by PYQ score ascending
        
        final_pack = pack.copy()
        replacements_made = 0
        
        for candidate in high_pyq_candidates[:2]:  # Limit replacements
            if replacements_made < len(pack_with_pyq_scores):
                # Replace lowest scoring question
                lowest_q, lowest_score = pack_with_pyq_scores[replacements_made]
                if candidate.get("pyq_frequency_score", 0) > lowest_score:
                    # Remove lowest and add candidate
                    final_pack = [q for q in final_pack if q["id"] != lowest_q["id"]]
                    final_pack.append(candidate)
                    replacements_made += 1
        
        return final_pack[:12]  # Ensure exactly 12
    
    def _shape_from_pack(self, pack: List[Dict]) -> Dict:
        """Recompute shape from final pack for accurate audit"""
        return {
            "easy": sum(1 for q in pack if q.get("difficulty_band") == "easy"),
            "medium": sum(1 for q in pack if q.get("difficulty_band") == "medium"),
            "hard": sum(1 for q in pack if q.get("difficulty_band") == "hard"),
        }
    
    def _pyq_from_pack(self, pack: List[Dict]) -> Dict:
        """Recompute PYQ counts from final pack for accurate audit"""
        c15 = sum(1 for q in pack if q.get("pyq_frequency_score", 0) >= 1.5)
        c10 = sum(1 for q in pack if 1.0 <= q.get("pyq_frequency_score", 0) < 1.5)
        return {"1_5": c15, "1_0": c10}

# Global instance
coverage_selector = CoverageSelector()

# Test function
async def test_coverage_selector():
    """Test the coverage selector service"""
    print("🧪 Testing Coverage Selector Service...")
    
    # Sample notebook and recipe
    sample_notebook = {
        "skills": [
            {"label": "relative speed", "status": "weak"},
            {"label": "ratio scaling", "status": "moderate"}
        ]
    }
    
    sample_recipe = {
        "easy": {"priority_skills": []},
        "medium": {"priority_skills": ["relative speed"]},
        "hard": {"priority_skills": []},
        "borrow_order": {
            "easy": ["moderate", "strong"],
            "medium": ["weak", "strong"],
            "hard": ["moderate", "weak"]
        },
        "pyq_intent": {"need_pyq_1_5": 2, "need_pyq_1_0": 2}
    }
    
    # Test selector
    pack, audit = await coverage_selector.select_pack("test_user", "test_session", sample_notebook, sample_recipe)
    
    print(f"📦 Selected pack: {len(pack)} questions")
    print(f"📊 Shape audit: {audit.get('shape', {})}")
    print(f"🏆 PYQ audit: {audit.get('pyq', {})}")
    
    if pack:
        print(f"📋 Sample questions:")
        for i, q in enumerate(pack[:3]):
            print(f"   {i+1}. {q.get('id', 'unknown')[:8]}... ({q.get('difficulty_band')}) - {q.get('anchors', [])}")
    
    return len(pack) == 12

if __name__ == "__main__":
    asyncio.run(test_coverage_selector())