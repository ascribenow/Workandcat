#!/usr/bin/env python3
"""
Fix Live Database Schema for OPTION 2 Enhanced Processing
Directly updates the SQLite database file used by the backend service
"""

import sqlite3
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_live_database_schema():
    """
    Directly update the live SQLite database with required OPTION 2 columns
    """
    try:
        # Connect to the actual database file used by the backend
        db_path = "/app/backend/cat_preparation.db"
        
        if not os.path.exists(db_path):
            logger.error(f"❌ Database file not found: {db_path}")
            return False
        
        logger.info(f"🔧 Connecting to live database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(questions)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"📋 Current columns: {len(existing_columns)} found")
        
        # List of required OPTION 2 columns
        required_columns = [
            ("pyq_frequency_score", "DECIMAL(5,4) DEFAULT 0.5"),
            ("pyq_conceptual_matches", "INTEGER DEFAULT 0"),
            ("total_pyq_analyzed", "INTEGER DEFAULT 0"),
            ("top_matching_concepts", "TEXT DEFAULT '[]'"),
            ("frequency_analysis_method", "VARCHAR(50) DEFAULT 'subcategory'"),
            ("frequency_last_updated", "DATETIME"),
            ("pattern_keywords", "TEXT DEFAULT '[]'"),
            ("pattern_solution_approach", "TEXT"),
            ("pyq_occurrences_last_10_years", "INTEGER DEFAULT 0"),
            ("total_pyq_count", "INTEGER DEFAULT 0")
        ]
        
        # Add missing columns
        columns_added = 0
        for column_name, column_definition in required_columns:
            if column_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE questions ADD COLUMN {column_name} {column_definition}"
                    cursor.execute(alter_sql)
                    logger.info(f"   ✅ Added column: {column_name}")
                    columns_added += 1
                except Exception as e:
                    logger.error(f"   ❌ Failed to add {column_name}: {e}")
            else:
                logger.info(f"   ✅ Column exists: {column_name}")
        
        # Commit changes
        conn.commit()
        
        # Update existing questions with estimated PYQ frequency scores
        logger.info("🔄 Updating existing questions with PYQ frequency estimates...")
        
        # High frequency subcategories (CAT pattern-based)
        high_freq_categories = [
            'Time–Speed–Distance (TSD)',
            'Percentages', 
            'Profit–Loss–Discount (PLD)',
            'Linear Equations',
            'Triangles',
            'Divisibility',
            'Permutation–Combination (P&C)'
        ]
        
        # Update high frequency questions
        for category in high_freq_categories:
            cursor.execute("""
                UPDATE questions 
                SET pyq_frequency_score = 0.8,
                    frequency_analysis_method = 'estimated_high_frequency'
                WHERE subcategory = ? AND pyq_frequency_score = 0.5
            """, (category,))
        
        high_updated = cursor.rowcount
        
        # Medium frequency subcategories
        medium_freq_categories = [
            'Time & Work',
            'Ratio–Proportion–Variation',
            'Averages & Alligation',
            'Simple & Compound Interest (SI–CI)',
            'Quadratic Equations',
            'Circles',
            'HCF–LCM',
            'Probability'
        ]
        
        # Update medium frequency questions
        for category in medium_freq_categories:
            cursor.execute("""
                UPDATE questions 
                SET pyq_frequency_score = 0.6,
                    frequency_analysis_method = 'estimated_medium_frequency'
                WHERE subcategory = ? AND pyq_frequency_score = 0.5
            """, (category,))
        
        medium_updated = cursor.rowcount
        
        # Update analysis timestamp
        cursor.execute("""
            UPDATE questions 
            SET frequency_last_updated = datetime('now')
            WHERE frequency_analysis_method IN ('estimated_high_frequency', 'estimated_medium_frequency')
        """)
        
        # Commit all updates
        conn.commit()
        
        # Get final statistics
        cursor.execute("SELECT COUNT(*) FROM questions WHERE is_active = 1")
        total_questions = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN pyq_frequency_score >= 0.7 THEN 'High (≥0.7)'
                    WHEN pyq_frequency_score >= 0.4 THEN 'Medium (0.4-0.7)'
                    ELSE 'Low (<0.4)'
                END as frequency_band,
                COUNT(*) as count
            FROM questions 
            WHERE is_active = 1
            GROUP BY 
                CASE 
                    WHEN pyq_frequency_score >= 0.7 THEN 'High (≥0.7)'
                    WHEN pyq_frequency_score >= 0.4 THEN 'Medium (0.4-0.7)'
                    ELSE 'Low (<0.4)'
                END
            ORDER BY count DESC
        """)
        
        distribution = cursor.fetchall()
        
        conn.close()
        
        logger.info("🎉 Live database schema update completed!")
        logger.info(f"   📊 Columns added: {columns_added}")
        logger.info(f"   📊 High frequency updated: {high_updated}")
        logger.info(f"   📊 Medium frequency updated: {medium_updated}")
        logger.info(f"   📊 Total active questions: {total_questions}")
        
        logger.info("📈 PYQ Frequency Distribution:")
        for band, count in distribution:
            logger.info(f"   {band}: {count} questions")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix live database schema: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 FIXING LIVE DATABASE SCHEMA FOR OPTION 2")
    logger.info("=" * 60)
    
    success = fix_live_database_schema()
    
    if success:
        print("\n✅ LIVE DATABASE SCHEMA FIX COMPLETED!")
        print("🔄 The backend service needs to be restarted to pick up schema changes.")
        print("🎯 OPTION 2 Enhanced Background Processing is now ready!")
    else:
        print("\n❌ LIVE DATABASE SCHEMA FIX FAILED!")
        sys.exit(1)