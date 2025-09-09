#!/usr/bin/env python3
"""
Canonical Taxonomy Service
Single source of truth for all taxonomy classifications
"""

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
    
    async def match_category(self, llm_category: str) -> Optional[str]:
        """Find best canonical category match using Direct + Enhanced Semantic matching"""
        if not llm_category:
            return None
            
        # Direct match first
        if llm_category in self.categories:
            logger.info(f"✅ Direct category match: '{llm_category}'")
            return llm_category
        
        # Enhanced LLM-assisted semantic analysis with descriptions
        logger.info(f"🧠 Attempting enhanced semantic analysis for category: '{llm_category}'")
        semantic_match = await self._enhanced_semantic_category_match(llm_category)
        if semantic_match:
            logger.info(f"🎯 Enhanced semantic match found: '{llm_category}' → '{semantic_match}'")
            return semantic_match
            
        # Final failure - no semantic match found
        logger.warning(f"⚠️ No category match found for: '{llm_category}'. Quality verification will fail.")
        return None
    
    async def match_subcategory(self, llm_subcategory: str, canonical_category: str) -> Optional[str]:
        """Find best canonical subcategory match using Direct + Enhanced Semantic matching"""
        if not llm_subcategory or not canonical_category:
            return None
            
        if canonical_category not in CANONICAL_TAXONOMY:
            return None
            
        category_subcategories = list(CANONICAL_TAXONOMY[canonical_category].keys())
        
        # Direct match first
        if llm_subcategory in category_subcategories:
            logger.info(f"✅ Direct subcategory match: '{llm_subcategory}'")
            return llm_subcategory
        
        # Enhanced LLM-assisted semantic analysis with descriptions
        logger.info(f"🧠 Attempting enhanced semantic analysis for subcategory: '{llm_subcategory}' in category '{canonical_category}'")
        semantic_match = await self._enhanced_semantic_subcategory_match(llm_subcategory, canonical_category)
        if semantic_match:
            logger.info(f"🎯 Enhanced semantic match found: '{llm_subcategory}' → '{semantic_match}'")
            return semantic_match
            
        # Final failure - no semantic match found
        logger.warning(f"⚠️ No subcategory match found for: '{llm_subcategory}' in category '{canonical_category}'. Quality verification will fail.")
        return None
    
    async def match_question_type(self, llm_type: str, canonical_category: str, canonical_subcategory: str) -> Optional[str]:
        """Find best canonical question type match using Direct + Enhanced Semantic matching"""
        if not llm_type or not canonical_category or not canonical_subcategory:
            return None
            
        if (canonical_category not in CANONICAL_TAXONOMY or 
            canonical_subcategory not in CANONICAL_TAXONOMY[canonical_category]):
            return None
            
        available_types = list(CANONICAL_TAXONOMY[canonical_category][canonical_subcategory]['types'].keys())
        
        # Direct match first
        if llm_type in available_types:
            logger.info(f"✅ Direct question type match: '{llm_type}'")
            return llm_type
        
        # Enhanced LLM-assisted semantic analysis with descriptions
        logger.info(f"🧠 Attempting enhanced semantic analysis for question type: '{llm_type}' in {canonical_category} → {canonical_subcategory}")
        semantic_match = await self._enhanced_semantic_question_type_match(llm_type, canonical_category, canonical_subcategory)
        if semantic_match:
            logger.info(f"🎯 Enhanced semantic match found: '{llm_type}' → '{semantic_match}'")
            return semantic_match
            
        # Final failure - no semantic match found
        logger.warning(f"⚠️ No question type match found for: '{llm_type}' in {canonical_category} → {canonical_subcategory}. Quality verification will fail.")
        return None
    
    async def get_canonical_taxonomy_path(self, llm_category: str, llm_subcategory: str, llm_type: str) -> Tuple[str, str, str]:
        """Get complete canonical taxonomy path with enhanced semantic matching"""
        
        # Step 1: Match category using enhanced semantic matching
        canonical_category = await self.match_category(llm_category)
        
        # Step 2: Match subcategory using enhanced semantic matching
        canonical_subcategory = await self.match_subcategory(llm_subcategory, canonical_category)
        
        # Step 3: Match question type using enhanced semantic matching
        canonical_type = await self.match_question_type(llm_type, canonical_category, canonical_subcategory)
        
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
            question_type in CANONICAL_TAXONOMY[category][subcategory]['types']
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
    
    async def _enhanced_semantic_category_match(self, llm_category: str) -> Optional[str]:
        """Use enhanced LLM semantic matching for category with 2 retries"""
        
        # Retry logic: 2 attempts
        for attempt in range(2):
            try:
                # Import here to avoid circular imports
                from advanced_llm_enrichment_service import call_llm_with_fallback
                
                # Build comprehensive context with all categories
                categories_context = []
                for category in self.categories:
                    # Get sample subcategories to provide context
                    sample_subcategories = list(CANONICAL_TAXONOMY[category].keys())[:3]
                    categories_context.append(f"- {category}: {', '.join(sample_subcategories)}...")
                
                system_message = f"""You are a mathematical taxonomy expert with deep understanding of CAT quantitative reasoning categories.

Your task is to find the most semantically appropriate canonical category match using detailed mathematical context.

AVAILABLE CANONICAL CATEGORIES WITH CONTEXT:
{chr(10).join(categories_context)}

ENHANCED MATCHING RULES:
1. Analyze the mathematical DOMAIN and CONCEPTUAL AREA of the input category
2. Consider the underlying mathematical principles and problem-solving approaches
3. Match based on MATHEMATICAL MEANING and CONCEPTUAL SIMILARITY
4. If no good semantic match exists, respond with "NO_MATCH"
5. Respond with ONLY the exact canonical category name or "NO_MATCH"

EXAMPLES OF SEMANTIC MATCHING:
- "Basic Calculations" → "Arithmetic" (computational focus)
- "Equation Solving" → "Algebra" (algebraic manipulation)
- "Shape Problems" → "Geometry and Mensuration" (spatial reasoning)
- "Integer Properties" → "Number System" (number theory)
- "Probability Questions" → "Modern Math" (advanced concepts)
- "Data Analysis" → "Modern Math" (statistical concepts)
- "Unrelated Physics Topic" → "NO_MATCH" (outside mathematical taxonomy)"""

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
                    logger.info(f"🤖 LLM semantic category matching: NO_MATCH for '{llm_category}' (attempt {attempt + 1})")
                    if attempt == 1:  # Last attempt
                        return None
                    continue
                elif response_text in self.categories:
                    logger.info(f"✅ Enhanced semantic category match: '{llm_category}' → '{response_text}' (attempt {attempt + 1}, model: {model_used})")
                    return response_text
                else:
                    logger.warning(f"⚠️ LLM returned invalid category: '{response_text}' (attempt {attempt + 1})")
                    if attempt == 1:  # Last attempt
                        return None
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Enhanced semantic category matching failed (attempt {attempt + 1}): {str(e)}")
                if attempt == 1:  # Last attempt
                    return None
                continue
        
        return None
    
    async def _enhanced_semantic_subcategory_match(self, llm_subcategory: str, canonical_category: str) -> Optional[str]:
        """Use enhanced LLM semantic matching for subcategory using descriptions with 2 retries"""
        
        if canonical_category not in CANONICAL_TAXONOMY:
            return None
            
        available_subcategories = list(CANONICAL_TAXONOMY[canonical_category].keys())
        
        # Retry logic: 2 attempts
        for attempt in range(2):
            try:
                # Import here to avoid circular imports
                from advanced_llm_enrichment_service import call_llm_with_fallback
                
                # Build comprehensive context with subcategory descriptions
                subcategories_context = []
                for subcategory in available_subcategories:
                    description = CANONICAL_TAXONOMY[canonical_category][subcategory]['description']
                    # Truncate description for context (first 150 chars)
                    short_desc = description[:150] + "..." if len(description) > 150 else description
                    subcategories_context.append(f"- {subcategory}: {short_desc}")
                
                system_message = f"""You are a mathematical taxonomy expert with deep understanding of CAT quantitative subcategories within {canonical_category}.

Your task is to find the most semantically appropriate subcategory match using detailed descriptions.

AVAILABLE SUBCATEGORIES IN {canonical_category.upper()} WITH DESCRIPTIONS:
{chr(10).join(subcategories_context)}

ENHANCED MATCHING RULES:
1. Analyze the mathematical CONCEPTS and PROBLEM TYPES described in the input
2. Match based on the MATHEMATICAL DOMAIN and PROBLEM-SOLVING APPROACH
3. Consider the CONCEPTUAL SIMILARITY between input and subcategory descriptions
4. Use the detailed descriptions to understand the true mathematical focus
5. If no good semantic match exists, respond with "NO_MATCH"
6. Respond with ONLY the exact subcategory name or "NO_MATCH"

EXAMPLES OF SEMANTIC MATCHING:
- "Speed Problems" → "Time-Speed-Distance" (motion and velocity focus)
- "Interest Calculations" → "Simple and Compound Interest" (financial mathematics)
- "Circle Properties" → "Circles" (circular geometry focus)
- "Mixture Analysis" → "Averages and Alligation" (combination problems)"""

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
                    logger.info(f"🤖 LLM semantic subcategory matching: NO_MATCH for '{llm_subcategory}' in {canonical_category} (attempt {attempt + 1})")
                    if attempt == 1:  # Last attempt
                        return None
                    continue
                elif response_text in available_subcategories:
                    logger.info(f"✅ Enhanced semantic subcategory match: '{llm_subcategory}' → '{response_text}' (attempt {attempt + 1}, model: {model_used})")
                    return response_text
                else:
                    logger.warning(f"⚠️ LLM returned invalid subcategory: '{response_text}' (attempt {attempt + 1})")
                    if attempt == 1:  # Last attempt
                        return None
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Enhanced semantic subcategory matching failed (attempt {attempt + 1}): {str(e)}")
                if attempt == 1:  # Last attempt
                    return None
                continue
        
        return None
    
    async def _enhanced_semantic_question_type_match(self, llm_type: str, canonical_category: str, canonical_subcategory: str) -> Optional[str]:
        """Use enhanced LLM semantic matching for question type using descriptions with 2 retries"""
        
        if (canonical_category not in CANONICAL_TAXONOMY or 
            canonical_subcategory not in CANONICAL_TAXONOMY[canonical_category]):
            return None
            
        available_types = list(CANONICAL_TAXONOMY[canonical_category][canonical_subcategory]['types'].keys())
        
        # Retry logic: 2 attempts
        for attempt in range(2):
            try:
                # Import here to avoid circular imports
                from advanced_llm_enrichment_service import call_llm_with_fallback
                
                # Build comprehensive context with question type descriptions
                types_context = []
                for question_type in available_types:
                    description = CANONICAL_TAXONOMY[canonical_category][canonical_subcategory]['types'][question_type]
                    # Truncate description for context (first 200 chars)
                    short_desc = description[:200] + "..." if len(description) > 200 else description
                    types_context.append(f"- {question_type}: {short_desc}")
                
                system_message = f"""You are a mathematical taxonomy expert with deep understanding of CAT question types within {canonical_category} → {canonical_subcategory}.

Your task is to find the most semantically appropriate question type match using detailed Type of Question Descriptions.

AVAILABLE QUESTION TYPES IN {canonical_category.upper()} → {canonical_subcategory.upper()} WITH DESCRIPTIONS:
{chr(10).join(types_context)}

ENHANCED MATCHING RULES:
1. Analyze the PROBLEM-SOLVING APPROACH and MATHEMATICAL TECHNIQUES described in the input
2. Match based on the QUESTION STRUCTURE and SOLUTION METHODOLOGY
3. Consider the CONCEPTUAL COMPLEXITY and PROBLEM CHARACTERISTICS
4. Use the detailed Type of Question Descriptions to understand the true problem focus
5. If no good semantic match exists, respond with "NO_MATCH"
6. Respond with ONLY the exact question type name or "NO_MATCH"

EXAMPLES OF SEMANTIC MATCHING:
- "Speed Calculation Problem" → "Basics" (fundamental applications)
- "Relative Motion Analysis" → "Relative Speed" (multi-object movement)
- "Complex Interest Problem" → "Compound Interest" (advanced interest calculations)
- "Basic Ratio Comparison" → "Simple Ratios" (fundamental ratio operations)"""

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
                    logger.info(f"🤖 LLM semantic question type matching: NO_MATCH for '{llm_type}' in {canonical_category} → {canonical_subcategory} (attempt {attempt + 1})")
                    if attempt == 1:  # Last attempt
                        return None
                    continue
                elif response_text in available_types:
                    logger.info(f"✅ Enhanced semantic question type match: '{llm_type}' → '{response_text}' (attempt {attempt + 1}, model: {model_used})")
                    return response_text
                else:
                    logger.warning(f"⚠️ LLM returned invalid question type: '{response_text}' (attempt {attempt + 1})")
                    if attempt == 1:  # Last attempt
                        return None
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Enhanced semantic question type matching failed (attempt {attempt + 1}): {str(e)}")
                if attempt == 1:  # Last attempt
                    return None
                continue
        
        return None

# Global instance
canonical_taxonomy_service = CanonicalTaxonomyService()