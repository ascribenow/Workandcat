#!/usr/bin/env python3
"""
Advanced Conceptual Similarity Calculator
Sophisticated mathematical pattern matching between regular questions and PYQ questions
"""

import json
import logging
import math
from typing import Dict, Any, List, Set, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class AdvancedSimilarityCalculator:
    """
    Advanced conceptual similarity calculation for PYQ frequency analysis
    Uses multiple sophisticated matching algorithms for accurate pattern recognition
    """
    
    def __init__(self):
        # Weights for different similarity components
        self.weights = {
            "core_concepts": 0.40,      # Most important: mathematical concepts
            "solution_method": 0.25,    # Important: solution approach
            "operations": 0.20,         # Moderate: mathematical operations
            "structure_type": 0.15      # Support: problem structure
        }
        
        # Concept similarity mapping for mathematical relationships
        self.concept_relationships = self._build_concept_relationships()
    
    def calculate_advanced_conceptual_similarity(self, regular_concepts: Dict[str, Any], pyq_concepts: Dict[str, Any]) -> float:
        """
        Calculate sophisticated conceptual similarity between regular and PYQ questions
        Returns similarity score from 0.0 (no similarity) to 1.0 (identical concepts)
        """
        try:
            if not regular_concepts or not pyq_concepts:
                return 0.0
            
            logger.debug(f"🔍 Calculating similarity between concepts")
            
            similarity_components = {}
            
            # COMPONENT 1: Core Concept Matching (40% weight)
            core_similarity = self._calculate_concept_set_similarity(
                regular_concepts.get('core_concepts', []),
                pyq_concepts.get('core_concepts', [])
            )
            similarity_components['core_concepts'] = core_similarity
            
            # COMPONENT 2: Solution Method Matching (25% weight)
            method_similarity = self._calculate_method_similarity(
                regular_concepts.get('solution_method', ''),
                pyq_concepts.get('solution_method', '')
            )
            similarity_components['solution_method'] = method_similarity
            
            # COMPONENT 3: Mathematical Operations Similarity (20% weight)
            ops_similarity = self._calculate_operations_similarity(
                regular_concepts.get('operations', []),
                pyq_concepts.get('operations', [])
            )
            similarity_components['operations'] = ops_similarity
            
            # COMPONENT 4: Problem Structure Similarity (15% weight)
            structure_similarity = self._calculate_structure_similarity(
                regular_concepts.get('structure_type', ''),
                pyq_concepts.get('structure_type', '')
            )
            similarity_components['structure_type'] = structure_similarity
            
            # Calculate weighted final similarity
            final_similarity = sum(
                self.weights[component] * score 
                for component, score in similarity_components.items()
            )
            
            logger.debug(f"📊 Similarity components: {similarity_components}")
            logger.debug(f"🎯 Final similarity: {final_similarity:.3f}")
            
            return min(1.0, max(0.0, final_similarity))
            
        except Exception as e:
            logger.error(f"❌ Error calculating conceptual similarity: {e}")
            return 0.0
    
    def _calculate_concept_set_similarity(self, regular_concepts: List[str], pyq_concepts: List[str]) -> float:
        """
        Calculate similarity between two sets of mathematical concepts
        Uses both exact matching and semantic similarity
        """
        try:
            if not regular_concepts or not pyq_concepts:
                return 0.0
            
            # Convert to lowercase sets for comparison
            regular_set = set(concept.lower().strip() for concept in regular_concepts if concept)
            pyq_set = set(concept.lower().strip() for concept in pyq_concepts if concept)
            
            if not regular_set or not pyq_set:
                return 0.0
            
            # EXACT MATCHES (60% weight)
            exact_matches = len(regular_set & pyq_set)
            exact_score = exact_matches / len(regular_set | pyq_set) if regular_set | pyq_set else 0.0
            
            # SEMANTIC SIMILARITY (40% weight) - related concepts
            semantic_score = self._calculate_semantic_concept_similarity(regular_set, pyq_set)
            
            final_score = 0.6 * exact_score + 0.4 * semantic_score
            
            logger.debug(f"🔗 Concept similarity: exact={exact_score:.3f}, semantic={semantic_score:.3f}, final={final_score:.3f}")
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Error calculating concept set similarity: {e}")
            return 0.0
    
    def _calculate_semantic_concept_similarity(self, regular_concepts: Set[str], pyq_concepts: Set[str]) -> float:
        """
        Calculate semantic similarity between mathematical concepts
        """
        try:
            if not regular_concepts or not pyq_concepts:
                return 0.0
            
            # Find semantically related concepts
            semantic_matches = 0
            total_comparisons = 0
            
            for regular_concept in regular_concepts:
                for pyq_concept in pyq_concepts:
                    total_comparisons += 1
                    
                    # Check if concepts are semantically related
                    if self._are_concepts_related(regular_concept, pyq_concept):
                        semantic_matches += 1
            
            return semantic_matches / total_comparisons if total_comparisons > 0 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Error calculating semantic concept similarity: {e}")
            return 0.0
    
    def _are_concepts_related(self, concept1: str, concept2: str) -> bool:
        """
        Check if two mathematical concepts are semantically related
        """
        try:
            # Exact match
            if concept1 == concept2:
                return True
            
            # Check concept relationships mapping
            related_concepts = self.concept_relationships.get(concept1, set())
            if concept2 in related_concepts:
                return True
            
            # Reverse check
            related_concepts = self.concept_relationships.get(concept2, set())
            if concept1 in related_concepts:
                return True
            
            # String similarity for variations (e.g., "speed_calculation" vs "speed_analysis")
            similarity = SequenceMatcher(None, concept1, concept2).ratio()
            return similarity > 0.7
            
        except Exception as e:
            logger.error(f"❌ Error checking concept relationship: {e}")
            return False
    
    def _calculate_method_similarity(self, regular_method: str, pyq_method: str) -> float:
        """
        Calculate similarity between solution methods
        """
        try:
            if not regular_method or not pyq_method:
                return 0.0
            
            regular_method = regular_method.lower().strip()
            pyq_method = pyq_method.lower().strip()
            
            # Exact match
            if regular_method == pyq_method:
                return 1.0
            
            # Check for method relationships
            method_families = {
                'algebraic': ['algebraic_method', 'algebraic_manipulation', 'equation_solving', 'substitution_method'],
                'arithmetic': ['arithmetic_method', 'calculation_method', 'basic_calculation', 'numerical_method'],
                'geometric': ['geometric_analysis', 'geometric_method', 'geometric_construction', 'spatial_analysis'],
                'proportional': ['ratio_proportion_method', 'unitary_method', 'proportion_analysis', 'scaling_method'],
                'financial': ['commercial_mathematics', 'interest_formula', 'financial_analysis', 'business_calculation'],
                'motion': ['speed_distance_analysis', 'motion_analysis', 'kinematics', 'relative_motion_method']
            }
            
            # Find family matches
            regular_family = None
            pyq_family = None
            
            for family, methods in method_families.items():
                if regular_method in methods:
                    regular_family = family
                if pyq_method in methods:
                    pyq_family = family
            
            if regular_family and regular_family == pyq_family:
                return 0.8  # High similarity for same family
            
            # String similarity as fallback
            string_similarity = SequenceMatcher(None, regular_method, pyq_method).ratio()
            return string_similarity if string_similarity > 0.5 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Error calculating method similarity: {e}")
            return 0.0
    
    def _calculate_operations_similarity(self, regular_ops: List[str], pyq_ops: List[str]) -> float:
        """
        Calculate similarity between mathematical operations
        """
        try:
            if not regular_ops or not pyq_ops:
                return 0.0
            
            # Convert to lowercase sets
            regular_set = set(op.lower().strip() for op in regular_ops if op)
            pyq_set = set(op.lower().strip() for op in pyq_ops if op)
            
            if not regular_set or not pyq_set:
                return 0.0
            
            # Calculate Jaccard similarity (intersection over union)
            intersection = len(regular_set & pyq_set)
            union = len(regular_set | pyq_set)
            
            jaccard_similarity = intersection / union if union > 0 else 0.0
            
            # Bonus for having many operations in common (indicates similar complexity)
            complexity_bonus = min(0.2, intersection * 0.05) if intersection > 2 else 0.0
            
            return min(1.0, jaccard_similarity + complexity_bonus)
            
        except Exception as e:
            logger.error(f"❌ Error calculating operations similarity: {e}")
            return 0.0
    
    def _calculate_structure_similarity(self, regular_structure: str, pyq_structure: str) -> float:
        """
        Calculate similarity between problem structures
        """
        try:
            if not regular_structure or not pyq_structure:
                return 0.0
            
            regular_structure = regular_structure.lower().strip()
            pyq_structure = pyq_structure.lower().strip()
            
            # Exact match
            if regular_structure == pyq_structure:
                return 1.0
            
            # Structure categories for partial matching
            structure_categories = {
                'word_problems': ['word_problem', 'word_problem_single_entity', 'word_problem_multi_step', 'story_problem'],
                'comparison': ['comparison_problem', 'relative_comparison', 'ranking_problem'],
                'optimization': ['optimization_problem', 'maximum_minimum', 'best_case_problem'],
                'sequential': ['sequence_problem', 'series_problem', 'progression_problem'],
                'geometric': ['geometric_problem', 'shape_problem', 'spatial_problem'],
                'business': ['business_problem', 'commercial_problem', 'financial_problem']
            }
            
            # Find category matches
            regular_category = None
            pyq_category = None
            
            for category, structures in structure_categories.items():
                if regular_structure in structures:
                    regular_category = category
                if pyq_structure in structures:
                    pyq_category = category
            
            if regular_category and regular_category == pyq_category:
                return 0.7  # Good similarity for same category
            
            # String similarity as fallback
            string_similarity = SequenceMatcher(None, regular_structure, pyq_structure).ratio()
            return string_similarity if string_similarity > 0.6 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Error calculating structure similarity: {e}")
            return 0.0
    
    def _build_concept_relationships(self) -> Dict[str, Set[str]]:
        """
        Build a mapping of related mathematical concepts for semantic matching
        """
        return {
            # Speed, Time, Distance concepts
            'relative_speed': {'speed_calculation', 'distance_formula', 'velocity', 'average_speed'},
            'speed_calculation': {'relative_speed', 'distance_formula', 'time_calculation', 'velocity'},
            'distance_formula': {'speed_calculation', 'relative_speed', 'displacement'},
            'time_calculation': {'speed_calculation', 'duration_analysis', 'temporal_analysis'},
            
            # Percentage concepts
            'percentage_calculation': {'proportional_change', 'percent_change', 'percentage_increase'},
            'percentage_increase': {'percentage_decrease', 'percentage_calculation', 'growth_rate'},
            'percentage_decrease': {'percentage_increase', 'percentage_calculation', 'reduction_rate'},
            'proportional_change': {'percentage_calculation', 'ratio_change', 'proportional_analysis'},
            
            # Profit/Loss concepts
            'cost_price_analysis': {'profit_margin', 'selling_price_analysis', 'business_calculation'},
            'profit_margin': {'cost_price_analysis', 'markup_analysis', 'profit_calculation'},
            'discount_calculation': {'markup_analysis', 'price_reduction', 'commercial_mathematics'},
            'markup_analysis': {'discount_calculation', 'profit_margin', 'price_increase'},
            
            # Interest concepts
            'simple_interest': {'compound_interest', 'interest_calculation', 'principal_calculation'},
            'compound_interest': {'simple_interest', 'compound_calculation', 'exponential_growth'},
            'principal_calculation': {'interest_calculation', 'amount_calculation', 'financial_analysis'},
            
            # Geometric concepts
            'area_calculation': {'perimeter_calculation', 'geometric_measurement', 'shape_analysis'},
            'perimeter_calculation': {'area_calculation', 'boundary_measurement', 'geometric_analysis'},
            'triangle_similarity': {'geometric_similarity', 'proportional_triangles', 'similar_figures'},
            'angle_properties': {'geometric_properties', 'angular_measurement', 'geometric_relationships'},
            
            # Algebraic concepts
            'linear_equations': {'equation_solving', 'algebraic_manipulation', 'variable_solving'},
            'quadratic_equations': {'polynomial_equations', 'quadratic_roots', 'algebraic_equations'},
            'algebraic_manipulation': {'equation_solving', 'algebraic_simplification', 'expression_handling'},
            
            # Ratio/Proportion concepts
            'ratio_analysis': {'proportion_calculation', 'proportional_analysis', 'comparative_analysis'},
            'proportion_calculation': {'ratio_analysis', 'proportional_relationships', 'scaling'},
            'direct_variation': {'proportional_relationships', 'linear_relationships', 'direct_proportionality'},
            'inverse_variation': {'inversely_proportional', 'reciprocal_relationships', 'hyperbolic_relationships'}
        }
    
    def get_similarity_breakdown(self, regular_concepts: Dict[str, Any], pyq_concepts: Dict[str, Any]) -> Dict[str, float]:
        """
        Get detailed breakdown of similarity components for analysis
        """
        try:
            breakdown = {}
            
            breakdown['core_concepts'] = self._calculate_concept_set_similarity(
                regular_concepts.get('core_concepts', []),
                pyq_concepts.get('core_concepts', [])
            )
            
            breakdown['solution_method'] = self._calculate_method_similarity(
                regular_concepts.get('solution_method', ''),
                pyq_concepts.get('solution_method', '')
            )
            
            breakdown['operations'] = self._calculate_operations_similarity(
                regular_concepts.get('operations', []),
                pyq_concepts.get('operations', [])
            )
            
            breakdown['structure_type'] = self._calculate_structure_similarity(
                regular_concepts.get('structure_type', ''),
                pyq_concepts.get('structure_type', '')
            )
            
            breakdown['weighted_total'] = sum(
                self.weights[component] * score 
                for component, score in breakdown.items() 
                if component in self.weights
            )
            
            return breakdown
            
        except Exception as e:
            logger.error(f"❌ Error getting similarity breakdown: {e}")
            return {}

# Utility functions for integration
def calculate_question_similarity(regular_concepts: Dict[str, Any], pyq_concepts: Dict[str, Any]) -> float:
    """
    Utility function to calculate similarity between question concepts
    """
    calculator = AdvancedSimilarityCalculator()
    return calculator.calculate_advanced_conceptual_similarity(regular_concepts, pyq_concepts)

def get_detailed_similarity_analysis(regular_concepts: Dict[str, Any], pyq_concepts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get detailed similarity analysis for debugging and optimization
    """
    calculator = AdvancedSimilarityCalculator()
    
    similarity_score = calculator.calculate_advanced_conceptual_similarity(regular_concepts, pyq_concepts)
    breakdown = calculator.get_similarity_breakdown(regular_concepts, pyq_concepts)
    
    return {
        "similarity_score": similarity_score,
        "component_breakdown": breakdown,
        "weights_used": calculator.weights,
        "threshold_recommendation": "Use similarity > 0.4 for meaningful matches"
    }

if __name__ == "__main__":
    # Test the similarity calculator
    calculator = AdvancedSimilarityCalculator()
    print("✅ Advanced Similarity Calculator initialized successfully")
    print(f"📊 Concept relationships: {len(calculator.concept_relationships)} concepts mapped")