#!/usr/bin/env python3
"""
Diagnostic Database Queries for Adaptive Gates and Constraint Failures
Step 3 & 7 from Diagnostic Runbook
"""

import os
import sys
from database import SessionLocal
from sqlalchemy import text
import json

def run_diagnostic_queries():
    """Run the specific database queries requested in the review"""
    
    print("🔍 STEP 3 & 7 DIAGNOSTIC RUNBOOK: Adaptive Gates and Constraint Failures")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # 1. User Adaptive Settings
        print("\n1. USER ADAPTIVE SETTINGS:")
        print("-" * 40)
        
        user_query = text("""
            SELECT id, email, adaptive_enabled 
            FROM users 
            WHERE email = 'sp@theskinmantra.com'
        """)
        
        user_result = db.execute(user_query).fetchone()
        if user_result:
            print(f"✅ User found:")
            print(f"   ID: {user_result.id}")
            print(f"   Email: {user_result.email}")
            print(f"   Adaptive Enabled: {user_result.adaptive_enabled}")
            user_id = user_result.id
        else:
            print("❌ User not found!")
            return
        
        # 2. Recent Session Pack Plans
        print("\n2. RECENT SESSION PACK PLANS:")
        print("-" * 40)
        
        session_query = text("""
            SELECT user_id, session_id, status, created_at, served_at, completed_at,
                   jsonb_array_length(pack) AS pack_count,
                   pack->0->>'difficulty_band' as first_difficulty,
                   pack->0->>'pyq_frequency_score' as first_pyq_score
            FROM session_pack_plan 
            WHERE user_id = :user_id
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        session_results = db.execute(session_query, {'user_id': user_id}).fetchall()
        if session_results:
            print(f"✅ Found {len(session_results)} session pack plans:")
            for i, row in enumerate(session_results, 1):
                print(f"   {i}. Session ID: {row.session_id[:12]}...")
                print(f"      Status: {row.status}")
                print(f"      Created: {row.created_at}")
                print(f"      Served: {row.served_at}")
                print(f"      Completed: {row.completed_at}")
                print(f"      Pack Count: {row.pack_count}")
                print(f"      First Difficulty: {row.first_difficulty}")
                print(f"      First PYQ Score: {row.first_pyq_score}")
                print()
        else:
            print("❌ No session pack plans found for this user!")
            print("   This explains the 404 errors - no packs exist to fetch!")
        
        # 3. Sessions Table Check
        print("\n3. SESSIONS TABLE CHECK:")
        print("-" * 40)
        
        sessions_query = text("""
            SELECT session_id, sess_seq, status, created_at, served_at
            FROM sessions
            WHERE user_id = :user_id
            ORDER BY sess_seq DESC
            LIMIT 5
        """)
        
        sessions_results = db.execute(sessions_query, {'user_id': user_id}).fetchall()
        if sessions_results:
            print(f"✅ Found {len(sessions_results)} sessions:")
            for i, row in enumerate(sessions_results, 1):
                print(f"   {i}. Session ID: {row.session_id[:12]}...")
                print(f"      Sess Seq: {row.sess_seq}")
                print(f"      Status: {row.status}")
                print(f"      Created: {row.created_at}")
                print(f"      Served: {row.served_at}")
                print()
        else:
            print("❌ No sessions found for this user!")
        
        # 4. Constraint Analysis (if packs exist)
        if session_results:
            print("\n4. CONSTRAINT ANALYSIS (Latest Pack):")
            print("-" * 40)
            
            constraint_query = text("""
                SELECT sess_seq, status, jsonb_array_length(pack) AS n,
                       COUNT(*) FILTER (WHERE (elem->>'difficulty_band')='Easy')  AS e3,
                       COUNT(*) FILTER (WHERE (elem->>'difficulty_band')='Medium') AS m6,
                       COUNT(*) FILTER (WHERE (elem->>'difficulty_band')='Hard')   AS h3,
                       COUNT(*) FILTER (WHERE (elem->>'pyq_frequency_score')='1.5') AS pyq15,
                       COUNT(*) FILTER (WHERE (elem->>'pyq_frequency_score')='1.0') AS pyq10
                FROM (
                  SELECT 1 as sess_seq, status, pack as pack_json, jsonb_path_query(pack, '$[*]') AS elem
                  FROM session_pack_plan
                  WHERE user_id = :user_id
                  ORDER BY created_at DESC
                  LIMIT 1
                ) t
                GROUP BY sess_seq, status, pack_json
            """)
            
            constraint_results = db.execute(constraint_query, {'user_id': user_id}).fetchall()
            if constraint_results:
                for row in constraint_results:
                    print(f"✅ Latest pack constraint analysis:")
                    print(f"   Status: {row.status}")
                    print(f"   Total Questions (n): {row.n}")
                    print(f"   Easy Questions (e3): {row.e3}")
                    print(f"   Medium Questions (m6): {row.m6}")
                    print(f"   Hard Questions (h3): {row.h3}")
                    print(f"   PYQ Score 1.5 (pyq15): {row.pyq15}")
                    print(f"   PYQ Score 1.0 (pyq10): {row.pyq10}")
                    
                    # Check constraint violations
                    violations = []
                    if row.n != 12:
                        violations.append(f"Total questions should be 12, got {row.n}")
                    if row.e3 != 3:
                        violations.append(f"Easy questions should be 3, got {row.e3}")
                    if row.m6 != 6:
                        violations.append(f"Medium questions should be 6, got {row.m6}")
                    if row.h3 != 3:
                        violations.append(f"Hard questions should be 3, got {row.h3}")
                    
                    if violations:
                        print(f"   ❌ CONSTRAINT VIOLATIONS:")
                        for violation in violations:
                            print(f"      - {violation}")
                    else:
                        print(f"   ✅ All constraints satisfied")
            else:
                print("❌ Could not analyze constraints - no pack data")
        
        # 5. Check for any attempt_events
        print("\n5. ATTEMPT EVENTS CHECK:")
        print("-" * 40)
        
        attempts_query = text("""
            SELECT COUNT(*) as attempt_count
            FROM attempt_events
            WHERE user_id = :user_id
        """)
        
        attempts_result = db.execute(attempts_query, {'user_id': user_id}).fetchone()
        if attempts_result:
            print(f"✅ Found {attempts_result.attempt_count} attempt events for this user")
        else:
            print("❌ No attempt events found")
        
        # 6. Check database table existence
        print("\n6. DATABASE SCHEMA CHECK:")
        print("-" * 40)
        
        tables_to_check = ['users', 'sessions', 'session_pack_plan', 'attempt_events']
        for table in tables_to_check:
            try:
                count_query = text(f"SELECT COUNT(*) as count FROM {table}")
                result = db.execute(count_query).fetchone()
                print(f"✅ Table '{table}' exists with {result.count} records")
            except Exception as e:
                print(f"❌ Table '{table}' error: {e}")
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_diagnostic_queries()