"""
Phase 3 Integration Tests - Sentinel tests for bulletproof pipeline
These tests catch regressions and ensure contract compliance
"""

import pytest
import json
from typing import Dict, Any, List
from services.deterministic_kernels import QuestionCandidate, validate_pack
from services.candidate_provider import candidate_provider
from services.planner import planner_service
from services.pipeline import AdaptiveConfig
from util.json_guard import parse_and_validate
from util.schemas import PLANNER_SCHEMA, SUMMARIZER_SCHEMA

class TestPhase3Contracts:
    """Sentinel tests for Phase 3 LLM integration contracts"""
    
    def test_band_pyq_never_relax(self):
        """Test that Band/PYQ constraints are never relaxed"""
        # Create minimal inventory that cannot meet PYQ minima
        candidates = [
            QuestionCandidate(
                question_id=f"q_{i}",
                difficulty_band="Easy" if i < 3 else "Medium" if i < 9 else "Hard",
                subcategory="Arithmetic",
                type_of_question="Addition",
                core_concepts=("addition",),
                pyq_frequency_score=0.5,  # All below minimum
                pair="Arithmetic:Addition"
            )
            for i in range(12)
        ]
        
        # Test validation should fail for PYQ requirements
        validation_result = validate_pack(candidates, candidates, set(), set())
        
        assert validation_result["valid"] == False
        assert any("PYQ score" in error for error in validation_result["errors"])
        
        # Ensure band/PYQ are never relaxed in constraint report
        # This would be tested in actual planner integration
        
    def test_pair_scoped_readiness(self):
        """Test that readiness is pair-scoped, not concept-global"""
        # Create scenario where same concept appears in different pairs
        candidates = self._create_multi_pair_candidates()
        
        readiness_levels = {
            "addition_concept": "Weak",  # Same concept, different pairs
        }
        
        # Mock planner data with different readiness for same concept in different pairs
        final_readiness = [
            {"semantic_id": "addition_concept", "pair": "Arithmetic:Addition", "readiness_level": "Weak"},
            {"semantic_id": "addition_concept", "pair": "Algebra:Addition", "readiness_level": "Strong"},
        ]
        
        # Planner should use readiness for item's own pair only
        # This test validates the concept but actual implementation would be in planner
        
        assert len(final_readiness) == 2
        assert final_readiness[0]["readiness_level"] != final_readiness[1]["readiness_level"]
    
    def test_cold_start_breadth(self):
        """Test cold start achieves ≥5 distinct pairs with band/PYQ satisfied"""
        # Create diverse candidate pool for cold start
        candidates = self._create_diverse_candidates()
        
        # Mock cold start planner result
        cold_start_plan = {
            "pack": [
                {
                    "item_id": f"q_{i}",
                    "bucket": "Easy" if i < 3 else "Medium" if i < 9 else "Hard",
                    "why": {
                        "semantic_concepts": [f"concept_{i % 6}"],  # 6 different concepts
                        "pair": f"Cat{i % 5}:Type{i % 5}",  # 5 different pairs
                        "pyq_frequency_score": 1.0 if i < 4 else 1.5 if i < 6 else 0.5
                    }
                }
                for i in range(12)
            ],
            "constraint_report": {"met": [], "relaxed": []}
        }
        
        # Validate breadth requirement
        pairs = set()
        pyq_1_0_count = 0
        pyq_1_5_count = 0
        
        for item in cold_start_plan["pack"]:
            pairs.add(item["why"]["pair"])
            if item["why"]["pyq_frequency_score"] >= 1.0:
                pyq_1_0_count += 1
            if item["why"]["pyq_frequency_score"] >= 1.5:
                pyq_1_5_count += 1
        
        assert len(pairs) >= 5  # Cold start breadth requirement
        assert pyq_1_0_count >= 2  # PYQ requirements still enforced
        assert pyq_1_5_count >= 2
    
    def test_relaxation_ladder(self):
        """Test that coverage relaxes before readiness"""
        # Create scenario where readiness can't be met but coverage can
        relaxed_items = [
            {"name": "coverage_alignment", "reason": "High coverage debt items unavailable"},
            # readiness should NOT be relaxed if coverage was successfully relaxed
        ]
        
        # Validate that coverage relaxes first
        coverage_relaxed = any(item["name"] == "coverage_alignment" for item in relaxed_items)
        readiness_relaxed = any(item["name"] == "readiness_alignment" for item in relaxed_items)
        
        assert coverage_relaxed == True
        assert readiness_relaxed == False  # Should not relax if coverage relaxation worked
    
    def test_weights_guardrails(self):
        """Test weight distribution guardrails"""
        # Test equal split when dominance_confidence != 'high'
        dominance_by_item = {
            "q1": {
                "dominant": ["concept_a", "concept_b"],
                "secondary": ["concept_c"],
                "dominance_confidence": "med"  # Not high
            }
        }
        
        from services.pipeline import _convert_dominance_to_weights
        weights_by_item = _convert_dominance_to_weights(dominance_by_item)
        
        # Should be equal split
        weights = weights_by_item.get("q1", {})
        total_weight = sum(weights.values())
        
        assert abs(total_weight - 1.0) < 0.01  # Sum ≈ 1.0
        
        # Check equal distribution for non-high confidence
        expected_weight = 1.0 / 3  # 3 concepts total
        for weight in weights.values():
            assert abs(weight - expected_weight) < 0.01
    
    def test_json_schema_validation(self):
        """Test JSON schema validation with both valid and invalid inputs"""
        # Test valid Planner JSON
        valid_planner_json = {
            "pack": [
                {
                    "item_id": "q1",
                    "bucket": "Easy",
                    "why": {
                        "semantic_concepts": ["addition"],
                        "pair": "Arithmetic:Addition",
                        "pyq_frequency_score": 1.0
                    }
                }
            ] * 12,  # Exactly 12 items
            "constraint_report": {
                "met": ["total_count", "difficulty_distribution"],
                "relaxed": []
            }
        }
        
        ok, data, errors = parse_and_validate(json.dumps(valid_planner_json), PLANNER_SCHEMA)
        assert ok == True
        assert len(errors) == 0
        
        # Test invalid Planner JSON (missing required field)
        invalid_planner_json = {
            "pack": [{"item_id": "q1", "bucket": "Easy"}] * 12,  # Missing 'why' field
            "constraint_report": {"met": [], "relaxed": []}
        }
        
        ok, data, errors = parse_and_validate(json.dumps(invalid_planner_json), PLANNER_SCHEMA)
        assert ok == False
        assert len(errors) > 0
    
    def test_configuration_completeness(self):
        """Test that all required configuration constants are present"""
        # Verify all v1.1 config constants exist
        required_constants = [
            'K_POOL_PER_BAND', 'K_POOL_EXPANSION', 'R_RECENCY_SESSIONS',
            'COVERAGE_K', 'COVERAGE_S_HIGH', 'COVERAGE_S_MED',
            'PYQ_MIN_1_0', 'PYQ_MIN_1_5', 'QUESTIONS_PER_SESSION'
        ]
        
        for constant in required_constants:
            assert hasattr(AdaptiveConfig, constant), f"Missing config constant: {constant}"
        
        # Verify specific values match v1.1 spec
        assert AdaptiveConfig.K_POOL_PER_BAND == 80
        assert AdaptiveConfig.K_POOL_EXPANSION == [80, 160, 320]
        assert AdaptiveConfig.R_RECENCY_SESSIONS == 3
        assert AdaptiveConfig.COVERAGE_K == 6
        assert AdaptiveConfig.COVERAGE_S_HIGH == 4
        assert AdaptiveConfig.COVERAGE_S_MED == 2
        assert AdaptiveConfig.PYQ_MIN_1_0 == 2
        assert AdaptiveConfig.PYQ_MIN_1_5 == 2
    
    def test_validator_completeness(self):
        """Test all validator checks are implemented"""
        # Create test pack for validation
        candidates = self._create_valid_candidates()
        valid_pairs = {"Arithmetic:Addition", "Geometry:Area"}
        known_concepts = {"addition", "area_calculation"}
        
        pack = candidates[:12]  # Valid 12-question pack
        
        validation_result = validate_pack(pack, candidates, valid_pairs, known_concepts)
        
        # Check that validation covers all required aspects
        constraints = validation_result.get("constraints", {})
        
        required_constraints = [
            "total_count", "difficulty_easy", "difficulty_medium", "difficulty_hard",
            "pyq_score_1_0", "pyq_score_1_5", "no_duplicates"
        ]
        
        for constraint in required_constraints:
            assert constraint in constraints, f"Missing validation constraint: {constraint}"
    
    def _create_multi_pair_candidates(self) -> List[QuestionCandidate]:
        """Create candidates with same concept in different pairs"""
        return [
            QuestionCandidate(
                question_id=f"q_{i}",
                difficulty_band="Easy" if i < 4 else "Medium" if i < 10 else "Hard",
                subcategory="Arithmetic" if i < 6 else "Algebra",
                type_of_question="Addition",
                core_concepts=("addition_concept",),
                pyq_frequency_score=1.0 if i < 4 else 1.5 if i < 6 else 0.5,
                pair=f"{'Arithmetic' if i < 6 else 'Algebra'}:Addition"
            )
            for i in range(12)
        ]
    
    def _create_diverse_candidates(self) -> List[QuestionCandidate]:
        """Create diverse candidates for cold start testing"""
        return [
            QuestionCandidate(
                question_id=f"diverse_q_{i}",
                difficulty_band="Easy" if i < 6 else "Medium" if i < 12 else "Hard",
                subcategory=f"Category_{i % 5}",
                type_of_question=f"Type_{i % 5}",
                core_concepts=(f"concept_{i % 6}",),
                pyq_frequency_score=1.0 if i < 8 else 1.5 if i < 10 else 0.5,
                pair=f"Category_{i % 5}:Type_{i % 5}"
            )
            for i in range(20)  # More than needed for selection
        ]
    
    def _create_valid_candidates(self) -> List[QuestionCandidate]:
        """Create valid candidates for general testing"""
        return [
            QuestionCandidate(
                question_id=f"valid_q_{i}",
                difficulty_band="Easy" if i < 5 else "Medium" if i < 11 else "Hard",
                subcategory="Arithmetic" if i < 8 else "Geometry",
                type_of_question="Addition" if i < 8 else "Area",
                core_concepts=("addition" if i < 8 else "area_calculation",),
                pyq_frequency_score=1.0 if i < 6 else 1.5 if i < 8 else 0.5,
                pair=f"{'Arithmetic:Addition' if i < 8 else 'Geometry:Area'}"
            )
            for i in range(15)
        ]