"""
Enhanced Quality Verifier
Integrates Anchor Writer V1 into the existing quality verification pipeline
Ensures quality_verified=TRUE only if valid anchors are present
"""

import asyncio
import json
import logging
import psycopg2
from typing import List, Dict, Tuple
import os
from dotenv import load_dotenv
from services.anchor_writer_v1 import AnchorWriterV1

load_dotenv()

logger = logging.getLogger(__name__)

class EnhancedQualityVerifier:
    def __init__(self):
        self.anchor_writer = AnchorWriterV1()
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def run_enhanced_verification(self, batch_size: int = 10, limit: int = None) -> Dict[str, any]:
        """
        Run enhanced quality verification on all active questions
        Only questions with valid anchors will have quality_verified=TRUE
        
        Args:
            batch_size: Number of questions to process in each batch
            limit: Optional limit on number of questions to process (for testing)
            
        Returns:
            Statistics about the verification process
        """
        logger.info("🚀 Starting Enhanced Quality Verification with Anchor Writer V1...")
        
        conn = self._get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get all active questions that need anchor generation
            query = """
                SELECT id, subcategory, type_of_question, problem_structure, 
                       operations_required, core_concepts, concept_keywords,
                       stem, solution_approach, detailed_solution, 
                       principle_to_remember, difficulty_band, pyq_frequency_score,
                       anchors, quality_verified
                FROM questions 
                WHERE is_active = TRUE
                AND (anchors IS NULL OR anchors = '[]'::jsonb OR quality_verified = FALSE)
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            questions = cur.fetchall()
            
            if not questions:
                logger.info("✅ No questions need anchor generation - all up to date!")
                return {
                    "total_processed": 0,
                    "anchors_generated": 0,
                    "quality_verified": 0,
                    "failed": 0
                }
            
            logger.info(f"📊 Found {len(questions)} questions needing anchor generation")
            
            # Process questions in batches
            total_processed = 0
            anchors_generated = 0
            quality_verified = 0
            failed = 0
            
            for i in range(0, len(questions), batch_size):
                batch = questions[i:i+batch_size]
                logger.info(f"🔄 Processing batch {i//batch_size + 1}/{(len(questions) + batch_size - 1)//batch_size} ({len(batch)} questions)")
                
                # Convert batch to question dictionaries
                batch_questions = []
                for row in batch:
                    question_data = {
                        'id': row[0],
                        'subcategory': row[1],
                        'type_of_question': row[2], 
                        'problem_structure': row[3],
                        'operations_required': json.loads(row[4]) if row[4] else [],
                        'core_concepts': json.loads(row[5]) if row[5] else [],
                        'concept_keywords': json.loads(row[6]) if row[6] else [],
                        'stem': row[7],
                        'solution_approach': row[8],
                        'detailed_solution': row[9],
                        'principle_to_remember': row[10],
                        'difficulty_band': row[11],
                        'pyq_frequency_score': float(row[12]) if row[12] else 0.0
                    }
                    batch_questions.append(question_data)
                
                # Generate anchors for batch
                anchor_results = await self.anchor_writer.generate_anchors_batch(batch_questions, batch_size=5)
                
                # Update database with results
                for question_data in batch_questions:
                    question_id = question_data['id']
                    anchors = anchor_results.get(question_id, [])
                    
                    try:
                        if anchors and len(anchors) > 0:
                            # Valid anchors generated - set quality_verified=TRUE
                            cur.execute("""
                                UPDATE questions 
                                SET anchors = %s, quality_verified = TRUE 
                                WHERE id = %s
                            """, (json.dumps(anchors), question_id))
                            
                            anchors_generated += 1
                            quality_verified += 1
                            logger.debug(f"✅ {question_id}: Generated anchors {anchors}")
                            
                        else:
                            # Failed to generate anchors - set quality_verified=FALSE
                            cur.execute("""
                                UPDATE questions 
                                SET quality_verified = FALSE 
                                WHERE id = %s
                            """, (question_id,))
                            
                            failed += 1
                            logger.warning(f"❌ {question_id}: Failed to generate anchors")
                        
                        total_processed += 1
                        
                    except Exception as update_error:
                        logger.error(f"❌ Failed to update question {question_id}: {update_error}")
                        failed += 1
                
                # Commit batch changes
                conn.commit()
                
                # Small delay between batches to respect API rate limits
                if i + batch_size < len(questions):
                    await asyncio.sleep(3)  # 3 second delay
            
            # Final statistics
            stats = {
                "total_processed": total_processed,
                "anchors_generated": anchors_generated,
                "quality_verified": quality_verified,
                "failed": failed,
                "success_rate": (anchors_generated / total_processed * 100) if total_processed > 0 else 0
            }
            
            logger.info("🎉 Enhanced Quality Verification completed!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   Total processed: {stats['total_processed']}")
            logger.info(f"   Anchors generated: {stats['anchors_generated']}")
            logger.info(f"   Quality verified: {stats['quality_verified']}")
            logger.info(f"   Failed: {stats['failed']}")
            logger.info(f"   Success rate: {stats['success_rate']:.1f}%")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Enhanced Quality Verification failed: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
    
    def get_verification_status(self) -> Dict[str, int]:
        """Get current verification status across all questions"""
        conn = self._get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get comprehensive statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_active,
                    COUNT(*) FILTER (WHERE quality_verified = TRUE) as quality_verified_count,
                    COUNT(*) FILTER (WHERE quality_verified = FALSE) as quality_unverified_count,
                    COUNT(*) FILTER (WHERE anchors IS NOT NULL AND anchors != '[]'::jsonb) as has_anchors_count,
                    COUNT(*) FILTER (WHERE anchors IS NULL OR anchors = '[]'::jsonb) as missing_anchors_count
                FROM questions 
                WHERE is_active = TRUE
            """)
            
            result = cur.fetchone()
            
            return {
                "total_active": result[0],
                "quality_verified": result[1],
                "quality_unverified": result[2], 
                "has_anchors": result[3],
                "missing_anchors": result[4]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get verification status: {e}")
            return {}
        finally:
            cur.close()
            conn.close()

# Test function
async def test_enhanced_verifier(limit=5):
    """Test the enhanced verifier with a small batch"""
    verifier = EnhancedQualityVerifier()
    
    print("📊 Current verification status:")
    status = verifier.get_verification_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\n🧪 Testing Enhanced Quality Verifier with {limit} questions...")
    stats = await verifier.run_enhanced_verification(batch_size=3, limit=limit)
    
    print("\n📈 Test Results:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return stats

if __name__ == "__main__":
    asyncio.run(test_enhanced_verifier())