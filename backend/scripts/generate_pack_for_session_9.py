"""
Generate Pack for Existing Session #9 (511067a1)
This script directly generates a 12-question pack for the existing session
"""
import os
import sys
import asyncio
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.simplified_job_handlers import (
    gather_user_learning_data,
    generate_personalized_session_pack,
    persist_session_pack
)

SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"
USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"

async def generate_pack_for_existing_session():
    print("=" * 80)
    print("GENERATING PACK FOR EXISTING SESSION #9")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # 1. Verify session exists
        print("\n1. Verifying session...")
        result = db.execute(text("""
            SELECT session_id, user_id, sess_seq, status
            FROM sessions
            WHERE session_id = :session_id
        """), {"session_id": SESSION_ID})
        
        session = result.fetchone()
        if not session:
            print(f"✗ Session {SESSION_ID} not found!")
            return False
        
        print(f"✓ Session found")
        print(f"  Session #: {session[2]}")
        print(f"  Status: {session[3]}")
        
        # 2. Check if pack already exists
        print("\n2. Checking existing pack...")
        result = db.execute(text("""
            SELECT COUNT(*) FROM session_pack_questions
            WHERE session_id = CAST(:session_id AS uuid)
        """), {"session_id": SESSION_ID})
        
        existing_count = result.scalar()
        print(f"  Current questions: {existing_count}")
        
        if existing_count >= 12:
            print("✓ Pack already exists with sufficient questions!")
            return True
        
        # 3. Generate pack using existing service
        print("\n3. Generating personalized session pack...")
        
        # Gather user learning data
        learning_data = await gather_user_learning_data(USER_ID)
        print(f"  ✓ Gathered learning data")
        
        # Generate pack
        session_pack = await generate_personalized_session_pack(USER_ID, learning_data)
        print(f"  ✓ Generated pack with {len(session_pack.get('questions', []))} questions")
        
        # 4. Persist pack with specific session_id
        print("\n4. Persisting pack to database...")
        
        # Modify session_pack to use existing session_id
        session_pack['session_id'] = SESSION_ID
        
        # Persist using existing function but override session_id
        pack_id = await persist_session_pack_with_session_id(
            user_id=USER_ID,
            session_pack=session_pack,
            target_session_id=SESSION_ID
        )
        
        print(f"  ✓ Pack persisted: {pack_id}")
        
        # 5. Verify pack was created
        print("\n5. Verifying pack creation...")
        result = db.execute(text("""
            SELECT COUNT(*) FROM session_pack_questions
            WHERE session_id = CAST(:session_id AS uuid)
        """), {"session_id": SESSION_ID})
        
        final_count = result.scalar()
        print(f"  Questions in pack: {final_count}")
        
        if final_count >= 12:
            print(f"\n✅ SUCCESS: Pack generated with {final_count} questions!")
            print(f"   Session #9 (511067a1) is now ready to use")
            return True
        else:
            print(f"\n⚠️  Only {final_count} questions created")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def persist_session_pack_with_session_id(user_id: str, session_pack: dict, target_session_id: str) -> str:
    """
    Modified version of persist_session_pack that uses a specific session_id
    instead of creating a new one
    """
    from database import SessionLocal
    from sqlalchemy import text
    import json
    
    db = SessionLocal()
    
    try:
        # Use the target session_id instead of creating new
        session_id = target_session_id
        
        # Insert into session_pack_plan (if not exists)
        db.execute(text("""
            INSERT INTO session_pack_plan (
                user_id, session_id, pack, status, planning_strategy,
                created_at, served_at
            ) VALUES (
                :user_id, CAST(:session_id AS uuid), :pack, 'planned', 'adaptive',
                NOW(), NULL
            )
            ON CONFLICT (session_id) DO UPDATE
            SET pack = :pack, status = 'planned', created_at = NOW()
        """), {
            "user_id": user_id,
            "session_id": session_id,
            "pack": json.dumps(session_pack)
        })
        
        # Delete any existing questions for this session (in case of regeneration)
        db.execute(text("""
            DELETE FROM session_pack_questions WHERE session_id = CAST(:session_id AS uuid)
        """), {"session_id": session_id})
        
        # Insert questions
        questions = session_pack.get("questions", [])
        
        for idx, q in enumerate(questions):
            db.execute(text("""
                INSERT INTO session_pack_questions (
                    session_id, position, question_id, difficulty, subcategory,
                    type_of_question, pyq_score, is_pyq, question_text,
                    options, correct_answer, snap_read, solution_approach,
                    detailed_solution, principle_to_remember
                ) VALUES (
                    CAST(:session_id AS uuid), :position, :question_id, :difficulty,
                    :subcategory, :type_of_question, :pyq_score, :is_pyq,
                    :question_text, :options, :correct_answer, :snap_read,
                    :solution_approach, :detailed_solution, :principle_to_remember
                )
            """), {
                "session_id": session_id,
                "position": idx + 1,
                "question_id": q.get("question_id"),
                "difficulty": q.get("difficulty"),
                "subcategory": q.get("subcategory"),
                "type_of_question": q.get("type_of_question"),
                "pyq_score": q.get("pyq_score", 0),
                "is_pyq": q.get("is_pyq", False),
                "question_text": q.get("question_text", ""),
                "options": json.dumps(q.get("options", [])),
                "correct_answer": q.get("correct_answer", ""),
                "snap_read": q.get("snap_read", ""),
                "solution_approach": q.get("solution_approach", ""),
                "detailed_solution": q.get("detailed_solution", ""),
                "principle_to_remember": q.get("principle_to_remember", "")
            })
        
        db.commit()
        
        return session_id
        
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to persist pack: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(generate_pack_for_existing_session())
    sys.exit(0 if result else 1)
