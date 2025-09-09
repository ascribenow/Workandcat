#!/usr/bin/env python3
"""
Canonical Taxonomy Service
Single source of truth for all taxonomy classifications
"""

import difflib
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# SINGLE SOURCE OF TRUTH - CANONICAL TAXONOMY
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
    
    def fuzzy_match_category(self, llm_category: str, threshold: float = 0.8) -> Optional[str]:
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
    
    def fuzzy_match_subcategory(self, llm_subcategory: str, canonical_category: str, threshold: float = 0.8) -> Optional[str]:
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
    
    def fuzzy_match_question_type(self, llm_type: str, canonical_category: str, canonical_subcategory: str, threshold: float = 0.8) -> Optional[str]:
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
    
    def get_canonical_taxonomy_path(self, llm_category: str, llm_subcategory: str, llm_type: str) -> Tuple[str, str, str]:
        """Get complete canonical taxonomy path with fuzzy matching"""
        
        # Step 1: Match category
        canonical_category = self.fuzzy_match_category(llm_category)
        
        # Step 2: Match subcategory within canonical category
        canonical_subcategory = self.fuzzy_match_subcategory(llm_subcategory, canonical_category)
        
        # Step 3: Match question type within canonical subcategory
        canonical_type = self.fuzzy_match_question_type(llm_type, canonical_category, canonical_subcategory)
        
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

# Global instance
canonical_taxonomy_service = CanonicalTaxonomyService()