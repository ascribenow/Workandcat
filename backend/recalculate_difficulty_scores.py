#!/usr/bin/env python3
"""
Recalculate difficulty_score and difficulty_band for all existing questions
Uses new programmatic formula based on core_concepts, operations_required, solution_method
Only updates difficulty fields, preserves all other data
"""

from database import SessionLocal
from difficulty_calculator import calculate_difficulty_score_and_band, parse_solution_steps
from sqlalchemy import text
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recalculate_all_difficulty_scores():
    """Recalculate difficulty for all questions and pyq_questions"""
    
    logger.info("🔢 STARTING DIFFICULTY RECALCULATION")
    logger.info("=" * 60)
    logger.info("Formula: 0.25×Concepts + 0.50×Steps + 0.25×Operations")
    logger.info("Bands: Easy(≤2.0), Medium(2.0<score≤2.5), Hard(>2.5)")
    logger.info("=" * 60)
    
    db = SessionLocal()
    results = {
        "questions": {"updated": 0, "errors": 0, "distribution": {"Easy": 0, "Medium": 0, "Hard": 0}},
        "pyq_questions": {"updated": 0, "errors": 0, "distribution": {"Easy": 0, "Medium": 0, "Hard": 0}}
    }
    
    try:
        # Process regular questions
        logger.info("📋 Processing regular questions...")
        result = db.execute(text('SELECT id, core_concepts, operations_required, solution_method FROM questions ORDER BY id'))
        questions = result.fetchall()
        
        logger.info(f"   Found {len(questions)} questions to process")
        
        for i, question in enumerate(questions, 1):
            try:
                # Parse existing data safely
                try:
                    core_concepts = json.loads(question.core_concepts) if question.core_concepts else []
                except (json.JSONDecodeError, TypeError):
                    core_concepts = []
                
                try:
                    operations_required = json.loads(question.operations_required) if question.operations_required else []
                except (json.JSONDecodeError, TypeError):
                    operations_required = []
                
                steps_count = parse_solution_steps(question.solution_method or '')
                
                # Calculate new scores
                difficulty_score, difficulty_band = calculate_difficulty_score_and_band(
                    core_concepts, operations_required, steps_count
                )
                
                # Update only difficulty fields
                db.execute(text('''
                    UPDATE questions 
                    SET difficulty_score = :score, difficulty_band = :band 
                    WHERE id = :id
                '''), {
                    'score': difficulty_score,
                    'band': difficulty_band,
                    'id': question.id
                })
                
                results["questions"]["updated"] += 1
                results["questions"]["distribution"][difficulty_band] += 1
                
                if i % 25 == 0:
                    logger.info(f"   📊 Processed {i}/{len(questions)} questions...")
                    db.commit()  # Commit every 25 questions
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing question {question.id[:8]}...: {e}")
                results["questions"]["errors"] += 1
                continue
        
        db.commit()
        logger.info(f"✅ Regular questions complete: {results['questions']['updated']} updated, {results['questions']['errors']} errors")
        logger.info(f"   Distribution: Easy={results['questions']['distribution']['Easy']}, Medium={results['questions']['distribution']['Medium']}, Hard={results['questions']['distribution']['Hard']}")
        
        # Process PYQ questions
        logger.info("\n📋 Processing PYQ questions...")
        result = db.execute(text('SELECT id, core_concepts, operations_required, solution_method FROM pyq_questions ORDER BY id'))
        pyq_questions = result.fetchall()
        
        logger.info(f"   Found {len(pyq_questions)} PYQ questions to process")
        
        for i, pyq in enumerate(pyq_questions, 1):
            try:
                # Parse existing data safely
                try:
                    core_concepts = json.loads(pyq.core_concepts) if pyq.core_concepts else []
                except (json.JSONDecodeError, TypeError):
                    core_concepts = []
                
                try:
                    operations_required = json.loads(pyq.operations_required) if pyq.operations_required else []
                except (json.JSONDecodeError, TypeError):
                    operations_required = []
                
                steps_count = parse_solution_steps(pyq.solution_method or '')
                
                # Calculate new scores
                difficulty_score, difficulty_band = calculate_difficulty_score_and_band(
                    core_concepts, operations_required, steps_count
                )
                
                # Update only difficulty fields
                db.execute(text('''
                    UPDATE pyq_questions 
                    SET difficulty_score = :score, difficulty_band = :band 
                    WHERE id = :id
                '''), {
                    'score': difficulty_score,
                    'band': difficulty_band,
                    'id': pyq.id
                })
                
                results["pyq_questions"]["updated"] += 1
                results["pyq_questions"]["distribution"][difficulty_band] += 1
                
                if i % 25 == 0:
                    logger.info(f"   📊 Processed {i}/{len(pyq_questions)} PYQ questions...")
                    db.commit()  # Commit every 25 questions
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing PYQ {pyq.id[:8]}...: {e}")
                results["pyq_questions"]["errors"] += 1
                continue
        
        db.commit()
        logger.info(f"✅ PYQ questions complete: {results['pyq_questions']['updated']} updated, {results['pyq_questions']['errors']} errors")
        logger.info(f"   Distribution: Easy={results['pyq_questions']['distribution']['Easy']}, Medium={results['pyq_questions']['distribution']['Medium']}, Hard={results['pyq_questions']['distribution']['Hard']}")
        
        # Final summary
        total_updated = results["questions"]["updated"] + results["pyq_questions"]["updated"]
        total_errors = results["questions"]["errors"] + results["pyq_questions"]["errors"]
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 DIFFICULTY RECALCULATION COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"📊 TOTALS:")
        logger.info(f"   • Total Updated: {total_updated}")
        logger.info(f"   • Total Errors: {total_errors}")
        logger.info(f"   • Success Rate: {(total_updated/(total_updated+total_errors)*100):.1f}%")
        
        logger.info(f"\n📊 FINAL DISTRIBUTIONS:")
        logger.info(f"   Regular Questions:")
        logger.info(f"     Easy: {results['questions']['distribution']['Easy']} ({results['questions']['distribution']['Easy']/results['questions']['updated']*100:.1f}%)")
        logger.info(f"     Medium: {results['questions']['distribution']['Medium']} ({results['questions']['distribution']['Medium']/results['questions']['updated']*100:.1f}%)")
        logger.info(f"     Hard: {results['questions']['distribution']['Hard']} ({results['questions']['distribution']['Hard']/results['questions']['updated']*100:.1f}%)")
        
        logger.info(f"   PYQ Questions:")
        logger.info(f"     Easy: {results['pyq_questions']['distribution']['Easy']} ({results['pyq_questions']['distribution']['Easy']/results['pyq_questions']['updated']*100:.1f}%)")
        logger.info(f"     Medium: {results['pyq_questions']['distribution']['Medium']} ({results['pyq_questions']['distribution']['Medium']/results['pyq_questions']['updated']*100:.1f}%)")
        logger.info(f"     Hard: {results['pyq_questions']['distribution']['Hard']} ({results['pyq_questions']['distribution']['Hard']/results['pyq_questions']['updated']*100:.1f}%)")
        
        return {
            "success": True,
            "results": results,
            "total_updated": total_updated,
            "total_errors": total_errors
        }
        
    except Exception as e:
        logger.error(f"❌ Critical error during recalculation: {e}")
        db.rollback()
        return {
            "success": False, 
            "error": str(e),
            "results": results
        }
        
    finally:
        db.close()

def preview_calculation_sample():
    """Preview calculation on a small sample for verification"""
    logger.info("🔍 PREVIEWING DIFFICULTY CALCULATION ON SAMPLE")
    logger.info("=" * 50)
    
    db = SessionLocal()
    try:
        # Get 5 sample questions with existing data
        result = db.execute(text('''
            SELECT id, core_concepts, operations_required, solution_method, 
                   difficulty_score as old_score, difficulty_band as old_band
            FROM questions 
            WHERE core_concepts IS NOT NULL 
            AND operations_required IS NOT NULL 
            AND solution_method IS NOT NULL
            LIMIT 5
        '''))
        
        samples = result.fetchall()
        
        for i, sample in enumerate(samples, 1):
            try:
                # Parse data
                core_concepts = json.loads(sample.core_concepts) if sample.core_concepts else []
                operations_required = json.loads(sample.operations_required) if sample.operations_required else []
                steps_count = parse_solution_steps(sample.solution_method or '')
                
                # Calculate new scores
                new_score, new_band = calculate_difficulty_score_and_band(
                    core_concepts, operations_required, steps_count
                )
                
                logger.info(f"📋 Sample {i} (ID: {sample.id[:8]}...):")
                logger.info(f"   Components: {len(core_concepts)} concepts, {steps_count} steps, {len(operations_required)} operations")
                logger.info(f"   OLD: {sample.old_band} ({sample.old_score})")
                logger.info(f"   NEW: {new_band} ({new_score})")
                
                change = "✅ SAME" if new_band == sample.old_band else f"🔄 CHANGED ({sample.old_band} → {new_band})"
                logger.info(f"   Status: {change}")
                logger.info("")
                
            except Exception as e:
                logger.error(f"   ❌ Error processing sample {i}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error in preview: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        preview_calculation_sample()
    else:
        result = recalculate_all_difficulty_scores()
        if result["success"]:
            print(f"\n🎉 SUCCESS: Updated {result['total_updated']} questions total")
        else:
            print(f"\n❌ FAILED: {result['error']}")
            if result.get("results"):
                print(f"Partial results: {result['results']}")