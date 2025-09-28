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
        # Removed call tracking - let LLM run free!
    
    def generate_comprehensive_insights(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        PURE LLM FREEDOM APPROACH
        Give LLM complete user data and let it generate all insights naturally
        """
        try:
            from services.llm_utils import call_llm_with_fallback
            import os
            
            # Check for global fallback flag
            if os.environ.get("INSIGHTS_FORCE_FALLBACK", "false").lower() == "true":
                return self._generate_simple_fallback_insights(comprehensive_data)
            
            # Pure LLM freedom prompt - no restrictions, complete creative control
            prompt = self._build_comprehensive_insights_prompt(comprehensive_data)
            
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o",  # Best model for comprehensive analysis
                model_fallback="gemini-2.5-flash",
                max_tokens=800,  # Generous tokens for comprehensive insights
                timeout=20  # Adequate time for analysis
            )
            
            if response and len(response.strip()) > 50:
                # Parse LLM response (expecting JSON with all insights)
                try:
                    import json
                    insights_data = json.loads(response.strip())
                    insights_data["source"] = "llm_comprehensive"
                    insights_data["generated_at"] = datetime.now(timezone.utc).isoformat()
                    self.logger.info(f"Generated comprehensive insights via LLM")
                    return insights_data
                except json.JSONDecodeError:
                    # If not JSON, treat as markdown and structure it
                    self.logger.warning("LLM returned non-JSON, structuring response")
                    return {
                        "dashboard_all_time": response.strip(),
                        "dashboard_recent": "Your recent progress continues to build on your foundations.",
                        "pre_session_card": {
                            "title": "Ready to Learn 🎯",
                            "progress": "Building on your consistent preparation",
                            "way_forward": ["Stay focused", "Trust the process"],
                            "today": "Today's session will continue your growth"
                        },
                        "source": "llm_comprehensive_markdown",
                        "generated_at": datetime.now(timezone.utc).isoformat()
                    }
            else:
                return self._generate_simple_fallback_insights(comprehensive_data)
                
        except Exception as e:
            self.logger.error(f"Error in comprehensive insights generation: {e}")
            return self._generate_simple_fallback_insights(comprehensive_data)
        
    def _percent_to_human(self, accuracy: float) -> str:
        """Convert 0.42 -> 'about 4 out of 10 correct'"""
        if accuracy is None:
            return "about half right"
        out_of_10 = max(0, min(10, round(accuracy * 10)))
        return f"about {out_of_10} out of 10 correct"
    
    def _sanitize_coach_response(self, response: str) -> str:
        """Remove any technical formatting that slipped through - ENHANCED"""
        if not response:
            return response
            
        import re
        
        # Convert percentages to human format
        def convert_percentage(match):
            percent_str = match.group()
            try:
                if '.' in percent_str:
                    # Handle decimals like "42.3%" or "0.42"
                    num = float(percent_str.replace('%', ''))
                    if num > 1:  # Assume it's already a percentage
                        out_of_10 = max(0, min(10, round(num/10)))
                    else:  # Assume it's a decimal like 0.42
                        out_of_10 = max(0, min(10, round(num*10)))
                else:
                    # Handle whole percentages like "42%"
                    num = int(percent_str.replace('%', ''))
                    out_of_10 = max(0, min(10, round(num/10)))
                return f"about {out_of_10} out of 10"
            except:
                return "about half"
        
        # Apply conversions - more aggressive
        response = re.sub(r'\d+\.\d+%?', convert_percentage, response)
        response = re.sub(r'\d+%', convert_percentage, response)
        
        # Remove technical formatting more aggressively
        response = re.sub(r'^\s*[-*•]\s+', '', response, flags=re.MULTILINE)
        response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)  # Remove bold markdown
        
        # Remove technical deltas, scores, and parenthetical technical info
        response = re.sub(r'\([+-]?\d+\.?\d*\s*(points?|delta?|score?|%)\)', '', response)
        response = re.sub(r'[+-]?\d+\.?\d*\s*(points?|delta?|score?)', '', response)
        response = re.sub(r'\([+-]?\d+\s*points?\)', '', response)  # Remove "(+42 points)" type
        response = re.sub(r'[+-]\d+\s*points?', '', response)  # Remove "+42 points" type
        
        # Convert remaining technical patterns to coach voice
        response = re.sub(r'accuracy.*from.*\d+%.*to.*\d+%', 'your performance has been changing', response, flags=re.IGNORECASE)
        response = re.sub(r'\d+%.*to.*\d+%', 'your progress has been developing', response, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and punctuation
        response = re.sub(r'\s+', ' ', response).strip()
        response = re.sub(r'\s*:\s*', ': ', response)  # Clean up colons
        
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
                # COACH VOICE: Sanitize any technical formatting
                return self._sanitize_coach_response(response.strip())
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
                # COACH VOICE: Sanitize any technical formatting
                return self._sanitize_coach_response(response.strip())
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
                        # COACH VOICE: Sanitize each field in the JSON
                        for field in ["progress", "today"]:
                            if field in card_data and isinstance(card_data[field], str):
                                card_data[field] = self._sanitize_coach_response(card_data[field])
                        
                        # Sanitize way_forward bullets
                        if "way_forward" in card_data and isinstance(card_data["way_forward"], list):
                            card_data["way_forward"] = [
                                self._sanitize_coach_response(bullet) if isinstance(bullet, str) else bullet
                                for bullet in card_data["way_forward"]
                            ]
                        
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
- Do NOT show raw percentages like "42%" or decimals like "0.42" - use "about X out of 10" instead.
- Do NOT use bullets (•), technical deltas (+/-), or database formatting.
- Do NOT mention time or speed.
- ALWAYS convert accuracy numbers to "about X out of 10 correct" format.
Return plain text only - no markdown, no bullets, no technical formatting.

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
- Do NOT show raw percentages like "58%" or decimals like "0.58" - use "about X out of 10" instead.
- Do NOT use bullets (•), technical deltas (+/-), or database formatting.
- Do NOT mention specific session counts or time periods.
- ALWAYS convert accuracy to "about X out of 10 correct" format.
Return plain text only - no markdown, no bullets, no technical formatting.

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
- Do NOT use percentages like "42%" or decimals like "0.42" - use "about X out of 10" instead
- Do NOT use technical codes like "3E/6M/3H" - use plain language like "mixed difficulty"

Data: {json.dumps(slice_dict, indent=2)}
        """
    
    def _fallback_all_time_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Deterministic fallback for all-time insights (coach voice)"""
        total_sessions = slice_dict.get('total_sessions', 0)
        accuracy_series = slice_dict.get('accuracy_series', [])
        
        # Create coach voice based on actual data
        if accuracy_series and len(accuracy_series) >= 2:
            start_acc = accuracy_series[0]
            end_acc = accuracy_series[-1]
            start_human = self._percent_to_human(start_acc)
            end_human = self._percent_to_human(end_acc)
            
            if end_acc > start_acc:
                return f"Your journey has been impressive! You started around {start_human} and you're now hitting {end_human}. That upward trend shows your hard work is paying off. The concepts are clicking, and your problem-solving approach is getting sharper. Keep this momentum—you're building exactly the skills CAT demands."
            else:
                return f"You've tackled {total_sessions} sessions with determination, moving from {start_human} to {end_human}. While the numbers may look flat, you're actually working through tougher concepts now—that's growth. Your persistence through challenging material is exactly what separates good preparation from great preparation."
        else:
            sessions_text = f"{total_sessions} sessions" if total_sessions > 0 else "your practice sessions"
            return f"You've built a solid foundation through {sessions_text} of consistent work. Every question you've tackled has taught you something new about problem-solving patterns. That steady rhythm you've established is your secret weapon—keep trusting the process."
    
    def _fallback_recent_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Deterministic fallback for recent insights (coach voice)"""
        accuracy_series = slice_dict.get("accuracy_series", [])
        concept_shifts = slice_dict.get("concept_shifts_recent", [])
        
        # Simple coach voice based on data
        if len(accuracy_series) >= 2:
            start_acc = accuracy_series[0]
            end_acc = accuracy_series[-1]
            start_human = self._percent_to_human(start_acc)
            end_human = self._percent_to_human(end_acc)
            
            if end_acc > start_acc:
                return f"Your recent sessions are trending upward, moving from {start_human} to {end_human}. That upward momentum is exactly what we want to see—let's keep it rolling."
            else:
                return f"Recent accuracy has dipped a bit, going from {start_human} to {end_human}. This happens when questions get tougher—we'll steady the ship and build back up."
        
        # If no series data, focus on concepts
        if concept_shifts:
            concept = concept_shifts[0].get('concept', 'key areas')
            return f"You're working through adjustments in {concept} and similar areas. This kind of focused practice is exactly how improvement happens—stay with it."
        
        # Generic encouraging fallback
        return "Your recent work shows good consistency and engagement with the material. That steady practice rhythm is building the foundation for bigger breakthroughs ahead."
    
    def _fallback_pre_session_card(self, slice_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback for pre-session card (coach voice)"""
        accuracy_series = slice_dict.get("accuracy_series", [])
        today_preview = slice_dict.get("today_preview", {})
        concept_shifts = slice_dict.get("concept_shifts", [])
        
        # Coach voice progress based on accuracy
        if len(accuracy_series) >= 2:
            start_acc = accuracy_series[0]
            end_acc = accuracy_series[-1]
            start_human = self._percent_to_human(start_acc)
            end_human = self._percent_to_human(end_acc)
            progress = f"Last {len(accuracy_series)}: {start_human} to {end_human} — steady work."
        elif len(accuracy_series) == 1:
            acc_human = self._percent_to_human(accuracy_series[0])
            progress = f"Last session: {acc_human} — good effort."
        else:
            progress = "Ready to build on your preparation so far."
        
        # Coach voice way forward (max 2 bullets)
        way_forward = []
        
        if concept_shifts:
            concept = concept_shifts[0].get("concept", "key areas")
            status = concept_shifts[0].get("status", "")
            if status == "Strong":
                way_forward.append(f"Keep {concept} momentum going")
            else:
                way_forward.append(f"Work on {concept} fundamentals")
        
        # Add a second encouraging bullet
        if len(way_forward) < 2:
            way_forward.append("Stay focused and trust the process")
        
        # Today's session preview (coach style)
        focus_concepts = today_preview.get("focus_concepts", ["Quantitative Practice"])
        today = f"Today: Mixed practice with {', '.join(focus_concepts[:2])}"
        if len(focus_concepts) > 2:
            today += " + more"
        
        return {
            "title": "Let's Focus 🎯",
            "progress": progress,
            "way_forward": way_forward[:2],
            "today": today,
            "source": "fallback",
            "prompt_version": "v1.0_fallback"
        }
    
    def _build_comprehensive_insights_prompt(self, comprehensive_data: Dict[str, Any]) -> str:
        """Build comprehensive prompt for pure LLM freedom approach"""
        return f"""
You are a CAT Quant coach with complete creative freedom. Generate comprehensive insights for this learner.

You have access to ALL their data - use it creatively to provide the most helpful insights possible.

Generate a JSON response with these sections:
1. "dashboard_all_time": Comprehensive journey overview (markdown, 3-4 sentences)
2. "dashboard_recent": Recent momentum analysis (markdown, 2-3 sentences) 
3. "pre_session_card": {{
   "title": "Motivating title with emoji (≤40 chars)",
   "progress": "Recent progress summary",
   "way_forward": ["actionable tip 1", "actionable tip 2"],
   "today": "Session preview with focus areas"
}}

Coach voice guidelines:
- Be encouraging and specific
- Use "about X out of 10 correct" instead of percentages
- Mention concepts by name when relevant
- No technical jargon or formatting
- Focus on growth and momentum

Complete user data: {json.dumps(comprehensive_data, indent=2)}

Return ONLY valid JSON with all three sections.
        """
    
    def _generate_simple_fallback_insights(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback when LLM is unavailable"""
        return {
            "dashboard_all_time": "You're building solid foundations through consistent practice. Every session teaches you something new about problem-solving patterns. Keep trusting the process—your steady rhythm is your secret weapon.",
            "dashboard_recent": "Your recent work shows good consistency and engagement with the material. That steady practice rhythm is building the foundation for bigger breakthroughs ahead.",
            "pre_session_card": {
                "title": "Ready to Learn 🎯",
                "progress": "Building on your consistent preparation",
                "way_forward": ["Stay focused on fundamentals", "Trust the process"],
                "today": "Today's session will continue your growth"
            },
            "source": "simple_fallback",
            "generated_at": datetime.now(timezone.utc).isoformat()
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