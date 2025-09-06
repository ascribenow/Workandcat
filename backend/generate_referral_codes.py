"""
Script to generate referral codes for existing users who don't have them
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from referral_service import referral_service
from sqlalchemy import text
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_referral_codes_for_existing_users():
    """Generate referral codes for users who don't have them"""
    
    db = SessionLocal()
    try:
        logger.info("🔄 Generating referral codes for existing users...")
        
        # Get users without referral codes
        users_without_codes = db.execute(
            text("SELECT id, email FROM users WHERE referral_code IS NULL OR referral_code = ''")
        ).fetchall()
        
        logger.info(f"Found {len(users_without_codes)} users without referral codes")
        
        generated_count = 0
        for user in users_without_codes:
            try:
                referral_code = referral_service.assign_referral_code_to_user(user.id, db)
                logger.info(f"✅ Generated referral code {referral_code} for user {user.email}")
                generated_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to generate referral code for user {user.email}: {e}")
        
        logger.info(f"🎉 Generated referral codes for {generated_count} users")
        
        # Verify generation
        total_users_with_codes = db.execute(
            text("SELECT COUNT(*) as count FROM users WHERE referral_code IS NOT NULL AND referral_code != ''")
        ).fetchone()
        
        logger.info(f"📊 Total users with referral codes: {total_users_with_codes.count}")
        
    except Exception as e:
        logger.error(f"❌ Error generating referral codes: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    generate_referral_codes_for_existing_users()