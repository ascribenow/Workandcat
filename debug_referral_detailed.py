#!/usr/bin/env python3
"""
Debug script to test referral service with detailed error logging
"""

import sys
import os
sys.path.append('/app/backend')

from referral_service import ReferralService
from database import SessionLocal
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_referral_service_detailed():
    """Test referral service with detailed error logging"""
    print("🔍 DEBUGGING REFERRAL SERVICE WITH DETAILED LOGGING")
    print("=" * 60)
    
    referral_service = ReferralService()
    db = SessionLocal()
    
    try:
        # Test parameters
        referral_code = "XTJC41"
        user_id = "test-user-id-detailed"
        user_email = "debug_detailed_test@example.com"
        subscription_type = "pro_exclusive"
        original_amount = 256500  # ₹2,565 in paise
        
        print(f"Testing referral code: {referral_code}")
        print(f"User email: {user_email}")
        print(f"Subscription type: {subscription_type}")
        print(f"Original amount: ₹{original_amount/100} ({original_amount} paise)")
        print()
        
        # Step 1: Test validation
        print("Step 1: Testing referral code validation")
        try:
            validation_result = referral_service.validate_referral_code(referral_code, user_email, db)
            print(f"Validation result: {validation_result}")
            print()
            
            if validation_result.get("valid") and validation_result.get("can_use"):
                # Step 2: Test discount application with detailed error handling
                print("Step 2: Testing discount application with detailed logging")
                
                # Manually implement the discount logic to see where it fails
                referral_code = referral_code.upper().strip()
                discount_amount_paise = 50000  # Fixed ₹500 discount = 50000 paise
                
                print(f"  Normalized referral code: {referral_code}")
                print(f"  Discount amount: ₹{discount_amount_paise/100} ({discount_amount_paise} paise)")
                
                # Calculate discounted amount (minimum ₹1 = 100 paise)
                discounted_amount = max(original_amount - discount_amount_paise, 100)
                actual_discount = original_amount - discounted_amount
                
                print(f"  Calculated discounted amount: ₹{discounted_amount/100} ({discounted_amount} paise)")
                print(f"  Actual discount: ₹{actual_discount/100} ({actual_discount} paise)")
                
                # Test UUID generation
                usage_id = referral_service._generate_uuid()
                print(f"  Generated usage ID: {usage_id}")
                
                # Test database insertion
                print("  Testing database insertion...")
                from sqlalchemy import text
                
                try:
                    db.execute(
                        text("""
                            INSERT INTO referral_usage 
                            (id, referral_code, used_by_user_id, used_by_email, discount_amount, subscription_type)
                            VALUES (:id, :code, :user_id, :email, :discount, :sub_type)
                        """),
                        {
                            "id": usage_id,
                            "code": referral_code,
                            "user_id": user_id,
                            "email": user_email.lower(),
                            "discount": actual_discount,
                            "sub_type": subscription_type
                        }
                    )
                    db.commit()
                    print("  ✅ Database insertion successful")
                    
                    print(f"✅ MANUAL DISCOUNT APPLICATION SUCCESS:")
                    print(f"  Original amount: ₹{original_amount/100} ({original_amount} paise)")
                    print(f"  Discounted amount: ₹{discounted_amount/100} ({discounted_amount} paise)")
                    print(f"  Discount applied: ₹{actual_discount/100} ({actual_discount} paise)")
                    print(f"  Expected final: ₹{206500/100} ({206500} paise)")
                    print(f"  Actual final: ₹{discounted_amount/100} ({discounted_amount} paise)")
                    
                    if discounted_amount == 206500:
                        print("✅ DISCOUNT CALCULATION CORRECT")
                    else:
                        print("❌ DISCOUNT CALCULATION INCORRECT")
                        
                except Exception as db_error:
                    print(f"  ❌ Database insertion failed: {db_error}")
                    print(f"  Error type: {type(db_error)}")
                    traceback.print_exc()
                    db.rollback()
                
            else:
                print(f"❌ VALIDATION FAILED: {validation_result.get('error')}")
                
        except Exception as validation_error:
            print(f"❌ VALIDATION ERROR: {validation_error}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ GENERAL ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_referral_service_detailed()