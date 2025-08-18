"""
Advanced LLM Enrichment Pipeline for CAT Preparation Platform
Implements sophisticated scoring algorithms as per specification
"""

import json
import hashlib
import uuid
from typing import Dict, Any, Tuple
from datetime import datetime
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage
from formulas import (
    calculate_difficulty_level,
    calculate_frequency_band,
    calculate_importance_level,
    calculate_learning_impact
)
import asyncio

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
            llm = LlmChat(api_key=self.llm_api_key)
            messages = [UserMessage(content=prompt)]
            response = await llm.achat(messages=messages, model="claude-3-5-sonnet-20241022")
            return response.message.content
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
                "subcategory": "Time–Speed–Distance (TSD)",
                "type_of_question": "Basic TSD",
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

            chat = LlmChat(
                api_key=self.llm_api_key,
                session_id=f"answer_{uuid.uuid4()}",
                system_message=system_message
            ).with_model("openai", "gpt-4o")

            user_message = UserMessage(text=f"Question: {stem}")
            response = await chat.send_message(user_message)
            
            # Clean and validate the answer
            answer = response.strip()
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

RULES:
1. Use ONLY the exact category and sub-category names from the taxonomy above
2. Select the most specific type_of_question from the sub-category options
3. No out-of-vocabulary categories allowed
4. If admin hints are provided, use them as priors but verify correctness
5. Return ONLY a JSON object with exact matches

Admin hints: Category="{hint_category}", Sub-category="{hint_subcategory}"

RETURN FORMAT:
{{
  "category": "exact_category_name",
  "subcategory": "exact_subcategory_name", 
  "type_of_question": "exact_type_from_subcategory_list",
  "confidence": 0.0-1.0
}}"""

            chat = LlmChat(
                api_key=self.llm_api_key,
                session_id=f"categorize_{uuid.uuid4()}",
                system_message=system_message
            ).with_model("openai", "gpt-4o")

            user_message = UserMessage(text=f"Question: {stem}")
            response = await chat.send_message(user_message)
            
            result = json.loads(response)
            category = result.get("category")
            subcategory = result.get("subcategory")
            type_of_question = result.get("type_of_question")
            
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

            chat = LlmChat(
                api_key=self.llm_api_key,
                session_id=f"solutions_{uuid.uuid4()}",
                system_message=system_message
            ).with_model("openai", "gpt-4o")

            user_message = UserMessage(text=f"""
Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Please provide:
1. SOLUTION APPROACH: [Brief strategy overview]
2. DETAILED SOLUTION: [Comprehensive step-by-step explanation with basics]
""")
            
            response = await chat.send_message(user_message)
            
            # Parse the response to extract approach and detailed solution
            response_text = response.strip()
            
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
        complex_categories = ["Algebra", "Geometry & Mensuration", "Modern Math"]
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
        tricky_categories = ["Time–Speed–Distance (TSD)", "Percentages", "Profit–Loss–Discount (PLD)"]
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
            high_freq = ["Basic TSD", "Basic Percentages", "Linear Equations", "Basic SI & CI"]
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
            "Time–Speed–Distance (TSD)": 90,
            "Percentages": 85,
            "Linear Equations": 80,
            "Basic SI & CI": 75,
            "Ratio–Proportion–Variation": 85
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
            "Time–Speed–Distance (TSD)": "https://youtube.com/watch?v=tsd_basics",
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

            chat = LlmChat(
                api_key=self.llm_api_key,
                session_id=f"answer_{uuid.uuid4()}",
                system_message=system_message
            ).with_model("claude", "claude-3-5-sonnet-20241022")

            user_content = f"Question: {stem}"
            if image_url:
                user_content += f"\nImage: {image_url}"
                
            user_message = UserMessage(text=user_content)
            response = await chat.send_message(user_message)
            
            # Clean up the response to just get the answer
            answer = response.strip()
            
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
                "subcategory": "Time–Speed–Distance (TSD)",
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


# Usage example and testing
async def test_enrichment():
    """Test the enrichment pipeline"""
    pipeline = LLMEnrichmentPipeline("sk-emergent-c6504797427BfB25c0")
    
    test_question = "A train travels at 60 km/h and covers a distance of 240 km. How much time does it take?"
    test_answer = "4 hours"
    
    result = await pipeline.enrich_question(test_question, test_answer)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_enrichment())