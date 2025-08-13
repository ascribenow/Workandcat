"""
LLM-Powered Conceptual Frequency Analyzer
Analyzes mathematical concepts and patterns using LLM intelligence
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta
from database import Question, PYQQuestion, PYQPaper, AsyncSession

logger = logging.getLogger(__name__)

class ConceptualFrequencyAnalyzer:
    """
    LLM-powered analyzer that understands mathematical concepts beyond text matching
    """
    
    def __init__(self, llm_pipeline):
        self.llm_pipeline = llm_pipeline
        self.concept_cache = {}  # Cache for analyzed patterns
        
    async def calculate_conceptual_frequency(
        self, 
        db: AsyncSession, 
        question: Question, 
        years_window: int = 10
    ) -> Dict[str, Any]:
        """
        Calculate conceptual frequency using LLM pattern recognition
        """
        try:
            logger.info(f"Starting conceptual frequency analysis for question {question.id}")
            
            # Step 1: Extract question pattern using LLM
            question_pattern = await self.analyze_question_pattern(question)
            
            # Step 2: Find conceptually similar PYQ questions
            similar_pyq_questions = await self.find_conceptual_matches(
                db, question_pattern, years_window
            )
            
            # Step 3: Calculate conceptual similarity scores
            conceptual_score = await self.calculate_conceptual_score(
                question_pattern, similar_pyq_questions
            )
            
            # Step 4: Update question with results
            await self.update_question_with_analysis(
                db, question, question_pattern, similar_pyq_questions, conceptual_score
            )
            
            return {
                'status': 'completed',
                'question_id': str(question.id),
                'conceptual_matches': len(similar_pyq_questions),
                'pattern_keywords': question_pattern.get('keywords', []),
                'solution_approach': question_pattern.get('solution_approach', ''),
                'conceptual_score': conceptual_score,
                'frequency_category': self.determine_frequency_category(conceptual_score),
                'analysis_method': 'llm_conceptual_pattern'
            }
            
        except Exception as e:
            logger.error(f"Error in conceptual frequency analysis: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question_id': str(question.id)
            }
    
    async def analyze_question_pattern(self, question: Question) -> Dict[str, Any]:
        """
        Use LLM to extract mathematical concepts and patterns from question
        """
        try:
            # Check cache first
            cache_key = f"pattern_{hash(question.stem)}"
            if cache_key in self.concept_cache:
                return self.concept_cache[cache_key]
            
            prompt = f"""
            Analyze this CAT quantitative aptitude question and extract its mathematical pattern:
            
            Question: {question.stem}
            
            Please provide:
            1. Key mathematical concepts involved (3-5 keywords)
            2. Solution approach/method required
            3. Difficulty indicators
            4. Core mathematical operations
            5. Similar concept variations
            
            Format your response as JSON with keys: keywords, solution_approach, difficulty_indicators, operations, variations
            """
            
            try:
                # Use LLM to analyze pattern
                llm_response = await self.llm_pipeline.generate_response(
                    prompt, 
                    model="gpt-4o",
                    max_tokens=500
                )
                
                # Parse LLM response
                import json
                try:
                    pattern_data = json.loads(llm_response)
                except json.JSONDecodeError:
                    # Fallback parsing
                    pattern_data = self.fallback_pattern_extraction(question)
                
                # Cache the result
                self.concept_cache[cache_key] = pattern_data
                
                return pattern_data
                
            except Exception as llm_error:
                logger.warning(f"LLM pattern analysis failed: {llm_error}, using fallback")
                return self.fallback_pattern_extraction(question)
                
        except Exception as e:
            logger.error(f"Error analyzing question pattern: {e}")
            return self.fallback_pattern_extraction(question)
    
    def fallback_pattern_extraction(self, question: Question) -> Dict[str, Any]:
        """
        Fallback pattern extraction when LLM is unavailable
        """
        # Basic keyword extraction based on question content
        keywords = []
        
        # Mathematical concept keywords
        concept_keywords = {
            'percentage': ['percent', '%', 'percentage'],
            'time_speed_distance': ['speed', 'distance', 'time', 'kmph', 'mph'],
            'profit_loss': ['profit', 'loss', 'cost', 'selling', 'cp', 'sp'],
            'interest': ['interest', 'principal', 'rate', 'compound', 'simple'],
            'ratio_proportion': ['ratio', 'proportion', 'varies', ':'],
            'algebra': ['equation', 'solve', 'x', 'variable'],
            'geometry': ['area', 'volume', 'triangle', 'circle', 'square'],
            'probability': ['probability', 'chance', 'random'],
            'statistics': ['average', 'mean', 'median', 'mode']
        }
        
        question_text = question.stem.lower()
        
        for concept, words in concept_keywords.items():
            if any(word in question_text for word in words):
                keywords.append(concept)
        
        return {
            'keywords': keywords[:5],  # Top 5 keywords
            'solution_approach': question.subcategory or 'general_approach',
            'difficulty_indicators': ['medium'],  # Default
            'operations': ['calculation'],
            'variations': []
        }
    
    async def find_conceptual_matches(
        self, 
        db: AsyncSession, 
        question_pattern: Dict[str, Any], 
        years_window: int
    ) -> List[PYQQuestion]:
        """
        Find PYQ questions with similar mathematical concepts
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=years_window * 365)
            
            # Get PYQ questions from the relevance window
            result = await db.execute(
                select(PYQQuestion)
                .join(PYQPaper, PYQQuestion.paper_id == PYQPaper.id)
                .where(
                    and_(
                        PYQPaper.exam_date >= cutoff_date,
                        PYQQuestion.is_active == True
                    )
                )
                .limit(500)  # Reasonable limit for analysis
            )
            
            pyq_questions = result.scalars().all()
            
            # Find conceptually similar questions
            similar_questions = []
            pattern_keywords = set(question_pattern.get('keywords', []))
            
            for pyq_q in pyq_questions:
                similarity_score = await self.calculate_similarity_score(
                    question_pattern, pyq_q
                )
                
                if similarity_score > 0.3:  # Similarity threshold
                    similar_questions.append(pyq_q)
            
            logger.info(f"Found {len(similar_questions)} conceptually similar PYQ questions")
            return similar_questions
            
        except Exception as e:
            logger.error(f"Error finding conceptual matches: {e}")
            return []
    
    async def calculate_similarity_score(
        self, 
        question_pattern: Dict[str, Any], 
        pyq_question: PYQQuestion
    ) -> float:
        """
        Calculate semantic similarity between question pattern and PYQ question
        """
        try:
            # Simple similarity based on subcategory and keywords
            score = 0.0
            
            # Subcategory match (40% weight)
            if (question_pattern.get('solution_approach', '').lower() == 
                pyq_question.subcategory.lower() if pyq_question.subcategory else False):
                score += 0.4
            
            # Keyword overlap (40% weight)
            pattern_keywords = set(question_pattern.get('keywords', []))
            pyq_text = pyq_question.question_text.lower() if pyq_question.question_text else ""
            
            keyword_matches = sum(1 for keyword in pattern_keywords 
                                 if keyword.lower() in pyq_text)
            
            if pattern_keywords:
                keyword_score = keyword_matches / len(pattern_keywords)
                score += 0.4 * keyword_score
            
            # Difficulty similarity (20% weight)
            if (pyq_question.difficulty_level and 
                pyq_question.difficulty_level.lower() in 
                question_pattern.get('difficulty_indicators', [])):
                score += 0.2
            
            return min(1.0, score)
            
        except Exception as e:
            logger.warning(f"Error calculating similarity score: {e}")
            return 0.0
    
    async def calculate_conceptual_score(
        self, 
        question_pattern: Dict[str, Any], 
        similar_pyq_questions: List[PYQQuestion]
    ) -> float:
        """
        Calculate final conceptual frequency score
        """
        try:
            if not similar_pyq_questions:
                return 0.0
            
            # Base score from count of similar questions
            base_score = min(100.0, len(similar_pyq_questions) * 5)
            
            # Quality adjustment based on similarity scores
            total_similarity = 0.0
            for pyq_q in similar_pyq_questions:
                similarity = await self.calculate_similarity_score(question_pattern, pyq_q)
                total_similarity += similarity
            
            if similar_pyq_questions:
                avg_similarity = total_similarity / len(similar_pyq_questions)
                quality_multiplier = 0.5 + (0.5 * avg_similarity)  # 0.5 to 1.0
            else:
                quality_multiplier = 0.5
            
            final_score = base_score * quality_multiplier
            
            return min(100.0, final_score)
            
        except Exception as e:
            logger.error(f"Error calculating conceptual score: {e}")
            return 0.0
    
    def determine_frequency_category(self, score: float) -> str:
        """
        Determine frequency category based on conceptual score
        """
        if score >= 70:
            return "High"
        elif score >= 40:
            return "Medium"
        elif score > 0:
            return "Low"
        else:
            return "None"
    
    async def update_question_with_analysis(
        self,
        db: AsyncSession,
        question: Question,
        question_pattern: Dict[str, Any],
        similar_pyq_questions: List[PYQQuestion],
        conceptual_score: float
    ):
        """
        Update question with conceptual frequency analysis results
        """
        try:
            # Update question fields
            question.pyq_conceptual_matches = len(similar_pyq_questions)
            question.frequency_score = conceptual_score
            question.frequency_band = self.determine_frequency_category(conceptual_score)
            question.frequency_analysis_method = 'llm_conceptual_pattern'
            question.frequency_last_updated = datetime.utcnow()
            
            # Store pattern analysis results
            if hasattr(question, 'pattern_keywords'):
                question.pattern_keywords = question_pattern.get('keywords', [])
            if hasattr(question, 'pattern_solution_approach'):
                question.pattern_solution_approach = question_pattern.get('solution_approach', '')
            if hasattr(question, 'top_matching_concepts'):
                question.top_matching_concepts = question_pattern.get('keywords', [])[:3]
            
            await db.commit()
            logger.info(f"Updated question {question.id} with conceptual analysis")
            
        except Exception as e:
            logger.error(f"Error updating question with analysis: {e}")
            await db.rollback()
    
    async def analyze_multiple_questions(
        self, 
        db: AsyncSession, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze multiple questions for batch processing
        """
        try:
            # Get questions that need analysis
            result = await db.execute(
                select(Question)
                .where(
                    and_(
                        Question.is_active == True,
                        Question.frequency_analysis_method != 'llm_conceptual_pattern'
                    )
                )
                .limit(limit)
            )
            
            questions = result.scalars().all()
            
            analyzed_count = 0
            error_count = 0
            
            for question in questions:
                try:
                    analysis_result = await self.calculate_conceptual_frequency(
                        db, question, years_window=10
                    )
                    
                    if analysis_result.get('status') == 'completed':
                        analyzed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error analyzing question {question.id}: {e}")
                    error_count += 1
            
            return {
                'status': 'completed',
                'analyzed_questions': analyzed_count,
                'errors': error_count,
                'total_processed': analyzed_count + error_count
            }
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }