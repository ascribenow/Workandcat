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
    
    # Tables that still need to be dropped (after first run)
    remaining_tables = [
        'doubts_conversations',
        'diagnostic_set_questions', 
        'student_coverage_tracking',
        'plans',
        'diagnostics', 
        'mastery',
        'topics'
    ]
    
    dropped_tables = []
    failed_tables = []
    
    logger.info("🗑️  Continuing deletion of remaining legacy tables...")
    logger.info("=" * 50)
    
    # Process each table in its own transaction
    for i, table_name in enumerate(remaining_tables, 1):
        db = SessionLocal()  # New connection for each table
        try:
            logger.info(f"🔄 [{i}/{len(remaining_tables)}] Dropping table: {table_name}")
            
            # Check if table exists first
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name} LIMIT 1"))
                count = result.scalar()
                logger.info(f"   📊 Table has {count} rows")
            except Exception as e:
                if "does not exist" in str(e):
                    logger.info(f"   ✅ Table {table_name} already deleted")
                    dropped_tables.append(table_name)
                    continue
                else:
                    raise e
            
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
            db.rollback()
        finally:
            db.close()
    
    logger.info("=" * 50)
    logger.info("🎉 REMAINING TABLE DELETION COMPLETE!")
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
    
    total_dropped = 6 + len(dropped_tables)  # Previous run + this run
    logger.info(f"\n📊 Total database cleanup: {total_dropped}/13 tables removed")
    
    return {
        "success": len(failed_tables) == 0,
        "dropped_tables": dropped_tables,
        "failed_tables": failed_tables,
        "total_attempted": len(remaining_tables)
    }

if __name__ == "__main__":
    result = drop_deleted_tables()
    if result["success"]:
        print(f"\n🎉 SUCCESS: All {result['total_attempted']} tables deleted!")
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {len(result['dropped_tables'])}/{result['total_attempted']} tables deleted")
        if result.get("error"):
            print(f"Error: {result['error']}")