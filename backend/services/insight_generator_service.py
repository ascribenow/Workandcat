import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Import existing LLM utils
from llm_utils import call_llm_with_fallback

logger = logging.getLogger(__name__)

class InsightGeneratorService:
    """Service for generating LLM-powered adaptive insights with fallbacks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # LLM cost control flags
        self.max_calls_per_user_per_day = 3
        self.user_call_counts = {}  # In-memory cache for demo (use Redis in production)
        
    def _percent_to_human(self, accuracy: float) -> str:
        """Convert 0.42 -> 'about 4 out of 10 correct'"""
        if accuracy is None:
            return "about half right"
        out_of_10 = max(0, min(10, round(accuracy * 10)))
        return f"about {out_of_10} out of 10 correct"
    
    def _sanitize_coach_response(self, response: str) -> str:
        """Remove any technical formatting that slipped through"""
        if not response:
            return response
        # Remove percentage signs and decimals
        import re
        response = re.sub(r'\d+\.\d+%?', lambda m: 'about half' if '.' in m.group() else m.group(), response)
        response = re.sub(r'\d+%', lambda m: f"about {min(10, max(0, int(m.group()[:-1])//10))} out of 10", response)
        return response
    
    def gen_all_time_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Generate all-time journey markdown with LLM + fallback"""
        try:
            # GLOBAL FALLBACK FEATURE FLAG
            import os
            if os.environ.get("INSIGHTS_FORCE_FALLBACK", "false").lower() == "true":
                return self._fallback_all_time_markdown(slice_dict)
                
            # LLM cost control
            if not self._should_use_llm(slice_dict.get("user_id", ""), "dashboard"):
                return self._fallback_all_time_markdown(slice_dict)
                
            prompt = self._build_all_time_prompt(slice_dict)
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o",
                model_fallback="gemini-2.5-flash",
                max_tokens=400  # Generous tokens for comprehensive insights
            )
            
            if response and len(response.strip()) > 10:
                self._track_llm_usage(slice_dict.get("user_id", ""), "dashboard")
                return response.strip()
            else:
                return self._fallback_all_time_markdown(slice_dict)
                
        except Exception as e:
            self.logger.error(f"LLM call failed for all-time insights: {e}")
            return self._fallback_all_time_markdown(slice_dict)
    
    def gen_recent_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Generate recent momentum markdown with LLM + fallback"""
        try:
            # GLOBAL FALLBACK FEATURE FLAG
            import os
            if os.environ.get("INSIGHTS_FORCE_FALLBACK", "false").lower() == "true":
                return self._fallback_recent_markdown(slice_dict)
                
            # LLM cost control 
            if not self._should_use_llm(slice_dict.get("user_id", ""), "dashboard"):
                return self._fallback_recent_markdown(slice_dict)
                
            prompt = self._build_recent_prompt(slice_dict)
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o", 
                model_fallback="gemini-2.5-flash",
                max_tokens=350  # Rich insights for recent momentum
            )
            
            if response and len(response.strip()) > 10:
                self._track_llm_usage(slice_dict.get("user_id", ""), "dashboard")
                return response.strip()
            else:
                return self._fallback_recent_markdown(slice_dict)
                
        except Exception as e:
            self.logger.error(f"LLM call failed for recent insights: {e}")
            return self._fallback_recent_markdown(slice_dict)
    
    def gen_pre_session_card(self, slice_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pre-session card with LLM + fallback"""
        try:
            # GLOBAL FALLBACK FEATURE FLAG
            import os
            if os.environ.get("INSIGHTS_FORCE_FALLBACK", "false").lower() == "true":
                fallback = self._fallback_pre_session_card(slice_dict)
                fallback["prompt_version"] = "v1.0_fallback_forced"
                fallback["source"] = "fallback_forced"
                return fallback
                
            # LLM cost control
            if not self._should_use_llm(slice_dict.get("user_id", ""), "pre_session"):
                fallback = self._fallback_pre_session_card(slice_dict)
                fallback["prompt_version"] = "v1.0_fallback"
                return fallback
                
            prompt = self._build_pre_session_prompt(slice_dict)
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o",  # Best model for quality insights
                model_fallback="gemini-2.5-flash", 
                max_tokens=200,  # Generous tokens for rich insights  
                timeout=15  # Adequate timeout for quality
            )
            
            if response:
                try:
                    # Parse JSON response
                    card_data = json.loads(response.strip())
                    if self._validate_card_format(card_data):
                        self._track_llm_usage(slice_dict.get("user_id", ""), "pre_session")
                        # Add source flag for debugging
                        card_data["source"] = "llm"
                        card_data["prompt_version"] = "v1.0_llm"
                        return card_data
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON parse error in pre-session card: {e}")
            
            fallback_card = self._fallback_pre_session_card(slice_dict)
            fallback_card["source"] = "fallback"
            return fallback_card
            
        except Exception as e:
            self.logger.error(f"LLM call failed for pre-session card: {e}")
            fallback_card = self._fallback_pre_session_card(slice_dict)
            fallback_card["source"] = "fallback"
            return fallback_card
    
    def _should_use_llm(self, user_id: str, surface: str) -> bool:
        """LLM cost control: limit calls per user per day"""
        if not user_id:
            return True  # Allow if no user_id provided
            
        today = datetime.now(timezone.utc).date().isoformat()
        key = f"{user_id}_{surface}_{today}"
        
        current_count = self.user_call_counts.get(key, 0)
        return current_count < self.max_calls_per_user_per_day
    
    def _track_llm_usage(self, user_id: str, surface: str):
        """Track LLM usage for cost control"""
        if not user_id:
            return
            
        today = datetime.now(timezone.utc).date().isoformat()
        key = f"{user_id}_{surface}_{today}"
        
        current_count = self.user_call_counts.get(key, 0)
        self.user_call_counts[key] = current_count + 1
    
    def _build_all_time_prompt(self, slice_dict: Dict[str, Any]) -> str:
        """Build coach voice prompt for all-time journey insights"""
        return f"""
You are a CAT Quant coach speaking to one learner.
Write a short, friendly insight about their all-time journey using ONLY the JSON you receive.

Tone & style:
- Human and encouraging, like a coach after practice.
- Plain words, no jargon, no decimals.
- Prefer "about 4 out of 10 correct" over "42%".
- Mention at most 2–3 concepts by name.
- No bullets, no tables, no headings. 2–4 sentences total.

Content rules (if present in JSON):
- Start with the big arc: how accuracy has moved from the beginning to now, in "x out of 10" terms.
- Name one strength and one struggle (from concept journeys) with simple language (e.g., "Ratios is steadier now"; "Percentages needs a little rebuilding").
- If coverage relief exists, acknowledge it briefly ("Triangles debt is easing"). If a gap is rising, note it gently.
- If PYQ totals exist, end with a nudge ("You've already tackled about N PYQs—great exposure!").

Strict constraints:
- Do NOT invent numbers or concepts.
- Do NOT show raw percentages, deltas, or decimals.
- Do NOT mention time or speed.
Return plain text only.

Data: {json.dumps(slice_dict, indent=2)}
        """
    
    def _build_recent_prompt(self, slice_dict: Dict[str, Any]) -> str:
        """Build coach voice prompt for recent momentum insights"""
        return f"""
You are a CAT Quant coach speaking to one learner.
Write a short, friendly insight about their recent momentum using ONLY the JSON you receive.

Tone & style:
- Human and encouraging, like a coach reviewing recent practice.
- Plain words, no jargon, no decimals.
- Prefer "about 6 out of 10 correct lately" over "58%".
- Mention at most 1–2 concepts by name.
- No bullets, no tables, no headings. 2–3 sentences total.

Content rules (if present in JSON):
- Start with recent accuracy trend in "x out of 10" terms over the last few sessions.
- Name one concept that's improving or one that needs work (from recent shifts) with simple language.
- If coverage changes exist, acknowledge briefly ("Algebra gaps are shrinking" or "Geometry needs some attention").
- If recent PYQ data exists, end with encouragement ("Nice work on those recent PYQs!").

Strict constraints:
- Do NOT invent numbers or concepts.
- Do NOT show raw percentages, deltas, or decimals.
- Do NOT mention specific session counts or time periods.
Return plain text only.

Data: {json.dumps(slice_dict, indent=2)}
        """
    
    def _build_pre_session_prompt(self, slice_dict: Dict[str, Any]) -> str:
        """Build coach voice prompt for pre-session card"""
        return f"""
You are a CAT Quant coach speaking to one learner before their session.
Return valid JSON with these exact keys: title, progress, way_forward, today.

JSON Schema:
{{
  "title": "string (≤40 chars, 1 emoji, encouraging)",
  "progress": "string (1 sentence about recent accuracy in 'x out of 10' terms)",
  "way_forward": ["string", "string"] (max 2 bullets, coach voice, actionable),
  "today": "string (session preview: difficulty bands + focus concepts + PYQ counts)"
}}

Coach voice rules:
- Use plain words, no jargon, no decimals
- Say "about 6 out of 10 correct" not "58%"
- Be encouraging and specific
- Use ONLY data from the JSON provided

Content guidelines:
- Title: Motivating phrase with emoji (e.g., "Ready to Build 🚀", "Let's Focus 🎯")
- Progress: Recent accuracy trend in human terms
- Way forward: 1-2 actionable bullets based on concept shifts or coverage changes
- Today: Session structure like "3E/6M/3H with Ratios focus; 2×PYQ-1.5"

Strict constraints:
- Return ONLY valid JSON
- Do NOT invent data not in the provided JSON
- Do NOT use percentages or decimals

Data: {json.dumps(slice_dict, indent=2)}
        """
    
    def _fallback_all_time_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Deterministic fallback for all-time insights"""
        overall = slice_dict.get("overall", {})
        acc_start = overall.get("acc_start", 0.0)
        acc_now = overall.get("acc_now", 0.0)
        
        concepts = slice_dict.get("concepts_journey", [])
        pyq_totals = slice_dict.get("pyq_totals", {})
        coverage = slice_dict.get("coverage_alltime", {})
        
        lines = []
        
        # Overall accuracy
        if acc_start > 0:
            acc_change = ((acc_now - acc_start) * 100)
            lines.append(f"Your accuracy improved from {acc_start:.0%} to {acc_now:.0%} ({acc_change:+.0f} points).")
        else:
            lines.append(f"Current accuracy stands at {acc_now:.0%}.")
        
        # Concept journeys
        if concepts:
            lines.append("\n**Concept Progress:**")
            for concept in concepts[:3]:
                delta_str = f"{concept.get('delta', 0):+.2f}"
                lines.append(f"• {concept.get('concept', 'Unknown')}: {concept.get('from', 'Unknown')} → {concept.get('to', 'Unknown')} ({delta_str})")
        
        # Coverage
        relief_pairs = coverage.get("relief", [])
        rising_pairs = coverage.get("rising", [])
        
        if relief_pairs:
            lines.append(f"\n• **Coverage Relief:** Improved in {relief_pairs[0].get('pair', 'key areas')}")
        if rising_pairs:
            lines.append(f"• **Focus Areas:** Need attention in {rising_pairs[0].get('pair', 'some areas')}")
        
        # PYQ totals
        total15 = pyq_totals.get("total15", 0)
        acc15 = pyq_totals.get("acc15", 0.0)
        if total15 > 0:
            lines.append(f"\nCompleted {total15} high-frequency PYQ questions with {acc15:.0%} accuracy.")
        
        return "\n".join(lines)
    
    def _fallback_recent_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Deterministic fallback for recent insights"""
        accuracy_series = slice_dict.get("accuracy_series", [])
        concept_shifts = slice_dict.get("concept_shifts_recent", [])
        coverage_recent = slice_dict.get("coverage_recent", {})
        pyq_recent = slice_dict.get("pyq_recent", {})
        range_sessions = slice_dict.get("range_sessions", 20)
        
        lines = []
        
        # Accuracy trend
        if len(accuracy_series) >= 2:
            start_acc = accuracy_series[0]
            end_acc = accuracy_series[-1]
            trend = "improving" if end_acc > start_acc else "steady"
            lines.append(f"Last {len(accuracy_series)} sessions show {trend} accuracy from {start_acc:.0%} to {end_acc:.0%}.")
        elif len(accuracy_series) == 1:
            lines.append(f"Recent accuracy: {accuracy_series[0]:.0%}.")
        else:
            lines.append("Building momentum with recent sessions.")
        
        # Concept shifts
        if concept_shifts:
            lines.append("\n**Recent Changes:**")
            for shift in concept_shifts[:2]:
                lines.append(f"• {shift.get('concept', 'Unknown')}: {shift.get('note', 'Updated')}")
        
        # Coverage changes
        relief = coverage_recent.get("relief", [])
        rising = coverage_recent.get("rising", [])
        
        if relief:
            lines.append(f"• **Progress:** Relief in {relief[0].get('pair', 'key areas')}")
        if rising:
            lines.append(f"• **Focus:** Rising challenge in {rising[0].get('pair', 'some areas')}")
        
        # PYQ recent
        count15 = pyq_recent.get("count15", 0)
        if count15 > 0:
            acc15 = pyq_recent.get("acc15", 0.0)
            lines.append(f"\nRecent PYQ: {count15} high-frequency questions at {acc15:.0%} accuracy.")
        
        return "\n".join(lines)
    
    def _fallback_pre_session_card(self, slice_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback for pre-session card"""
        accuracy_series = slice_dict.get("accuracy_series", [])
        today_preview = slice_dict.get("today_preview", {})
        concept_shifts = slice_dict.get("concept_shifts", [])
        coverage_change = slice_dict.get("coverage_change", {})
        window = slice_dict.get("window", 5)
        
        # Generate basic progress sentence
        if len(accuracy_series) >= 2:
            start_acc = accuracy_series[0]
            end_acc = accuracy_series[-1] 
            progress = f"Last {len(accuracy_series)}: accuracy {start_acc:.0%}→{end_acc:.0%}."
        elif len(accuracy_series) == 1:
            progress = f"Last session: {accuracy_series[0]:.0%} accuracy."
        else:
            progress = "Ready for your next session."
        
        # Generate way forward bullets (max 2, avoid duplicates)
        way_forward = []
        concepts_mentioned = set()
        
        # Add concept-based bullets
        for shift in concept_shifts[:1]:
            concept = shift.get("concept", "")
            if concept and concept not in concepts_mentioned:
                if shift.get("delta_ready", "").startswith("+"):
                    way_forward.append(f"Build on {concept} progress")
                else:
                    way_forward.append(f"Focus on {concept} concepts")
                concepts_mentioned.add(concept)
        
        # Add coverage-based bullets if space and no duplicates
        if len(way_forward) < 2 and coverage_change:
            pair = coverage_change.get("pair", "")
            if pair:
                pair_concept = pair.split(":")[0] if ":" in pair else pair
                if pair_concept not in concepts_mentioned:
                    way_forward.append(f"Address {pair_concept} gaps")
        
        # Default bullet if nothing specific
        if not way_forward:
            way_forward.append("Continue building on recent progress")
        
        # Generate today preview
        focus_concepts = today_preview.get("focus_concepts", [])
        pyq15_count = today_preview.get("pyq15_count", 0)
        pyq10_count = today_preview.get("pyq10_count", 0)
        
        today_parts = ["3E/6M/3H"]
        if focus_concepts:
            concepts_text = ", ".join(focus_concepts[:2])
            today_parts.append(f"with {concepts_text}")
        if pyq15_count or pyq10_count:
            today_parts.append(f"{pyq15_count}×PYQ-1.5, {pyq10_count}×PYQ-1.0")
        
        return {
            "title": "Ready to Learn 📚",
            "progress": progress,
            "way_forward": way_forward[:2],  # Cap at 2 bullets
            "today": "; ".join(today_parts) + "."
        }
    
    def _validate_card_format(self, card_data: Any) -> bool:
        """Validate pre-session card format"""
        if not isinstance(card_data, dict):
            return False
        
        required_keys = ["title", "progress", "way_forward", "today"]
        for key in required_keys:
            if key not in card_data:
                return False
        
        if not isinstance(card_data["way_forward"], list):
            return False
        
        # Cap way_forward to 2 bullets
        if len(card_data["way_forward"]) > 2:
            card_data["way_forward"] = card_data["way_forward"][:2]
        
        return True

# Global service instance
insight_generator_service = InsightGeneratorService()