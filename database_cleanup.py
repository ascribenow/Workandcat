#!/usr/bin/env python3
"""
Database Cleanup: Remove Legacy Data from Adaptive-Only System
"""

import os
import sys
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database import SessionLocal

load_dotenv('/app/backend/.env')

def cleanup_legacy_database_data():
    """Remove legacy data that's no longer needed in adaptive-only system"""
    
    print("🧹 DATABASE CLEANUP - Legacy Data Removal")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Remove deprecated columns that might exist
        print("\n📋 PHASE 1: Checking for deprecated columns...")
        
        # Check what tables and columns exist
        result = db.execute(text("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND (column_name LIKE '%legacy%' OR column_name LIKE '%non_adaptive%')
            ORDER BY table_name, column_name
        """))
        deprecated_columns = result.fetchall()
        
        if deprecated_columns:
            print(f"   ⚠️ Found {len(deprecated_columns)} potentially deprecated columns:")
            for row in deprecated_columns:
                print(f"     - {row.table_name}.{row.column_name}")
        else:
            print("   ✅ No deprecated columns found")
        
        # 2. Clean up any session data that references legacy endpoints
        print("\n🗂️ PHASE 2: Cleaning session-related legacy data...")
        
        # Count sessions with potentially legacy data
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM sessions s
            WHERE s.status NOT IN ('planned', 'served', 'completed')
        """))
        row = result.fetchone()
        legacy_sessions = row.count if row else 0
        
        if legacy_sessions > 0:
            print(f"   🔄 Found {legacy_sessions} sessions with non-standard status")
            # Could clean these up if needed
        else:
            print("   ✅ All sessions have standard status values")
        
        # 3. Check for unused pack data
        print("\n📦 PHASE 3: Analyzing pack data efficiency...")
        
        result = db.execute(text("""
            SELECT 
                status,
                COUNT(*) as count,
                ROUND(AVG(LENGTH(pack_json::text))) as avg_pack_size
            FROM session_pack_plan 
            GROUP BY status
            ORDER BY count DESC
        """))
        pack_stats = result.fetchall()
        
        print("   📊 Pack data distribution:")
        total_packs = 0
        for row in pack_stats:
            print(f"     - {row.status}: {row.count} packs (avg size: {row.avg_pack_size} bytes)")
            total_packs += row.count
        
        # 4. Analyze question data for optimization
        print("\n❓ PHASE 4: Analyzing question data...")
        
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_questions,
                COUNT(CASE WHEN mcq_options IS NOT NULL THEN 1 END) as questions_with_options,
                COUNT(CASE WHEN is_active = true THEN 1 END) as active_questions,
                ROUND(AVG(LENGTH(mcq_options))) as avg_option_size
            FROM questions
        """))
        question_stats = result.fetchone()
        
        print(f"   📊 Question statistics:")
        print(f"     - Total questions: {question_stats.total_questions}")
        print(f"     - With MCQ options: {question_stats.questions_with_options}")
        print(f"     - Active questions: {question_stats.active_questions}")
        print(f"     - Avg option size: {question_stats.avg_option_size} bytes")
        
        # 5. Check for orphaned data
        print("\n🔍 PHASE 5: Checking for orphaned data...")
        
        # Check for attempt_events without corresponding sessions
        result = db.execute(text("""
            SELECT COUNT(*) as orphaned_attempts
            FROM attempt_events ae
            LEFT JOIN sessions s ON ae.session_id = s.session_id
            WHERE s.session_id IS NULL
        """))
        row = result.fetchone()
        orphaned_attempts = row.orphaned_attempts if row else 0
        
        if orphaned_attempts > 0:
            print(f"   ⚠️ Found {orphaned_attempts} orphaned attempt_events")
        else:
            print("   ✅ No orphaned attempt_events found")
        
        # 6. Database size analysis
        print("\n💾 PHASE 6: Database size analysis...")
        
        result = db.execute(text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10
        """))
        
        table_sizes = result.fetchall()
        print("   📊 Largest tables:")
        for row in table_sizes:
            print(f"     - {row.tablename}: {row.size}")
        
        print("\n" + "=" * 60)
        print("🎯 CLEANUP RECOMMENDATIONS:")
        
        recommendations = []
        
        if orphaned_attempts > 0:
            recommendations.append(f"• Clean up {orphaned_attempts} orphaned attempt_events")
        
        if legacy_sessions > 0:
            recommendations.append(f"• Review {legacy_sessions} sessions with non-standard status")
        
        # Performance recommendations
        total_questions_active = question_stats.active_questions
        total_questions_all = question_stats.total_questions
        inactive_questions = total_questions_all - total_questions_active
        
        if inactive_questions > 0:
            recommendations.append(f"• Consider archiving {inactive_questions} inactive questions")
        
        if len(recommendations) == 0:
            print("✅ Database is clean and optimized!")
        else:
            print(f"Found {len(recommendations)} optimization opportunities:")
            for rec in recommendations:
                print(f"   {rec}")
        
    except Exception as e:
        print(f"❌ Error during cleanup analysis: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_legacy_database_data()