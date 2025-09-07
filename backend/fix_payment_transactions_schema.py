#!/usr/bin/env python3
"""
Fix PaymentTransaction Schema Migration
Add missing columns to payment_transactions table if they don't exist
"""

import asyncio
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

async def fix_payment_transactions_schema():
    """
    Add missing columns to payment_transactions table if they don't exist
    """
    try:
        # Convert async URL to sync URL for inspection
        sync_database_url = DATABASE_URL.replace("asyncpg://", "postgresql://") if "asyncpg://" in DATABASE_URL else DATABASE_URL
        
        # Create sync engine for inspection
        sync_engine = create_engine(sync_database_url)
        inspector = inspect(sync_engine)
        
        # Check if payment_transactions table exists
        if not inspector.has_table('payment_transactions'):
            logger.info("❌ payment_transactions table not found - cannot proceed")
            return False
        
        # Get existing columns
        existing_columns = [col['name'] for col in inspector.get_columns('payment_transactions')]
        logger.info(f"📊 Existing columns in payment_transactions: {existing_columns}")
        
        # Define required columns that might be missing
        required_columns = {
            'description': 'TEXT',
            'fee': 'INTEGER',
            'tax': 'INTEGER',
            'notes': 'JSON DEFAULT \'{}\'::json',
            'method': 'VARCHAR(50)',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        missing_columns = []
        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                missing_columns.append((col_name, col_type))
        
        if not missing_columns:
            logger.info("✅ All required columns exist in payment_transactions table")
            return True
        
        logger.info(f"🔧 Missing columns found: {[col[0] for col in missing_columns]}")
        
        # Create async engine for executing commands using asyncpg
        async_database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://") if "postgresql://" in DATABASE_URL and "asyncpg" not in DATABASE_URL else DATABASE_URL
        async_engine = create_async_engine(async_database_url)
        
        async with async_engine.begin() as conn:
            for col_name, col_type in missing_columns:
                try:
                    logger.info(f"🔨 Adding column: {col_name} ({col_type})")
                    
                    sql = f"ALTER TABLE payment_transactions ADD COLUMN {col_name} {col_type}"
                    await conn.execute(text(sql))
                    logger.info(f"✅ Successfully added column: {col_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to add column {col_name}: {e}")
                    # Continue with other columns even if one fails
        
        logger.info("🎉 PaymentTransaction schema fix completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: PaymentTransaction schema fix failed: {e}")
        return False

async def verify_schema_fix():
    """
    Verify that the schema fix was successful
    """
    try:
        # Convert async URL to sync URL for inspection
        sync_database_url = DATABASE_URL.replace("asyncpg://", "postgresql://") if "asyncpg://" in DATABASE_URL else DATABASE_URL
        
        sync_engine = create_engine(sync_database_url)
        inspector = inspect(sync_engine)
        
        columns_after = [col['name'] for col in inspector.get_columns('payment_transactions')]
        logger.info(f"📊 Final columns in payment_transactions: {columns_after}")
        
        required_columns = ['description', 'fee', 'tax', 'notes', 'method', 'updated_at']
        missing_after = [col for col in required_columns if col not in columns_after]
        
        if missing_after:
            logger.warning(f"⚠️ Still missing columns: {missing_after}")
            return False
        else:
            logger.info("✅ All required columns verified present")
            return True
            
    except Exception as e:
        logger.error(f"❌ Schema verification failed: {e}")
        return False

if __name__ == "__main__":
    async def main():
        logger.info("🔧 STARTING PAYMENT TRANSACTIONS SCHEMA FIX")
        logger.info("=" * 60)
        
        success = await fix_payment_transactions_schema()
        
        if success:
            verification_success = await verify_schema_fix()
            if verification_success:
                logger.info("🎉 SCHEMA FIX COMPLETED AND VERIFIED SUCCESSFULLY")
            else:
                logger.error("❌ SCHEMA FIX COMPLETED BUT VERIFICATION FAILED")
        else:
            logger.error("❌ SCHEMA FIX FAILED")
    
    asyncio.run(main())