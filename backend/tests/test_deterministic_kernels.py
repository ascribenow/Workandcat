#!/usr/bin/env python3
"""
Unit tests for deterministic kernels
"""

import pytest
import sys
import os

# Add the parent directory to the path to import services
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.deterministic_kernels import (
    stable_semantic_id,
    weights_from_dominance,
    compute_weighted_counts,
    finalize_readiness,
    coverage_debt_by_sessions,
    validate_pack,
    AttemptEvent,
    QuestionCandidate,
    ReadinessLevel
)

class TestStableSemanticId:
    """Test stable_semantic_id kernel"""
    
    def test_basic_functionality(self):
        """Test basic semantic ID generation"""
        result = stable_semantic_id("Distance")
        assert isinstance(result, str)
        assert len(result) == 12
        
        # Should be deterministic
        result2 = stable_semantic_id("Distance")
        assert result == result2
        
    def test_normalization(self):
        """Test that normalization works correctly"""
        # Different cases should produce same result
        assert stable_semantic_id("Distance") == stable_semantic_id("distance")
        assert stable_semantic_id(" Distance ") == stable_semantic_id("distance")
        assert stable_semantic_id("DISTANCE") == stable_semantic_id("distance")
        
    def test_different_concepts(self):
        """Test that different concepts produce different IDs"""
        id1 = stable_semantic_id("Distance")
        id2 = stable_semantic_id("Rate")
        assert id1 != id2
        
    def test_invalid_input(self):
        """Test error handling for invalid input"""
        with pytest.raises(ValueError):
            stable_semantic_id("")
        with pytest.raises(ValueError):
            stable_semantic_id(None)
        with pytest.raises(ValueError):
            stable_semantic_id(123)

class TestWeightsFromDominance:
    """Test weights_from_dominance kernel"""
    
    def test_basic_mapping(self):
        """Test basic dominance to weight mapping"""
        dominance = {
            "concept1": "High",
            "concept2": "Medium", 
            "concept3": "Low"
        }
        
        weights = weights_from_dominance(dominance)
        
        assert weights["concept1"] == 1.0
        assert weights["concept2"] == 0.6
        assert weights["concept3"] == 0.3
        
    def test_case_insensitive(self):
        """Test case insensitive label handling"""
        dominance = {
            "concept1": "HIGH",
            "concept2": "medium",
            "concept3": "Low"
        }
        
        weights = weights_from_dominance(dominance)
        
        assert weights["concept1"] == 1.0
        assert weights["concept2"] == 0.6
        assert weights["concept3"] == 0.3
    
    def test_unknown_labels(self):
        """Test handling of unknown dominance labels"""
        dominance = {
            "concept1": "Unknown",
            "concept2": "Medium"
        }
        
        weights = weights_from_dominance(dominance)
        
        assert weights["concept1"] == 0.6  # Default to Medium
        assert weights["concept2"] == 0.6
        
    def test_confidence_threshold(self):
        """Test confidence threshold behavior"""
        dominance = {
            "concept1": "High",
            "concept2": "Low",
            "concept3": "Low"
        }
        
        # Should work without errors even with many low-confidence
        weights = weights_from_dominance(dominance, confidence_threshold=0.5)
        assert len(weights) == 3
        
    def test_invalid_input(self):
        """Test error handling for invalid input"""
        with pytest.raises(ValueError):
            weights_from_dominance("not_a_dict")
        with pytest.raises(ValueError):
            weights_from_dominance({}, confidence_threshold=-0.1)
        with pytest.raises(ValueError):
            weights_from_dominance({}, confidence_threshold=1.1)

class TestComputeWeightedCounts:
    """Test compute_weighted_counts kernel"""
    
    def test_basic_counting(self):
        """Test basic weighted counting"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=1,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["Addition"],
                pyq_frequency_score=1.0
            ),
            AttemptEvent(
                question_id="q2", was_correct=False, skipped=False,
                response_time_ms=45000, sess_seq_at_serve=1,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["Addition"],
                pyq_frequency_score=1.0
            )
        ]
        
        concept_weights = {"add123": 1.0}
        semantic_id_map = {"Addition": "add123"}
        
        counts = compute_weighted_counts(events, concept_weights, semantic_id_map)
        
        assert "add123" in counts
        assert counts["add123"]["correct"] == 1.0
        assert counts["add123"]["wrong"] == 1.0
        assert counts["add123"]["skipped"] == 0.0
        assert counts["add123"]["total"] == 2.0
        
    def test_weighted_counting(self):
        """Test that weights are properly applied"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=1,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["Addition"],
                pyq_frequency_score=1.0
            )
        ]
        
        concept_weights = {"add123": 0.5}
        semantic_id_map = {"Addition": "add123"}
        
        counts = compute_weighted_counts(events, concept_weights, semantic_id_map)
        
        assert counts["add123"]["correct"] == 0.5
        assert counts["add123"]["total"] == 0.5
        
    def test_multiple_concepts_per_question(self):
        """Test questions with multiple concepts"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=1,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Word Problems", 
                core_concepts=["Addition", "Multiplication"],
                pyq_frequency_score=1.0
            )
        ]
        
        concept_weights = {"add123": 1.0, "mult456": 0.8}
        semantic_id_map = {"Addition": "add123", "Multiplication": "mult456"}
        
        counts = compute_weighted_counts(events, concept_weights, semantic_id_map)
        
        assert "add123" in counts
        assert "mult456" in counts
        assert counts["add123"]["correct"] == 1.0
        assert counts["mult456"]["correct"] == 0.8
        
    def test_unmapped_concepts(self):
        """Test handling of unmapped concepts"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=1,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["UnknownConcept"],
                pyq_frequency_score=1.0
            )
        ]
        
        concept_weights = {}
        semantic_id_map = {}
        
        counts = compute_weighted_counts(events, concept_weights, semantic_id_map)
        
        # Should be empty since concept is unmapped
        assert len(counts) == 0
        
    def test_default_weights(self):
        """Test default weight assignment for unknown concepts"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=1,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["Addition"],
                pyq_frequency_score=1.0
            )
        ]
        
        concept_weights = {}  # Empty weights
        semantic_id_map = {"Addition": "add123"}
        
        counts = compute_weighted_counts(events, concept_weights, semantic_id_map)
        
        # Should use default weight of 0.6
        assert counts["add123"]["correct"] == 0.6

class TestFinalizeReadiness:
    """Test finalize_readiness kernel"""
    
    def test_skip_rule(self):
        """Test skip → Weak rule"""
        counts = {
            "concept1": {"correct": 0.0, "wrong": 0.0, "skipped": 3.0, "total": 3.0}
        }
        
        readiness = finalize_readiness(counts)
        assert readiness["concept1"] == ReadinessLevel.WEAK
        
    def test_never_correct_rule(self):
        """Test never-correct → Weak rule"""
        counts = {
            "concept1": {"correct": 0.0, "wrong": 2.0, "skipped": 0.0, "total": 2.0}
        }
        
        readiness = finalize_readiness(counts)
        assert readiness["concept1"] == ReadinessLevel.WEAK
        
    def test_high_wrong_rule(self):
        """Test wrong > 3 → Moderate rule"""
        counts = {
            "concept1": {"correct": 1.0, "wrong": 4.0, "skipped": 0.0, "total": 5.0}
        }
        
        readiness = finalize_readiness(counts)
        assert readiness["concept1"] == ReadinessLevel.MODERATE
        
    def test_good_correct_range_rule(self):
        """Test correct 1-3 → Strong rule"""
        for correct_count in [1.0, 2.0, 3.0]:
            counts = {
                "concept1": {"correct": correct_count, "wrong": 0.0, "skipped": 0.0, "total": correct_count}
            }
            
            readiness = finalize_readiness(counts)
            assert readiness["concept1"] == ReadinessLevel.STRONG
            
    def test_high_correct_rule(self):
        """Test correct > 3 → Moderate rule"""
        counts = {
            "concept1": {"correct": 5.0, "wrong": 0.0, "skipped": 0.0, "total": 5.0}
        }
        
        readiness = finalize_readiness(counts)
        assert readiness["concept1"] == ReadinessLevel.MODERATE
        
    def test_insufficient_data_rule(self):
        """Test insufficient data → Moderate rule"""
        counts = {
            "concept1": {"correct": 0.0, "wrong": 0.0, "skipped": 0.0, "total": 0.0}
        }
        
        readiness = finalize_readiness(counts)
        assert readiness["concept1"] == ReadinessLevel.MODERATE

class TestCoverageDebtBySessions:
    """Test coverage_debt_by_sessions kernel"""
    
    def test_basic_coverage_calculation(self):
        """Test basic coverage debt calculation"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=3,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["Addition"],
                pyq_frequency_score=1.0
            ),
            AttemptEvent(
                question_id="q2", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=3,
                difficulty_band="Medium", subcategory="Geometry",
                type_of_question="Triangles", core_concepts=["Triangles"],
                pyq_frequency_score=1.0
            ),
            AttemptEvent(
                question_id="q3", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=3,
                difficulty_band="Medium", subcategory="Arithmetic",
                type_of_question="Addition", core_concepts=["Addition"],
                pyq_frequency_score=1.0
            )
        ]
        
        debt = coverage_debt_by_sessions(events, sessions_lookback=5)
        
        # Arithmetic:Addition appears twice, Geometry:Triangles once
        # So Geometry:Triangles should have higher debt
        assert "Arithmetic:Addition" in debt
        assert "Geometry:Triangles" in debt
        assert debt["Geometry:Triangles"] > debt["Arithmetic:Addition"]
        
    def test_sessions_lookback(self):
        """Test sessions lookback window"""
        events = [
            AttemptEvent(
                question_id="q1", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=1,  # Old session
                difficulty_band="Medium", subcategory="Old",
                type_of_question="Content", core_concepts=["Old"],
                pyq_frequency_score=1.0
            ),
            AttemptEvent(
                question_id="q2", was_correct=True, skipped=False,
                response_time_ms=30000, sess_seq_at_serve=5,  # Recent session
                difficulty_band="Medium", subcategory="Recent",
                type_of_question="Content", core_concepts=["Recent"],
                pyq_frequency_score=1.0
            )
        ]
        
        debt = coverage_debt_by_sessions(events, sessions_lookback=1)
        
        # Should only consider session 5 (most recent)
        assert "Recent:Content" in debt
        assert "Old:Content" not in debt
        
    def test_empty_events(self):
        """Test handling of empty events list"""
        debt = coverage_debt_by_sessions([])
        assert debt == {}

class TestValidatePack:
    """Test validate_pack kernel"""
    
    def create_valid_pack(self):
        """Helper to create a valid 12-question pack"""
        pack = []
        
        # 3 Easy questions
        for i in range(3):
            pack.append(QuestionCandidate(
                question_id=f"easy_{i}",
                difficulty_band="Easy",
                subcategory="Arithmetic",
                type_of_question="Addition",
                core_concepts=["Addition"],
                pyq_frequency_score=1.0,
                pair="Arithmetic:Addition"
            ))
            
        # 6 Medium questions
        for i in range(6):
            pack.append(QuestionCandidate(
                question_id=f"medium_{i}",
                difficulty_band="Medium",
                subcategory="Geometry",
                type_of_question="Triangles",
                core_concepts=["Triangles"],
                pyq_frequency_score=1.2 if i < 2 else 1.6,  # Ensure PYQ minima
                pair="Geometry:Triangles"
            ))
            
        # 3 Hard questions
        for i in range(3):
            pack.append(QuestionCandidate(
                question_id=f"hard_{i}",
                difficulty_band="Hard",
                subcategory="Algebra",
                type_of_question="Equations",
                core_concepts=["Equations"],
                pyq_frequency_score=1.8,
                pair="Algebra:Equations"
            ))
            
        return pack
    
    def test_valid_pack(self):
        """Test validation of a completely valid pack"""
        pack = self.create_valid_pack()
        pool = pack  # Same as pack for this test
        valid_pairs = {"Arithmetic:Addition", "Geometry:Triangles", "Algebra:Equations"}
        known_concepts = {"Addition", "Triangles", "Equations"}
        
        result = validate_pack(pack, pool, valid_pairs, known_concepts)
        
        assert result["valid"] == True
        assert len(result["errors"]) == 0
        assert result["constraints"]["total_count"]["passed"] == True
        assert result["constraints"]["difficulty_distribution"]["passed"] == True
        assert result["constraints"]["pyq_score_1_0"]["passed"] == True
        assert result["constraints"]["pyq_score_1_5"]["passed"] == True
        
    def test_wrong_total_count(self):
        """Test validation failure for wrong question count"""
        pack = self.create_valid_pack()[:10]  # Only 10 questions
        
        result = validate_pack(pack, pack, set(), set())
        
        assert result["valid"] == False
        assert any("Expected 12 questions, got 10" in error for error in result["errors"])
        
    def test_wrong_difficulty_distribution(self):
        """Test validation failure for wrong difficulty distribution"""
        pack = self.create_valid_pack()
        # Change one Easy to Medium
        pack[0].difficulty_band = "Medium"
        
        result = validate_pack(pack, pack, set(), set())
        
        assert result["valid"] == False
        assert result["constraints"]["difficulty_easy"]["passed"] == False
        assert result["constraints"]["difficulty_medium"]["passed"] == False
        
    def test_insufficient_pyq_scores(self):
        """Test validation failure for insufficient PYQ scores"""
        pack = self.create_valid_pack()
        # Set all PYQ scores to 0.5 (below minimum)
        for question in pack:
            question.pyq_frequency_score = 0.5
            
        result = validate_pack(pack, pack, set(), set())
        
        assert result["valid"] == False
        assert result["constraints"]["pyq_score_1_0"]["passed"] == False
        assert result["constraints"]["pyq_score_1_5"]["passed"] == False
        
    def test_duplicate_questions(self):
        """Test validation failure for duplicate questions"""
        pack = self.create_valid_pack()
        # Duplicate the first question
        pack[1].question_id = pack[0].question_id
        
        result = validate_pack(pack, pack, set(), set())
        
        assert result["valid"] == False
        assert result["constraints"]["no_duplicates"]["passed"] == False

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])