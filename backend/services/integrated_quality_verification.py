"""
Integrated Quality Verification System
Extends existing quality verification to include anchor generation as a mandatory requirement
"""

import asyncio
import json
import logging
import psycopg2
from typing import List, Dict, Tuple, Optional
import os
from dotenv import load_dotenv
from services.anchor_writer_v1 import AnchorWriterV1

load_dotenv()

logger = logging.getLogger(__name__)

class IntegratedQualityVerificationSystem:
    """
    Unified quality verification system that combines:
    1. Existing quality verification logic
    2. Anchor generation as mandatory requirement
    3. Single quality_verified=TRUE gate
    """
    
    def __init__(self):
        self.anchor_writer = AnchorWriterV1()
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def run_integrated_quality_verification(self, batch_size: int = 5, limit: int = None) -> Dict[str, any]:
        """
        Run integrated quality verification that ensures quality_verified=TRUE ONLY when:
        1. All existing quality checks pass (using existing enrichment logic)
        2. Valid anchors are successfully generated
        
        This replaces the previous separate anchor generation approach
        """
        logger.info("🚀 Starting Integrated Quality Verification System...")
        logger.info("📋 This will verify BOTH existing quality criteria AND anchor generation")
        
        conn = self._get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get questions that either:
            # 1. Have no anchors (need anchor generation)  
            # 2. Are marked as quality_verified=FALSE (failed previous checks)
            # 3. Need re-verification
            query = """
                SELECT id, subcategory, type_of_question, problem_structure, 
                       operations_required, core_concepts, concept_keywords,
                       stem, solution_approach, detailed_solution, 
                       principle_to_remember, difficulty_band, pyq_frequency_score,
                       anchors, quality_verified, concept_extraction_status, is_active
                FROM questions 
                WHERE is_active = TRUE
                AND (
                    -- Missing anchors OR
                    (anchors IS NULL OR anchors = '[]'::jsonb) OR
                    -- Previously failed quality verification OR  
                    quality_verified = FALSE OR
                    -- Needs re-verification
                    concept_extraction_status != 'completed'
                )
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            questions = cur.fetchall()
            
            if not questions:
                logger.info("✅ All questions already have integrated quality verification complete!")
                return {
                    "total_processed": 0,
                    "passed_existing_quality": 0,
                    "anchors_generated": 0, 
                    "quality_verified_final": 0,
                    "failed_existing_quality": 0,
                    "failed_anchor_generation": 0,
                    "total_failed": 0
                }
            
            logger.info(f"📊 Found {len(questions)} questions needing integrated quality verification")
            
            # Process questions in batches
            stats = {
                "total_processed": 0,
                "passed_existing_quality": 0,
                "anchors_generated": 0,
                "quality_verified_final": 0,
                "failed_existing_quality": 0, 
                "failed_anchor_generation": 0,
                "total_failed": 0
            }
            
            for i in range(0, len(questions), batch_size):
                batch = questions[i:i+batch_size]
                logger.info(f"🔄 Processing batch {i//batch_size + 1}/{(len(questions) + batch_size - 1)//batch_size} ({len(batch)} questions)")
                
                # Process each question in the batch
                for row in batch:
                    question_id = row[0]
                    question_data = {
                        'id': question_id,
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
                        'pyq_frequency_score': float(row[12]) if row[12] else 0.0,
                        'existing_anchors': json.loads(row[13]) if row[13] else [],
                        'current_quality_verified': row[14],
                        'concept_extraction_status': row[15],
                        'is_active': row[16]
                    }
                    
                    # Step 1: Check existing quality criteria
                    passes_existing_quality = await self._check_existing_quality_criteria(question_data)
                    
                    if not passes_existing_quality:
                        # Failed existing quality checks - mark as quality_verified=FALSE
                        cur.execute("""
                            UPDATE questions 
                            SET quality_verified = FALSE, concept_extraction_status = 'failed'
                            WHERE id = %s
                        """, (question_id,))
                        
                        stats["failed_existing_quality"] += 1
                        stats["total_failed"] += 1
                        logger.debug(f"❌ {question_id[:8]}: Failed existing quality criteria")
                        
                    else:
                        stats["passed_existing_quality"] += 1
                        
                        # Step 2: Generate anchors (mandatory for quality_verified=TRUE)
                        if not question_data['existing_anchors']:
                            anchors = await self.anchor_writer.generate_anchors(question_data)
                        else:
                            anchors = question_data['existing_anchors']  # Keep existing valid anchors
                        
                        if anchors and len(anchors) > 0:
                            # Both existing quality + valid anchors = quality_verified=TRUE
                            cur.execute("""
                                UPDATE questions 
                                SET anchors = %s, 
                                    quality_verified = TRUE,
                                    concept_extraction_status = 'completed',
                                    is_active = TRUE
                                WHERE id = %s
                            """, (json.dumps(anchors), question_id))
                            
                            stats["anchors_generated"] += 1
                            stats["quality_verified_final"] += 1
                            logger.debug(f"✅ {question_id[:8]}: PASSED integrated quality verification")
                            
                        else:
                            # Passed existing quality but failed anchor generation
                            cur.execute("""
                                UPDATE questions 
                                SET quality_verified = FALSE, concept_extraction_status = 'anchor_generation_failed'
                                WHERE id = %s
                            """, (question_id,))
                            
                            stats["failed_anchor_generation"] += 1
                            stats["total_failed"] += 1
                            logger.warning(f"⚠️ {question_id[:8]}: Passed existing quality but failed anchor generation")
                    
                    stats["total_processed"] += 1
                
                # Commit batch changes
                conn.commit()
                
                # Rate limiting for API calls
                if i + batch_size < len(questions):
                    await asyncio.sleep(3)
            
            # Calculate final success rate
            stats["success_rate"] = (stats["quality_verified_final"] / stats["total_processed"] * 100) if stats["total_processed"] > 0 else 0
            
            logger.info("🎉 Integrated Quality Verification completed!")
            logger.info(f"📊 Final Statistics:")
            logger.info(f"   Total processed: {stats['total_processed']}")
            logger.info(f"   Passed existing quality: {stats['passed_existing_quality']}")
            logger.info(f"   Generated anchors: {stats['anchors_generated']}")
            logger.info(f"   Final quality_verified=TRUE: {stats['quality_verified_final']}")
            logger.info(f"   Failed existing quality: {stats['failed_existing_quality']}")
            logger.info(f"   Failed anchor generation: {stats['failed_anchor_generation']}")
            logger.info(f"   Success rate: {stats['success_rate']:.1f}%")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Integrated Quality Verification failed: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
    
    async def _check_existing_quality_criteria(self, question_data: Dict) -> bool:
        """
        Check if question meets existing quality criteria
        This replicates the complete logic from regular_enrichment_service.py
        
        Checks 21 required fields + concept_extraction_status:
        - CSV Upload Fields (7): stem, snap_read, solution_approach, detailed_solution, principle_to_remember, answer, mcq_options  
        - LLM Generated Fields (14): right_answer, category, subcategory, type_of_question, difficulty_score, difficulty_band, core_concepts, concept_difficulty, operations_required, problem_structure, concept_keywords, solution_method, pyq_frequency_score, concept_extraction_status
        """
        try:
            # Get additional fields from database for complete verification
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT stem, snap_read, solution_approach, detailed_solution, 
                       principle_to_remember, answer, mcq_options, right_answer, 
                       category, subcategory, type_of_question, difficulty_score, 
                       difficulty_band, core_concepts, concept_difficulty, 
                       operations_required, problem_structure, concept_keywords, 
                       solution_method, pyq_frequency_score, concept_extraction_status
                FROM questions WHERE id = %s
            """, (question_data['id'],))
            
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if not row:
                return False
            
            # Map database fields to verification data
            verification_data = {
                # CSV Upload Fields (7 fields)
                'stem': row[0],
                'snap_read': row[1], 
                'solution_approach': row[2],
                'detailed_solution': row[3],
                'principle_to_remember': row[4],
                'answer': row[5],
                'mcq_options': row[6],
                
                # LLM Generated Fields (14 fields)
                'right_answer': row[7],
                'category': row[8],
                'subcategory': row[9],
                'type_of_question': row[10],
                'difficulty_score': row[11],
                'difficulty_band': row[12],
                'core_concepts': json.loads(row[13]) if row[13] else [],
                'concept_difficulty': row[14],
                'operations_required': json.loads(row[15]) if row[15] else [],
                'problem_structure': row[16],
                'concept_keywords': json.loads(row[17]) if row[17] else [],
                'solution_method': row[18],
                'pyq_frequency_score': row[19],
                'concept_extraction_status': row[20]
            }
            
            # STEP 1: Check all 21 required fields are present and meaningful
            required_fields = [
                # CSV Upload Fields (7 fields)
                'stem', 'snap_read', 'solution_approach', 'detailed_solution', 
                'principle_to_remember', 'answer', 'mcq_options',
                
                # LLM Generated Fields (14 fields)  
                'right_answer', 'category', 'subcategory', 'type_of_question',
                'difficulty_score', 'difficulty_band', 'core_concepts', 'concept_difficulty',
                'operations_required', 'problem_structure', 'concept_keywords', 
                'solution_method', 'pyq_frequency_score'
            ]
            
            missing_or_invalid_fields = []
            for field in required_fields:
                value = verification_data.get(field)
                
                # Check: Not Null AND Not Empty String AND Not Placeholder
                if (value is None or 
                    value == '' or 
                    value in ['To be classified by LLM', 'N/A', 'null', 'None'] or
                    (isinstance(value, list) and len(value) == 0)):
                    missing_or_invalid_fields.append(field)
            
            # STEP 2: Check concept_extraction_status = 'completed'
            concept_status = verification_data.get('concept_extraction_status', '')
            if concept_status != 'completed':
                missing_or_invalid_fields.append('concept_extraction_status')
            
            # STEP 3: Check difficulty band is valid
            difficulty_band = verification_data.get('difficulty_band', '').lower()
            if difficulty_band not in ['easy', 'medium', 'hard']:
                missing_or_invalid_fields.append('difficulty_band_invalid')
            
            # STEP 4: Check minimum stem length
            stem = verification_data.get('stem', '')
            if len(stem.strip()) < 20:
                missing_or_invalid_fields.append('stem_too_short')
            
            if missing_or_invalid_fields:
                logger.debug(f"Failed quality criteria - missing/invalid fields: {missing_or_invalid_fields}")
                return False
            
            logger.debug("✅ All 21 fields + concept_extraction_status + validation checks passed")
            return True
            
        except Exception as e:
            logger.error(f"Error in comprehensive quality criteria check: {e}")
            return False
    
    def get_integrated_verification_status(self) -> Dict[str, int]:
        """Get comprehensive verification status"""
        conn = self._get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_active,
                    COUNT(*) FILTER (WHERE quality_verified = TRUE) as quality_verified_count,
                    COUNT(*) FILTER (WHERE quality_verified = FALSE) as quality_unverified_count,
                    COUNT(*) FILTER (WHERE anchors IS NOT NULL AND anchors != '[]'::jsonb) as has_anchors_count,
                    COUNT(*) FILTER (WHERE anchors IS NULL OR anchors = '[]'::jsonb) as missing_anchors_count,
                    COUNT(*) FILTER (WHERE quality_verified = TRUE AND anchors IS NOT NULL AND anchors != '[]'::jsonb) as fully_verified_count,
                    COUNT(*) FILTER (WHERE concept_extraction_status = 'completed') as extraction_completed_count
                FROM questions 
                WHERE is_active = TRUE
            """)
            
            result = cur.fetchone()
            
            return {
                "total_active": result[0],
                "quality_verified": result[1],
                "quality_unverified": result[2], 
                "has_anchors": result[3],
                "missing_anchors": result[4],
                "fully_verified": result[5],  # Both quality_verified=TRUE AND has_anchors
                "extraction_completed": result[6]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get verification status: {e}")
            return {}
        finally:
            cur.close()
            conn.close()

# Test function
async def test_integrated_verifier(limit=5):
    """Test the integrated verifier with a small batch"""
    verifier = IntegratedQualityVerificationSystem()
    
    print("📊 BEFORE - Integrated verification status:")
    status = verifier.get_integrated_verification_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\n🧪 Testing Integrated Quality Verifier with {limit} questions...")
    stats = await verifier.run_integrated_quality_verification(batch_size=3, limit=limit)
    
    print("\n📈 Test Results:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n📊 AFTER - Final verification status:")
    final_status = verifier.get_integrated_verification_status()
    for key, value in final_status.items():
        print(f"   {key}: {value}")
    
    return stats

if __name__ == "__main__":
    asyncio.run(test_integrated_verifier())