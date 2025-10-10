"""
Simple fix: Generate pack for Session #9 using existing pack as template
"""
import os
import sys
import asyncio
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.simplified_job_handlers import (
    gather_user_learning_data,
    generate_personalized_session_pack
)

SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"
USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"

async def fix_session_9():
    print("=" * 80)
    print("SIMPLE FIX: Generate Pack for Session #9")
    print("=" * 80)
    
    try:
        # 1. Generate pack using existing service
        print("\n1. Generating session pack...")
        learning_data = await gather_user_learning_data(USER_ID)
        session_pack = await generate_personalized_session_pack(USER_ID, learning_data)
        
        print(f"✓ Pack generated with {len(session_pack.get('questions', []))} questions")
        
        # 2. Manually insert into session_packs using Session #9's ID
        print("\n2. Persisting pack directly to Session #9...")
        
        db = SessionLocal()
        
        try:
            import json
            from utils.timezone_utils import now_ist
            
            # Insert into session_packs with Session #9's ID
            constraint_report_json = json.dumps({
                "pack_type": session_pack["pack_type"],
                "difficulty_distribution": session_pack["difficulty_distribution"],
                "planning_strategy": session_pack["planning_strategy"],
                "weak_concepts_targeted": session_pack["weak_concepts_targeted"],
                "high_debt_pairs_addressed": session_pack["high_debt_pairs_addressed"]
            })
            
            db.execute(text("""
                INSERT INTO session_packs (
                    session_id, user_id, constraint_report, created_at
                ) VALUES (
                    CAST(:session_id AS uuid), CAST(:user_id AS uuid), CAST(:constraint_report AS jsonb), :created_at
                )
                ON CONFLICT (session_id) DO UPDATE 
                SET constraint_report = CAST(:constraint_report AS jsonb), created_at = :created_at
            """), {
                "session_id": SESSION_ID,
                "user_id": USER_ID,
                "constraint_report": constraint_report_json,
                "created_at": now_ist()
            })
            
            # Delete any existing questions (cleanup)
            db.execute(text("""
                DELETE FROM session_pack_questions WHERE session_id = CAST(:session_id AS uuid)
            """), {"session_id": SESSION_ID})
            
            # Insert all questions
            questions = session_pack.get("questions", [])
            
            for idx, question in enumerate(questions, 1):
                core_concepts = question.get("core_concepts", [])
                if isinstance(core_concepts, str):
                    core_concepts = json.loads(core_concepts)
                elif not isinstance(core_concepts, list):
                    core_concepts = list(core_concepts) if core_concepts else []
                
                question_data_json = json.dumps({
                    "id": question["id"],
                    "stem": question["stem"],
                    "answer": question["answer"],
                    "explanation": question.get("explanation", ""),
                    "option_a": question.get("option_a", ""),
                    "option_b": question.get("option_b", ""),
                    "option_c": question.get("option_c", ""),
                    "option_d": question.get("option_d", ""),
                    "difficulty_band": question["difficulty_band"],
                    "subcategory": question["subcategory"],
                    "type_of_question": question["type_of_question"],
                    "core_concepts": core_concepts,
                    "pyq_frequency_score": question.get("pyq_frequency_score", 0),
                    "snap_read": question.get("snap_read", ""),
                    "solution_approach": question.get("solution_approach", ""),
                    "detailed_solution": question.get("detailed_solution", ""),
                    "principle_to_remember": question.get("principle_to_remember", "")
                })
                
                db.execute(text("""
                    INSERT INTO session_pack_questions (
                        session_id, position, question_id, question_data
                    ) VALUES (
                        CAST(:session_id AS uuid), :position, CAST(:question_id AS uuid), CAST(:question_data AS jsonb)
                    )
                """), {
                    "session_id": SESSION_ID,
                    "position": question["position"],
                    "question_id": question["id"],
                    "question_data": question_data_json
                })
            
            db.commit()
            print(f"✓ Persisted {len(questions)} questions to Session #9")
            
            # 3. Verify
            result = db.execute(text("""
                SELECT COUNT(*) FROM session_pack_questions WHERE session_id = CAST(:sid AS uuid)
            """), {"sid": SESSION_ID})
            count = result.scalar()
            
            print(f"\n3. Verification: {count} questions in Session #9")
            
            if count >= 12:
                print(f"\n✅ SUCCESS! Session #9 now has {count} questions")
                print(f"   User twelvrhelp@gmail.com can now resume their session")
                return True
            else:
                print(f"\n⚠️  Only {count} questions - expected 12")
                return False
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(fix_session_9())
    sys.exit(0 if result else 1)
