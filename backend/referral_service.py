"""
Referral Service for handling referral code generation, validation, and usage tracking
"""

import random
import string
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from database import User, ReferralUsage, SessionLocal
import logging

logger = logging.getLogger(__name__)

class ReferralService:
    """Service to handle all referral-related operations"""
    
    def __init__(self):
        self.code_length = 6
    
    def generate_unique_referral_code(self, db: Session) -> str:
        """
        Generate a unique 6-character alphanumeric referral code
        Ensures the code is not already in use
        """
        max_attempts = 100
        
        for _ in range(max_attempts):
            # Generate 6-character alphanumeric code (uppercase)
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=self.code_length))
            
            # Check if code already exists
            existing_user = db.execute(
                text("SELECT id FROM users WHERE referral_code = :code"),
                {"code": code}
            ).fetchone()
            
            if not existing_user:
                return code
        
        raise Exception("Unable to generate unique referral code after 100 attempts")
    
    def assign_referral_code_to_user(self, user_id: str, db: Session) -> str:
        """
        Assign a unique referral code to a user
        Returns the generated referral code
        """
        try:
            # Check if user already has a referral code
            user = db.execute(
                text("SELECT referral_code FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if user and user.referral_code:
                logger.info(f"User {user_id} already has referral code: {user.referral_code}")
                return user.referral_code
            
            # Generate unique referral code
            referral_code = self.generate_unique_referral_code(db)
            
            # Update user with referral code
            db.execute(
                text("UPDATE users SET referral_code = :code WHERE id = :user_id"),
                {"code": referral_code, "user_id": user_id}
            )
            db.commit()
            
            logger.info(f"Generated referral code {referral_code} for user {user_id}")
            return referral_code
            
        except Exception as e:
            logger.error(f"Error assigning referral code to user {user_id}: {e}")
            db.rollback()
            raise
    
    def validate_referral_code(self, code: str, user_email: str, db: Session) -> Dict[str, Any]:
        """
        Validate a referral code for use by a specific user
        Returns validation result with details
        """
        try:
            code = code.upper().strip()  # Normalize to uppercase
            
            if len(code) != self.code_length:
                return {
                    "valid": False,
                    "error": "Invalid referral code format",
                    "can_use": False
                }
            
            # Check if referral code exists
            referral_owner = db.execute(
                text("SELECT id, email, full_name FROM users WHERE referral_code = :code"),
                {"code": code}
            ).fetchone()
            
            if not referral_owner:
                return {
                    "valid": False,
                    "error": "Referral code not found",
                    "can_use": False
                }
            
            # Check if user is trying to use their own referral code
            if referral_owner.email.lower() == user_email.lower():
                return {
                    "valid": False,
                    "error": "Cannot use your own referral code",
                    "can_use": False
                }
            
            # Check if this email has already used any referral code
            existing_usage = db.execute(
                text("SELECT id FROM referral_usage WHERE used_by_email = :email"),
                {"email": user_email.lower()}
            ).fetchone()
            
            if existing_usage:
                return {
                    "valid": False,
                    "error": "You have already used a referral code",
                    "can_use": False
                }
            
            # Code is valid and can be used
            return {
                "valid": True,
                "can_use": True,
                "referral_code": code,
                "referrer_name": referral_owner.full_name,
                "discount_amount": 50000  # ₹500 in paise
            }
            
        except Exception as e:
            logger.error(f"Error validating referral code {code} for {user_email}: {e}")
            return {
                "valid": False,
                "error": "An error occurred during validation",
                "can_use": False
            }
    
    def calculate_referral_discount(self, referral_code: str, user_email: str, 
                                  subscription_type: str, original_amount: int, db: Session) -> Dict[str, Any]:
        """
        Calculate referral discount WITHOUT recording usage
        Only validates and calculates - usage recorded after payment success
        """
        try:
            referral_code = referral_code.upper().strip()
            discount_amount_paise = 50000  # Fixed ₹500 discount = 50000 paise
            
            # Validate the referral code first
            validation_result = self.validate_referral_code(referral_code, user_email, db)
            
            if not validation_result["valid"] or not validation_result["can_use"]:
                return {
                    "success": False,
                    "error": validation_result.get("error", "Invalid referral code"),
                    "original_amount": original_amount,
                    "discounted_amount": original_amount,
                    "discount_applied": 0
                }
            
            # Calculate discounted amount (minimum ₹1 = 100 paise)
            discounted_amount = max(original_amount - discount_amount_paise, 100)
            actual_discount = original_amount - discounted_amount
            
            logger.info(f"Calculated referral discount: {referral_code} for {user_email}, discount: ₹{actual_discount/100:.2f} (original: ₹{original_amount/100:.2f} → final: ₹{discounted_amount/100:.2f}) - NOT YET RECORDED")
            
            return {
                "success": True,
                "original_amount": original_amount,
                "discounted_amount": discounted_amount,
                "discount_applied": actual_discount,
                "referral_code": referral_code,
                "pending_usage": True  # Indicates usage not yet recorded
            }
            
        except Exception as e:
            logger.error(f"Error calculating referral discount {referral_code} for {user_email}: {e}")
            return {
                "success": False,
                "error": "An error occurred while calculating the discount",
                "original_amount": original_amount,
                "discounted_amount": original_amount,
                "discount_applied": 0
            }
    
    def record_referral_usage(self, referral_code: str, user_id: str, user_email: str, 
                            subscription_type: str, discount_amount: int, payment_id: str, db: Session) -> Dict[str, Any]:
        """
        Record referral usage ONLY after successful payment verification
        This ensures users don't lose their one-time usage if payment fails/abandoned
        """
        try:
            referral_code = referral_code.upper().strip()
            
            # Double-check that user hasn't already used a referral code
            # (in case of race conditions or multiple payment attempts)
            existing_usage = db.execute(
                text("SELECT id FROM referral_usage WHERE used_by_email = :email"),
                {"email": user_email.lower()}
            ).fetchone()
            
            if existing_usage:
                logger.warning(f"Attempted to record referral usage for {user_email} but usage already exists - preventing duplicate")
                return {
                    "success": False,
                    "error": "Referral code already used by this email",
                    "duplicate_prevented": True
                }
            
            # Record referral usage with payment reference
            usage_id = self._generate_uuid()
            db.execute(
                text("""
                    INSERT INTO referral_usage 
                    (id, referral_code, used_by_user_id, used_by_email, discount_amount, subscription_type, payment_reference)
                    VALUES (:id, :code, :user_id, :email, :discount, :sub_type, :payment_ref)
                """),
                {
                    "id": usage_id,
                    "code": referral_code,
                    "user_id": user_id,
                    "email": user_email.lower(),
                    "discount": discount_amount,
                    "sub_type": subscription_type,
                    "payment_ref": payment_id
                }
            )
            db.commit()
            
            logger.info(f"✅ RECORDED referral usage: {referral_code} used by {user_email}, discount: ₹{discount_amount/100:.2f}, payment: {payment_id}")
            
            return {
                "success": True,
                "usage_id": usage_id,
                "referral_code": referral_code,
                "discount_amount": discount_amount,
                "recorded_at": "payment_verification"
            }
            
        except Exception as e:
            logger.error(f"Error recording referral usage {referral_code} for {user_email}: {e}")
            db.rollback()
            return {
                "success": False,
                "error": "An error occurred while recording referral usage",
                "critical": True
            }

    def apply_referral_discount(self, referral_code: str, user_id: str, user_email: str, 
                              subscription_type: str, original_amount: int, db: Session) -> Dict[str, Any]:
        """
        DEPRECATED: Use calculate_referral_discount + record_referral_usage instead
        This method is kept for backward compatibility but logs a warning
        """
        logger.warning(f"DEPRECATED: apply_referral_discount called for {user_email} - should use calculate_referral_discount + record_referral_usage")
        
        # For backward compatibility, use the new calculate method
        return self.calculate_referral_discount(referral_code, user_email, subscription_type, original_amount, db)
    
    def get_referral_usage_stats(self, referral_code: str, db: Session) -> Dict[str, Any]:
        """
        Get usage statistics for a referral code
        """
        try:
            code = referral_code.upper().strip()
            
            # Get referral code owner
            owner = db.execute(
                text("SELECT id, email, full_name FROM users WHERE referral_code = :code"),
                {"code": code}
            ).fetchone()
            
            if not owner:
                return {"error": "Referral code not found"}
            
            # Get usage statistics
            usage_stats = db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_uses,
                        SUM(discount_amount) as total_discount_given,
                        COUNT(CASE WHEN subscription_type = 'pro_regular' THEN 1 END) as pro_regular_uses,
                        COUNT(CASE WHEN subscription_type = 'pro_exclusive' THEN 1 END) as pro_exclusive_uses
                    FROM referral_usage 
                    WHERE referral_code = :code
                """),
                {"code": code}
            ).fetchone()
            
            # Get recent usage details
            recent_usage = db.execute(
                text("""
                    SELECT used_by_email, subscription_type, discount_amount, created_at
                    FROM referral_usage 
                    WHERE referral_code = :code
                    ORDER BY created_at DESC 
                    LIMIT 10
                """),
                {"code": code}
            ).fetchall()
            
            return {
                "referral_code": code,
                "owner": {
                    "id": owner.id,
                    "email": owner.email,
                    "full_name": owner.full_name
                },
                "stats": {
                    "total_uses": usage_stats.total_uses or 0,
                    "total_discount_given": usage_stats.total_discount_given or 0,
                    "pro_regular_uses": usage_stats.pro_regular_uses or 0,
                    "pro_exclusive_uses": usage_stats.pro_exclusive_uses or 0
                },
                "recent_usage": [
                    {
                        "email": usage.used_by_email,
                        "subscription_type": usage.subscription_type,
                        "discount_amount": usage.discount_amount,
                        "created_at": usage.created_at.isoformat()
                    }
                    for usage in recent_usage
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting referral usage stats for {referral_code}: {e}")
            return {"error": "An error occurred while fetching statistics"}
    
    def _generate_uuid(self) -> str:
        """Generate a UUID for database records"""
        import uuid
        return str(uuid.uuid4())

# Global service instance
referral_service = ReferralService()