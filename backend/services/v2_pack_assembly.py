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
                difficulty_band=question.difficulty_band or 'Medium'
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
        """Parse MCQ options from database field - handles text format"""
        if not mcq_options:
            return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
        
        try:
            # First try JSON parsing (in case some are stored as JSON)
            if isinstance(mcq_options, dict):
                return {
                    'a': mcq_options.get('a', mcq_options.get('option_a', 'Option A')),
                    'b': mcq_options.get('b', mcq_options.get('option_b', 'Option B')),
                    'c': mcq_options.get('c', mcq_options.get('option_c', 'Option C')),
                    'd': mcq_options.get('d', mcq_options.get('option_d', 'Option D'))
                }
            elif isinstance(mcq_options, str):
                # Try JSON first
                try:
                    parsed = json.loads(mcq_options)
                    return self._parse_mcq_options(parsed)  # Recursive call with parsed dict
                except json.JSONDecodeError:
                    # Handle text format: "(A) 20%\n(B) 30%\n(C) 35.2%\n(D) 40%"
                    return self._parse_text_mcq_options(mcq_options)
            elif isinstance(mcq_options, list) and len(mcq_options) >= 4:
                return {
                    'a': mcq_options[0],
                    'b': mcq_options[1], 
                    'c': mcq_options[2],
                    'd': mcq_options[3]
                }
            else:
                return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
                
        except Exception as e:
            logger.warning(f"Error parsing MCQ options: {e}")
            return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
    
    def _parse_text_mcq_options(self, text_options: str) -> Dict[str, str]:
        """Parse text format MCQ options like '(A) 20%\\n(B) 30%\\n(C) 35.2%\\n(D) 40%'"""
        try:
            options = {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
            
            # Split by lines and parse each option
            lines = text_options.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Match patterns like "(A) 20%" or "A) 30%" or "A. text"
                if line.startswith('(A)') or line.startswith('A)') or line.startswith('A.'):
                    options['a'] = line.split(')', 1)[-1].split('.', 1)[-1].strip()
                elif line.startswith('(B)') or line.startswith('B)') or line.startswith('B.'):
                    options['b'] = line.split(')', 1)[-1].split('.', 1)[-1].strip()
                elif line.startswith('(C)') or line.startswith('C)') or line.startswith('C.'):
                    options['c'] = line.split(')', 1)[-1].split('.', 1)[-1].strip()
                elif line.startswith('(D)') or line.startswith('D)') or line.startswith('D.'):
                    options['d'] = line.split(')', 1)[-1].split('.', 1)[-1].strip()
            
            # Validate we got real options (not just defaults)
            real_options = [v for v in options.values() if not v.startswith('Option ')]
            if len(real_options) >= 2:  # At least 2 real options found
                return options
            else:
                logger.warning(f"Failed to parse sufficient real options from: {text_options[:100]}")
                return {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'}
                
        except Exception as e:
            logger.warning(f"Error parsing text MCQ options: {e}")
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