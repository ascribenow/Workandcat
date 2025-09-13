#!/usr/bin/env python3
"""
Drop all deleted tables in correct order to avoid foreign key constraint violations
This script removes the 13 tables that were marked as deleted during database cleanup
"""

from database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_deleted_tables():
    """Drop all deleted tables in dependency order"""
    
    # Define deletion order to respect foreign key constraints
    deletion_order = [
        # First: Drop tables that depend on others
        'doubts_conversations',  # depends on sessions
        'plan_units',            # depends on plans  
        'diagnostic_set_questions',  # depends on diagnostic_sets
        'mastery_history',       # may depend on mastery
        'student_coverage_tracking',  # standalone
        
        # Second: Drop parent tables
        'sessions',              # now free (doubts_conversations removed)
        'plans',                 # now free (plan_units removed)
        'diagnostic_sets',       # now free (diagnostic_set_questions removed)
        'diagnostics',           # standalone
        'attempts',              # standalone  
        'mastery',               # standalone
        'type_mastery',          # standalone
        
        # Last: Self-referencing table (drop all data first)
        'topics'                 # self-referencing (parent_id)
    ]
    
    db = SessionLocal()
    dropped_tables = []
    failed_tables = []
    
    try:
        logger.info("🗑️  Starting deletion of 13 legacy tables...")
        logger.info("=" * 50)
        
        for i, table_name in enumerate(deletion_order, 1):
            try:
                logger.info(f"🔄 [{i}/13] Dropping table: {table_name}")
                
                # Check if table exists first
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name} LIMIT 1"))
                count = result.scalar()
                logger.info(f"   📊 Table has {count} rows")
                
                # Drop the table with CASCADE to handle any remaining constraints
                db.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                db.commit()
                
                # Verify it's gone
                try:
                    db.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                    logger.error(f"   ❌ Table {table_name} still exists!")
                    failed_tables.append(table_name)
                except Exception:
                    logger.info(f"   ✅ Table {table_name} successfully dropped")
                    dropped_tables.append(table_name)
                
            except Exception as e:
                logger.error(f"   ❌ Failed to drop {table_name}: {e}")
                failed_tables.append(table_name)
                # Continue with other tables
                db.rollback()
                continue
        
        logger.info("=" * 50)
        logger.info("🎉 TABLE DELETION COMPLETE!")
        logger.info(f"✅ Successfully dropped: {len(dropped_tables)} tables")
        logger.info(f"❌ Failed to drop: {len(failed_tables)} tables")
        
        if dropped_tables:
            logger.info("\nSuccessfully dropped:")
            for table in dropped_tables:
                logger.info(f"  ✅ {table}")
        
        if failed_tables:
            logger.info("\nFailed to drop:")
            for table in failed_tables:
                logger.info(f"  ❌ {table}")
        
        logger.info(f"\n📊 Database cleanup: {len(dropped_tables)}/13 tables removed")
        
        return {
            "success": len(failed_tables) == 0,
            "dropped_tables": dropped_tables,
            "failed_tables": failed_tables,
            "total_attempted": len(deletion_order)
        }
        
    except Exception as e:
        logger.error(f"❌ Critical error during table deletion: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "dropped_tables": dropped_tables,
            "failed_tables": failed_tables
        }
    finally:
        db.close()

if __name__ == "__main__":
    result = drop_deleted_tables()
    if result["success"]:
        print(f"\n🎉 SUCCESS: All {result['total_attempted']} tables deleted!")
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {len(result['dropped_tables'])}/{result['total_attempted']} tables deleted")
        if result.get("error"):
            print(f"Error: {result['error']}")