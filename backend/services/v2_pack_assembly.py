"""
V2 Pack Assembly Service - Fast heavy-field fetching

Assembles final pack from ordered IDs by fetching heavy fields (stem, options) 
in a single indexed query. NO multiple queries. NO N+1 problems.
"""

import logging
import json
from typing import List, Dict, Any
from database import SessionLocal, Question
from sqlalchemy import select
from util.v2_contract import V2Pack, V2PackItem, validate_pack_constraints

logger = logging.getLogger(__name__)

class V2PackAssemblyService:
    """
    V2 Pack Assembly - Single Query Heavy Field Fetch
    
    Takes ordered IDs and fetches all heavy fields in one query.
    Preserves order. Validates constraints. Ready for frontend.
    """
    
    def assemble_pack(self, ordered_ids: List[str]) -> Dict[str, Any]:
        """
        V2 Pack Assembly - Single query for all heavy fields
        
        Args:
            ordered_ids: 12 UUIDs in final optimized order
            
        Returns:
            {
                "pack": V2Pack,                    # Complete pack for frontend
                "constraint_validation": dict,     # Constraint check results
                "assembly_meta": dict             # Assembly metadata
            }
        """
        if len(ordered_ids) != 12:
            raise ValueError(f"V2 requires exactly 12 IDs for pack assembly, got {len(ordered_ids)}")
        
        logger.info(f"V2 Pack Assembly: Fetching heavy fields for {len(ordered_ids)} questions")
        
        # Single query to fetch all heavy fields by ID IN (...)
        questions_data = self._fetch_questions_by_ids(ordered_ids)
        
        # Preserve order from planner
        ordered_questions = []
        id_to_question = {q.id: q for q in questions_data}
        
        for question_id in ordered_ids:
            if question_id in id_to_question:
                ordered_questions.append(id_to_question[question_id])
            else:
                logger.error(f"V2 Pack Assembly: Question {question_id} not found in database")
                raise ValueError(f"Question {question_id} not found")
        
        # Convert to V2 pack items with full question data
        pack_items = []
        for question in ordered_questions:
            # Parse MCQ options from the mcq_options field
            options = self._parse_mcq_options(question.mcq_options)
            
            pack_items.append(V2PackItem(
                item_id=question.id,
                why=question.stem or "Question content unavailable",
                bucket=(question.difficulty_band or "Medium").lower(),
                pair=f"{question.subcategory or 'Unknown'}:{question.type_of_question or 'Unknown'}",
                pyq_frequency_score=float(question.pyq_frequency_score or 0.5),
                semantic_concepts=self._parse_concepts(question.core_concepts),
                # V2 FIX: Add MCQ options for frontend
                option_a=options.get('a', 'Option A'),
                option_b=options.get('b', 'Option B'), 
                option_c=options.get('c', 'Option C'),
                option_d=options.get('d', 'Option D'),
                answer=question.answer or "Not specified",  # Use ONLY answer field, never right_answer
                subcategory=question.subcategory or 'Unknown',
                difficulty_band=question.difficulty_band or 'Medium',
                # Solution feedback fields for educational content
                snap_read=question.snap_read or "",
                solution_approach=question.solution_approach or "",
                detailed_solution=question.detailed_solution or "",
                principle_to_remember=question.principle_to_remember or ""
            ))
        
        # Create V2 pack
        pack = V2Pack(
            items=pack_items,
            meta={
                "assembly_time_ms": 0,  # Would measure if needed
                "total_questions": len(pack_items),
                "strategy": "v2_single_query"
            }
        )
        
        # Validate constraints
        constraint_validation = validate_pack_constraints(pack)
        
        # Assembly metadata
        assembly_meta = {
            "questions_fetched": len(questions_data),
            "order_preserved": len(pack_items) == len(ordered_ids),
            "constraint_violations": len(constraint_validation.violated),
            "difficulty_distribution": self._analyze_difficulty(pack_items),
            "pyq_distribution": self._analyze_pyq(pack_items)
        }
        
        logger.info(f"V2 Pack Assembly: Complete - {len(pack_items)} items, "
                   f"{len(constraint_validation.violated)} violations")
        
        return {
            "pack": pack,
            "constraint_validation": constraint_validation,
            "assembly_meta": assembly_meta
        }
    
    def _fetch_questions_by_ids(self, question_ids: List[str]) -> List[Question]:
        """Single query to fetch all questions by ID"""
        db = SessionLocal()
        try:
            # Single indexed query - much faster than N queries
            query = select(Question).where(Question.id.in_(question_ids))
            questions = db.execute(query).scalars().all()
            return list(questions)
        finally:
            db.close()
    
    def _parse_mcq_options(self, mcq_options) -> Dict[str, str]:
        """Parse MCQ options from new standardized JSON array format"""
        if not mcq_options:
            return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
        
        try:
            # NEW FORMAT: JSON array with 4 clean values in A→B→C→D order
            if isinstance(mcq_options, str):
                options_array = json.loads(mcq_options)
            elif isinstance(mcq_options, list):
                options_array = mcq_options
            else:
                # Fallback to defaults
                return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
            
            # Ensure we have exactly 4 options
            if len(options_array) >= 4:
                return {
                    'a': str(options_array[0]).strip(),
                    'b': str(options_array[1]).strip(), 
                    'c': str(options_array[2]).strip(),
                    'd': str(options_array[3]).strip()
                }
            else:
                # Pad with defaults if not enough options
                padded = list(options_array) + ['Option A', 'Option B', 'Option C', 'Option D']
                return {
                    'a': str(padded[0]).strip(),
                    'b': str(padded[1]).strip(),
                    'c': str(padded[2]).strip(), 
                    'd': str(padded[3]).strip()
                }
                
        except (json.JSONDecodeError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing JSON array MCQ options: {e}")
            return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
    
    def _parse_concepts(self, core_concepts) -> List[str]:
        """Parse core concepts from various formats"""
        if isinstance(core_concepts, list):
            return core_concepts
        elif isinstance(core_concepts, str):
            try:
                return json.loads(core_concepts)
            except:
                return []
        else:
            return []
    
    def _analyze_difficulty(self, items: List[V2PackItem]) -> Dict[str, int]:
        """Analyze difficulty distribution for telemetry"""
        distribution = {"easy": 0, "medium": 0, "hard": 0}
        for item in items:
            bucket = item.bucket.lower()
            if bucket in distribution:
                distribution[bucket] += 1
        return distribution
    
    def _analyze_pyq(self, items: List[V2PackItem]) -> Dict[str, int]:
        """Analyze PYQ distribution for telemetry"""
        pyq_15 = sum(1 for item in items if item.pyq_frequency_score >= 1.5)
        pyq_10 = sum(1 for item in items if item.pyq_frequency_score >= 1.0)
        return {
            "pyq_15_count": pyq_15,
            "pyq_10_count": pyq_10,
            "pyq_requirements_met": pyq_15 >= 2 and pyq_10 >= 2
        }

# Global instance
v2_pack_assembly = V2PackAssemblyService()