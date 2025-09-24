#!/usr/bin/env python3
"""
Validate Phase 1B Migration Completion
"""

import asyncio
import os
import asyncpg
import json
from pathlib import Path

async def validate_phase_1b():
    """Validate that Phase 1B migration completed successfully"""
    
    # Load .env
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    connection = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    
    print("🔍 PHASE 1B VALIDATION REPORT")
    print("=" * 40)
    
    # Check blueprint tables population
    blueprint_stats = await connection.fetchrow("""
        SELECT 
            (SELECT COUNT(*) FROM session_packs) as packs_count,
            (SELECT COUNT(*) FROM session_pack_questions) as questions_count,
            (SELECT COUNT(*) FROM session_answers) as answers_count,
            (SELECT COUNT(*) FROM advisory_locks) as locks_count
    """)
    
    print(f"📊 Blueprint Data Population:")
    print(f"   session_packs: {blueprint_stats['packs_count']}")
    print(f"   session_pack_questions: {blueprint_stats['questions_count']}")
    print(f"   session_answers: {blueprint_stats['answers_count']}")
    print(f"   advisory_locks: {blueprint_stats['locks_count']}")
    
    # Validate position constraints (Deviation #2)
    if blueprint_stats['questions_count'] > 0:
        position_validation = await connection.fetchrow("""
            SELECT 
                MIN(position) as min_pos,
                MAX(position) as max_pos,
                COUNT(DISTINCT position) as unique_positions
            FROM session_pack_questions
        """)
        
        print(f"\n✅ Position Validation (Deviation #2):")
        print(f"   Position range: {position_validation['min_pos']} to {position_validation['max_pos']}")
        print(f"   Unique positions: {position_validation['unique_positions']}")
        
        if position_validation['min_pos'] == 1 and position_validation['max_pos'] <= 12:
            print("   ✅ Position constraints compliant (1-based positions)")
        else:
            print("   ❌ Position constraints invalid")
    
    # Validate idempotency constraints (Deviation #4)
    print(f"\n🔒 Idempotency Validation (Deviation #4):")
    
    # Check unique constraints exist
    unique_constraints = await connection.fetch("""
        SELECT 
            tc.constraint_name,
            tc.table_name
        FROM information_schema.table_constraints tc
        WHERE tc.table_schema = 'public'
        AND tc.constraint_type = 'UNIQUE'
        AND tc.table_name IN ('session_pack_questions', 'session_answers')
    """)
    
    constraint_tables = [c['table_name'] for c in unique_constraints]
    
    if 'session_pack_questions' in constraint_tables:
        print("   ✅ session_pack_questions has unique constraint")
    else:
        print("   ❌ session_pack_questions missing unique constraint")
    
    if 'session_answers' in constraint_tables:
        print("   ✅ session_answers has unique constraint")
    else:
        print("   ❌ session_answers missing unique constraint")
    
    # Validate pack completeness
    if blueprint_stats['packs_count'] > 0:
        pack_completeness = await connection.fetch("""
            SELECT 
                session_id,
                (SELECT COUNT(*) FROM session_pack_questions spq WHERE spq.session_id = sp.session_id) as question_count
            FROM session_packs sp
        """)
        
        complete_packs = [p for p in pack_completeness if p['question_count'] == 12]
        incomplete_packs = [p for p in pack_completeness if p['question_count'] != 12]
        
        print(f"\n📦 Pack Completeness:")
        print(f"   Complete packs (12 questions): {len(complete_packs)}")
        print(f"   Incomplete packs: {len(incomplete_packs)}")
        
        if incomplete_packs:
            print(f"   Sample incomplete pack question counts: {[p['question_count'] for p in incomplete_packs[:3]]}")
    
    # Validate constraint reports (Deviation #7)
    if blueprint_stats['packs_count'] > 0:
        constraint_reports = await connection.fetchval("""
            SELECT COUNT(*) 
            FROM session_packs 
            WHERE constraint_report IS NOT NULL 
            AND constraint_report != '{}'
        """)
        
        print(f"\n📋 Constraint Reports (Deviation #7):")
        print(f"   Packs with constraint reports: {constraint_reports}/{blueprint_stats['packs_count']}")
        
        if constraint_reports > 0:
            sample_report = await connection.fetchval("""
                SELECT constraint_report 
                FROM session_packs 
                WHERE constraint_report IS NOT NULL 
                LIMIT 1
            """)
            
            if isinstance(sample_report, dict):
                print(f"   Sample report keys: {list(sample_report.keys())}")
            else:
                print(f"   Sample report type: {type(sample_report)}")
    
    # Validate advisory lock system (Deviation #3)
    advisory_functions = await connection.fetch("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name LIKE '%advisory_lock%'
    """)
    
    print(f"\n🔐 Advisory Lock System (Deviation #3):")
    print(f"   Functions available: {len(advisory_functions)}")
    for func in advisory_functions:
        print(f"      {func['routine_name']}")
    
    # Overall Phase 1B assessment
    print(f"\n🎯 PHASE 1B ASSESSMENT:")
    
    checks_passed = 0
    total_checks = 6
    
    # Check 1: Blueprint tables populated
    if blueprint_stats['packs_count'] > 0 and blueprint_stats['questions_count'] > 0:
        print("   ✅ Blueprint tables populated")
        checks_passed += 1
    else:
        print("   ❌ Blueprint tables empty")
    
    # Check 2: Position constraints
    if blueprint_stats['questions_count'] > 0:
        pos_valid = position_validation['min_pos'] == 1 and position_validation['max_pos'] <= 12
        if pos_valid:
            print("   ✅ Position constraints valid")
            checks_passed += 1
        else:
            print("   ❌ Position constraints invalid")
    else:
        print("   ⏭️ Position constraints (no data to check)")
    
    # Check 3: Unique constraints
    if len(constraint_tables) >= 2:
        print("   ✅ Idempotency constraints in place")
        checks_passed += 1
    else:
        print("   ❌ Missing idempotency constraints")
    
    # Check 4: Pack completeness
    if blueprint_stats['packs_count'] > 0 and len(complete_packs) > 0:
        print("   ✅ Complete packs available")
        checks_passed += 1
    else:
        print("   ⚠️ No complete packs found")
    
    # Check 5: Constraint reports
    if constraint_reports > 0:
        print("   ✅ Constraint reports present")
        checks_passed += 1
    else:
        print("   ⚠️ No constraint reports")
    
    # Check 6: Advisory locks
    if len(advisory_functions) >= 2:
        print("   ✅ Advisory lock system ready")
        checks_passed += 1
    else:
        print("   ❌ Advisory lock system incomplete")
    
    success_rate = (checks_passed / total_checks) * 100
    
    print(f"\n📈 Phase 1B Success Rate: {success_rate:.1f}% ({checks_passed}/{total_checks})")
    
    if success_rate >= 80:
        print("🎉 PHASE 1B: COMPLETED SUCCESSFULLY")
        phase_1b_status = "COMPLETED"
    elif success_rate >= 60:
        print("⚠️ PHASE 1B: MOSTLY COMPLETE (minor issues)")
        phase_1b_status = "MOSTLY_COMPLETE"
    else:
        print("❌ PHASE 1B: INCOMPLETE")
        phase_1b_status = "INCOMPLETE"
    
    await connection.close()
    
    return {
        "status": phase_1b_status,
        "success_rate": success_rate,
        "packs_count": blueprint_stats['packs_count'],
        "questions_count": blueprint_stats['questions_count'],
        "complete_packs": len(complete_packs) if blueprint_stats['packs_count'] > 0 else 0
    }

if __name__ == "__main__":
    result = asyncio.run(validate_phase_1b())
    print(f"\nValidation Result: {json.dumps(result, indent=2)}")