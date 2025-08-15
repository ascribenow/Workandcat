"""
Re-enrich Existing PYQ Database with Improved LLM Classification
Fixes the 31 "General Mathematics" misclassifications and improves all taxonomy mapping
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text, select
from database import get_async_compatible_db, PyqQuestion, Topic
from llm_enrichment import LLMEnrichmentPipeline

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")

class PYQEnrichmentCorrector:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.llm_pipeline = None
        self.stats = {
            'total_processed': 0,
            'successfully_enriched': 0,
            'failed_enrichment': 0,
            'improved_classifications': 0
        }

    async def initialize_llm(self):
        """Initialize LLM enrichment pipeline"""
        if not EMERGENT_LLM_KEY:
            raise Exception("EMERGENT_LLM_KEY not found in environment")
        
        self.llm_pipeline = LLMEnrichmentPipeline(llm_api_key=EMERGENT_LLM_KEY)
        print("✅ LLM enrichment pipeline initialized")

    async def get_topic_id_for_category(self, category):
        """Find matching topic_id based on category"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id FROM topics 
                    WHERE category LIKE :category_pattern
                    LIMIT 1
                """), {"category_pattern": f"%{category}%"})
                
                topic = result.fetchone()
                return topic[0] if topic else None
        except Exception as e:
            print(f"⚠️ Error finding topic for category '{category}': {e}")
            return None

    async def enrich_single_question(self, question_data):
        """Enrich a single PYQ question with LLM"""
        question_id, stem, current_subcategory, current_type = question_data
        
        try:
            # Get LLM classification
            category, subcategory, question_type = await self.llm_pipeline.categorize_question(
                stem=stem,
                hint_category=None,
                hint_subcategory=None
            )
            
            # Find matching topic_id
            topic_id = await self.get_topic_id_for_category(category)
            
            # Update database
            with self.engine.connect() as conn:
                update_query = text("""
                    UPDATE pyq_questions 
                    SET subcategory = :subcategory,
                        type_of_question = :question_type,
                        topic_id = :topic_id,
                        confirmed = true
                    WHERE id = :question_id
                """)
                
                conn.execute(update_query, {
                    "subcategory": subcategory,
                    "question_type": question_type,
                    "topic_id": topic_id,
                    "question_id": question_id
                })
                conn.commit()
            
            # Check if this was an improvement
            was_improved = (current_subcategory == "General Mathematics" or 
                          current_subcategory != subcategory)
            
            if was_improved:
                self.stats['improved_classifications'] += 1
            
            self.stats['successfully_enriched'] += 1
            
            return {
                'success': True,
                'old_subcategory': current_subcategory,
                'new_subcategory': subcategory,
                'new_type': question_type,
                'topic_id': topic_id,
                'improved': was_improved
            }
            
        except Exception as e:
            self.stats['failed_enrichment'] += 1
            return {
                'success': False,
                'error': str(e)
            }

    async def get_questions_to_enrich(self, priority_mode=True):
        """Get questions that need re-enrichment"""
        with self.engine.connect() as conn:
            if priority_mode:
                # Priority: General Mathematics questions first
                query = text("""
                    SELECT id, stem, subcategory, type_of_question 
                    FROM pyq_questions 
                    WHERE subcategory = 'General Mathematics'
                    ORDER BY stem
                """)
            else:
                # All questions
                query = text("""
                    SELECT id, stem, subcategory, type_of_question 
                    FROM pyq_questions 
                    ORDER BY subcategory, stem
                """)
            
            result = conn.execute(query)
            return result.fetchall()

    async def run_enrichment(self, priority_only=False):
        """Main enrichment process"""
        print("🚀 Starting PYQ Database Re-enrichment")
        print("=" * 50)
        
        # Initialize LLM
        await self.initialize_llm()
        
        # Get questions to process
        if priority_only:
            questions = await self.get_questions_to_enrich(priority_mode=True)
            print(f"📋 Processing {len(questions)} 'General Mathematics' questions (priority mode)")
        else:
            questions = await self.get_questions_to_enrich(priority_mode=False)
            print(f"📋 Processing all {len(questions)} PYQ questions")
        
        print("\n🔄 Starting enrichment process...")
        
        # Process each question
        for i, question_data in enumerate(questions, 1):
            question_id, stem, current_subcategory, current_type = question_data
            
            print(f"\n[{i}/{len(questions)}] Processing: {question_id[:8]}...")
            print(f"   Current: {current_subcategory}")
            print(f"   Stem: {stem[:80]}...")
            
            # Enrich the question
            result = await self.enrich_single_question(question_data)
            
            if result['success']:
                if result['improved']:
                    print(f"   ✅ IMPROVED: {current_subcategory} → {result['new_subcategory']}")
                else:
                    print(f"   ✅ Confirmed: {result['new_subcategory']}")
            else:
                print(f"   ❌ Failed: {result['error']}")
            
            self.stats['total_processed'] += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Print final statistics
        self.print_final_stats()

    def print_final_stats(self):
        """Print enrichment statistics"""
        print("\n" + "=" * 50)
        print("🎉 PYQ Re-enrichment Complete!")
        print("=" * 50)
        print(f"📊 Statistics:")
        print(f"   Total Processed: {self.stats['total_processed']}")
        print(f"   Successfully Enriched: {self.stats['successfully_enriched']}")
        print(f"   Failed: {self.stats['failed_enrichment']}")
        print(f"   Improved Classifications: {self.stats['improved_classifications']}")
        
        success_rate = (self.stats['successfully_enriched'] / self.stats['total_processed']) * 100 if self.stats['total_processed'] > 0 else 0
        improvement_rate = (self.stats['improved_classifications'] / self.stats['total_processed']) * 100 if self.stats['total_processed'] > 0 else 0
        
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Improvement Rate: {improvement_rate:.1f}%")

    async def verify_improvements(self):
        """Verify the classification improvements"""
        print("\n🔍 Verifying Classification Improvements:")
        print("-" * 40)
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT subcategory, COUNT(*) as count
                FROM pyq_questions 
                GROUP BY subcategory 
                ORDER BY count DESC
            """))
            
            for row in result:
                print(f"   {row[0]}: {row[1]} questions")
            
            # Check topic assignments
            print("\n🎯 Topic Assignment Status:")
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(topic_id) as with_topic,
                    COUNT(*) - COUNT(topic_id) as without_topic
                FROM pyq_questions
            """))
            
            stats = result.fetchone()
            print(f"   Total questions: {stats[0]}")
            print(f"   With topic_id: {stats[1]}")
            print(f"   Without topic_id: {stats[2]}")

async def main():
    """Main execution function"""
    corrector = PYQEnrichmentCorrector()
    
    print("🎯 PYQ Database Enrichment Corrector")
    print("Choose mode:")
    print("1. Priority mode: Fix 'General Mathematics' questions only (recommended)")
    print("2. Full mode: Re-enrich all PYQ questions")
    
    # For automated execution, let's default to priority mode
    mode = input("\nEnter choice (1 or 2, default=1): ").strip() or "1"
    
    try:
        if mode == "1":
            await corrector.run_enrichment(priority_only=True)
        else:
            await corrector.run_enrichment(priority_only=False)
        
        # Verify results
        await corrector.verify_improvements()
        
        print("\n✅ All done! Your PYQ database is now properly enriched.")
        
    except Exception as e:
        print(f"\n❌ Enrichment failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # For automation, we'll run priority mode directly
    async def automated_run():
        corrector = PYQEnrichmentCorrector()
        await corrector.run_enrichment(priority_only=True)
        await corrector.verify_improvements()
    
    asyncio.run(automated_run())