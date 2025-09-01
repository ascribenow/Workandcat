#!/usr/bin/env python3
"""
Production Concept Extractor
High-performance LLM-based concept extraction for regular questions to enable PYQ matching
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ProductionConceptExtractor:
    """
    Production-grade concept extraction for regular questions
    Extracts mathematical concepts for advanced PYQ frequency matching
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.concept_cache = {}  # In-memory cache for performance
        if not self.openai_api_key:
            logger.error("OpenAI API key not found for ProductionConceptExtractor")
    
    async def extract_question_concepts(self, question) -> Dict[str, Any]:
        """
        Extract comprehensive mathematical concepts from regular questions
        Optimized for conceptual matching with PYQ questions
        """
        try:
            # Check cache first for performance
            cache_key = f"concepts_{hash(question.stem)}"
            if cache_key in self.concept_cache:
                logger.info(f"📋 Using cached concepts for question {question.id}")
                return self.concept_cache[cache_key]
            
            logger.info(f"🧠 Extracting concepts for regular question {question.id}")
            
            concept_prompt = f"""Analyze this CAT quantitative aptitude question for mathematical concepts and patterns:

Question: {question.stem}
Answer: {question.answer if hasattr(question, 'answer') and question.answer else 'Not provided'}
Subcategory: {question.subcategory if hasattr(question, 'subcategory') else 'Not provided'}
Solution Approach: {question.solution_approach if hasattr(question, 'solution_approach') else 'Not provided'}

Extract precise mathematical concepts for pattern matching with PYQ questions:

1. Core Mathematical Concepts (3-7 specific concepts, not generic topics):
   - Focus on mathematical ideas, formulas, principles
   - Examples: "relative_speed", "compound_interest_formula", "triangle_similarity", "quadratic_roots"

2. Primary Solution Methodology (single most important approach):
   - The main technique/method required to solve
   - Examples: "substitution_method", "unitary_method", "algebraic_manipulation", "geometric_construction"

3. Mathematical Operations (specific operations involved):
   - Actual mathematical operations required
   - Examples: ["multiplication", "division", "square_root", "percentage_calculation", "factorization"]

4. Problem Structure Type (overall pattern):
   - The structural pattern of the problem
   - Examples: "comparison_problem", "optimization_problem", "rate_problem", "geometric_proof"

5. Complexity Indicators (what makes it challenging):
   - Factors that determine difficulty
   - Examples: ["multiple_variables", "indirect_relationships", "multi_step_reasoning", "conditional_logic"]

6. Searchable Keywords (key terms for matching):
   - Important terms that appear in similar problems
   - Examples: ["profit", "loss", "percentage", "speed", "distance", "time"]

Return ONLY valid JSON with exact keys: core_concepts, solution_method, operations, structure_type, complexity_indicators, concept_keywords"""

            try:
                import openai
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert mathematical concept analyzer for CAT questions. Extract precise, specific concepts for pattern matching. Return valid JSON only."},
                        {"role": "user", "content": concept_prompt}
                    ],
                    max_tokens=600,
                    temperature=0.2
                )
                
                concept_text = response.choices[0].message.content.strip()
                
                # Parse LLM response
                try:
                    concepts_data = json.loads(concept_text)
                    
                    # Validate and clean the response
                    validated_concepts = self._validate_and_clean_concepts(concepts_data)
                    
                    # Cache the result for performance
                    self.concept_cache[cache_key] = validated_concepts
                    
                    logger.info(f"✅ Concepts extracted: {len(validated_concepts['core_concepts'])} core concepts")
                    return validated_concepts
                    
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Could not parse concept JSON, using fallback")
                    return await self._fallback_concept_extraction(question)
                
            except Exception as llm_error:
                logger.warning(f"⚠️ LLM concept extraction failed: {llm_error}, using fallback")
                return await self._fallback_concept_extraction(question)
                
        except Exception as e:
            logger.error(f"❌ Error extracting question concepts: {e}")
            return await self._fallback_concept_extraction(question)
    
    def _validate_and_clean_concepts(self, concepts_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean concept extraction results
        """
        # Ensure all required fields exist
        required_fields = {
            "core_concepts": [],
            "solution_method": "general_approach", 
            "operations": [],
            "structure_type": "standard_problem",
            "complexity_indicators": [],
            "concept_keywords": []
        }
        
        for field, default in required_fields.items():
            if field not in concepts_data or not concepts_data[field]:
                concepts_data[field] = default
        
        # Clean and validate arrays
        for array_field in ["core_concepts", "operations", "complexity_indicators", "concept_keywords"]:
            if isinstance(concepts_data[array_field], list):
                # Remove empty strings and ensure lowercase
                concepts_data[array_field] = [
                    item.lower().strip() for item in concepts_data[array_field] 
                    if item and isinstance(item, str) and item.strip()
                ]
            else:
                concepts_data[array_field] = []
        
        # Clean string fields
        for string_field in ["solution_method", "structure_type"]:
            if isinstance(concepts_data[string_field], str):
                concepts_data[string_field] = concepts_data[string_field].lower().strip()
            else:
                concepts_data[string_field] = required_fields[string_field]
        
        return concepts_data
    
    async def _fallback_concept_extraction(self, question) -> Dict[str, Any]:
        """
        Fallback concept extraction using enhanced keyword analysis
        """
        try:
            stem_lower = question.stem.lower() if question.stem else ""
            subcategory = question.subcategory.lower() if hasattr(question, 'subcategory') and question.subcategory else ""
            
            # Enhanced concept mapping based on content analysis
            advanced_concept_mappings = {
                'time_speed_distance': {
                    'triggers': ['speed', 'distance', 'time', 'kmph', 'mph', 'train', 'car', 'travel', 'meet', 'overtake', 'relative'],
                    'core_concepts': ['relative_speed', 'distance_formula', 'time_calculation', 'average_speed'],
                    'solution_method': 'speed_distance_analysis',
                    'operations': ['division', 'multiplication', 'subtraction', 'ratio_calculation'],
                    'structure_type': 'motion_problem',
                    'complexity_indicators': ['relative_motion', 'multiple_entities'],
                    'concept_keywords': ['speed', 'distance', 'time', 'travel', 'relative']
                },
                'percentage': {
                    'triggers': ['percent', '%', 'percentage', 'increase', 'decrease', 'change', 'growth', 'reduction'],
                    'core_concepts': ['percentage_calculation', 'proportional_change', 'percentage_increase', 'percentage_decrease'],
                    'solution_method': 'percentage_formula',
                    'operations': ['multiplication', 'division', 'percentage', 'proportion'],
                    'structure_type': 'percentage_problem',
                    'complexity_indicators': ['compound_changes', 'successive_changes'],
                    'concept_keywords': ['percentage', 'increase', 'decrease', 'change']
                },
                'profit_loss': {
                    'triggers': ['profit', 'loss', 'cost', 'selling', 'cp', 'sp', 'discount', 'markup', 'margin'],
                    'core_concepts': ['cost_price_analysis', 'profit_margin', 'discount_calculation', 'markup_analysis'],
                    'solution_method': 'commercial_mathematics',
                    'operations': ['subtraction', 'percentage', 'ratio', 'proportion'],
                    'structure_type': 'business_problem',
                    'complexity_indicators': ['multiple_transactions', 'compound_discounts'],
                    'concept_keywords': ['profit', 'loss', 'cost', 'selling', 'discount']
                },
                'interest': {
                    'triggers': ['interest', 'principal', 'rate', 'compound', 'simple', 'amount', 'ci', 'si'],
                    'core_concepts': ['simple_interest', 'compound_interest', 'principal_calculation', 'rate_calculation'],
                    'solution_method': 'interest_formula',
                    'operations': ['multiplication', 'exponentiation', 'addition', 'percentage'],
                    'structure_type': 'financial_problem',
                    'complexity_indicators': ['compound_calculation', 'time_periods'],
                    'concept_keywords': ['interest', 'principal', 'rate', 'compound', 'simple']
                },
                'ratio_proportion': {
                    'triggers': ['ratio', 'proportion', 'varies', 'directly', 'inversely', 'partnership', 'mixture'],
                    'core_concepts': ['ratio_analysis', 'proportion_calculation', 'direct_variation', 'inverse_variation'],
                    'solution_method': 'ratio_proportion_method',
                    'operations': ['ratio', 'proportion', 'cross_multiplication', 'division'],
                    'structure_type': 'proportion_problem',
                    'complexity_indicators': ['multiple_ratios', 'compound_proportions'],
                    'concept_keywords': ['ratio', 'proportion', 'varies', 'partnership']
                },
                'algebra': {
                    'triggers': ['equation', 'solve', 'x', 'y', 'variable', 'linear', 'quadratic', 'polynomial'],
                    'core_concepts': ['linear_equations', 'quadratic_equations', 'algebraic_manipulation', 'variable_solving'],
                    'solution_method': 'algebraic_method',
                    'operations': ['addition', 'subtraction', 'multiplication', 'division', 'factorization'],
                    'structure_type': 'algebraic_problem',
                    'complexity_indicators': ['multiple_variables', 'higher_degree'],
                    'concept_keywords': ['equation', 'solve', 'variable', 'algebraic']
                },
                'geometry': {
                    'triggers': ['triangle', 'circle', 'square', 'rectangle', 'angle', 'area', 'perimeter', 'volume'],
                    'core_concepts': ['geometric_shapes', 'area_calculation', 'perimeter_calculation', 'angle_properties'],
                    'solution_method': 'geometric_analysis',
                    'operations': ['multiplication', 'square', 'square_root', 'trigonometry'],
                    'structure_type': 'geometric_problem',
                    'complexity_indicators': ['3d_geometry', 'complex_shapes'],
                    'concept_keywords': ['triangle', 'circle', 'area', 'perimeter', 'angle']
                }
            }
            
            # Find best matching category
            best_match = None
            max_matches = 0
            
            for category, data in advanced_concept_mappings.items():
                matches = sum(1 for trigger in data['triggers'] if trigger in stem_lower or trigger in subcategory)
                if matches > max_matches:
                    max_matches = matches
                    best_match = data
            
            if best_match and max_matches > 0:
                logger.info(f"📋 Fallback concept extraction: {max_matches} keyword matches found")
                return {
                    "core_concepts": best_match['core_concepts'],
                    "solution_method": best_match['solution_method'],
                    "operations": best_match['operations'],
                    "structure_type": best_match['structure_type'],
                    "complexity_indicators": best_match['complexity_indicators'],
                    "concept_keywords": best_match['concept_keywords']
                }
            else:
                # Ultimate fallback
                logger.warning(f"⚠️ No keyword matches found, using generic fallback")
                return {
                    "core_concepts": ["mathematical_problem"],
                    "solution_method": "general_approach",
                    "operations": ["basic_calculation"],
                    "structure_type": "standard_problem",
                    "complexity_indicators": ["standard"],
                    "concept_keywords": ["mathematics", "calculation"]
                }
                
        except Exception as e:
            logger.error(f"❌ Fallback concept extraction failed: {e}")
            return {
                "core_concepts": ["unknown"],
                "solution_method": "unknown",
                "operations": ["unknown"],
                "structure_type": "unknown", 
                "complexity_indicators": ["unknown"],
                "concept_keywords": ["unknown"]
            }
    
    def clear_cache(self):
        """Clear the concept cache for memory management"""
        self.concept_cache.clear()
        logger.info("🗑️ Concept cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_concepts": len(self.concept_cache),
            "memory_usage_estimate": len(str(self.concept_cache))
        }

# Utility functions for integration
async def extract_concepts_for_question(question_id: str) -> Dict[str, Any]:
    """
    Utility function to extract concepts for a single question
    """
    try:
        from database import SessionLocal, Question
        
        db = SessionLocal()
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            
            if not question:
                logger.error(f"Question {question_id} not found for concept extraction")
                return {"success": False, "error": "Question not found"}
            
            extractor = ProductionConceptExtractor()
            concepts = await extractor.extract_question_concepts(question)
            
            return {"success": True, "concepts": concepts}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error extracting concepts for question: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test the concept extractor
    import asyncio
    
    async def test_extractor():
        extractor = ProductionConceptExtractor()
        print("✅ Production Concept Extractor initialized successfully")
        print(f"📊 Cache stats: {extractor.get_cache_stats()}")
    
    asyncio.run(test_extractor())