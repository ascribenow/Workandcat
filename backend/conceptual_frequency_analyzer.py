#!/usr/bin/env python3
"""
Conceptual Frequency Analyzer - LLM-Powered Pattern Recognition
Analyzes conceptual similarity between question bank and PYQ patterns
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import Question, PYQQuestion, Topic

logger = logging.getLogger(__name__)

@dataclass
class QuestionPattern:
    """Structured representation of question pattern"""
    category: str
    subcategory: str
    type_of_question: str
    concept_keywords: List[str]
    solution_approach: str
    difficulty_indicators: List[str]
    mathematical_concepts: List[str]
    
@dataclass
class ConceptualMatch:
    """Represents a conceptual match between question bank and PYQ"""
    pyq_question_id: str
    similarity_score: float
    matching_concepts: List[str]
    pattern_type: str
    reasoning: str

class ConceptualFrequencyAnalyzer:
    """
    LLM-powered analyzer for conceptual frequency patterns
    """
    
    def __init__(self, llm_pipeline):
        self.llm_pipeline = llm_pipeline
        self.similarity_threshold = 0.75  # Minimum similarity for pattern match
        self.concept_cache = {}  # Cache for analyzed patterns
        
    async def analyze_question_pattern(self, question: Question) -> QuestionPattern:
        """
        Use LLM to extract conceptual pattern from a question
        """
        try:
            # Create analysis prompt for pattern extraction
            analysis_prompt = f"""
            Analyze this CAT quantitative aptitude question and extract its conceptual pattern:
            
            QUESTION: {question.stem}
            CATEGORY: {question.subcategory}
            TYPE: {question.type_of_question or 'Unknown'}
            
            Extract the following pattern elements:
            1. Core mathematical concepts involved
            2. Solution approach/method required
            3. Difficulty indicators (complexity markers)
            4. Key concept keywords
            5. Problem-solving pattern type
            
            Respond in JSON format:
            {{
                "concept_keywords": ["keyword1", "keyword2", ...],
                "solution_approach": "main solution method",
                "difficulty_indicators": ["indicator1", "indicator2", ...],
                "mathematical_concepts": ["concept1", "concept2", ...],
                "pattern_type": "specific pattern classification"
            }}
            """
            
            # Get LLM analysis
            response = await self.llm_pipeline.analyze_text(analysis_prompt)
            
            try:
                pattern_data = json.loads(response)
                
                return QuestionPattern(
                    category=question.subcategory or "Unknown",
                    subcategory=question.subcategory or "Unknown", 
                    type_of_question=question.type_of_question or "General",
                    concept_keywords=pattern_data.get("concept_keywords", []),
                    solution_approach=pattern_data.get("solution_approach", ""),
                    difficulty_indicators=pattern_data.get("difficulty_indicators", []),
                    mathematical_concepts=pattern_data.get("mathematical_concepts", [])
                )
                
            except json.JSONDecodeError:
                # Fallback pattern if JSON parsing fails
                logger.warning(f"Failed to parse LLM response for question {question.id}")
                return self._create_fallback_pattern(question)
                
        except Exception as e:
            logger.error(f"Error analyzing question pattern: {e}")
            return self._create_fallback_pattern(question)
    
    def _create_fallback_pattern(self, question: Question) -> QuestionPattern:
        """Create a basic pattern when LLM analysis fails"""
        return QuestionPattern(
            category=question.subcategory or "Unknown",
            subcategory=question.subcategory or "Unknown",
            type_of_question=question.type_of_question or "General",
            concept_keywords=[],
            solution_approach="Unknown",
            difficulty_indicators=[],
            mathematical_concepts=[]
        )
    
    async def find_conceptual_matches(self, 
                                    question_pattern: QuestionPattern, 
                                    pyq_questions: List[Dict],
                                    max_matches: int = 100) -> List[ConceptualMatch]:
        """
        Find PYQ questions that are conceptually similar to the given pattern
        """
        try:
            matches = []
            
            # Batch analyze PYQ questions for efficiency
            for i in range(0, len(pyq_questions), 10):  # Process in batches of 10
                batch = pyq_questions[i:i+10]
                batch_matches = await self._analyze_pyq_batch(question_pattern, batch)
                matches.extend(batch_matches)
                
                # Stop if we have enough high-quality matches
                high_quality_matches = [m for m in matches if m.similarity_score >= self.similarity_threshold]
                if len(high_quality_matches) >= max_matches:
                    break
            
            # Sort by similarity score and return top matches
            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            return matches[:max_matches]
            
        except Exception as e:
            logger.error(f"Error finding conceptual matches: {e}")
            return []
    
    async def _analyze_pyq_batch(self, 
                                question_pattern: QuestionPattern, 
                                pyq_batch: List[Dict]) -> List[ConceptualMatch]:
        """
        Analyze a batch of PYQ questions for conceptual similarity
        """
        try:
            # Create batch analysis prompt
            pyq_summaries = []
            for i, pyq in enumerate(pyq_batch):
                pyq_summaries.append(f"{i}: {pyq['stem'][:200]}... (Category: {pyq['subcategory']})")
            
            analysis_prompt = f"""
            REFERENCE PATTERN:
            - Concepts: {', '.join(question_pattern.concept_keywords)}
            - Solution Method: {question_pattern.solution_approach}
            - Mathematical Concepts: {', '.join(question_pattern.mathematical_concepts)}
            - Category: {question_pattern.subcategory}
            
            ANALYZE THESE PYQ QUESTIONS FOR CONCEPTUAL SIMILARITY:
            {chr(10).join(pyq_summaries)}
            
            For each PYQ question (0-{len(pyq_batch)-1}), determine:
            1. Conceptual similarity score (0.0-1.0)
            2. Which concepts match
            3. Pattern type similarity
            4. Brief reasoning
            
            Focus on mathematical concepts, solution approaches, and problem-solving patterns, NOT exact wording.
            
            Respond in JSON format:
            {{
                "matches": [
                    {{
                        "pyq_index": 0,
                        "similarity_score": 0.85,
                        "matching_concepts": ["concept1", "concept2"],
                        "pattern_type": "similar pattern description",
                        "reasoning": "why these are conceptually similar"
                    }}, ...
                ]
            }}
            """
            
            response = await self.llm_pipeline.analyze_text(analysis_prompt)
            
            try:
                analysis_result = json.loads(response)
                matches = []
                
                for match_data in analysis_result.get("matches", []):
                    pyq_index = match_data.get("pyq_index")
                    if pyq_index is not None and 0 <= pyq_index < len(pyq_batch):
                        pyq = pyq_batch[pyq_index]
                        
                        match = ConceptualMatch(
                            pyq_question_id=pyq["id"],
                            similarity_score=match_data.get("similarity_score", 0.0),
                            matching_concepts=match_data.get("matching_concepts", []),
                            pattern_type=match_data.get("pattern_type", ""),
                            reasoning=match_data.get("reasoning", "")
                        )
                        matches.append(match)
                
                return matches
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse batch analysis response")
                return []
                
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            return []
    
    async def calculate_conceptual_frequency(self, 
                                           db: AsyncSession,
                                           question: Question,
                                           years_window: int = 10) -> Dict[str, Any]:
        """
        Calculate frequency score based on conceptual similarity to PYQ patterns
        """
        try:
            # Get PYQ questions from the last N years
            current_year = datetime.now().year
            window_start_year = current_year - years_window
            window_start = datetime(window_start_year, 1, 1)
            
            # Fetch PYQ questions within the window
            pyq_result = await db.execute(
                select(PYQQuestion).where(PYQQuestion.created_at >= window_start)
            )
            pyq_questions = pyq_result.scalars().all()
            
            if not pyq_questions:
                return {
                    "frequency_score": 0.0,
                    "conceptual_matches": 0,
                    "total_pyq_analyzed": 0,
                    "top_matching_concepts": [],
                    "analysis_method": "conceptual_similarity"
                }
            
            # Convert to dict format for analysis
            pyq_dict_list = []
            for pyq in pyq_questions:
                pyq_dict_list.append({
                    "id": str(pyq.id),
                    "stem": pyq.stem,
                    "subcategory": pyq.subcategory,
                    "type_of_question": pyq.type_of_question or "General",
                    "answer": pyq.answer
                })
            
            # Analyze the question pattern
            question_pattern = await self.analyze_question_pattern(question)
            
            # Find conceptual matches
            conceptual_matches = await self.find_conceptual_matches(
                question_pattern, 
                pyq_dict_list,
                max_matches=50
            )
            
            # Filter for high-quality matches
            significant_matches = [
                match for match in conceptual_matches 
                if match.similarity_score >= self.similarity_threshold
            ]
            
            # Calculate frequency score
            total_pyq_count = len(pyq_dict_list)
            conceptual_frequency = len(significant_matches) / total_pyq_count if total_pyq_count > 0 else 0.0
            
            # Analyze matching concepts
            all_matching_concepts = []
            for match in significant_matches:
                all_matching_concepts.extend(match.matching_concepts)
            
            # Get top matching concepts
            concept_counts = {}
            for concept in all_matching_concepts:
                concept_counts[concept] = concept_counts.get(concept, 0) + 1
            
            top_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                "frequency_score": min(conceptual_frequency, 1.0),  # Cap at 1.0
                "conceptual_matches": len(significant_matches),
                "total_pyq_analyzed": total_pyq_count,
                "top_matching_concepts": [concept for concept, count in top_concepts],
                "analysis_method": "conceptual_similarity",
                "pattern_keywords": question_pattern.concept_keywords,
                "solution_approach": question_pattern.solution_approach
            }
            
        except Exception as e:
            logger.error(f"Error calculating conceptual frequency for question {question.id}: {e}")
            return {
                "frequency_score": 0.0,
                "conceptual_matches": 0,
                "total_pyq_analyzed": 0,
                "top_matching_concepts": [],
                "analysis_method": "error_fallback"
            }
    
    async def batch_calculate_frequencies(self, 
                                        db: AsyncSession,
                                        questions: List[Question],
                                        years_window: int = 10) -> Dict[str, Dict]:
        """
        Calculate conceptual frequencies for multiple questions efficiently
        """
        logger.info(f"Starting batch conceptual frequency calculation for {len(questions)} questions")
        
        results = {}
        
        # Process questions in smaller batches to avoid overwhelming the LLM
        batch_size = 5  # Process 5 questions at a time
        
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i+batch_size]
            batch_results = await asyncio.gather(
                *[self.calculate_conceptual_frequency(db, question, years_window) for question in batch],
                return_exceptions=True
            )
            
            # Process batch results
            for j, result in enumerate(batch_results):
                question = batch[j]
                if isinstance(result, Exception):
                    logger.error(f"Error processing question {question.id}: {result}")
                    results[str(question.id)] = {
                        "frequency_score": 0.0,
                        "analysis_method": "error",
                        "error": str(result)
                    }
                else:
                    results[str(question.id)] = result
            
            # Log progress
            processed = min(i + batch_size, len(questions))
            logger.info(f"Processed {processed}/{len(questions)} questions for conceptual frequency")
        
        logger.info(f"Completed batch conceptual frequency calculation")
        return results