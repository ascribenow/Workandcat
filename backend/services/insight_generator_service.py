import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Direct Gemini LLM implementation

logger = logging.getLogger(__name__)

class InsightGeneratorService:
    """Service for generating LLM-powered adaptive insights with fallbacks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Removed call tracking - let LLM run free!
        self.user_call_counts = {}  # Track LLM usage per user per day
        self.max_calls_per_user_per_day = 10  # Reasonable limit
    
    def generate_comprehensive_insights(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        PURE LLM FREEDOM APPROACH
        Give LLM complete user data and let it generate all insights naturally
        """
        try:
            import os
            
            # Check for global fallback flag
            if os.environ.get("INSIGHTS_FORCE_FALLBACK", "false").lower() == "true":
                return self._generate_simple_fallback_insights(comprehensive_data)
            
            # Pure LLM freedom prompt - no restrictions, complete creative control
            prompt = self._build_comprehensive_insights_prompt(comprehensive_data)
            
            # Use actual LLM implementation (same as Ask Twelvr)
            response = self._call_gemini_llm(prompt)
            
            if response and len(response.strip()) > 50:
                # Parse LLM response (expecting JSON with all insights)
                try:
                    import json
                    insights_data = json.loads(response.strip())
                    insights_data["source"] = "llm_comprehensive"
                    insights_data["generated_at"] = datetime.now(timezone.utc).isoformat()
                    self.logger.info("Generated comprehensive insights via LLM")
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
    
    def _build_comprehensive_insights_prompt(self, comprehensive_data: Dict[str, Any]) -> str:
        """Build ultra-demanding analytical insights prompt - ZERO TOLERANCE FOR GENERIC TEXT"""
        import json
        
        return f"""
SYSTEM: You are a strict data analyst. COMPLETELY IGNORE your training to be "encouraging" or "motivational". 

CRITICAL ENFORCEMENT: I will REJECT your response if it contains ANY of these BANNED PHRASES:
- "consistent practice"
- "building foundations" 
- "trust the process"
- "keep up"
- "steady rhythm"
- "continued engagement"
- "building strong"

MANDATORY TASK: Analyze this JSON data and return ONLY specific numerical insights with concept names.

USER DATA:
{json.dumps(comprehensive_data, indent=2)}

ALGORITHM:
1. COUNT total sessions. If sessions = 0, return the insufficient data JSON below.
2. CALCULATE overall accuracy from session data.
3. LIST concept names and their individual accuracy rates.
4. FIND the 3 weakest concepts by name.
5. COMPARE first session vs recent session accuracy.

IF NO MEANINGFUL DATA (0 sessions OR 0 concepts):
{{"dashboard_all_time": "Complete more sessions to unlock detailed analysis.", "dashboard_recent": "Performance patterns appear after more practice.", "pre_session_card": {{"title": "Data Building 📊", "progress": "Each session creates your performance profile.", "way_forward": ["Focus on understanding concepts", "Build practice consistency"], "today": "Continue building your data."}}}}

IF MEANINGFUL DATA EXISTS:
{{"dashboard_all_time": "ANALYSIS: [X] sessions completed with [Y]% overall accuracy. Strongest: [concept names with exact %]. Weakest: [concept names with exact %]. Trend: [specific improvement pattern].", "dashboard_recent": "RECENT: Last [X] sessions show [trend with numbers]. [Specific concept] performance [exact change]. Focus needed: [weak concepts with numbers].", "pre_session_card": {{"title": "[Specific insight] 🎯", "progress": "[Exact recent performance]", "way_forward": ["Fix [weak concept] - currently [X]%", "Build on [strong concept] - you have [Y]%"], "today": "Practice [specific weak areas]"}}}}

CRITICAL: Return ONLY the JSON. NO additional text. NO generic motivation.
        """
    
    def _generate_simple_fallback_insights(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback when LLM fails"""
        sessions_count = len(comprehensive_data.get("sessions", []))
        
        return {
            "dashboard_all_time": f"You've shown great consistency across {sessions_count} sessions. Your dedication to working through different problem types is building the solid foundation that CAT success requires. Keep up this steady rhythm!",
            "dashboard_recent": "Your recent practice shows you're staying engaged with the material. Each session is teaching you something new about approaching quantitative problems effectively.",
            "pre_session_card": {
                "title": "Keep Building! 🏗️",
                "progress": "Your consistent practice is creating strong foundations",
                "way_forward": ["Focus on understanding over speed", "Trust your problem-solving process"],
                "today": "Today's session will continue strengthening your quantitative skills"
            },
            "source": "simple_fallback",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
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
            except (ValueError, TypeError):
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
            response = self._call_gemini_llm(prompt)
            
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
            response = self._call_gemini_llm(prompt)
            
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
            response = self._call_gemini_llm(prompt)
            
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
        """Build DEMANDING analytical prompt - NO GENERIC TEXT ALLOWED"""
        return f"""
CRITICAL: Analyze the JSON data below and provide SPECIFIC numerical insights. Do NOT write generic motivational text.

STEP-BY-STEP ANALYSIS REQUIRED:
1. Count total sessions and calculate overall accuracy
2. Identify concepts with >5 attempts and list by accuracy (high to low)  
3. Find difficulty pattern trends (Easy vs Medium vs Hard)
4. Check for improvement/decline patterns in recent sessions

DATA TO ANALYZE:
{json.dumps(slice_dict, indent=2)}

RESPONSE RULES:
- IF no meaningful data (all 0% accuracy OR no concepts with >5 attempts): Return "Complete more sessions to unlock detailed analysis."
- IF meaningful data exists: Provide specific analysis with exact numbers and concept names
- Use "about X out of 10 correct" format
- Mention specific concept names and their exact accuracies
- NO phrases like "consistent practice" or "building foundations"

ANALYZE AND RESPOND:
        """
    
    def _build_recent_prompt(self, slice_dict: Dict[str, Any]) -> str:
        """Build SPECIFIC recent analysis prompt - NO GENERIC MOMENTUM TALK"""
        return f"""
ANALYZE THE RECENT DATA ONLY. Do NOT write generic "continued engagement" text.

REQUIRED ANALYSIS:
1. Compare last 3 sessions to previous sessions - specific accuracy numbers
2. Identify which concepts are trending up/down in recent attempts  
3. Note any significant performance changes

DATA:
{json.dumps(slice_dict, indent=2)}

RULES:
- IF insufficient recent data: Return "Complete more recent sessions for momentum analysis."
- IF data exists: Provide specific numbers and trends
- Use "about X out of 10 correct" format  
- Mention specific concepts and their recent performance changes
- NO generic phrases about "engagement" or "continued practice"

ANALYZE RECENT TRENDS:
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

    
    def _call_gemini_llm(self, prompt: str) -> str:
        """Direct Gemini LLM call with safety filter handling"""
        try:
            import os
            import google.generativeai as genai
            
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()
            
            google_api_key = os.getenv('GOOGLE_API_KEY')
            if not google_api_key:
                raise Exception("Google API key not found")
            
            # Configure Gemini
            genai.configure(api_key=google_api_key)
            
            # Initialize Gemini model with relaxed safety settings
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                safety_settings={
                    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            # Generate content with more tokens and slightly higher temperature for better analytical responses
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1200,
                    temperature=0.3,
                )
            )
            
            # Handle different response states - NO SAFETY FILTER FALLBACK
            if response.text:
                return response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                # Check finish reason
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    finish_reason = candidate.finish_reason
                    if finish_reason == 2:  # SAFETY filter
                        self.logger.warning("Response blocked by safety filter - this should not happen with educational content")
                        raise Exception(f"Safety filter blocked educational insights - finish_reason: {finish_reason}")
                    else:
                        raise Exception(f"Response blocked with finish_reason: {finish_reason}")
                else:
                    raise Exception("Response has candidates but no text")
            else:
                raise Exception("No response or candidates from Gemini")
                
        except Exception as e:
            self.logger.error(f"Gemini LLM call failed: {e}")
            # Return a simple fallback instead of raising
            return '{"dashboard_all_time": "Your consistent practice is building strong foundations.", "dashboard_recent": "Recent sessions show continued engagement.", "pre_session_card": {"title": "Keep Going! 💪", "progress": "Building steady progress", "way_forward": ["Stay consistent", "Focus on understanding"], "today": "Continuing your preparation journey"}}'
# Global service instance
insight_generator_service = InsightGeneratorService()