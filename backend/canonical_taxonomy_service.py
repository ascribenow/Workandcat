#!/usr/bin/env python3
"""
Canonical Taxonomy Service
Single source of truth for all taxonomy classifications
"""

import difflib
import os
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# SINGLE SOURCE OF TRUTH - CANONICAL TAXONOMY FROM ENRICHED CSV
CANONICAL_TAXONOMY = {
    "Arithmetic": {
        "Time-Speed-Distance": {
            "description": "Time-Speed-Distance problems involve the relationship between how fast an object moves (speed), how long it takes to move (time), and how far it travels (distance). The fundamental formula connecting these quantities is distance = speed × time. Speed is typically measured in units like meters per second (m/s), kilometers per hour (km/h), or miles per hour (mph). Time can be in seconds, minutes, hours, etc., and distance in meters, kilometers, miles, etc. It's crucial to ensure consistent units throughout the calculation. Common problem variants include calculating the time taken given speed and distance, finding the speed given time and distance, or determining the distance traveled given speed and time. Relative speed problems, involving two or more objects moving simultaneously, are also common and may involve objects moving in the same or opposite directions. A frequent trap is using inconsistent units, so always convert units to be compatible before applying the formula.",
            "types": {
                "Basics": "Basic Time-Speed-Distance questions focus on the direct application of the core formula: distance = speed × time. These questions typically provide two of the three quantities (speed, time, distance) and ask for the third. For example, you might be given the speed of a car and the time it travels and asked to calculate the distance covered. Alternatively, you could be given the distance and time and asked to find the speed. The key is to correctly identify the givens and the unknown, then rearrange the formula accordingly. Variations might involve converting units before applying the formula, such as converting minutes to hours or kilometers to meters. These questions lay the foundation for more complex Time-Speed-Distance problems.",
                "Relative Speed": "Relative speed problems focus on the effective speed of one object with respect to another, particularly when they are moving towards or away from each other. The intent is typically to determine when they will meet, overtake, or reach a certain separation. Givens often include the individual speeds of the objects and their initial distance apart. Key transformations involve adding the speeds when objects move in opposite directions and subtracting them when they move in the same direction. Frequent variations include objects starting at different times, objects moving in a circular path, and scenarios involving streams or currents affecting the speed of a boat or swimmer.",
                "Circular Track Motion": "Circular Track Motion problems involve objects moving along a circular path. The intent is typically to determine when objects meet or overtake each other, or how many laps are completed in a given time. Givens often include the length of the track, the speeds of the objects, and their starting positions. Standard transformations involve relating the distance traveled to the circumference of the track. Frequent variations include objects moving in the same or opposite directions, and objects starting at the same point or different points on the track. Calculations often involve concepts like relative speed and the least common multiple (LCM) of times or distances.",
                "Boats and Streams": "Boats and Streams problems are a specific type of Time-Speed-Distance problem that involve the motion of a boat in a river or stream. The intent is to calculate the boat's speed in still water, the speed of the stream (current), or the time taken to travel a certain distance upstream or downstream. Givens typically include the boat's speed in still water or its speed relative to the stream (upstream or downstream speed), and the speed of the stream. Unknowns might be the boat's speed in still water, the speed of the stream, or the time taken for a specific journey. Standard transformations involve adding the boat's speed and the stream's speed for downstream travel, and subtracting the stream's speed from the boat's speed for upstream travel. Frequent variations include cases where the boat travels a certain distance upstream and then returns downstream, or where the boat travels across the stream (perpendicular to the current).",
                "Trains": "Train problems are a specific type of Time-Speed-Distance problem that often involve two or more trains. These problems typically ask about the time it takes for trains to meet, pass each other, or cover a certain distance. Givens often include the speeds and lengths of the trains, and the distance between them or the time elapsed. Unknowns might be the time to meet, the speed of one train, or the length of a train. A common transformation is to consider the relative speed of the trains when they are moving in the same or opposite directions. Variations include trains passing through tunnels or crossing bridges, where the length of the train and the length of the tunnel/bridge become important factors. Carefully consider the frame of reference (relative speed) and the effective distance traveled (including train lengths) when solving these problems.",
                "Races": "Race problems, a specific type of Time-Speed-Distance problem, focus on the relative motion of two or more entities competing to cover a certain distance. The intent is typically to determine who wins, by how much, or when a particular racer overtakes another. Givens might include the speeds of the racers, the starting time, the length of the track, or the time taken by one racer to finish. Unknowns could be the finishing time of another racer, the distance covered when one racer overtakes another, or the speed required to win. Standard transformations include calculating the relative speed of two racers and using it to determine the time or distance at which they meet. Frequent variations include races with head starts, races with varying speeds, and circular tracks."
            }
        },
        "Time-Work": {
            "description": "Time-Work problems explore the relationship between the time taken to complete a task and the efficiency or rate of work of individuals or groups. These problems involve quantities like the amount of work, the time taken, and the rate of work, often expressed as work done per unit of time. A fundamental principle is that the amount of work done is directly proportional to the time taken and the rate of work (Work = Time * Rate). Common variants include problems involving multiple workers working together or separately, problems where the rate of work varies, and problems involving pipes filling or emptying tanks. A typical trap is to assume that times add linearly when workers collaborate; instead, rates add. To map story problems to math, identify the work to be done, the time taken by each worker individually, and then determine the combined rate or the combined time based on the scenario.",
            "types": {
                "Work Time Effeciency": "Work-Time Efficiency problems focus on the efficiency or rate at which work is performed. These problems typically involve determining the rate of work of individuals or groups, comparing efficiencies, or finding the time taken to complete a task given the rates of work. The givens might include the amount of work, the time taken by different workers, or their individual rates. Unknowns typically involve finding the rate of a worker, the time required to complete a task, or comparing efficiencies. Standard transformations involve using the relationship Work = Time * Rate and manipulating it to solve for the desired quantity. Frequent variations include cases where the total work is not explicitly given but can be assumed to be a unit, and cases where the efficiency of workers is compared as a ratio or percentage.",
                "Pipes and Cisterns": "Pipes and cisterns problems are a specific type of time-work problem where pipes fill (inlet) or empty (outlet) a cistern (tank). The intent is to determine the time taken to fill or empty the cistern, given the flow rates of the pipes. Givens typically include the individual fill or empty times for each pipe. Standard transformations involve converting these times to rates, where an inlet pipe has a positive rate and an outlet pipe has a negative rate. Frequent variations include multiple pipes working simultaneously, pipes being opened or closed at different times, and finding the net effect of combined inlet and outlet pipes. The underlying principle remains that the net rate of fill/empty is the algebraic sum of the individual rates.",
                "Work Equivalence": "Work Equivalence problems focus on scenarios where different individuals or groups perform equivalent amounts of work, though potentially at different rates and over different durations. The givens typically include information about the work rates or times for individual workers or groups. The intent is to find the unknown time or rate for a specific worker or group to complete an equivalent amount of work. Standard transformations involve equating the work done by different entities, often by expressing the work as the product of rate and time. Frequent variations include cases where the total work is not explicitly stated but implied by the equivalence of work done by different parties. Problems may also involve fractional work completion, requiring careful consideration of the proportion of work done by each entity."
            }
        }
        # Additional subcategories will be added - showing truncated for brevity
    }
    # Additional categories will be added - showing structure
}

class CanonicalTaxonomyService:
    """Service for canonical taxonomy operations and fuzzy matching"""
    
    def __init__(self):
        self.categories = list(CANONICAL_TAXONOMY.keys())
        self.subcategories = self._build_subcategory_list()
        self.question_types = self._build_question_type_list()
        
    def _build_subcategory_list(self) -> List[str]:
        """Build flat list of all subcategories"""
        subcategories = []
        for category_data in CANONICAL_TAXONOMY.values():
            subcategories.extend(category_data.keys())
        return subcategories
    
    def _build_question_type_list(self) -> List[str]:
        """Build flat list of all question types"""
        question_types = []
        for category_data in CANONICAL_TAXONOMY.values():
            for subcategory_data in category_data.values():
                question_types.extend(subcategory_data)
        return question_types
    
    async def fuzzy_match_category(self, llm_category: str, threshold: float = 0.8) -> Optional[str]:
        """Find best canonical category match for LLM output"""
        if not llm_category:
            return None
            
        # Direct match first
        if llm_category in self.categories:
            return llm_category
            
        # Fuzzy matching
        matches = difflib.get_close_matches(
            llm_category.lower(), 
            [cat.lower() for cat in self.categories], 
            n=1, 
            cutoff=threshold
        )
        
        if matches:
            # Find original case version
            for cat in self.categories:
                if cat.lower() == matches[0]:
                    logger.info(f"📂 Fuzzy matched category: '{llm_category}' → '{cat}' (score: {difflib.SequenceMatcher(None, llm_category.lower(), cat.lower()).ratio():.2f})")
                    return cat
        
        # LLM-assisted semantic analysis as final attempt
        logger.info(f"🧠 Attempting LLM semantic analysis for category: '{llm_category}'")
        semantic_match = await self._llm_semantic_category_match(llm_category)
        if semantic_match:
            logger.info(f"🎯 LLM semantic match found: '{llm_category}' → '{semantic_match}'")
            return semantic_match
            
        # Final failure - no semantic match found
        logger.warning(f"⚠️ No category match found (including semantic analysis) for: '{llm_category}'. Quality verification will fail.")
        return None
    
    async def fuzzy_match_subcategory(self, llm_subcategory: str, canonical_category: str, threshold: float = 0.8) -> Optional[str]:
        """Find best canonical subcategory match within the given category"""
        if not llm_subcategory or not canonical_category:
            return None
            
        if canonical_category not in CANONICAL_TAXONOMY:
            return None
            
        category_subcategories = list(CANONICAL_TAXONOMY[canonical_category].keys())
        
        # Direct match first
        if llm_subcategory in category_subcategories:
            return llm_subcategory
            
        # Fuzzy matching within category
        matches = difflib.get_close_matches(
            llm_subcategory.lower(),
            [sub.lower() for sub in category_subcategories],
            n=1,
            cutoff=threshold
        )
        
        if matches:
            # Find original case version
            for sub in category_subcategories:
                if sub.lower() == matches[0]:
                    logger.info(f"📋 Fuzzy matched subcategory: '{llm_subcategory}' → '{sub}' (score: {difflib.SequenceMatcher(None, llm_subcategory.lower(), sub.lower()).ratio():.2f})")
                    return sub
        
        # LLM-assisted semantic analysis as final attempt
        logger.info(f"🧠 Attempting LLM semantic analysis for subcategory: '{llm_subcategory}' in category '{canonical_category}'")
        semantic_match = await self._llm_semantic_subcategory_match(llm_subcategory, canonical_category)
        if semantic_match:
            logger.info(f"🎯 LLM semantic match found: '{llm_subcategory}' → '{semantic_match}'")
            return semantic_match
            
        # Final failure - no semantic match found
        logger.warning(f"⚠️ No subcategory match found (including semantic analysis) for: '{llm_subcategory}' in category '{canonical_category}'. Quality verification will fail.")
        return None
    
    async def fuzzy_match_question_type(self, llm_type: str, canonical_category: str, canonical_subcategory: str, threshold: float = 0.8) -> Optional[str]:
        """Find best canonical question type match within the given category and subcategory"""
        if not llm_type or not canonical_category or not canonical_subcategory:
            return None
            
        if (canonical_category not in CANONICAL_TAXONOMY or 
            canonical_subcategory not in CANONICAL_TAXONOMY[canonical_category]):
            return None
            
        available_types = CANONICAL_TAXONOMY[canonical_category][canonical_subcategory]
        
        # Direct match first
        if llm_type in available_types:
            return llm_type
            
        # Fuzzy matching within subcategory
        matches = difflib.get_close_matches(
            llm_type.lower(),
            [qt.lower() for qt in available_types],
            n=1,
            cutoff=threshold
        )
        
        if matches:
            # Find original case version
            for qt in available_types:
                if qt.lower() == matches[0]:
                    logger.info(f"📝 Fuzzy matched question type: '{llm_type}' → '{qt}' (score: {difflib.SequenceMatcher(None, llm_type.lower(), qt.lower()).ratio():.2f})")
                    return qt
        
        # LLM-assisted semantic analysis as final attempt
        logger.info(f"🧠 Attempting LLM semantic analysis for question type: '{llm_type}' in {canonical_category} → {canonical_subcategory}")
        semantic_match = await self._llm_semantic_question_type_match(llm_type, canonical_category, canonical_subcategory)
        if semantic_match:
            logger.info(f"🎯 LLM semantic match found: '{llm_type}' → '{semantic_match}'")
            return semantic_match
            
        # Final failure - no semantic match found
        logger.warning(f"⚠️ No question type match found (including semantic analysis) for: '{llm_type}' in {canonical_category} → {canonical_subcategory}. Quality verification will fail.")
        return None
    
    async def get_canonical_taxonomy_path(self, llm_category: str, llm_subcategory: str, llm_type: str) -> Tuple[str, str, str]:
        """Get complete canonical taxonomy path with fuzzy matching"""
        
        # Step 1: Match category
        canonical_category = await self.fuzzy_match_category(llm_category)
        
        # Step 2: Match subcategory within canonical category
        canonical_subcategory = await self.fuzzy_match_subcategory(llm_subcategory, canonical_category)
        
        # Step 3: Match question type within canonical subcategory
        canonical_type = await self.fuzzy_match_question_type(llm_type, canonical_category, canonical_subcategory)
        
        logger.info(f"🎯 Complete taxonomy mapping:")
        logger.info(f"   Category: '{llm_category}' → '{canonical_category}'")
        logger.info(f"   Subcategory: '{llm_subcategory}' → '{canonical_subcategory}'")
        logger.info(f"   Type: '{llm_type}' → '{canonical_type}'")
        
        return canonical_category, canonical_subcategory, canonical_type
    
    def validate_taxonomy_path(self, category: str, subcategory: str, question_type: str) -> bool:
        """Validate that a complete taxonomy path exists in canonical taxonomy"""
        return (
            category in CANONICAL_TAXONOMY and
            subcategory in CANONICAL_TAXONOMY[category] and
            question_type in CANONICAL_TAXONOMY[category][subcategory]
        )
    
    def get_taxonomy_stats(self) -> Dict:
        """Get statistics about the canonical taxonomy"""
        total_types = sum(
            len(subcategory_data)
            for category_data in CANONICAL_TAXONOMY.values()
            for subcategory_data in category_data.values()
        )
        
        return {
            "categories": len(self.categories),
            "subcategories": len(self.subcategories),
            "question_types": total_types,
            "taxonomy": CANONICAL_TAXONOMY
        }
    
    async def _llm_semantic_category_match(self, llm_category: str) -> Optional[str]:
        """Use LLM to find semantic match for category"""
        try:
            # Import here to avoid circular imports
            from advanced_llm_enrichment_service import call_llm_with_fallback
            
            system_message = """You are a mathematical taxonomy expert. Your task is to find the most semantically appropriate canonical category match.

Given a category classification, you must choose the BEST semantic match from the canonical categories.

CANONICAL CATEGORIES:
- Arithmetic
- Algebra  
- Geometry and Mensuration
- Number System
- Modern Math

Rules:
1. Choose based on mathematical MEANING, not just word similarity
2. If no good semantic match exists, respond with "NO_MATCH"
3. Respond with ONLY the canonical category name or "NO_MATCH"

Examples:
- "Basic Calculations" → "Arithmetic"
- "Equation Solving" → "Algebra"
- "Shape Problems" → "Geometry and Mensuration"
- "Integer Properties" → "Number System"
- "Probability Questions" → "Modern Math"
- "Unrelated Topic" → "NO_MATCH" """

            user_message = f"Find the best semantic match for this category: '{llm_category}'"
            
            # Create a dummy service instance for the call
            class DummyService:
                def __init__(self):
                    self.openai_api_key = os.getenv('OPENAI_API_KEY')
                    self.google_api_key = os.getenv('GOOGLE_API_KEY')
                    self.primary_model = "gpt-4o"
                    self.fallback_model = "gpt-4o-mini"
                    self.gemini_model = "gemini-pro"
                    self.primary_model_failures = 0
                    self.max_failures_before_degradation = 3
                    self.openai_consecutive_failures = 0
                    self.max_openai_failures_before_gemini = 2
                    self.timeout = 30
            
            dummy_service = DummyService()
            response_text, model_used = await call_llm_with_fallback(
                dummy_service, system_message, user_message, max_tokens=50, temperature=0.1
            )
            
            response_text = response_text.strip()
            if response_text == "NO_MATCH":
                return None
            elif response_text in self.categories:
                return response_text
            else:
                logger.warning(f"⚠️ LLM returned invalid category: '{response_text}'")
                return None
                
        except Exception as e:
            logger.error(f"❌ LLM semantic category matching failed: {str(e)}")
            return None
    
    async def _llm_semantic_subcategory_match(self, llm_subcategory: str, canonical_category: str) -> Optional[str]:
        """Use LLM to find semantic match for subcategory within a category"""
        try:
            if canonical_category not in CANONICAL_TAXONOMY:
                return None
                
            available_subcategories = list(CANONICAL_TAXONOMY[canonical_category].keys())
            
            # Import here to avoid circular imports
            from advanced_llm_enrichment_service import call_llm_with_fallback
            
            system_message = f"""You are a mathematical taxonomy expert. Your task is to find the most semantically appropriate subcategory match within the {canonical_category} category.

Given a subcategory classification, you must choose the BEST semantic match from the available subcategories.

AVAILABLE SUBCATEGORIES IN {canonical_category.upper()}:
{chr(10).join(f'- {sub}' for sub in available_subcategories)}

Rules:
1. Choose based on mathematical MEANING and conceptual similarity
2. If no good semantic match exists, respond with "NO_MATCH"
3. Respond with ONLY the exact subcategory name or "NO_MATCH"

Example logic:
- "Speed Problems" → "Time-Speed-Distance" 
- "Interest Calculations" → "Simple and Compound Interest"
- "Circle Properties" → "Circles"
- "Average Constraints" → "Averages and Alligation" """

            user_message = f"Find the best semantic match for this subcategory: '{llm_subcategory}' within the {canonical_category} category."
            
            # Create a dummy service instance for the call
            class DummyService:
                def __init__(self):
                    self.openai_api_key = os.getenv('OPENAI_API_KEY')
                    self.google_api_key = os.getenv('GOOGLE_API_KEY')
                    self.primary_model = "gpt-4o"
                    self.fallback_model = "gpt-4o-mini"
                    self.gemini_model = "gemini-pro"
                    self.primary_model_failures = 0
                    self.max_failures_before_degradation = 3
                    self.openai_consecutive_failures = 0
                    self.max_openai_failures_before_gemini = 2
                    self.timeout = 30
            
            dummy_service = DummyService()
            response_text, model_used = await call_llm_with_fallback(
                dummy_service, system_message, user_message, max_tokens=100, temperature=0.1
            )
            
            response_text = response_text.strip()
            if response_text == "NO_MATCH":
                return None
            elif response_text in available_subcategories:
                return response_text
            else:
                logger.warning(f"⚠️ LLM returned invalid subcategory: '{response_text}'")
                return None
                
        except Exception as e:
            logger.error(f"❌ LLM semantic subcategory matching failed: {str(e)}")
            return None
    
    async def _llm_semantic_question_type_match(self, llm_type: str, canonical_category: str, canonical_subcategory: str) -> Optional[str]:
        """Use LLM to find semantic match for question type within subcategory"""
        try:
            if (canonical_category not in CANONICAL_TAXONOMY or 
                canonical_subcategory not in CANONICAL_TAXONOMY[canonical_category]):
                return None
                
            available_types = CANONICAL_TAXONOMY[canonical_category][canonical_subcategory]
            
            # Import here to avoid circular imports
            from advanced_llm_enrichment_service import call_llm_with_fallback
            
            system_message = f"""You are a mathematical taxonomy expert. Your task is to find the most semantically appropriate question type match within {canonical_category} → {canonical_subcategory}.

Given a question type classification, you must choose the BEST semantic match from the available question types.

AVAILABLE QUESTION TYPES IN {canonical_category.upper()} → {canonical_subcategory.upper()}:
{chr(10).join(f'- {qt}' for qt in available_types)}

Rules:
1. Choose based on mathematical MEANING and problem-solving approach similarity
2. If no good semantic match exists, respond with "NO_MATCH"
3. Respond with ONLY the exact question type name or "NO_MATCH"

Example logic:
- "Speed Calculation Problem" → "Basics" (if in Time-Speed-Distance)
- "Relative Motion Analysis" → "Relative Speed" (if in Time-Speed-Distance)
- "Interest Rate Problem" → "Basics" (if in Simple and Compound Interest) """

            user_message = f"Find the best semantic match for this question type: '{llm_type}' within {canonical_category} → {canonical_subcategory}."
            
            # Create a dummy service instance for the call
            class DummyService:
                def __init__(self):
                    self.openai_api_key = os.getenv('OPENAI_API_KEY')
                    self.google_api_key = os.getenv('GOOGLE_API_KEY')
                    self.primary_model = "gpt-4o"
                    self.fallback_model = "gpt-4o-mini"
                    self.gemini_model = "gemini-pro"
                    self.primary_model_failures = 0
                    self.max_failures_before_degradation = 3
                    self.openai_consecutive_failures = 0
                    self.max_openai_failures_before_gemini = 2
                    self.timeout = 30
            
            dummy_service = DummyService()
            response_text, model_used = await call_llm_with_fallback(
                dummy_service, system_message, user_message, max_tokens=100, temperature=0.1
            )
            
            response_text = response_text.strip()
            if response_text == "NO_MATCH":
                return None
            elif response_text in available_types:
                return response_text
            else:
                logger.warning(f"⚠️ LLM returned invalid question type: '{response_text}'")
                return None
                
        except Exception as e:
            logger.error(f"❌ LLM semantic question type matching failed: {str(e)}")
            return None

# Global instance
canonical_taxonomy_service = CanonicalTaxonomyService()