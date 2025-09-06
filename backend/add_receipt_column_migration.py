"""
Migration script to add missing 'receipt' column to payment_orders table
This column is required by the payment service but missing from the database schema
"""

from sqlalchemy import text
from database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_receipt_column():
    """Add receipt column to payment_orders table"""
    
    db = SessionLocal()
    try:
        logger.info("🔄 Adding receipt column to payment_orders table...")
        
        # Add receipt column as nullable VARCHAR(255)
        add_column_query = """
        ALTER TABLE payment_orders 
        ADD COLUMN IF NOT EXISTS receipt VARCHAR(255);
        """
        
        db.execute(text(add_column_query))
        db.commit()
        logger.info("✅ Successfully added receipt column to payment_orders table")
        
        # Verify the column was added
        verify_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'payment_orders' AND column_name = 'receipt';
        """
        result = db.execute(text(verify_query)).fetchone()
        
        if result:
            logger.info("✅ Receipt column verified in payment_orders table")
        else:
            logger.error("❌ Receipt column not found after adding")
        
        # Show current table structure
        logger.info("📋 Current payment_orders table structure:")
        columns_query = """
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'payment_orders' 
        ORDER BY ordinal_position;
        """
        columns = db.execute(text(columns_query)).fetchall()
        
        for column in columns:
            logger.info(f"  - {column.column_name}: {column.data_type} (nullable: {column.is_nullable})")
        
        logger.info("🎉 Receipt column migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_receipt_column()