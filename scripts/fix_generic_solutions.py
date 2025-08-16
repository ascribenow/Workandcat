"""
CRITICAL FIX: Re-enrich all questions with generic solutions using proper LLM
Fixes the bug where questions have hardcoded generic solutions instead of question-specific ones
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text, select
from database import get_async_compatible_db, Question
from llm_enrichment import LLMEnrichmentPipeline

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")

class SolutionFixer:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.llm_pipeline = None
        self.stats = {
            'total_processed': 0,
            'successfully_enriched': 0,
            'failed_enrichment': 0,
            'generic_solutions_found': 0
        }

    async def initialize_llm(self):
        """Initialize LLM enrichment pipeline"""
        if not EMERGENT_LLM_KEY:
            raise ValueError("EMERGENT_LLM_KEY not found in environment variables")
        
        self.llm_pipeline = LLMEnrichmentPipeline()
        print("✅ LLM enrichment pipeline initialized")

    async def find_generic_solutions(self, db_session):
        """Find all questions with generic hardcoded solutions"""
        
        # Query for questions with generic solutions
        generic_patterns = [
            "Mathematical approach to solve this problem",
            "Example answer based on the question pattern",
            "Detailed solution for:"
        ]
        
        questions_with_generic_solutions = []
        
        for pattern in generic_patterns:
            result = await db_session.execute(
                select(Question).where(
                    Question.solution_approach.like(f'%{pattern}%')
                )
            )
            questions = result.scalars().all()
            questions_with_generic_solutions.extend(questions)
        
        # Remove duplicates
        unique_questions = list({q.id: q for q in questions_with_generic_solutions}.values())
        
        self.stats['generic_solutions_found'] = len(unique_questions)
        print(f"Found {len(unique_questions)} questions with generic solutions")
        
        return unique_questions

    async def fix_question_solution(self, question, db_session):
        """Fix a single question's solution using LLM"""
        try:
            print(f"\n🔧 Fixing question: {question.stem[:60]}...")
            
            # Use LLM to generate proper solutions
            enrichment_result = await self.llm_pipeline.complete_auto_generation(
                stem=question.stem,
                hint_category=question.category,
                hint_subcategory=question.subcategory
            )
            
            # Update the question with proper solutions
            old_solution = question.solution_approach
            
            question.answer = enrichment_result.get('answer', question.answer)
            question.solution_approach = enrichment_result.get('solution_approach', question.solution_approach)
            question.detailed_solution = enrichment_result.get('detailed_solution', question.detailed_solution)
            question.difficulty_score = enrichment_result.get('difficulty_score', question.difficulty_score)
            question.difficulty_band = enrichment_result.get('difficulty_band', question.difficulty_band)
            question.learning_impact = enrichment_result.get('learning_impact', question.learning_impact)
            
            await db_session.commit()
            
            print(f"✅ Updated question {question.id}")
            print(f"   OLD: {old_solution[:50]}...")
            print(f"   NEW: {question.solution_approach[:50]}...")
            print(f"   Answer: {question.answer}")
            
            self.stats['successfully_enriched'] += 1
            return True
            
        except Exception as e:
            print(f"❌ Failed to fix question {question.id}: {e}")
            self.stats['failed_enrichment'] += 1
            return False

    async def run_solution_fix(self):
        """Main function to fix all generic solutions"""
        print("🚨 CRITICAL FIX: Re-enriching questions with generic solutions")
        print("=" * 70)
        print("Issue: Questions have hardcoded generic solutions")
        print("Fix: Replace with actual LLM-generated question-specific solutions")
        print("=" * 70)
        
        try:
            # Initialize LLM
            await self.initialize_llm()
            
            # Process questions
            async for db_session in get_async_compatible_db():
                # Find questions with generic solutions
                questions_to_fix = await self.find_generic_solutions(db_session)
                
                if not questions_to_fix:
                    print("✅ No questions found with generic solutions")
                    return
                
                print(f"\n🔧 Processing {len(questions_to_fix)} questions...")
                
                for i, question in enumerate(questions_to_fix, 1):
                    print(f"\n[{i}/{len(questions_to_fix)}] Processing...")
                    self.stats['total_processed'] += 1
                    
                    success = await self.fix_question_solution(question, db_session)
                    
                    if success:
                        # Add small delay to avoid overwhelming LLM API
                        await asyncio.sleep(1)
                
                break  # Only process first session
            
            # Print final statistics
            print("\n" + "=" * 70)
            print("🎉 SOLUTION FIX COMPLETE!")
            print("=" * 70)
            print(f"📊 Statistics:")
            print(f"   Generic solutions found: {self.stats['generic_solutions_found']}")
            print(f"   Questions processed: {self.stats['total_processed']}")
            print(f"   Successfully fixed: {self.stats['successfully_enriched']}")
            print(f"   Failed to fix: {self.stats['failed_enrichment']}")
            
            success_rate = (self.stats['successfully_enriched'] / max(1, self.stats['total_processed'])) * 100
            print(f"   Success rate: {success_rate:.1f}%")
            
            if self.stats['successfully_enriched'] > 0:
                print("\n🚀 SUCCESS: Students will now see proper question-specific solutions!")
                print("   No more generic 'Mathematical approach to solve this problem'")
                print("   Each question now has its own detailed solution")
            
        except Exception as e:
            print(f"❌ Critical error in solution fix: {e}")
            raise

async def main():
    """Main execution function"""
    fixer = SolutionFixer()
    await fixer.run_solution_fix()

if __name__ == "__main__":
    asyncio.run(main())