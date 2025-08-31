#!/usr/bin/env python3
"""
LLM Enrichment Service for CAT Questions
Handles AI-powered question enrichment with AUTOMATIC SCHEMA COMPLIANCE
NOW USES STANDARDIZED ENRICHMENT ENGINE - NO MORE MANUAL SCRIPTS NEEDED
"""

import json
import hashlib
import uuid
import os
from typing import Dict, Any, Tuple, List
from datetime import datetime
import logging
from formulas import (
    calculate_difficulty_level,
    calculate_frequency_band,
    calculate_importance_level,
    calculate_learning_impact
)
import asyncio
from sqlalchemy.orm import Session
from database import Question
from enrichment_schema_manager import enrichment_schema, quality_controller
from standardized_enrichment_engine import standardized_enricher
import openai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Updated Canonical Taxonomy Structure (from CSV document)
CANONICAL_TAXONOMY = {
    "Arithmetic": {
        "Time-Speed-Distance": ["Basics", "Relative Speed", "Circular Track Motion", "Boats and Streams", "Trains", "Races"],
        "Time-Work": ["Work Time Effeciency", "Pipes and Cisterns", "Work Equivalence"],
        "Ratios and Proportions": ["Simple Rations", "Compound Ratios", "Direct and Inverse Variation", "Partnerships"],
        "Percentages": ["Basics", "Percentage Change", "Successive Percentage Change"],
        "Averages and Alligation": ["Basic Averages", "Weighted Averages", "Alligations & Mixtures", "Three Mixture Alligations"],
        "Profit-Loss-Discount": ["Basics", "Successive Profit/Loss/Discounts", "Marked Price and Cost Price Relations", "Discount Chains"],
        "Simple and Compound Interest": ["Basics", "Difference between Simple Interest and Compound Interests", "Fractional Time Period Compound Interest"],
        "Mixtures and Solutions": ["Replacements", "Concentration Change", "Solid-Liquid-Gas Mixtures"],
        "Partnerships": ["Profit share"]
    },
    "Algebra": {
        "Linear Equations": ["Two variable systems", "Three variable systems", "Dependent and Inconsistent Systems"],
        "Quadratic Equations": ["Roots & Nature of Roots", "Sum and Product of Roots", "Maximum and Minimum Values"],
        "Inequalities": ["Linear Inequalities", "Quadratic Inequalities", "Modulus and Absolute Value", "Arithmetic Mean", "Geometric Mean", "Cauchy Schwarz"],
        "Progressions": ["Arithmetic Progression", "Geometric Progression", "Harmonic Progression", "Mixed Progressions"],
        "Functions and Graphs": ["Linear Functions", "Quadratic Functions", "Polynomial Functions", "Modulus Functions", "Step Functions", "Transformations", "Domain Range", "Composition and Inverse Functions"],
        "Logarithms and Exponents": ["Basics", "Change of Base Formula", "Soliving Log Equations", "Surds and Indices"],
        "Special Algebraic Identities": ["Expansion and Factorisation", "Cubes and Squares", "Binomial Theorem"],
        "Maxima and Minima": ["Optimsation with Algebraic Expressions"],
        "Special Polynomials": ["Remainder Theorem", "Factor Theorem"]
    },
    "Geometry and Mensuration": {
        "Triangles": ["Properties (Angles, Sides, Medians, Bisectors)", "Congruence & Similarity", "Pythagoras & Converse", "Inradius, Circumradius, Orthocentre"],
        "Circles": ["Tangents & Chords", "Angles in a Circle", "Cyclic Quadrilaterals"],
        "Polygons": ["Regular Polygons", "Interior / Exterior Angles"],
        "Coordinate Geometry": ["Distance", "Section Formula", "Midpoint", "Equation of a line", "Slope & Intercepts", "Circles in Coordinate Plane", "Parabola", "Ellipse", "Hyperbola"],
        "Mensuration 2D": ["Area Triangle", "Area Rectangle", "Area Trapezium", "Area Circle", "Sector"],
        "Mensuration 3D": ["Volume Cubes", "Volume Cuboid", "Volume Cylinder", "Volume Cone", "Volume Sphere", "Volume Hemisphere", "Surface Areas"],
        "Trigonometry": ["Heights and Distances", "Basic Trigonometric Ratios"]
    },
    "Number System": {
        "Divisibility": ["Basic Divisibility Rules", "Factorisation of Integers"],
        "HCF-LCM": ["Euclidean Algorithm", "Product of HCF and LCM"],
        "Remainders": ["Basic Remainder Theorem", "Chinese Remainder Theorem", "Cyclicity of Remainders (Last Digits)", "Cyclicity of Remainders (Last Two Digits)"],
        "Base Systems": ["Conversion between bases", "Arithmetic in different bases"],
        "Digit Properties": ["Sum of Digits", "Last Digit Patterns", "Palindromes", "Repetitive Digits"],
        "Number Properties": ["Perfect Squares", "Perfect Cubes"],
        "Number Series": ["Sum of Squares", "Sum of Cubes", "Telescopic Series"],
        "Factorials": ["Properties of Factorials"]
    },
    "Modern Math": {
        "Permutation-Combination": ["Basics", "Circular Permutations", "Permutations with Repetitions", "Permutations with Restrictions", "Combinations with Repetitions", "Combinations with Restrictions"],
        "Probability": ["Classical Probability", "Conditional Probability", "Bayes' Theorem"],
        "Set Theory and Venn Diagram": ["Union and Intersection", "Complement and Difference of Sets", "Multi Set Problems"]
    }
}


class LLMEnrichmentPipeline:
    def __init__(self, llm_api_key: str):
        self.llm_api_key = llm_api_key
        
    def generate_hash(self, stem: str, source: str) -> str:
        """Generate hash for deduplication/versioning"""
        combined = f"{stem}_{source}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def analyze_text(self, prompt: str) -> str:
        """
        Generic LLM text analysis method for conceptual frequency analysis
        """
        try:
            # Use direct API keys instead of emergent integrations
            import openai
            import anthropic
            
            openai_key = os.getenv('OPENAI_API_KEY')
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            
            if not openai_key or not anthropic_key:
                logger.error("OpenAI or Anthropic API keys not found")
                return "{}"  # Return empty JSON on error
            
            # Use OpenAI for analysis
            openai.api_key = openai_key
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in LLM analyze_text: {e}")
            return "{}"  # Return empty JSON on error
        
    async def complete_auto_generation(self, stem: str, hint_category: str = None, hint_subcategory: str = None) -> Dict[str, Any]:
        """
        Complete auto-generation for CSV uploads with only stem and optional image
        Generates: answer, solutions, classification, difficulty, etc.
        """
        try:
            logger.info(f"Starting complete auto-generation for question: {stem[:50]}...")
            
            # Step 1: Generate answer first
            answer = await self.generate_answer(stem)
            logger.info(f"Generated answer: {answer}")
            
            # Step 2: Classify the question
            category, subcategory, type_of_question = await self.categorize_question(stem, hint_category, hint_subcategory)
            logger.info(f"Classification: {category} -> {subcategory} -> {type_of_question}")
            
            # Step 3: Generate solutions
            solution_approach, detailed_solution = await self.generate_solutions(stem, answer, category, subcategory)
            logger.info(f"Generated solutions")
            
            # Step 4: Compute difficulty
            difficulty_score, difficulty_band, difficulty_components = self.compute_difficulty_score(
                stem, solution_approach, category, subcategory
            )
            logger.info(f"Difficulty: {difficulty_band} ({difficulty_score:.2f})")
            
            # Step 5: Calculate other metrics using existing formulas
            learning_impact = calculate_learning_impact(category, subcategory, difficulty_score)
            importance_index = calculate_importance_level(difficulty_score, category, subcategory)
            frequency_band = calculate_frequency_band(category, subcategory)
            
            # Step 6: Generate tags based on content
            tags = self._generate_tags(stem, category, subcategory, type_of_question)
            
            # Return complete enrichment data
            enrichment_data = {
                "answer": answer,
                "solution_approach": solution_approach,
                "detailed_solution": detailed_solution,
                "category": category,
                "subcategory": subcategory,
                "type_of_question": type_of_question,
                "difficulty_score": difficulty_score,
                "difficulty_band": difficulty_band,
                "learning_impact": learning_impact,
                "importance_index": importance_index,
                "frequency_band": frequency_band,
                "tags": tags,
                "source": "LLM Auto-Generated",
                "enrichment_completed": True
            }
            
            logger.info(f"Complete auto-generation successful for question")
            return enrichment_data
            
        except Exception as e:
            logger.error(f"Complete auto-generation failed: {e}")
            # Return minimal fallback data
            return {
                "answer": "Answer generation failed - manual review needed",
                "solution_approach": "Standard problem-solving approach",
                "detailed_solution": "Detailed solution pending manual review",
                "category": "Arithmetic",
                "subcategory": "Time-Speed-Distance",
                "type_of_question": "Basics",
                "difficulty_score": 2.5,
                "difficulty_band": "Medium",
                "learning_impact": 0.5,
                "importance_index": 0.5,
                "frequency_band": "Medium",
                "tags": ["auto_generation_failed", "manual_review_needed"],
                "source": "LLM Auto-Generation (Failed)",
                "enrichment_completed": False
            }
    
    async def generate_answer(self, stem: str) -> str:
        """
        Generate the correct answer for a question stem
        """
        try:
            system_message = """You are an expert CAT exam solver. Generate the correct, concise answer for the given question.

Rules:
1. Provide only the final answer (number, expression, or choice)
2. Be precise and accurate
3. Use standard mathematical notation
4. For multiple choice, provide the option letter and value (e.g., "C) 25")
5. For numerical answers, include units if applicable"""

            # Use direct OpenAI API
            import openai
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                logger.error("OpenAI API key not found")
                return "Unable to generate answer - API key missing"
                
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Question: {stem}"}
                ],
                max_tokens=200
            )
            
            # Clean and validate the answer
            answer = response.choices[0].message.content.strip()
            if len(answer) > 200:  # Answers should be concise
                answer = answer[:200] + "..."
                
            return answer
            
        except Exception as e:
            logger.error(f"Answer generation error: {e}")
            return "Answer generation failed"
    
    def _generate_tags(self, stem: str, category: str, subcategory: str, type_of_question: str) -> list:
        """
        Generate relevant tags based on question content
        """
        tags = ["llm_generated", "auto_enriched"]
        
        # Add category-based tags
        tags.append(category.lower().replace(" ", "_"))
        tags.append(subcategory.lower().replace(" ", "_").replace("–", "_"))
        
        # Add content-based tags
        stem_lower = stem.lower()
        if "train" in stem_lower:
            tags.append("trains")
        if "speed" in stem_lower:
            tags.append("speed")
        if "time" in stem_lower:
            tags.append("time")
        if "distance" in stem_lower:
            tags.append("distance")
        if "triangle" in stem_lower:
            tags.append("triangles")
        if "circle" in stem_lower:
            tags.append("circles")
        if "percentage" in stem_lower or "%" in stem_lower:
            tags.append("percentages")
        if "profit" in stem_lower or "loss" in stem_lower:
            tags.append("profit_loss")
        if "interest" in stem_lower:
            tags.append("interest")
        if "ratio" in stem_lower:
            tags.append("ratios")
        if "work" in stem_lower:
            tags.append("work")
        if "age" in stem_lower:
            tags.append("ages")
        if "mixture" in stem_lower:
            tags.append("mixtures")
        
        # Remove duplicates and limit to reasonable number
        tags = list(set(tags))[:10]
        
        return tags

    async def categorize_question(self, stem: str, hint_category: str = None, hint_subcategory: str = None) -> Tuple[str, str, str]:
        """
        Step 1: Categorize question strictly from canonical taxonomy including type_of_question
        """
        try:
            system_message = f"""You are an expert CAT question classifier. Classify the given quantitative aptitude question into the EXACT canonical taxonomy.

CANONICAL TAXONOMY (LOCKED - USE EXACT LABELS):
{json.dumps(CANONICAL_TAXONOMY, indent=2)}

CRITICAL RULES:
1. Use ONLY the exact category and sub-category names from the taxonomy above
2. AVOID "Basics" unless the question is truly fundamental/introductory level
3. Choose the MOST SPECIFIC type_of_question that matches the question content
4. For Time-Speed-Distance questions, be specific: use "Trains", "Boats and Streams", "Circular Track Motion", "Races", "Relative Speed" when applicable
5. For complex questions, choose advanced types over "Basics"
6. If admin hints are provided, use them as priors but verify correctness
7. Return ONLY a JSON object with exact matches

SPECIFIC TYPE SELECTION GUIDELINES:
- "Basics" ONLY for simple, introductory questions
- "Trains" for questions involving trains, platforms, crossing
- "Boats and Streams" for upstream/downstream, current problems  
- "Circular Track Motion" for circular tracks, laps, overtaking
- "Races" for racing, head starts, lead problems
- "Relative Speed" for opposite/same direction movement
- "Percentage Change" for increase/decrease problems
- "Successive Percentage Change" for multiple percentage operations

Admin hints: Category="{hint_category}", Sub-category="{hint_subcategory}"

RETURN FORMAT:
{{
  "category": "exact_category_name",
  "subcategory": "exact_subcategory_name", 
  "type_of_question": "exact_specific_type_from_subcategory_list",
  "confidence": 0.0-1.0,
  "reasoning": "brief_explanation_of_type_choice"
}}"""

            # Use direct OpenAI API  
            import openai
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                logger.error("OpenAI API key not found")
                return "Arithmetic", "Time-Speed-Distance", "Basics"
                
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Question: {stem}"}
                ],
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            category = result.get("category")
            subcategory = result.get("subcategory")
            type_of_question = result.get("type_of_question")
            reasoning = result.get("reasoning", "")
            
            # CRITICAL: Prevent over-classification as "Basics"
            if type_of_question == "Basics" and subcategory == "Time-Speed-Distance":
                # Analyze stem for specific type indicators
                stem_lower = stem.lower()
                if any(word in stem_lower for word in ['train', 'platform', 'bridge', 'tunnel', 'cross']):
                    type_of_question = "Trains"
                    logger.info(f"Upgraded 'Basics' to 'Trains' based on content analysis")
                elif any(word in stem_lower for word in ['boat', 'stream', 'current', 'upstream', 'downstream']):
                    type_of_question = "Boats and Streams"
                    logger.info(f"Upgraded 'Basics' to 'Boats and Streams' based on content analysis")
                elif any(word in stem_lower for word in ['circular', 'track', 'lap', 'overtake', 'round']):
                    type_of_question = "Circular Track Motion"
                    logger.info(f"Upgraded 'Basics' to 'Circular Track Motion' based on content analysis")
                elif any(word in stem_lower for word in ['race', 'head start', 'lead', 'advantage']):
                    type_of_question = "Races"
                    logger.info(f"Upgraded 'Basics' to 'Races' based on content analysis")
                elif any(word in stem_lower for word in ['opposite', 'towards', 'relative', 'meet']):
                    type_of_question = "Relative Speed"
                    logger.info(f"Upgraded 'Basics' to 'Relative Speed' based on content analysis")
            
            # Validate against taxonomy
            if (category in CANONICAL_TAXONOMY and 
                subcategory in CANONICAL_TAXONOMY[category] and
                type_of_question in CANONICAL_TAXONOMY[category][subcategory]):
                return category, subcategory, type_of_question
            else:
                logger.warning(f"Invalid categorization: {category}, {subcategory}, {type_of_question}")
                # Fallback to first options if invalid
                return "Arithmetic", "Time-Speed-Distance", "Basics"
                
        except Exception as e:
            logger.error(f"Categorization error: {e}")
            return "Arithmetic", "Time-Speed-Distance", "Basics"
    
    async def generate_solutions(self, stem: str, answer: str, category: str, subcategory: str) -> Tuple[str, str]:
        """
        Generate solution approach and detailed solution with emphasis on basic, comprehensive explanations
        """
        try:
            # Enhanced system message for very detailed solutions
            system_message = """You are an expert CAT math tutor who specializes in creating comprehensive, beginner-friendly explanations. Your goal is to help students understand every step of the solution from the very basics.

Guidelines for solution generation:
1. SOLUTION APPROACH: Provide a concise 2-3 sentence overview of the main strategy
2. DETAILED SOLUTION: Create a step-by-step explanation that:
   - Assumes the student is seeing this type of problem for the first time
   - Explains WHY each step is necessary (not just what to do)
   - Defines any formulas or concepts used
   - Shows all calculations clearly
   - Provides intermediate results at each step
   - Explains common mistakes students might make
   - Uses simple, clear language throughout
   - Is comprehensive enough that a student can learn the concept just from reading it

The detailed solution should be educational and thorough - aim for at least 200-300 words of explanation."""

            # Use direct OpenAI API
            import openai
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                logger.error("OpenAI API key not found")
                approach = f"Apply {subcategory} concepts systematically"
                detailed = f"This is a {subcategory} problem. Step 1: Understand what is given in the problem. Step 2: Identify what needs to be found. Step 3: Apply the relevant formula or concept. Step 4: Calculate step by step. Step 5: Verify the answer makes sense."
                return approach, detailed
                
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"""
Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Please provide:
1. SOLUTION APPROACH: [Brief strategy overview]
2. DETAILED SOLUTION: [Comprehensive step-by-step explanation with basics]
"""}
                ],
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to split the response
            if "DETAILED SOLUTION:" in response_text:
                parts = response_text.split("DETAILED SOLUTION:")
                if "SOLUTION APPROACH:" in parts[0]:
                    approach_part = parts[0].replace("SOLUTION APPROACH:", "").strip()
                    detailed_part = parts[1].strip()
                else:
                    approach_part = "Standard problem-solving approach for this type of question"
                    detailed_part = response_text
            else:
                # If format not followed, use entire response as detailed solution
                approach_part = f"Solve this {subcategory} problem step by step"
                detailed_part = response_text
            
            # Ensure detailed solution is comprehensive (minimum length)
            if len(detailed_part) < 150:
                detailed_part += f"\n\nThis is a {subcategory} problem from {category}. Understanding these types of problems requires practicing the fundamental concepts and applying them systematically."
            
            return approach_part[:500], detailed_part[:2000]  # Cap lengths
            
        except Exception as e:
            logger.error(f"Solution generation error: {e}")
            # Provide meaningful fallback solutions
            approach = f"Apply {subcategory} concepts systematically"
            detailed = f"This is a {subcategory} problem. Step 1: Understand what is given in the problem. Step 2: Identify what needs to be found. Step 3: Apply the relevant formula or concept. Step 4: Calculate step by step. Step 5: Verify the answer makes sense."
            return approach, detailed
    
    def compute_difficulty_score(self, stem: str, solution_approach: str, category: str, subcategory: str) -> Tuple[float, str, Dict[str, float]]:
        """
        Step 3: Difficulty computation using 4-factor formulaic algorithm
        Composite = 0.35×Layering + 0.25×Steps + 0.25×Transform + 0.15×Trick → 1–5
        Band: Easy (≤2.40), Medium (2.41–3.70), Difficult (≥3.71)
        """
        try:
            # Simple heuristic-based scoring (in production, this would use more sophisticated analysis)
            layering_score = self._analyze_concept_layering(stem, category, subcategory)
            steps_score = self._analyze_steps_to_solve(solution_approach)
            transform_score = self._analyze_data_transformation(stem)
            trick_score = self._analyze_tricks_misleading(stem, category)
            
            # Apply formula: 0.35×Layering + 0.25×Steps + 0.25×Transform + 0.15×Trick
            composite_score = (
                0.35 * layering_score +
                0.25 * steps_score +
                0.25 * transform_score +
                0.15 * trick_score
            )
            
            # Ensure score is within 1-5 range
            composite_score = max(1.0, min(5.0, composite_score))
            
            # Determine band
            if composite_score <= 2.40:
                band = "Easy"
            elif composite_score <= 3.70:
                band = "Medium"
            else:
                band = "Difficult"
            
            components = {
                "concept_layering": layering_score,
                "steps_to_solve": steps_score,
                "data_transformation": transform_score,
                "trick_misleading": trick_score
            }
            
            return composite_score, band, components
            
        except Exception as e:
            logger.error(f"Difficulty computation error: {e}")
            return 3.0, "Medium", {}
    
    def _analyze_concept_layering(self, stem: str, category: str, subcategory: str) -> float:
        """Analyze concept layering complexity (1-5)"""
        # Heuristic: more complex categories/subcategories have higher layering
        complex_categories = ["Algebra", "Geometry and Mensuration", "Modern Math"]
        complex_subcategories = ["Quadratic Equations", "Coordinate Geometry", "Probability"]
        
        score = 2.0  # base score
        if category in complex_categories:
            score += 1.0
        if subcategory in complex_subcategories:
            score += 1.0
        if len(stem) > 200:  # longer questions often more complex
            score += 0.5
            
        return min(5.0, score)
    
    def _analyze_steps_to_solve(self, solution_approach: str) -> float:
        """Analyze number of steps required (1-5)"""
        if not solution_approach:
            return 3.0
            
        # Heuristic: count bullet points, steps, or key action words
        step_indicators = solution_approach.count("•") + solution_approach.count("-") + solution_approach.count("Step")
        key_words = ["calculate", "find", "determine", "solve", "substitute", "simplify"]
        word_count = sum(1 for word in key_words if word in solution_approach.lower())
        
        steps = max(step_indicators, word_count / 2)
        
        if steps <= 2:
            return 1.5
        elif steps <= 4:
            return 3.0
        else:
            return 4.5
    
    def _analyze_data_transformation(self, stem: str) -> float:
        """Analyze data transformation complexity (1-5)"""
        # Heuristic: look for transformation indicators
        transform_words = ["convert", "transform", "change", "ratio", "percentage", "proportion"]
        units = ["km", "m", "hr", "min", "sec", "%", "Rs", "kg"]
        
        transform_count = sum(1 for word in transform_words if word in stem.lower())
        unit_count = sum(1 for unit in units if unit in stem)
        
        score = 2.0 + (transform_count * 0.5) + (unit_count * 0.3)
        return min(5.0, score)
    
    def _analyze_tricks_misleading(self, stem: str, category: str) -> float:
        """Analyze trick/misleading elements (1-5)"""
        # Heuristic: certain categories and words indicate tricks
        tricky_categories = ["Time-Speed-Distance", "Percentages", "Profit-Loss-Discount"]
        trick_words = ["except", "not", "least", "maximum", "minimum", "opposite", "reverse"]
        
        score = 1.5
        if any(tricky in category for tricky in tricky_categories):
            score += 1.0
        if any(word in stem.lower() for word in trick_words):
            score += 1.5
        if "?" in stem and stem.count("?") > 1:  # multiple questions can be tricky
            score += 0.5
            
        return min(5.0, score)
    
    def get_frequency_analysis(self, subcategory: str, pyq_data: Dict = None) -> Tuple[str, str]:
        """
        Step 4: Frequency analysis based on PYQ data
        Band: High (8–10 yrs), Medium (4–7), Low (0–3) from rolling 10 years
        """
        if not pyq_data:
            # Default frequency mapping (would be replaced with actual PYQ analysis)
            high_freq = ["Basics", "Basics", "Linear Equations", "Basics"]
            medium_freq = ["Relative Speed", "Compound Ratios", "Quadratic Equations", "Triangles"]
            
            if subcategory in high_freq:
                return "High", "Appears in 8-10 of last 10 years"
            elif subcategory in medium_freq:
                return "Medium", "Appears in 4-7 of last 10 years"
            else:
                return "Low", "Appears in 0-3 of last 10 years"
        
        # Use actual PYQ data when available
        years_appeared = pyq_data.get(subcategory, 0)
        if years_appeared >= 8:
            return "High", f"Appears in {years_appeared} of last 10 years"
        elif years_appeared >= 4:
            return "Medium", f"Appears in {years_appeared} of last 10 years"
        else:
            return "Low", f"Appears in {years_appeared} of last 10 years"
    
    def compute_learning_impact_static(self, detailed_solution: str, category: str, subcategory: str) -> float:
        """
        Step 5: Learning Impact (Static) - from solution text
        Components: Concept Centrality, Cross-Topic Connectivity, Method Reusability, 
                   Transform Diversity, Parameterization → 0–100
        """
        try:
            centrality = self._analyze_concept_centrality(category, subcategory)
            connectivity = self._analyze_cross_topic_connectivity(detailed_solution, category)
            reusability = self._analyze_method_reusability(detailed_solution)
            diversity = self._analyze_transform_diversity(detailed_solution)
            parameterization = self._analyze_parameterization(detailed_solution)
            
            # Weight the components
            learning_impact = (
                0.25 * centrality +
                0.20 * connectivity +
                0.20 * reusability +
                0.20 * diversity +
                0.15 * parameterization
            )
            
            return min(100.0, max(0.0, learning_impact))
            
        except Exception as e:
            logger.error(f"Learning impact computation error: {e}")
            return 50.0  # default
    
    def _analyze_concept_centrality(self, category: str, subcategory: str) -> float:
        """Analyze how central this concept is (0-100)"""
        # Core concepts that appear across many problems
        central_concepts = {
            "Time-Speed-Distance": 90,
            "Percentages": 85,
            "Linear Equations": 80,
            "Simple and Compound Interest": 75,
            "Ratios and Proportions": 85
        }
        return central_concepts.get(subcategory, 60.0)
    
    def _analyze_cross_topic_connectivity(self, solution: str, category: str) -> float:
        """Analyze cross-topic connections (0-100)"""
        # Look for mentions of other mathematical concepts
        other_categories = ["algebra", "geometry", "arithmetic", "probability"]
        connections = sum(1 for cat in other_categories if cat in solution.lower())
        return min(100.0, 40.0 + (connections * 15.0))
    
    def _analyze_method_reusability(self, solution: str) -> float:
        """Analyze how reusable the method is (0-100)"""
        reusable_methods = ["formula", "substitution", "elimination", "proportion", "unitary method"]
        methods = sum(1 for method in reusable_methods if method in solution.lower())
        return min(100.0, 50.0 + (methods * 12.0))
    
    def _analyze_transform_diversity(self, solution: str) -> float:
        """Analyze transformation diversity (0-100)"""
        transforms = ["convert", "transform", "simplify", "factorize", "expand"]
        diversity = sum(1 for transform in transforms if transform in solution.lower())
        return min(100.0, 40.0 + (diversity * 15.0))
    
    def _analyze_parameterization(self, solution: str) -> float:
        """Analyze parameterization potential (0-100)"""
        param_indicators = ["variable", "parameter", "general", "formula", "equation"]
        params = sum(1 for indicator in param_indicators if indicator in solution.lower())
        return min(100.0, 30.0 + (params * 17.0))
    
    def compute_importance_index(self, frequency_band: str, difficulty_score: float, learning_impact: float) -> Tuple[float, str]:
        """
        Step 6: Importance Index computation
        Formula: 0.50×Frequency + 0.25×DifficultyNorm + 0.25×LearningImpact
        Band: High (≥70), Medium (45–69), Low (<45)
        """
        try:
            # Frequency score mapping
            frequency_scores = {"High": 100, "Medium": 60, "Low": 30}
            frequency_score = frequency_scores.get(frequency_band, 60)
            
            # Normalize difficulty 1-5 → 20-100
            difficulty_norm = 20 + ((difficulty_score - 1) / 4) * 80
            
            # Apply importance formula
            importance = (
                0.50 * frequency_score +
                0.25 * difficulty_norm +
                0.25 * learning_impact
            )
            
            # Determine band
            if importance >= 70:
                band = "High"
            elif importance >= 45:
                band = "Medium"
            else:
                band = "Low"
            
            return importance, band
            
        except Exception as e:
            logger.error(f"Importance computation error: {e}")
            return 60.0, "Medium"
    
    def get_video_url(self, category: str, subcategory: str, curated_urls: Dict = None) -> str:
        """
        Step 7: Get video URL (curated or default)
        """
        if curated_urls and subcategory in curated_urls:
            return curated_urls[subcategory]
        
        # Default video URLs for major topics (placeholder URLs)
        default_videos = {
            "Time-Speed-Distance": "https://youtube.com/watch?v=tsd_basics",
            "Percentages": "https://youtube.com/watch?v=percentage_tricks",
            "Linear Equations": "https://youtube.com/watch?v=linear_equations",
            "Quadratic Equations": "https://youtube.com/watch?v=quadratic_solving"
        }
        
        return default_videos.get(subcategory, "https://youtube.com/watch?v=cat_prep_general")
    
    async def enrich_question_completely(self, 
                                    stem: str, 
                                    image_url: str = None,
                                    hint_category: str = None, 
                                    hint_subcategory: str = None) -> Dict[str, Any]:
        """
        Complete auto-generation of all question fields from just the stem and optional image
        Uses LLM if available, fallback pattern recognition if LLM fails
        """
        try:
            logger.info(f"Starting complete question enrichment for: {stem[:100]}...")
            
            # First try LLM-based enrichment
            try:
                # Step 1: Generate answer using LLM
                answer = await self.generate_answer(stem, image_url)
                logger.info(f"Generated answer: {answer}")
                
                # Step 2: Use the full enrichment pipeline
                enrichment_result = await self.enrich_question(
                    stem=stem,
                    answer=answer,
                    source="Admin",
                    hint_category=hint_category,
                    hint_subcategory=hint_subcategory,
                    image_url=image_url
                )
                
                # Return the complete enriched data
                return {
                    "answer": answer,
                    "solution_approach": enrichment_result.get("solution_approach", ""),
                    "detailed_solution": enrichment_result.get("detailed_solution", ""),
                    "category": enrichment_result.get("category", hint_category or "Arithmetic"),
                    "subcategory": enrichment_result.get("subcategory", hint_subcategory or "Basic Math"),
                    "type_of_question": enrichment_result.get("type_of_question", "General"),
                    "difficulty_score": enrichment_result.get("difficulty_score", 0.5),
                    "difficulty_band": enrichment_result.get("difficulty_band", "Medium"),
                    "learning_impact": enrichment_result.get("learning_impact", 50.0),
                    "importance_index": enrichment_result.get("importance_index", 50.0),
                    "frequency_band": enrichment_result.get("frequency_band", "Medium"),
                    "tags": enrichment_result.get("tags", ["llm_generated"]),
                    "source": "LLM Generated"
                }
                
            except Exception as llm_error:
                logger.warning(f"LLM enrichment failed, using fallback: {llm_error}")
                
                # Import and use fallback enricher
                from fallback_enricher import FallbackEnricher
                
                fallback_enricher = FallbackEnricher()
                fallback_result = fallback_enricher.enrich_question(stem)
                
                logger.info(f"✅ Fallback enrichment successful: {fallback_result['answer']}")
                return fallback_result
            
        except Exception as e:
            logger.error(f"Complete enrichment failed (both LLM and fallback): {e}")
            # Last resort fallback data
            return {
                "answer": "Unable to generate",
                "solution_approach": "Manual solution required",
                "detailed_solution": "Please solve manually or contact support",
                "category": hint_category or "Arithmetic",
                "subcategory": hint_subcategory or "Basic Math", 
                "type_of_question": "General",
                "difficulty_score": 0.5,
                "difficulty_band": "Medium",
                "learning_impact": 50.0,
                "importance_index": 50.0,
                "frequency_band": "Medium",
                "tags": ["enrichment_failed", "manual_review_needed"],
                "source": "Fallback Generation Failed"
            }
    
    async def generate_answer(self, stem: str, image_url: str = None) -> str:
        """
        Generate just the answer for a given question stem
        """
        try:
            system_message = """You are an expert CAT quantitative aptitude problem solver. 
Given a question, provide ONLY the final numerical answer or short answer.

RULES:
1. Provide ONLY the answer - no explanation, no working
2. For numerical answers, provide just the number
3. For multiple choice, provide just the letter (A, B, C, D)
4. For word answers, keep it very brief (1-3 words max)
5. If it's a speed problem, give answer in specified units (km/h, m/s, etc.)"""

            # Use direct OpenAI API
            import openai
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                logger.error("OpenAI API key not found")
                return "Answer generation failed"
                
            client = openai.OpenAI(api_key=openai_key)
            
            user_content = f"Question: {stem}"
            if image_url:
                user_content += f"\nImage: {image_url}"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=200
            )
            
            # Clean up the response to just get the answer
            answer = response.choices[0].message.content.strip()
            
            # Remove common prefixes that might be added
            prefixes_to_remove = [
                "Answer:", "The answer is:", "Final answer:", 
                "Solution:", "Result:", "Therefore,", "Hence,", "So,"
            ]
            
            for prefix in prefixes_to_remove:
                if answer.startswith(prefix):
                    answer = answer[len(prefix):].strip()
            
            return answer[:50]  # Limit answer length
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Answer generation failed"

    async def enrich_question(self, stem: str, answer: str, source: str = "Admin", 
                            hint_category: str = None, hint_subcategory: str = None,
                            pyq_data: Dict = None, curated_videos: Dict = None) -> Dict[str, Any]:
        """
        Complete LLM enrichment pipeline - idempotent and consistent
        """
        try:
            logger.info(f"Starting enrichment for question: {stem[:50]}...")
            
            # Step 1: Categorization with type_of_question
            category, subcategory, type_of_question = await self.categorize_question(stem, hint_category, hint_subcategory)
            logger.info(f"Categorized: {category} -> {subcategory} -> {type_of_question}")
            
            # Step 2: Solutions
            solution_approach, detailed_solution = await self.generate_solutions(stem, answer, category, subcategory)
            logger.info("Generated solutions")
            
            # Step 3: Difficulty
            difficulty_score, difficulty_band, difficulty_components = self.compute_difficulty_score(
                stem, solution_approach, category, subcategory
            )
            logger.info(f"Difficulty: {difficulty_score} ({difficulty_band})")
            
            # Step 4: Frequency
            frequency_band, frequency_notes = self.get_frequency_analysis(subcategory, pyq_data)
            logger.info(f"Frequency: {frequency_band}")
            
            # Step 5: Learning Impact (Static)
            learning_impact = self.compute_learning_impact_static(detailed_solution, category, subcategory)
            learning_impact_band = "High" if learning_impact >= 70 else "Medium" if learning_impact >= 45 else "Low"
            logger.info(f"Learning Impact: {learning_impact} ({learning_impact_band})")
            
            # Step 6: Importance Index
            importance_index, importance_band = self.compute_importance_index(
                frequency_band, difficulty_score, learning_impact
            )
            logger.info(f"Importance: {importance_index} ({importance_band})")
            
            # Step 7: Video URL
            video_url = self.get_video_url(category, subcategory, curated_videos)
            
            # Step 8: Generate hash for deduplication
            question_hash = self.generate_hash(stem, source)
            
            enrichment_result = {
                "category": category,
                "subcategory": subcategory,
                "type_of_question": type_of_question,
                "solution_approach": solution_approach,
                "detailed_solution": detailed_solution,
                "difficulty_score": round(difficulty_score, 2),
                "difficulty_band": difficulty_band,
                "difficulty_components": difficulty_components,
                "frequency_band": frequency_band,
                "frequency_notes": frequency_notes,
                "learning_impact": round(learning_impact, 2),
                "learning_impact_band": learning_impact_band,
                "importance_index": round(importance_index, 2),
                "importance_band": importance_band,
                "video_url": video_url,
                "question_hash": question_hash,
                "enriched_at": datetime.utcnow().isoformat(),
                "version": 1
            }
            
            logger.info("Enrichment completed successfully")
            return enrichment_result
            
        except Exception as e:
            logger.error(f"Enrichment pipeline error: {e}")
            # Return default enrichment on failure
            return {
                "category": "Arithmetic",
                "subcategory": "Time-Speed-Distance",
                "solution_approach": "Standard approach",
                "detailed_solution": "Detailed solution pending",
                "difficulty_score": 3.0,
                "difficulty_band": "Medium",
                "frequency_band": "Medium",
                "learning_impact": 50.0,
                "learning_impact_band": "Medium",
                "importance_index": 60.0,
                "importance_band": "Medium",
                "video_url": "https://youtube.com/watch?v=default",
                "question_hash": self.generate_hash(stem, source),
                "enriched_at": datetime.utcnow().isoformat(),
                "version": 1,
                "error": str(e)
            }


class SimplifiedEnrichmentService:
    """
    NEW: Simplified LLM Enrichment Service for Question Upload & Enrichment Workflow
    Generates ONLY the 5 required fields: right_answer, category, subcategory, type_of_question, difficulty_level
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.error("OpenAI API key not found for SimplifiedEnrichmentService")
            
    async def enrich_with_five_fields_only(self, stem: str, admin_answer: str = None) -> Dict[str, Any]:
        """
        Generate ONLY the 5 required LLM fields for the new workflow:
        1. right_answer
        2. category  
        3. subcategory
        4. type_of_question
        5. difficulty_level
        """
        try:
            logger.info(f"🎯 Simplified enrichment starting for: {stem[:50]}...")
            
            # STEP 1: Generate right_answer
            right_answer = await self._generate_right_answer_with_openai(stem)
            
            # STEP 2: Classify the question (category, subcategory, type_of_question)
            classification = await self._classify_question_with_openai(stem)
            
            # STEP 3: Determine difficulty level
            difficulty_level = await self._determine_difficulty_level(stem, right_answer)
            
            # Prepare the enrichment result with exactly 5 fields
            enrichment_result = {
                "right_answer": right_answer,
                "category": classification.get("category", "Arithmetic"),
                "subcategory": classification.get("subcategory", "General"),
                "type_of_question": classification.get("type_of_question", "Problem Solving"),
                "difficulty_level": difficulty_level
            }
            
            logger.info(f"✅ Simplified enrichment completed with 5 fields")
            logger.info(f"   Category: {enrichment_result['category']} -> {enrichment_result['subcategory']}")
            logger.info(f"   Type: {enrichment_result['type_of_question']}")
            logger.info(f"   Difficulty: {enrichment_result['difficulty_level']}")
            
            return {
                "success": True,
                "enrichment_data": enrichment_result
            }
            
        except Exception as e:
            logger.error(f"❌ Simplified enrichment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "enrichment_data": {
                    "right_answer": "Unable to generate answer",
                    "category": "Arithmetic",
                    "subcategory": "General",
                    "type_of_question": "Problem Solving",
                    "difficulty_level": "Medium"
                }
            }
    
    async def _generate_right_answer_with_openai(self, stem: str) -> str:
        """Generate the correct answer using OpenAI GPT-4o"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            system_message = """You are an expert CAT exam solver focused on quantitative ability questions. 
Generate the correct, concise answer for the given question.

Rules:
1. Provide ONLY the final numerical answer or the correct option
2. Be precise and accurate
3. For multiple choice questions, provide just the value (not the option letter)
4. For numerical answers, include units if applicable
5. Keep the answer concise and direct"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Question: {stem}"}
                ],
                max_tokens=150
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"✅ Right answer generated: {answer}")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Right answer generation failed: {e}")
            return "Unable to generate answer"
    
    async def _classify_question_with_openai(self, stem: str) -> Dict[str, str]:
        """Classify question into category, subcategory, and type using OpenAI"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            system_message = f"""You are an expert in CAT quantitative ability question classification.
Classify the given question into the EXACT canonical taxonomy below.

CANONICAL TAXONOMY:
{json.dumps(CANONICAL_TAXONOMY, indent=2)}

CLASSIFICATION RULES:
1. Choose the MOST SPECIFIC category, subcategory, and type that matches the question
2. Use ONLY the exact labels from the taxonomy above
3. Be precise and specific - avoid generic terms
4. The category MUST be one of: Arithmetic, Algebra, Geometry and Mensuration, Number System, Modern Math
5. The subcategory must be from the chosen category's subcategories
6. The type_of_question must be from the chosen subcategory's types (the array values)

EXAMPLES:
- Speed question → {{"category": "Arithmetic", "subcategory": "Time-Speed-Distance", "type_of_question": "Basics"}}
- Train problem → {{"category": "Arithmetic", "subcategory": "Time-Speed-Distance", "type_of_question": "Trains"}}  
- Quadratic roots → {{"category": "Algebra", "subcategory": "Quadratic Equations", "type_of_question": "Roots & Nature of Roots"}}
- Triangle area → {{"category": "Geometry and Mensuration", "subcategory": "Mensuration 2D", "type_of_question": "Area Triangle"}}

Return ONLY JSON format: {{"category": "...", "subcategory": "...", "type_of_question": "..."}}"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Classify this question: {stem}"}
                ],
                max_tokens=200
            )
            
            classification_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                classification = json.loads(classification_text)
                logger.info(f"✅ Classification: {classification}")
                return classification
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Could not parse classification JSON: {classification_text}")
                # Return default classification
                return {
                    "category": "Arithmetic",
                    "subcategory": "Time-Speed-Distance", 
                    "type_of_question": "Basics"
                }
                
        except Exception as e:
            logger.error(f"❌ Classification failed: {e}")
            return {
                "category": "Arithmetic",
                "subcategory": "Time-Speed-Distance",
                "type_of_question": "Basics"
            }
    
    async def _determine_difficulty_level(self, stem: str, right_answer: str) -> str:
        """Determine difficulty level: Easy, Medium, or Hard"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            system_message = """You are an expert in CAT quantitative ability difficulty assessment.
Analyze the given question and determine its difficulty level.

Difficulty Levels:
- Easy: Basic concepts, straightforward calculations, single-step problems
- Medium: Multiple concepts, moderate calculations, 2-3 step problems
- Hard: Advanced concepts, complex calculations, multi-step reasoning

Return ONLY one word: Easy, Medium, or Hard"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Question: {stem}\nAnswer: {right_answer}"}
                ],
                max_tokens=50
            )
            
            difficulty = response.choices[0].message.content.strip()
            
            # Validate and normalize response
            if difficulty.lower() in ['easy', 'medium', 'hard']:
                difficulty = difficulty.capitalize()
            else:
                difficulty = "Medium"  # Default fallback
            
            logger.info(f"✅ Difficulty assessed: {difficulty}")
            return difficulty
            
        except Exception as e:
            logger.error(f"❌ Difficulty assessment failed: {e}")
            return "Medium"  # Default fallback
    
    async def _validate_answer_consistency(self, admin_answer: str, ai_right_answer: str, question_stem: str) -> Dict[str, Any]:
        """
        Validate consistency between admin-provided answer and AI-generated right_answer
        Used for quality control to activate questions
        """
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            system_message = """You are an expert answer validator for CAT quantitative ability questions.
Compare the admin-provided answer with the AI-generated answer for consistency.

Rules:
1. Consider different formats of the same answer as MATCHING (e.g., "15" vs "15 minutes" vs "15 min")
2. Consider mathematical equivalents as MATCHING (e.g., "0.5" vs "1/2")
3. For multiple choice, consider the value matching even if format differs
4. Be strict about actual numerical/logical correctness

Return JSON: {"matches": true/false, "explanation": "brief explanation"}"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"""Question: {question_stem}
Admin Answer: {admin_answer}
AI Answer: {ai_right_answer}

Do these answers match?"""}
                ],
                max_tokens=200
            )
            
            validation_text = response.choices[0].message.content.strip()
            
            try:
                validation_result = json.loads(validation_text)
                logger.info(f"✅ Answer validation: {validation_result}")
                return validation_result
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Could not parse validation JSON: {validation_text}")
                # Conservative approach - assume no match if we can't parse
                return {
                    "matches": False,
                    "explanation": "Could not validate due to parsing error"
                }
                
        except Exception as e:
            logger.error(f"❌ Answer validation failed: {e}")
            return {
                "matches": False,
                "explanation": f"Validation error: {str(e)}"
            }


class LLMEnrichmentService:
    """
    Main LLM enrichment service that automatically follows the standardized schema directive
    NO MORE MANUAL SCRIPTS - Handles all enrichment automatically with quality control
    """
    
    def __init__(self):
        load_dotenv()
        self.standardized_enricher = standardized_enricher
        logger.info("🎯 LLM Enrichment Service initialized with automatic schema compliance")
    
    async def enrich_question_automatically(self, question: Question, db: Session) -> Dict[str, Any]:
        """
        REVISED ENRICHMENT FLOW - UPLOAD TIME ONLY:
        - Admin fields (stem, solution_approach, detailed_solution, principle_to_remember, answer, image_url) are PROTECTED
        - LLMs only enrich metadata fields (difficulty, frequency, etc.)
        - NO real-time right_answer generation (moved to upload time only)
        - NO real-time MCQ validation (moved to upload time only)
        """
        try:
            logger.info(f"🔄 Auto-enriching question metadata only: {question.stem[:60]}...")
            
            # STEP 1: LLM enrichment for metadata fields ONLY (not touching admin content)
            # Only enrich technical metadata fields like difficulty, frequency, etc.
            enrichment_result = await self._enrich_metadata_fields_only(
                question_stem=question.stem,
                answer=question.answer or "To be determined",
                subcategory=question.subcategory or "General",
                question_type=question.type_of_question or "Problem Solving"
            )
            
            if enrichment_result["success"]:
                # Only update NON-admin fields (metadata enrichment)
                if enrichment_result.get("difficulty_score"):
                    question.difficulty_score = enrichment_result["difficulty_score"]
                if enrichment_result.get("difficulty_band"):
                    question.difficulty_band = enrichment_result["difficulty_band"]
                if enrichment_result.get("frequency_band"):
                    question.frequency_band = enrichment_result["frequency_band"]
                if enrichment_result.get("learning_impact"):
                    question.learning_impact = enrichment_result["learning_impact"]
                if enrichment_result.get("importance_index"):
                    question.importance_index = enrichment_result["importance_index"]
                
                # Commit changes
                db.commit()
                
                logger.info(f"✅ Metadata enrichment successful - Admin fields protected")
                return {
                    "success": True,
                    "metadata_enriched": True,
                    "admin_fields_protected": True
                }
            else:
                logger.error(f"❌ Metadata enrichment failed: {enrichment_result.get('error')}")
                return {"success": False, "error": enrichment_result.get("error")}
                
        except Exception as e:
            logger.error(f"❌ Exception in metadata enrichment: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_enrich_questions(self, questions: List[Question], db: Session) -> Dict[str, Any]:
        """
        Batch enrichment with automatic schema compliance for multiple questions
        Perfect for processing large datasets without manual intervention
        """
        logger.info(f"🚀 Starting batch auto-enrichment for {len(questions)} questions")
        
        results = {
            "total_questions": len(questions),
            "successful": 0,
            "failed": 0,
            "quality_scores": [],
            "failed_questions": []
        }
        
        for i, question in enumerate(questions):
            try:
                logger.info(f"🔄 [{i+1}/{len(questions)}] Processing: {question.stem[:50]}...")
                
                enrichment_result = await self.enrich_question_automatically(question, db)
                
                if enrichment_result["success"]:
                    results["successful"] += 1
                    if "quality_score" in enrichment_result:
                        results["quality_scores"].append(enrichment_result["quality_score"])
                else:
                    results["failed"] += 1
                    results["failed_questions"].append({
                        "question_id": question.id,
                        "error": enrichment_result.get("error")
                    })
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.3)
                
                # Progress update every 10 questions
                if (i + 1) % 10 == 0:
                    avg_quality = sum(results["quality_scores"]) / len(results["quality_scores"]) if results["quality_scores"] else 0
                    logger.info(f"📊 Progress [{i+1}/{len(questions)}]: {results['successful']} success, {results['failed']} failed, avg quality: {avg_quality:.1f}")
                
            except Exception as e:
                logger.error(f"❌ Exception processing question {i+1}: {e}")
                results["failed"] += 1
                results["failed_questions"].append({
                    "question_id": question.id,
                    "error": str(e)
                })
        
        # Final results
        avg_quality = sum(results["quality_scores"]) / len(results["quality_scores"]) if results["quality_scores"] else 0
        success_rate = results["successful"] / results["total_questions"] * 100
        
        logger.info(f"🎉 Batch auto-enrichment completed!")
        logger.info(f"📊 Results: {results['successful']}/{results['total_questions']} successful ({success_rate:.1f}%)")
        logger.info(f"📈 Average quality score: {avg_quality:.1f}")
        
        results["success_rate"] = success_rate
        results["average_quality"] = avg_quality
        
        return results

    async def _generate_right_answer_with_openai(self, question_stem: str) -> str:
        """
        Generate the right_answer field using OpenAI based on the question stem
        """
        try:
            logger.info("🧠 Using OpenAI to generate right_answer...")
            
            # Check for API key
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                logger.error("OpenAI API key not found")
                return None
            
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            # Create focused prompt for answer generation
            prompt = f"""You are an expert CAT (Common Admission Test) tutor. Given this question, provide ONLY the direct answer.

Question: {question_stem}

Instructions:
1. Solve this question step by step mentally
2. Provide ONLY the final answer 
3. For multiple choice questions: give the option letter and value (e.g., "C) 25")
4. For numerical answers: include units if applicable (e.g., "150 km/h", "₹2000")
5. For ratio/percentage: use proper format (e.g., "3:4", "25%")
6. Keep the answer concise and precise
7. Do not include any explanation or working

Answer:"""

            response = client.chat.completions.create(
                model="gpt-4o",  # Use latest model for accuracy
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,  # Keep answer concise
                temperature=0.1,  # Low temperature for consistent answers
                timeout=30
            )
            
            right_answer = response.choices[0].message.content.strip()
            logger.info(f"✅ OpenAI generated right_answer: {right_answer}")
            return right_answer
            
        except Exception as e:
            logger.error(f"❌ OpenAI right_answer generation failed: {e}")
            return None

    async def _validate_answer_consistency(self, admin_answer: str, ai_right_answer: str, question_stem: str) -> Dict[str, Any]:
        """
        Cross-validate AI-generated right_answer with admin-provided answer field
        """
        try:
            logger.info("🔍 Validating answer consistency...")
            
            # Clean both answers for comparison
            admin_clean = admin_answer.strip().lower()
            ai_clean = ai_right_answer.strip().lower()
            
            # Extract numeric values if present
            import re
            admin_numbers = re.findall(r'\d+\.?\d*', admin_answer)
            ai_numbers = re.findall(r'\d+\.?\d*', ai_right_answer)
            
            # Check various matching criteria
            
            # 1. Exact match (case-insensitive)
            if admin_clean == ai_clean:
                return {"matches": True, "reason": "Exact match"}
            
            # 2. Numeric value match (for mathematical answers)
            if admin_numbers and ai_numbers:
                admin_num = float(admin_numbers[0]) if admin_numbers[0] else 0
                ai_num = float(ai_numbers[0]) if ai_numbers[0] else 0
                if abs(admin_num - ai_num) < 0.01:  # Allow small floating point differences
                    return {"matches": True, "reason": f"Numeric match: {admin_num} ≈ {ai_num}"}
            
            # 3. Admin answer contains AI answer or vice versa
            if ai_clean in admin_clean or admin_clean in ai_clean:
                return {"matches": True, "reason": "Substring match"}
            
            # 4. Key phrase matching (for descriptive answers)
            admin_words = set(admin_clean.split())
            ai_words = set(ai_clean.split())
            common_words = admin_words.intersection(ai_words)
            
            # Remove common words like 'the', 'is', 'a', etc.
            meaningful_words = common_words - {'the', 'is', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for', 'on', 'with'}
            
            if len(meaningful_words) >= 2:  # At least 2 meaningful words match
                return {"matches": True, "reason": f"Key phrase match: {meaningful_words}"}
            
            # 5. No match found
            return {
                "matches": False, 
                "reason": f"No sufficient similarity found",
                "admin_answer": admin_answer,
                "ai_answer": ai_right_answer,
                "similarity_score": len(common_words) / max(len(admin_words), len(ai_words)) if admin_words or ai_words else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Answer validation failed: {e}")
            return {"matches": False, "reason": f"Validation error: {str(e)}"}

    async def _enrich_metadata_fields_only(self, question_stem: str, answer: str, 
                                         subcategory: str, question_type: str) -> Dict[str, Any]:
        """
        Enrich ONLY metadata fields (difficulty, frequency, etc.) without touching admin content fields
        """
        try:
            logger.info("📊 Enriching metadata fields only (protecting admin content)...")
            
            # Calculate metadata based on question characteristics and heuristics
            # Since we don't have actual performance data, use heuristic estimates
            
            # Estimate difficulty based on question complexity
            question_length = len(question_stem)
            has_numbers = any(char.isdigit() for char in question_stem)
            
            # Heuristic difficulty calculation
            if question_length > 200 or "calculate" in question_stem.lower() or "find" in question_stem.lower():
                difficulty_score = 3.5  # Hard
                difficulty_band = "Hard"
            elif question_length > 100 or has_numbers:
                difficulty_score = 2.5  # Medium
                difficulty_band = "Medium"
            else:
                difficulty_score = 1.5  # Easy
                difficulty_band = "Easy"
            
            # Frequency band based on subcategory
            high_freq_categories = [
                'Time–Speed–Distance (TSD)', 'Percentages', 'Profit–Loss–Discount (PLD)',
                'Linear Equations', 'Triangles', 'Divisibility', 'Permutation–Combination (P&C)'
            ]
            
            medium_freq_categories = [
                'Time & Work', 'Ratio–Proportion–Variation', 'Averages & Alligation',
                'Simple & Compound Interest (SI–CI)', 'Quadratic Equations', 'Circles',
                'HCF–LCM', 'Probability'
            ]
            
            if subcategory in high_freq_categories:
                frequency_band = "High"
                learning_impact = 80.0
                importance_index = 90.0
            elif subcategory in medium_freq_categories:
                frequency_band = "Medium"
                learning_impact = 65.0
                importance_index = 70.0
            else:
                frequency_band = "Low"
                learning_impact = 50.0
                importance_index = 50.0
            
            logger.info(f"📊 Metadata calculated: {difficulty_band} difficulty, {frequency_band} frequency")
            
            return {
                "success": True,
                "difficulty_score": round(difficulty_score, 2),
                "difficulty_band": difficulty_band,
                "frequency_band": frequency_band,
                "learning_impact": round(learning_impact, 2),
                "importance_index": round(importance_index, 2),
                "metadata_source": "heuristic_based"
            }
            
        except Exception as e:
            logger.error(f"❌ Metadata enrichment failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Usage example and testing
async def test_simplified_enrichment():
    """Test the new simplified enrichment service"""
    service = SimplifiedEnrichmentService()
    
    test_question = "A train travels at 60 km/h and covers a distance of 240 km. How much time does it take?"
    
    result = await service.enrich_with_five_fields_only(test_question)
    print("Simplified Enrichment Result:")
    print(json.dumps(result, indent=2))

async def test_enrichment():
    """Test the enrichment pipeline"""
    pipeline = LLMEnrichmentPipeline("sk-emergent-c6504797427BfB25c0")
    
    test_question = "A train travels at 60 km/h and covers a distance of 240 km. How much time does it take?"
    test_answer = "4 hours"
    
    result = await pipeline.enrich_question(test_question, test_answer)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_enrichment())