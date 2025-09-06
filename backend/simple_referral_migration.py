"""
Simple migration script for referral system
"""

from sqlalchemy import text
from database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_referral_table():
    db = SessionLocal()
    try:
        logger.info("Creating referral_usage table...")
        
        # Simple table creation
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS referral_usage (
            id VARCHAR(36) PRIMARY KEY,
            referral_code VARCHAR(6) NOT NULL,
            used_by_user_id VARCHAR(36),
            used_by_email VARCHAR(255) NOT NULL,
            discount_amount INTEGER NOT NULL DEFAULT 500,
            subscription_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
        
        db.execute(text(create_table_sql))
        db.commit()
        logger.info("✅ Successfully created referral_usage table")
        
        # Add foreign key constraint separately
        try:
            fk_sql = """
            ALTER TABLE referral_usage 
            ADD CONSTRAINT fk_referral_usage_user 
            FOREIGN KEY (used_by_user_id) REFERENCES users(id) ON DELETE CASCADE;
            """
            db.execute(text(fk_sql))
            db.commit()
            logger.info("✅ Added foreign key constraint")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⚠️ Foreign key constraint already exists")
            else:
                logger.warning(f"Foreign key creation failed: {e}")
                db.rollback()
        
        # Add unique constraint
        try:
            unique_sql = """
            ALTER TABLE referral_usage 
            ADD CONSTRAINT unique_email_referral 
            UNIQUE (used_by_email, referral_code);
            """
            db.execute(text(unique_sql))
            db.commit()
            logger.info("✅ Added unique constraint")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⚠️ Unique constraint already exists")
            else:
                logger.warning(f"Unique constraint creation failed: {e}")
                db.rollback()
        
        logger.info("🎉 Referral system migration completed!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_referral_table()