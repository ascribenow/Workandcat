#!/usr/bin/env python3
"""
Debug script to test referral service directly
"""

import sys
import os
sys.path.append('/app/backend')

from referral_service import ReferralService
from database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_referral_service():
    """Test referral service directly"""
    print("🔍 DEBUGGING REFERRAL SERVICE DIRECTLY")
    print("=" * 60)
    
    referral_service = ReferralService()
    db = SessionLocal()
    
    try:
        # Test parameters
        referral_code = "XTJC41"
        user_id = "test-user-id"
        user_email = "debug_test@example.com"
        subscription_type = "pro_exclusive"
        original_amount = 256500  # ₹2,565 in paise
        
        print(f"Testing referral code: {referral_code}")
        print(f"User email: {user_email}")
        print(f"Subscription type: {subscription_type}")
        print(f"Original amount: ₹{original_amount/100} ({original_amount} paise)")
        print()
        
        # Step 1: Test validation
        print("Step 1: Testing referral code validation")
        validation_result = referral_service.validate_referral_code(referral_code, user_email, db)
        print(f"Validation result: {validation_result}")
        print()
        
        if validation_result.get("valid") and validation_result.get("can_use"):
            # Step 2: Test discount application
            print("Step 2: Testing discount application")
            discount_result = referral_service.apply_referral_discount(
                referral_code, user_id, user_email, subscription_type, original_amount, db
            )
            print(f"Discount result: {discount_result}")
            print()
            
            if discount_result.get("success"):
                original = discount_result["original_amount"]
                discounted = discount_result["discounted_amount"]
                discount_applied = discount_result["discount_applied"]
                
                print(f"✅ SUCCESS:")
                print(f"  Original amount: ₹{original/100} ({original} paise)")
                print(f"  Discounted amount: ₹{discounted/100} ({discounted} paise)")
                print(f"  Discount applied: ₹{discount_applied/100} ({discount_applied} paise)")
                print(f"  Expected final: ₹{206500/100} ({206500} paise)")
                print(f"  Actual final: ₹{discounted/100} ({discounted} paise)")
                
                if discounted == 206500:
                    print("✅ DISCOUNT CALCULATION CORRECT")
                else:
                    print("❌ DISCOUNT CALCULATION INCORRECT")
            else:
                print(f"❌ DISCOUNT APPLICATION FAILED: {discount_result.get('error')}")
        else:
            print(f"❌ VALIDATION FAILED: {validation_result.get('error')}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_referral_service()