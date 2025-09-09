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

# Import the complete canonical taxonomy
try:
    from canonical_taxonomy_data import CANONICAL_TAXONOMY
except ImportError:
    # Fallback - build from CSV if file doesn't exist
    import csv
    import json
    from collections import defaultdict
    from io import StringIO
    
    # This will be replaced by the full taxonomy - showing structure only
    CANONICAL_TAXONOMY = {}

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
                question_types.extend(subcategory_data['types'].keys())
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