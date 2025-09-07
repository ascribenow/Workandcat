"""
Database migration to add idempotency constraints for payment security
Prevents duplicate payment processing and ensures data integrity
"""

import sys
import os
sys.path.append('/app/backend')

from database import get_database, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_payment_idempotency_constraints():
    """
    Add unique constraints to prevent duplicate payment processing
    CRITICAL for payment system integrity
    """
    try:
        db = get_database()
        
        logger.info("🔒 ADDING PAYMENT IDEMPOTENCY CONSTRAINTS")
        logger.info("=" * 60)
        
        # Add unique constraint on razorpay_payment_id to prevent duplicate payment processing
        logger.info("Adding unique constraint on payment_transactions.razorpay_payment_id...")
        try:
            db.execute(text("""
                ALTER TABLE payment_transactions 
                ADD CONSTRAINT unique_razorpay_payment_id 
                UNIQUE (razorpay_payment_id)
            """))
            logger.info("✅ Successfully added unique constraint on razorpay_payment_id")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info("✅ Unique constraint on razorpay_payment_id already exists")
            else:
                logger.error(f"❌ Failed to add unique constraint on razorpay_payment_id: {e}")
                raise
        
        # Add unique constraint on razorpay_order_id to prevent duplicate order processing
        logger.info("Adding unique constraint on payment_orders.razorpay_order_id...")
        try:
            db.execute(text("""
                ALTER TABLE payment_orders
                ADD CONSTRAINT unique_razorpay_order_id
                UNIQUE (razorpay_order_id)
            """))
            logger.info("✅ Successfully added unique constraint on razorpay_order_id")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info("✅ Unique constraint on razorpay_order_id already exists")
            else:
                logger.error(f"❌ Failed to add unique constraint on razorpay_order_id: {e}")
                raise
        
        # Add index on payment_transactions.created_at for reconciliation queries
        logger.info("Adding index on payment_transactions.created_at for performance...")
        try:
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at 
                ON payment_transactions(created_at)
            """))
            logger.info("✅ Successfully added performance index")
        except Exception as e:
            logger.error(f"❌ Failed to add performance index: {e}")
            raise
        
        # Add index on subscriptions.status for faster queries
        logger.info("Adding index on subscriptions.status for performance...")
        try:
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_subscriptions_status 
                ON subscriptions(status)
            """))
            logger.info("✅ Successfully added subscription status index")
        except Exception as e:
            logger.error(f"❌ Failed to add subscription status index: {e}")
            raise
        
        # Commit all changes
        db.commit()
        
        logger.info("🎉 PAYMENT IDEMPOTENCY CONSTRAINTS SUCCESSFULLY ADDED")
        logger.info("✅ Payment system now protected against duplicate processing")
        logger.info("✅ Database integrity constraints in place")
        logger.info("✅ Performance indexes added for reconciliation")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Failed to add payment idempotency constraints: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = add_payment_idempotency_constraints()
    if success:
        print("✅ Payment idempotency constraints migration completed successfully")
    else:
        print("❌ Payment idempotency constraints migration failed")
        sys.exit(1)