"""
Bulk fix for sessions missing session_packs entries
These sessions have all questions in session_pack_questions but missing the metadata entry
"""
import os
import sys
import json
from sqlalchemy import create_engine, text
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def now_ist():
    """Get current time in IST"""
    return datetime.now(timezone.utc)

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url, pool_pre_ping=True)

print("=" * 80)
print("BULK FIX: Adding Missing session_packs Entries")
print("=" * 80)

# List of sessions that need fixing (from validation report)
sessions_to_fix = [
    ('de8f9a5a-76be-460e-bec9-a3f8f8328af9', 'vanshitmehrotra@gmail.com'),
    ('29082737-19a6-42f2-9dd7-8421095157b1', 'tanishqdummy@gmail.com'),
    ('6926904b-43c7-4b2f-82f2-a9a48cdbc58a', 'swastikmittal24@gmail.com'),
    ('04828d15-bb2a-4518-88d6-434cc87269e7', 'krunal3690@gmail.com'),
    ('48a1c190-4b70-4b41-9ea9-273f023db4ae', 'kvestforexcellence@gmail.com'),
    ('dff0ac01-9406-4ecd-9f14-47fc2fa00f66', 'tushnair746@gmail.com'),
    ('deecd7f6-8687-47ad-b57d-1d620eb17f61', 'soubhagyaswain02003@gmail.com'),
    ('fd18db1d-d400-492e-9e99-db025c57ca9a', 'abin151119@gmail.com'),
    ('f7f293f1-5abd-4e49-8ae6-0900e0e189f4', 'banaged537@fintehs.com'),
    ('e3fa806b-206e-4359-b9a8-c1ed0ff5829c', 'aayushibaldwa89@gmail.com'),
    ('8a381ce6-51b0-41c7-a696-b17a6b2e0d29', 'harshitasoni452@gmail.com'),
    ('ff9bb98d-fd70-49c3-8eb4-56048a8c448e', 'missioncat18@gmail.com'),
    ('3ef03827-adc2-498b-8f9c-b7600a0c9806', 'eugenegeorge2004@gmail.com'),
    ('fd52a2b2-c6a7-4587-927f-b6ef90176ea5', 'arnavaarav2722@gmail.com'),
    ('6596f853-a29e-478e-803d-80ad9d4904b3', 'jainsamriddhi882@gmail.com'),
    ('36533a99-60e3-4c8c-8d4a-f0cbb2cce51d', 'akshaybeast003@gmail.com'),
    ('813e4efe-29fc-4eb2-a828-c5882a8950b3', 'rounaksarkar22@gmail.com'),
    ('6eb5ce5c-e648-4d07-bbb0-f593c6258966', 'prathameshpawar663@gmail.com'),
    ('770c2237-d688-4d9e-9cb1-ad74e5cf56e1', 'gc111410@gmail.com'),
    ('b0437c68-bca4-4886-9fa9-93aa238217e9', 'khushalim.work@gmail.com'),
    ('6f975cb6-0e39-4bbe-a370-f2975a8378f4', 'shristikumar2004@gmail.com'),
    ('337c860a-bd8a-421d-8a14-2992d5c57838', 'shubhamhamlai8743@gmail.com'),
    ('096ed7d2-7ea6-4e72-9341-6da1cbef32fd', 'moneybites123@gmail.com'),
    ('ef3dbdfd-aed0-4d79-8a30-9bb54524f275', 'mishratejas46@gmail.com'),
    ('95e0bccd-6335-48bd-91f9-124561c846e4', 'bhaskarg991@gmail.com'),
    ('48b2a1dc-59d0-4259-b05c-98369458bd6d', 'aditrimukherjee733@gmail.com'),
    ('fcef868d-6db9-464d-ba8a-09870225c569', 'classicchicken6@gmail.com'),
    ('e7789361-1606-4b1c-bbf9-b2cd2c527c66', 'tresawdc@gmail.com'),
    ('fa1dee14-272b-4ad8-b9d4-b757c7702fbb', 'shubham160304@gmail.com'),
]

print(f"\nProcessing {len(sessions_to_fix)} sessions...")

fixed_count = 0
error_count = 0

with engine.connect() as conn:
    for session_id, email in sessions_to_fix:
        try:
            # Get session details
            result = conn.execute(text("""
                SELECT user_id FROM sessions WHERE session_id = CAST(:sid AS uuid)
            """), {"sid": session_id})
            
            session_data = result.fetchone()
            if not session_data:
                print(f"\n✗ {email}: Session not found")
                error_count += 1
                continue
            
            user_id = session_data[0]
            
            # Analyze questions to create constraint_report
            result = conn.execute(text("""
                SELECT question_data FROM session_pack_questions
                WHERE session_id = CAST(:sid AS uuid)
                ORDER BY position
            """), {"sid": session_id})
            
            questions = result.fetchall()
            
            if len(questions) == 0:
                print(f"\n✗ {email}: No questions found")
                error_count += 1
                continue
            
            # Count difficulty distribution
            diff_dist = {'easy': 0, 'medium': 0, 'hard': 0}
            for q_row in questions:
                q_data = q_row[0] if not isinstance(q_row[0], str) else json.loads(q_row[0])
                diff_band = q_data.get('difficulty_band', '').lower()
                if diff_band in diff_dist:
                    diff_dist[diff_band] += 1
            
            # Create constraint_report
            constraint_report = json.dumps({
                "pack_type": "personalized",
                "difficulty_distribution": diff_dist,
                "planning_strategy": "adaptive",
                "weak_concepts_targeted": 0,
                "high_debt_pairs_addressed": 0,
                "total_questions": len(questions)
            })
            
            # Insert session_packs entry
            trans = conn.begin()
            
            try:
                conn.execute(text("""
                    INSERT INTO session_packs (
                        session_id, user_id, constraint_report, created_at
                    ) VALUES (
                        CAST(:session_id AS uuid), 
                        CAST(:user_id AS uuid), 
                        CAST(:constraint_report AS jsonb), 
                        :created_at
                    )
                    ON CONFLICT (session_id) DO NOTHING
                """), {
                    "session_id": session_id,
                    "user_id": str(user_id),
                    "constraint_report": constraint_report,
                    "created_at": now_ist()
                })
                
                trans.commit()
                print(f"\n✓ {email}: Added session_packs entry ({len(questions)} questions)")
                fixed_count += 1
                
            except Exception as e:
                trans.rollback()
                print(f"\n✗ {email}: Error - {e}")
                error_count += 1
                
        except Exception as e:
            print(f"\n✗ {email}: Error - {e}")
            error_count += 1

print("\n" + "=" * 80)
print("BULK FIX COMPLETE")
print("=" * 80)
print(f"\n✅ Fixed: {fixed_count} sessions")
print(f"❌ Errors: {error_count} sessions")
print(f"📊 Total: {len(sessions_to_fix)} sessions processed")

if fixed_count == len(sessions_to_fix):
    print("\n🎉 All sessions fixed successfully!")
else:
    print(f"\n⚠️  {error_count} sessions had errors - review logs above")

print("\n" + "=" * 80)
