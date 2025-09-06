"""
Migration script to add referral system to the database
Adds referral_code field to Users table and creates ReferralUsage table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from sqlalchemy import text
from database import SessionLocal, engine
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_referral_system():
    """Add referral system tables and fields"""
    
    db = SessionLocal()
    try:
        logger.info("🔄 Starting referral system migration...")
        
        # 1. Add referral_code field to users table
        logger.info("Adding referral_code field to users table...")
        add_referral_code_query = """
        ALTER TABLE users 
        ADD COLUMN referral_code VARCHAR(6) UNIQUE;
        """
        
        try:
            db.execute(text(add_referral_code_query))
            db.commit()
            logger.info("✅ Added referral_code field to users table")
        except Exception as e:
            db.rollback()  # Rollback transaction on error
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info("⚠️ referral_code field already exists in users table")
            else:
                logger.error(f"❌ Error adding referral_code field: {e}")
                raise
        
        # 2. Create ReferralUsage table
        logger.info("Creating referral_usage table...")
        create_referral_usage_query = """
        CREATE TABLE IF NOT EXISTS referral_usage (
            id VARCHAR(36) PRIMARY KEY DEFAULT (gen_random_uuid()::text),
            referral_code VARCHAR(6) NOT NULL,
            used_by_user_id VARCHAR(36),
            used_by_email VARCHAR(255) NOT NULL,
            discount_amount INTEGER NOT NULL DEFAULT 500,
            subscription_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            
            FOREIGN KEY (used_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(used_by_email, referral_code)  -- Ensure one referral per email
        );
        """
        
        try:
            db.execute(text(create_referral_usage_query))
            db.commit()
            logger.info("✅ Created referral_usage table")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⚠️ referral_usage table already exists")
            else:
                logger.error(f"❌ Error creating referral_usage table: {e}")
                raise
        
        # 3. Create indexes for performance
        logger.info("Creating indexes for referral system...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_referral_usage_code ON referral_usage(referral_code);",
            "CREATE INDEX IF NOT EXISTS idx_referral_usage_email ON referral_usage(used_by_email);",
            "CREATE INDEX IF NOT EXISTS idx_referral_usage_user ON referral_usage(used_by_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);"
        ]
        
        for index_query in indexes:
            try:
                db.execute(text(index_query))
                db.commit()
                logger.info(f"✅ Created index: {index_query.split('idx_')[1].split(' ')[0] if 'idx_' in index_query else 'unknown'}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"⚠️ Index already exists: {index_query}")
                else:
                    logger.error(f"❌ Error creating index: {e}")
        
        # 4. Verify the migration
        logger.info("Verifying referral system migration...")
        
        # Check if referral_code column exists
        check_column_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'referral_code';
        """
        result = db.execute(text(check_column_query)).fetchone()
        if result:
            logger.info("✅ referral_code column verified in users table")
        else:
            logger.error("❌ referral_code column not found in users table")
        
        # Check if referral_usage table exists
        check_table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'referral_usage';
        """
        result = db.execute(text(check_table_query)).fetchone()
        if result:
            logger.info("✅ referral_usage table verified")
        else:
            logger.error("❌ referral_usage table not found")
        
        logger.info("🎉 Referral system migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(add_referral_system())