#!/usr/bin/env python3
"""
Dry-run testing script for adaptive logic
Tests both cold start and adaptive modes with real pseudo data
"""

import sys
import asyncio
import logging
from typing import Dict, List, Any

sys.path.append('.')
from database import SessionLocal, Question
from sqlalchemy import text
from services.deterministic_kernels import (
    stable_semantic_id, weights_from_dominance, compute_weighted_counts,
    finalize_readiness, coverage_debt_by_sessions, validate_pack,
    AttemptEvent, QuestionCandidate, ReadinessLevel
)
from services.candidate_provider import candidate_provider
from services.pipeline import should_cold_start, get_user_session_history

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveDryRun:
    """Dry-run testing for adaptive logic components"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_test_users(self) -> List[Dict[str, Any]]:
        """Get test users for dry-run testing"""
        users = self.db.execute(text("""
            SELECT u.id, u.email,
                   COUNT(s.session_id) as session_count,
                   CASE 
                       WHEN u.email LIKE 'new_%' THEN 'new'
                       WHEN u.email LIKE 'early_%' THEN 'early'
                       WHEN u.email LIKE 'experienced_%' THEN 'experienced'
                   END as cohort
            FROM users u
            LEFT JOIN sessions s ON u.id = s.user_id AND s.status = 'completed'
            WHERE u.email LIKE '%_user_%@test.com'
            GROUP BY u.id, u.email
            ORDER BY cohort, u.email
            LIMIT 6
        """)).fetchall()
        
        return [
            {
                'user_id': user.id,
                'email': user.email,
                'session_count': user.session_count,
                'cohort': user.cohort
            }
            for user in users
        ]
    
    def load_user_attempts(self, user_id: str) -> List[AttemptEvent]:
        """Load user's attempt events as structured data"""
        attempts = self.db.execute(text("""
            SELECT question_id, was_correct, skipped, response_time_ms,
                   sess_seq_at_serve, difficulty_band, subcategory, 
                   type_of_question, core_concepts, pyq_frequency_score
            FROM attempt_events 
            WHERE user_id = :user_id
            ORDER BY sess_seq_at_serve, created_at
        """), {'user_id': user_id}).fetchall()
        
        attempt_events = []
        for attempt in attempts:
            try:
                # Parse core concepts
                if isinstance(attempt.core_concepts, list):
                    concepts = attempt.core_concepts
                elif isinstance(attempt.core_concepts, str):
                    import json
                    concepts = json.loads(attempt.core_concepts)
                else:
                    concepts = []
                
                event = AttemptEvent(
                    question_id=attempt.question_id,
                    was_correct=attempt.was_correct,
                    skipped=attempt.skipped,
                    response_time_ms=attempt.response_time_ms,
                    sess_seq_at_serve=attempt.sess_seq_at_serve,
                    difficulty_band=attempt.difficulty_band,
                    subcategory=attempt.subcategory,
                    type_of_question=attempt.type_of_question,
                    core_concepts=concepts,
                    pyq_frequency_score=float(attempt.pyq_frequency_score) if attempt.pyq_frequency_score else 0.5
                )
                attempt_events.append(event)
                
            except Exception as e:
                logger.warning(f"Error parsing attempt: {e}")
                continue
        
        return attempt_events
    
    def test_cold_start_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Test cold start logic for a new user"""
        user_id = user['user_id']
        email = user['email']
        
        logger.info(f"🧪 Testing COLD START for {email}")
        
        result = {
            'user_email': email,
            'user_id': user_id,
            'test_type': 'cold_start',
            'success': False,
            'errors': [],
            'details': {}
        }
        
        try:
            # Step 1: Verify cold start detection
            is_cold_start = should_cold_start(user_id)
            if not is_cold_start:
                result['errors'].append(f"Cold start detection failed: returned {is_cold_start}")
                return result
            
            result['details']['cold_start_detected'] = True
            
            # Step 2: Build cold start candidate pool
            candidates, metadata = candidate_provider.build_coldstart_pool(user_id)
            
            result['details']['candidate_pool'] = {
                'size': len(candidates),
                'strategy': metadata.get('selection_strategy'),
                'distinct_pairs': metadata.get('distinct_pairs'),
                'pool_expanded': metadata.get('pool_expanded', False)
            }
            
            if not candidates:
                result['errors'].append("No candidates returned from cold start pool")
                return result
            
            # Step 3: Simple question selection (12 questions with 3/6/3 distribution)
            selected_pack = self._select_cold_start_pack(candidates)
            
            if not selected_pack:
                result['errors'].append("Failed to select 12-question pack")
                return result
            
            result['details']['selected_pack'] = {
                'size': len(selected_pack),
                'difficulty_distribution': self._count_difficulty_distribution(selected_pack)
            }
            
            # Step 4: Validate pack
            validation_result = validate_pack(
                selected_pack, 
                candidates,
                candidate_provider.valid_pairs,
                candidate_provider.known_concepts
            )
            
            result['details']['validation'] = {
                'valid': validation_result['valid'],
                'errors': validation_result['errors'],
                'constraints_passed': validation_result['summary']['passed_constraints'],
                'total_constraints': validation_result['summary']['total_constraints']
            }
            
            if validation_result['valid']:
                result['success'] = True
                logger.info(f"   ✅ Cold start test PASSED for {email}")
            else:
                result['errors'].extend(validation_result['errors'])
                logger.error(f"   ❌ Cold start test FAILED for {email}: {validation_result['errors']}")
            
        except Exception as e:
            logger.error(f"   ❌ Cold start test ERROR for {email}: {e}")
            result['errors'].append(f"Exception: {e}")
        
        return result
    
    def test_adaptive_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Test adaptive logic for an experienced user"""
        user_id = user['user_id']
        email = user['email']
        session_count = user['session_count']
        
        logger.info(f"🧪 Testing ADAPTIVE for {email} ({session_count} sessions)")
        
        result = {
            'user_email': email,
            'user_id': user_id,
            'test_type': 'adaptive',
            'success': False,
            'errors': [],
            'details': {}
        }
        
        try:
            # Step 1: Verify NOT cold start
            is_cold_start = should_cold_start(user_id)
            if is_cold_start:
                result['errors'].append(f"Expected adaptive mode, but cold start detected")
                return result
            
            result['details']['adaptive_mode_detected'] = True
            
            # Step 2: Load user's attempt history
            attempt_events = self.load_user_attempts(user_id)
            
            if not attempt_events:
                result['errors'].append("No attempt history found")
                return result
            
            result['details']['attempt_history'] = {
                'total_attempts': len(attempt_events),
                'sessions_span': len(set(e.sess_seq_at_serve for e in attempt_events))
            }
            
            # Step 3: Run deterministic kernels
            kernels_result = self._run_deterministic_kernels(attempt_events)
            
            if not kernels_result['success']:
                result['errors'].extend(kernels_result['errors'])
                return result
            
            result['details']['kernels'] = kernels_result['details']
            
            # Step 4: Build adaptive candidate pool
            readiness_levels = kernels_result['readiness_levels']
            coverage_debt = kernels_result['coverage_debt']
            
            candidates, metadata = candidate_provider.build_candidate_pool(
                user_id, readiness_levels, coverage_debt
            )
            
            result['details']['candidate_pool'] = {
                'size': len(candidates),
                'strategy': metadata.get('selection_strategy'),
                'pool_expanded': metadata.get('pool_expanded', False)
            }
            
            if not candidates:
                result['errors'].append("No candidates returned from adaptive pool")
                return result
            
            # Step 5: Select adaptive pack (simplified - would use LLM Planner in full implementation)
            selected_pack = self._select_adaptive_pack(candidates, readiness_levels, coverage_debt)
            
            if not selected_pack:
                result['errors'].append("Failed to select adaptive pack")
                return result
            
            result['details']['selected_pack'] = {
                'size': len(selected_pack),
                'difficulty_distribution': self._count_difficulty_distribution(selected_pack)
            }
            
            # Step 6: Validate pack
            validation_result = validate_pack(
                selected_pack,
                candidates,
                candidate_provider.valid_pairs,
                candidate_provider.known_concepts
            )
            
            result['details']['validation'] = {
                'valid': validation_result['valid'],
                'errors': validation_result['errors'],
                'constraints_passed': validation_result['summary']['passed_constraints'],
                'total_constraints': validation_result['summary']['total_constraints']
            }
            
            if validation_result['valid']:
                result['success'] = True
                logger.info(f"   ✅ Adaptive test PASSED for {email}")
            else:
                result['errors'].extend(validation_result['errors'])
                logger.error(f"   ❌ Adaptive test FAILED for {email}: {validation_result['errors']}")
            
        except Exception as e:
            logger.error(f"   ❌ Adaptive test ERROR for {email}: {e}")
            result['errors'].append(f"Exception: {e}")
        
        return result
    
    def _run_deterministic_kernels(self, attempt_events: List[AttemptEvent]) -> Dict[str, Any]:
        """Run all deterministic kernels on attempt history"""
        try:
            # Step 1: Create concept alias map (simplified - normally from LLM)
            concept_alias_map = {}
            semantic_id_map = {}
            
            for event in attempt_events:
                for concept in event.core_concepts:
                    if concept not in semantic_id_map:
                        semantic_id = stable_semantic_id(concept)
                        semantic_id_map[concept] = semantic_id
                        concept_alias_map[semantic_id] = concept
            
            # Step 2: Create mock dominance weights (normally from LLM)
            dominance_labels = {}
            for semantic_id in concept_alias_map.keys():
                # Mock dominance based on concept frequency
                concept_frequency = sum(
                    1 for event in attempt_events 
                    for concept in event.core_concepts
                    if semantic_id_map.get(concept) == semantic_id
                )
                
                if concept_frequency >= 3:
                    dominance_labels[semantic_id] = "High"
                elif concept_frequency >= 2:
                    dominance_labels[semantic_id] = "Medium"
                else:
                    dominance_labels[semantic_id] = "Low"
            
            # Step 3: Convert dominance to weights
            concept_weights = weights_from_dominance(dominance_labels)
            
            # Step 4: Compute weighted counts
            weighted_counts = compute_weighted_counts(attempt_events, concept_weights, semantic_id_map)
            
            # Step 5: Finalize readiness
            readiness_map = finalize_readiness(weighted_counts)
            
            # Convert readiness to string format for candidate provider
            readiness_levels = {
                semantic_id: level.value for semantic_id, level in readiness_map.items()
            }
            
            # Step 6: Coverage debt
            coverage_debt = coverage_debt_by_sessions(attempt_events)
            
            return {
                'success': True,
                'readiness_levels': readiness_levels,
                'coverage_debt': coverage_debt,
                'details': {
                    'concepts_mapped': len(semantic_id_map),
                    'weighted_counts': len(weighted_counts),
                    'readiness_levels': {level.value: sum(1 for l in readiness_map.values() if l == level) 
                                       for level in ReadinessLevel},
                    'coverage_pairs': len(coverage_debt)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Kernels error: {e}"],
                'readiness_levels': {},
                'coverage_debt': {}
            }
    
    def _select_cold_start_pack(self, candidates: List[QuestionCandidate]) -> List[QuestionCandidate]:
        """Simple cold start pack selection (diversity-first)"""
        from collections import defaultdict
        import random
        
        # Group by difficulty
        by_difficulty = defaultdict(list)
        for candidate in candidates:
            by_difficulty[candidate.difficulty_band].append(candidate)
        
        pack = []
        target_distribution = {"Easy": 3, "Medium": 6, "Hard": 3}
        
        for band, target_count in target_distribution.items():
            available = by_difficulty[band]
            if len(available) >= target_count:
                selected = random.sample(available, target_count)
                pack.extend(selected)
        
        return pack
    
    def _select_adaptive_pack(self, 
                            candidates: List[QuestionCandidate],
                            readiness_levels: Dict[str, str],
                            coverage_debt: Dict[str, float]) -> List[QuestionCandidate]:
        """Simple adaptive pack selection with PYQ constraints"""
        from collections import defaultdict
        import random
        
        # First, ensure PYQ constraints can be met
        pyq_1_0_candidates = [c for c in candidates if c.pyq_frequency_score >= 1.0]
        pyq_1_5_candidates = [c for c in candidates if c.pyq_frequency_score >= 1.5]
        
        if len(pyq_1_0_candidates) < 2 or len(pyq_1_5_candidates) < 2:
            logger.warning(f"Insufficient PYQ candidates: {len(pyq_1_0_candidates)} ≥1.0, {len(pyq_1_5_candidates)} ≥1.5")
            return []
        
        # Group by difficulty
        by_difficulty = defaultdict(list)
        for candidate in candidates:
            by_difficulty[candidate.difficulty_band].append(candidate)
        
        pack = []
        target_distribution = {"Easy": 3, "Medium": 6, "Hard": 3}
        
        # Pre-select PYQ questions to ensure constraints
        selected_pyq_1_5 = random.sample(pyq_1_5_candidates, min(2, len(pyq_1_5_candidates)))
        selected_pyq_1_0 = random.sample(
            [c for c in pyq_1_0_candidates if c not in selected_pyq_1_5], 
            min(2, len([c for c in pyq_1_0_candidates if c not in selected_pyq_1_5]))
        )
        
        reserved_questions = set(selected_pyq_1_5 + selected_pyq_1_0)
        
        # Distribute reserved questions by difficulty band
        reserved_by_band = defaultdict(list)
        for q in reserved_questions:
            reserved_by_band[q.difficulty_band].append(q)
        
        # Select remaining questions for each band
        for band, target_count in target_distribution.items():
            available = by_difficulty[band]
            reserved_count = len(reserved_by_band[band])
            remaining_needed = target_count - reserved_count
            
            if remaining_needed > 0:
                # Get unreserved candidates
                unreserved = [c for c in available if c not in reserved_questions]
                
                if len(unreserved) >= remaining_needed:
                    # Sort by adaptive criteria
                    def adaptive_score(candidate):
                        score = 0.0
                        score += coverage_debt.get(candidate.pair, 0.5)
                        for concept in candidate.core_concepts:
                            if readiness_levels.get(concept, "Moderate") == "Weak":
                                score += 1.0
                        return score
                    
                    unreserved.sort(key=adaptive_score, reverse=True)
                    selected_additional = unreserved[:remaining_needed]
                    
                    # Add reserved + additional for this band
                    pack.extend(reserved_by_band[band])
                    pack.extend(selected_additional)
                else:
                    # Not enough candidates for this band
                    pack.extend(reserved_by_band[band])
                    pack.extend(unreserved)
            else:
                # Only reserved questions for this band
                pack.extend(reserved_by_band[band][:target_count])
        
        return pack
    
    def _count_difficulty_distribution(self, pack: List[QuestionCandidate]) -> Dict[str, int]:
        """Count difficulty distribution in pack"""
        distribution = {"Easy": 0, "Medium": 0, "Hard": 0}
        for question in pack:
            if question.difficulty_band in distribution:
                distribution[question.difficulty_band] += 1
        return distribution

async def main():
    """Main dry-run testing function"""
    print("🚀 STARTING ADAPTIVE LOGIC DRY-RUN TESTING")
    print("=" * 60)
    
    dry_run = AdaptiveDryRun()
    
    try:
        # Get test users
        test_users = dry_run.get_test_users()
        print(f"📊 Found {len(test_users)} test users")
        
        results = []
        
        # Test each user
        for user in test_users:
            cohort = user['cohort']
            
            if cohort == 'new':
                # Test cold start logic
                result = dry_run.test_cold_start_user(user)
            else:
                # Test adaptive logic
                result = dry_run.test_adaptive_user(user)
            
            results.append(result)
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 DRY-RUN TESTING SUMMARY")
        print("=" * 60)
        
        cold_start_tests = [r for r in results if r['test_type'] == 'cold_start']
        adaptive_tests = [r for r in results if r['test_type'] == 'adaptive']
        
        cold_start_passed = sum(1 for r in cold_start_tests if r['success'])
        adaptive_passed = sum(1 for r in adaptive_tests if r['success'])
        
        print(f"🔥 COLD START TESTS: {cold_start_passed}/{len(cold_start_tests)} passed")
        for result in cold_start_tests:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   {status} {result['user_email']}")
            if not result['success'] and result['errors']:
                for error in result['errors'][:2]:  # Show first 2 errors
                    print(f"      • {error}")
        
        print(f"\n🧠 ADAPTIVE TESTS: {adaptive_passed}/{len(adaptive_tests)} passed")
        for result in adaptive_tests:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   {status} {result['user_email']}")
            if not result['success'] and result['errors']:
                for error in result['errors'][:2]:  # Show first 2 errors
                    print(f"      • {error}")
        
        total_passed = cold_start_passed + adaptive_passed
        total_tests = len(results)
        
        print(f"\n🎯 OVERALL: {total_passed}/{total_tests} tests passed ({(total_passed/total_tests)*100:.1f}%)")
        
        if total_passed == total_tests:
            print("\n🎉 ✅ ALL TESTS PASSED! Deterministic kernels working correctly!")
        else:
            print(f"\n⚠️ {total_tests - total_passed} tests failed - review errors above")
        
    except Exception as e:
        print(f"❌ Dry-run testing failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if hasattr(dry_run, 'db'):
            dry_run.db.close()

if __name__ == "__main__":
    asyncio.run(main())