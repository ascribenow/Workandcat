#!/usr/bin/env python3
"""
Database inspection to understand the plan-next → pack fetch issue
"""

import sys
sys.path.append('/app/backend')

from database import SessionLocal
from sqlalchemy import text
import json

def inspect_database():
    print("🗄️ DATABASE INSPECTION: Understanding plan-next → pack fetch issue")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Check recent session_pack_plan records
        print("\n📋 Step 1: Recent session_pack_plan records")
        result = db.execute(text("""
            SELECT user_id, session_id, status, created_at, cold_start_mode, planning_strategy
            FROM session_pack_plan 
            WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
            ORDER BY created_at DESC 
            LIMIT 10
        """)).fetchall()
        
        if result:
            print(f"   ✅ Found {len(result)} session pack plans for user")
            for row in result:
                print(f"   📊 Session: {row.session_id[:8]}... | Status: {row.status} | Created: {row.created_at} | Strategy: {row.planning_strategy}")
        else:
            print(f"   ❌ No session pack plans found for user")
        
        # Check recent sessions table records
        print("\n📋 Step 2: Recent sessions table records")
        result = db.execute(text("""
            SELECT user_id, session_id, sess_seq, status, created_at
            FROM sessions 
            WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
            ORDER BY created_at DESC 
            LIMIT 10
        """)).fetchall()
        
        if result:
            print(f"   ✅ Found {len(result)} sessions for user")
            for row in result:
                print(f"   📊 Session: {row.session_id[:8]}... | Seq: {row.sess_seq} | Status: {row.status} | Created: {row.created_at}")
        else:
            print(f"   ❌ No sessions found for user")
        
        # Check for specific session IDs from logs
        print("\n📋 Step 3: Check specific session IDs from logs")
        test_sessions = [
            "7409bbc3-d8a3-4d9e-8337-f37685d60d58",  # This one returned 200 OK in logs
            "ac23d01f-e829-4191-bb18-8e72d3ce345d"   # This one returned 404 in logs
        ]
        
        for session_id in test_sessions:
            print(f"\n   🔍 Checking session: {session_id}")
            
            # Check session_pack_plan
            pack_result = db.execute(text("""
                SELECT user_id, session_id, status, created_at, pack
                FROM session_pack_plan 
                WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1' 
                AND session_id = :session_id
            """), {'session_id': session_id}).fetchone()
            
            if pack_result:
                pack_data = pack_result.pack
                if isinstance(pack_data, str):
                    try:
                        pack_json = json.loads(pack_data)
                        pack_size = len(pack_json) if isinstance(pack_json, list) else 0
                    except:
                        pack_size = "invalid_json"
                else:
                    pack_size = len(pack_data) if isinstance(pack_data, list) else 0
                
                print(f"     ✅ Found in session_pack_plan: Status={pack_result.status}, Pack size={pack_size}")
            else:
                print(f"     ❌ NOT found in session_pack_plan")
            
            # Check sessions table
            session_result = db.execute(text("""
                SELECT user_id, session_id, sess_seq, status
                FROM sessions 
                WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1' 
                AND session_id = :session_id
            """), {'session_id': session_id}).fetchone()
            
            if session_result:
                print(f"     ✅ Found in sessions: Seq={session_result.sess_seq}, Status={session_result.status}")
            else:
                print(f"     ❌ NOT found in sessions table")
        
        # Check for any session ID length issues
        print("\n📋 Step 4: Check session ID lengths")
        result = db.execute(text("""
            SELECT session_id, LENGTH(session_id) as id_length
            FROM session_pack_plan 
            WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
            ORDER BY created_at DESC 
            LIMIT 5
        """)).fetchall()
        
        if result:
            print(f"   📊 Session ID lengths:")
            for row in result:
                print(f"     {row.session_id[:8]}... | Length: {row.id_length}")
        
        # Check database schema for session_id column
        print("\n📋 Step 5: Check session_id column constraints")
        result = db.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'session_pack_plan' 
            AND column_name = 'session_id'
        """)).fetchone()
        
        if result:
            print(f"   📊 session_pack_plan.session_id: Type={result.data_type}, Max length={result.character_maximum_length}")
        
        result = db.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'sessions' 
            AND column_name = 'session_id'
        """)).fetchone()
        
        if result:
            print(f"   📊 sessions.session_id: Type={result.data_type}, Max length={result.character_maximum_length}")
        
    except Exception as e:
        print(f"❌ Database inspection error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_database()