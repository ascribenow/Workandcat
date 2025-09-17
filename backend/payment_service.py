"""
Razorpay Payment Service for Twelvr
Handles subscription payments and one-time payments with comprehensive payment options
"""

import os
import razorpay
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from database import Base, SessionLocal, Subscription, PaymentOrder, PaymentTransaction
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Pydantic models for API requests
class CreateOrderRequest(BaseModel):
    plan_type: str  # "pro_regular" or "pro_exclusive"
    user_email: str
    user_name: str
    user_phone: Optional[str] = None
    referral_code: Optional[str] = None  # Referral code for discount

class PaymentVerificationRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: str

class SubscriptionRequest(BaseModel):
    plan_type: str
    user_email: str
    user_name: str
    user_phone: Optional[str] = None
    referral_code: Optional[str] = None  # Referral code for discount

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(
                os.getenv("RAZORPAY_KEY_ID"),
                os.getenv("RAZORPAY_KEY_SECRET")
            )
        )
        
        # Plan configurations
        self.plans = {
            "pro_regular": {
                "name": "Pro Regular",
                "amount": 149500,  # ₹1,495 in paise
                "interval": "monthly",
                "period": 30,  # 30 days validity
                "description": "Pro Regular - Unlimited sessions for 30 days",
                "auto_renew": True,
                "features": ["unlimited_sessions"]
            },
            "pro_exclusive": {
                "name": "Pro Exclusive", 
                "amount": 256500,  # ₹2,565 in paise
                "interval": None,  # One-time payment
                "period": "fixed_date",  # Fixed end date: Dec 31, 2025
                "description": "Pro Exclusive - Unlimited sessions + Ask Twelvr till Dec 31, 2025",
                "auto_renew": False,
                "features": ["unlimited_sessions", "ask_twelvr"],
                "fixed_end_date": "2025-12-31 23:59:00"  # IST
            }
        }

    def calculate_final_amount(self, plan_type: str, referral_code: Optional[str] = None, user_email: Optional[str] = None) -> Dict[str, Any]:
        """
        BACKEND-ONLY AMOUNT CALCULATION FOR SECURITY
        Frontend should never be trusted for amount calculations
        """
        try:
            if plan_type not in self.plans:
                raise ValueError(f"Invalid plan type: {plan_type}")
            
            plan_config = self.plans[plan_type]
            base_amount = plan_config["amount"]
            
            calculation_result = {
                "plan_type": plan_type,
                "base_amount": base_amount,
                "base_amount_inr": base_amount / 100,
                "referral_discount": 0,
                "referral_discount_inr": 0,
                "final_amount": base_amount,
                "final_amount_inr": base_amount / 100,
                "referral_applied": False,
                "referral_code": referral_code or "none"
            }
            
            # Apply referral discount if provided and valid
            if referral_code and user_email:
                from referral_service import referral_service
                db = SessionLocal()
                try:
                    # Use the new calculate-only method (doesn't record usage)
                    referral_calculation = referral_service.calculate_referral_discount(
                        referral_code=referral_code,
                        user_email=user_email,
                        subscription_type=plan_type,
                        original_amount=base_amount,
                        db=db
                    )
                    
                    if referral_calculation["success"]:
                        final_amount = referral_calculation["discounted_amount"]
                        discount_amount = referral_calculation["discount_applied"]
                        
                        calculation_result.update({
                            "referral_discount": discount_amount,
                            "referral_discount_inr": discount_amount / 100,
                            "final_amount": final_amount,
                            "final_amount_inr": final_amount / 100,
                            "referral_applied": True,
                            "referral_code": referral_calculation["referral_code"],
                            "usage_will_be_recorded_after_payment": True
                        })
                        
                        logger.info(f"✅ BACKEND CALCULATION: Referral discount calculated (NOT recorded) - ₹{base_amount/100:.2f} → ₹{final_amount/100:.2f}")
                    else:
                        logger.info(f"⚠️ BACKEND CALCULATION: Referral code invalid - {referral_calculation.get('error', 'Unknown error')}")
                        calculation_result["referral_validation_error"] = referral_calculation.get('error')
                        
                finally:
                    db.close()
            
            logger.info(f"💰 BACKEND AMOUNT CALCULATION: {plan_type} = ₹{calculation_result['final_amount_inr']:.2f}")
            return calculation_result
            
        except Exception as e:
            logger.error(f"❌ Backend amount calculation failed: {e}")
            raise
    
    async def create_order(self, plan_type: str, user_email: str, user_name: str, user_id: str, user_phone: Optional[str] = None, referral_code: Optional[str] = None) -> Dict[str, Any]:
        """Create a Razorpay order for one-time payments using backend-only amount calculation"""
        try:
            # BACKEND-ONLY AMOUNT CALCULATION (SECURITY CRITICAL)
            amount_calculation = self.calculate_final_amount(plan_type, referral_code, user_email)
            
            final_amount = amount_calculation["final_amount"]
            original_amount = amount_calculation["base_amount"]
            referral_discount = amount_calculation["referral_discount"]
            
            logger.info(f"🔒 BACKEND-CALCULATED AMOUNTS: Original=₹{original_amount/100:.2f}, Final=₹{final_amount/100:.2f}, Discount=₹{referral_discount/100:.2f}")
            
            # Get plan configuration for metadata
            plan_config = self.plans[plan_type]
            
            # Create Razorpay order with all payment methods enabled
            order_data = {
                "amount": final_amount,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "plan_type": plan_type,
                    "user_email": user_email,
                    "user_name": user_name,
                    "user_id": user_id,
                    "referral_code": referral_code or "none",
                    "original_amount": str(original_amount),
                    "referral_discount": str(referral_discount),
                    "final_amount": str(final_amount),
                    "discount_applied": "yes" if referral_discount > 0 else "no",
                    "referrer_cashback_due": "500" if referral_discount > 0 else "0"
                }
            }
            
            razorpay_order = self.client.order.create(order_data)
            
            # Store order in database (synchronous)
            db = SessionLocal()
            try:
                db_order = PaymentOrder(
                    user_id=user_id,
                    razorpay_order_id=razorpay_order["id"],
                    plan_type=plan_type,
                    amount=final_amount,
                    status="created",
                    notes=order_data["notes"]  # Store the notes with referral info
                )
                db.add(db_order)
                db.commit()
            finally:
                db.close()
            
            return {
                "id": razorpay_order["id"],
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],  # This is the final discounted amount
                "original_amount": original_amount,  # Original price before discount
                "final_amount": final_amount,  # Final amount after discount (same as amount)
                "discount_applied": referral_discount,  # Actual discount applied
                "currency": razorpay_order["currency"],
                "key": os.getenv("RAZORPAY_KEY_ID"),  # Add the key for frontend
                "plan_name": plan_config["name"],
                "description": plan_config["description"],
                "prefill": {
                    "name": user_name,
                    "email": user_email,
                    "contact": user_phone or ""
                },
                "referral_info": {
                    "code_used": referral_code or "",
                    "referrer_discount_earned": 500 if referral_code else 0,  # Amount referrer will get
                    "discount_description": f"₹{referral_discount/100:.0f} referral discount applied" if referral_discount > 0 else "No discount applied"
                },
                "payment_verification": {
                    "expected_amount_paise": final_amount,
                    "expected_amount_rupees": f"₹{final_amount/100:.0f}",
                    "referral_code_in_notes": referral_code or "none",
                    "discount_calculation_verified": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            raise

    async def create_subscription(self, plan_type: str, user_email: str, user_name: str, user_id: str, user_phone: Optional[str] = None, referral_code: Optional[str] = None) -> Dict[str, Any]:
        """Create a Razorpay subscription for recurring payments (Pro Regular)
        
        Note: If Razorpay subscriptions are not enabled for the account,
        this will create a one-time payment order instead with subscription-like handling
        """
        try:
            if plan_type != "pro_regular":
                raise ValueError("Subscriptions are only available for Pro Regular plan")
            
            plan_config = self.plans[plan_type]
            original_amount = plan_config["amount"]
            final_amount = original_amount
            referral_discount = 0
            
            # Apply referral discount if provided
            if referral_code:
                try:
                    from referral_service import referral_service
                    db = SessionLocal()
                    try:
                        discount_result = referral_service.apply_referral_discount(
                            referral_code, user_id, user_email, plan_type, original_amount, db
                        )
                        if discount_result["success"]:
                            final_amount = discount_result["discounted_amount"]
                            referral_discount = discount_result["discount_applied"]
                            logger.info(f"Applied referral discount to subscription: {referral_code}, discount: ₹{referral_discount/100:.2f}")
                        else:
                            logger.warning(f"Referral code validation failed for subscription: {discount_result.get('error')}")
                    finally:
                        db.close()
                except Exception as e:
                    logger.error(f"Error applying referral discount to subscription: {e}")
                    # Continue without discount if referral service fails
            
            # Since Razorpay subscriptions require account activation, 
            # we'll implement Pro Regular as one-time payments with subscription-like UX
            logger.info(f"Creating Pro Regular payment (subscription-style) for user {user_id}")
            
            # Create as one-time payment but handle as subscription
            order_data = {
                "amount": final_amount,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "plan_type": plan_type,
                    "user_email": user_email,
                    "user_name": user_name,
                    "user_id": user_id,
                    "billing_cycle": "monthly",
                    "subscription_type": "pro_regular_monthly",
                    "referral_code": referral_code or "none",
                    "original_amount": str(original_amount),
                    "referral_discount": str(referral_discount),
                    "final_amount": str(final_amount),
                    "discount_applied": "yes" if referral_discount > 0 else "no",
                    "referrer_cashback_due": "500" if referral_discount > 0 else "0"
                }
            }
            
            razorpay_order = self.client.order.create(order_data)
            logger.info(f"Successfully created Pro Regular order: {razorpay_order['id']}")
            
            # Store order in database with subscription flag
            db = SessionLocal()
            try:
                db_order = PaymentOrder(
                    user_id=user_id,
                    razorpay_order_id=razorpay_order["id"],
                    plan_type=plan_type,
                    amount=final_amount,
                    status="created",
                    notes=order_data["notes"]  # Store the notes with referral info
                )
                db.add(db_order)
                db.commit()
                logger.info("Stored Pro Regular subscription order in database")
            finally:
                db.close()
            
            return {
                "id": razorpay_order["id"],
                "order_id": razorpay_order["id"], 
                "amount": razorpay_order["amount"],  # This is the final discounted amount
                "original_amount": original_amount,  # Original price before discount
                "final_amount": final_amount,  # Final amount after discount (same as amount)
                "discount_applied": referral_discount,  # Actual discount applied
                "currency": razorpay_order["currency"],
                "key": os.getenv("RAZORPAY_KEY_ID"),  # Add the key for frontend
                "plan_name": plan_config["name"],
                "description": f"{plan_config['description']} - Monthly Access",
                "prefill": {
                    "name": user_name,
                    "email": user_email,
                    "contact": user_phone or ""
                },
                "theme": {
                    "color": "#9ac026"  # Twelvr brand color
                },
                "modal": {
                    "ondismiss": "console.log('Payment modal closed')"
                },
                "subscription_style": True,
                "message": "Processing as monthly payment - 30 day access",
                "referral_info": {
                    "code_used": referral_code or "",
                    "referrer_discount_earned": 500 if referral_code else 0,  # Amount referrer will get
                    "discount_description": f"₹{referral_discount/100:.0f} referral discount applied" if referral_discount > 0 else "No discount applied"
                },
                "payment_verification": {
                    "expected_amount_paise": final_amount,
                    "expected_amount_rupees": f"₹{final_amount/100:.0f}",
                    "referral_code_in_notes": referral_code or "none",
                    "discount_calculation_verified": True,
                    "subscription_type": "pro_regular_monthly"
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating Pro Regular subscription: {str(e)}")
            raise

    async def _get_or_create_plan(self, plan_type: str) -> str:
        """Get or create a Razorpay plan for subscriptions"""
        try:
            plan_config = self.plans[plan_type]
            # Use a simpler plan ID without trying to fetch existing plans first
            plan_id = f"twelvr_{plan_type}"
            
            # Create new plan with correct structure (don't try to fetch existing ones)
            plan_data = {
                "period": "monthly",
                "interval": 1,
                "item": {
                    "name": plan_config["name"],
                    "amount": plan_config["amount"],
                    "currency": "INR",
                    "description": plan_config["description"]
                },
                "notes": {
                    "plan_type": plan_type,
                    "created_by": "twelvr_backend"
                }
            }
            
            logger.info(f"Creating Razorpay plan with data: {plan_data}")
            created_plan = self.client.plan.create(plan_data)
            logger.info(f"Successfully created plan: {created_plan}")
            return created_plan["id"]
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            # Log more details about the error
            logger.error(f"Plan type: {plan_type}")
            logger.error(f"Plan config: {self.plans.get(plan_type, {})}")
            raise

    async def verify_payment(self, order_id: str, payment_id: str, signature: str, user_id: str) -> Dict[str, Any]:
        """
        INDUSTRY-STANDARD PAYMENT VERIFICATION WITH DATA INTEGRITY
        Uses Razorpay API as source of truth for all payment data
        Includes idempotency protection against duplicate processing
        """
        try:
            logger.info(f"Starting industry-standard payment verification: Payment={payment_id}, Order={order_id}, User={user_id}")
            
            # STEP 0: IDEMPOTENCY CHECK - Prevent duplicate payment processing
            db = SessionLocal()
            try:
                existing_payment = db.query(PaymentTransaction).filter(
                    PaymentTransaction.razorpay_payment_id == payment_id
                ).first()
                
                if existing_payment:
                    logger.info(f"🔒 IDEMPOTENCY: Payment {payment_id} already processed at {existing_payment.created_at}")
                    
                    # Return existing payment information instead of processing again
                    return {
                        "status": "already_processed",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "amount": existing_payment.amount,
                        "amount_inr": existing_payment.amount / 100,
                        "currency": existing_payment.currency,
                        "method": existing_payment.method,
                        "original_processing_time": existing_payment.created_at.isoformat(),
                        "message": "Payment was already successfully processed",
                        "idempotency_protection": True
                    }
                    
            finally:
                db.close()
            
            logger.info(f"✅ IDEMPOTENCY: Payment {payment_id} not previously processed, continuing with verification")
            
            # Step 1: Verify signature (security check)
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # This will raise an exception if signature is invalid
            self.client.utility.verify_payment_signature(params_dict)
            logger.info(f"Payment signature verification passed for {payment_id}")
            
            # Step 2: Comprehensive payment integrity verification using Razorpay API
            integrity_result = await self.verify_payment_integrity(payment_id, order_id)
            
            if not integrity_result["success"]:
                logger.error(f"Payment integrity verification failed: {integrity_result['error']}")
                raise Exception(f"Payment integrity verification failed: {integrity_result['error']}")
            
            if integrity_result["verification_status"] != "passed":
                logger.error(f"Payment integrity checks failed: {integrity_result['integrity_checks']}")
                raise Exception(f"Payment integrity checks failed: {integrity_result['integrity_checks']}")
            
            # Extract verified data from Razorpay API
            payment_data = integrity_result["payment_data"]
            order_data = integrity_result["order_data"]
            detected_plan = integrity_result["detected_plan"]
            referral_info = integrity_result["referral_discount_applied"]
            
            logger.info(f"✅ Payment integrity verified - Plan: {detected_plan['plan_type']}, Amount: ₹{payment_data['amount']/100:.2f}, Referral: {referral_info['applied']}")
            
            # Step 3: Update database with VERIFIED data from Razorpay
            db = SessionLocal()
            try:
                # Update order status with actual payment data
                order = db.query(PaymentOrder).filter(PaymentOrder.razorpay_order_id == order_id).first()
                if order:
                    order.status = "paid"
                    order.updated_at = datetime.utcnow()
                    
                    # Verify order matches actual payment
                    if order.plan_type != detected_plan["plan_type"]:
                        logger.warning(f"Order plan type mismatch: DB={order.plan_type}, Actual={detected_plan['plan_type']}")
                
                # Create transaction record with ACTUAL payment data
                transaction = PaymentTransaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    razorpay_payment_id=payment_id,
                    razorpay_order_id=order_id,
                    amount=payment_data["amount"],  # ACTUAL amount from Razorpay
                    currency=payment_data["currency"],  # ACTUAL currency from Razorpay
                    status=payment_data["status"],  # ACTUAL status from Razorpay
                    method=payment_data.get("method"),  # ACTUAL method from Razorpay
                    created_at=datetime.utcnow()
                )
                db.add(transaction)
                
                # Step 4: Create subscription based on VERIFIED payment data
                subscription = None
                if detected_plan["plan_type"] == "pro_regular":
                    # Check if subscription already exists
                    existing_subscription = db.query(Subscription).filter(
                        Subscription.user_id == user_id,
                        Subscription.plan_type == "pro_regular",
                        Subscription.status == "active"
                    ).first()
                    
                    if existing_subscription:
                        # Extend existing subscription by 30 days
                        existing_subscription.current_period_end = existing_subscription.current_period_end + timedelta(days=30)
                        existing_subscription.updated_at = datetime.utcnow()
                        subscription = existing_subscription
                        logger.info(f"Extended existing Pro Regular subscription for user {user_id}")
                    else:
                        # Create new subscription with ACTUAL payment amount
                        current_period_start = datetime.utcnow()
                        current_period_end = current_period_start + timedelta(days=30)
                        
                        subscription = Subscription(
                            id=str(uuid.uuid4()),
                            user_id=user_id,
                            plan_type="pro_regular",
                            amount=payment_data["amount"],  # ACTUAL amount paid
                            status="active",
                            current_period_start=current_period_start,
                            current_period_end=current_period_end,
                            auto_renew=True,
                            created_at=current_period_start,
                            updated_at=current_period_start
                        )
                        db.add(subscription)
                        logger.info(f"Created new Pro Regular subscription for user {user_id} with actual amount ₹{payment_data['amount']/100:.2f}")
                
                elif detected_plan["plan_type"] == "pro_exclusive":
                    # Pro Exclusive - one-time payment till Dec 31, 2025
                    current_period_start = datetime.utcnow()
                    current_period_end = datetime(2025, 12, 31, 23, 59, 0)
                    
                    subscription = Subscription(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        plan_type="pro_exclusive",
                        amount=payment_data["amount"],  # ACTUAL amount paid
                        status="active",
                        current_period_start=current_period_start,
                        current_period_end=current_period_end,
                        auto_renew=False,
                        created_at=current_period_start,
                        updated_at=current_period_start
                    )
                    db.add(subscription)
                    logger.info(f"Created new Pro Exclusive subscription for user {user_id} with actual amount ₹{payment_data['amount']/100:.2f}")
                
                else:
                    logger.error(f"Unknown plan type detected from payment: {detected_plan}")
                    raise Exception(f"Cannot create subscription for unknown plan type: {detected_plan['plan_type']}")
                
                # Step 5: Subscription is now created with VERIFIED data from Razorpay API
                # User subscription status can be determined from active Subscription records
                logger.info(f"Subscription created with verified payment data for user {user_id}")
                
                # Step 5.1: Record referral usage ONLY after successful payment verification
                if referral_info["applied"] and referral_info["discount_amount"] > 0:
                    try:
                        referral_code = referral_info.get("referral_code")
                        if referral_code:
                            from referral_service import referral_service
                            
                            # Get user email from order or payment data
                            user_email = order.user_email if order else payment_data.get("email", "unknown@example.com")
                            
                            usage_result = referral_service.record_referral_usage(
                                referral_code=referral_code,
                                user_id=user_id,
                                user_email=user_email,
                                subscription_type=detected_plan["plan_type"],
                                discount_amount=referral_info["discount_amount"],
                                payment_id=payment_id,
                                db=db
                            )
                            
                            if usage_result["success"]:
                                logger.info(f"✅ REFERRAL USAGE RECORDED: {referral_code} for {user_email} after successful payment {payment_id}")
                            else:
                                logger.error(f"❌ Failed to record referral usage: {usage_result.get('error')}")
                                # Don't fail payment verification due to referral recording error
                                
                    except Exception as referral_error:
                        logger.error(f"Error recording referral usage after payment: {referral_error}")
                        # Don't fail the payment verification due to referral recording error
                
                db.commit()
                
                # Step 6: Send payment confirmation email with ACCURATE data
                try:
                    from gmail_service import gmail_service
                    user_email = order.user_email if order else payment_data.get("email", "user@example.com")
                    plan_name = detected_plan["plan_type"].replace("_", " ").title()
                    amount_rupees = f"₹{payment_data['amount'] / 100:.2f}"
                    
                    # Format end date for email
                    end_date_text = None
                    if subscription and subscription.current_period_end:
                        end_date_text = subscription.current_period_end.strftime("%B %d, %Y")
                    
                    email_sent = gmail_service.send_payment_confirmation_email(
                        to_email=user_email,
                        plan_name=plan_name,
                        amount=amount_rupees,
                        payment_id=payment_id,
                        end_date=end_date_text
                    )
                    
                    if email_sent:
                        logger.info(f"Payment confirmation email sent to {user_email} with verified data")
                    else:
                        logger.warning(f"Failed to send payment confirmation email to {user_email}")
                        
                except Exception as email_error:
                    logger.error(f"Error sending payment confirmation email: {email_error}")
                    # Don't fail the payment verification due to email error
                
            finally:
                db.close()
            
            # Step 7: Return comprehensive verification result
            return {
                "status": "success",
                "payment_id": payment_id,
                "order_id": order_id,
                "method": payment_data.get("method"),
                "amount": payment_data["amount"],
                "amount_inr": payment_data["amount"] / 100,
                "currency": payment_data["currency"],
                "plan_type": detected_plan["plan_type"],
                "referral_discount_applied": referral_info["applied"],
                "referral_discount_amount": referral_info["discount_amount_inr"],
                "verification_timestamp": integrity_result["verification_timestamp"],
                "data_integrity_status": "verified_from_razorpay_api"
            }
            
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            # Update order status to failed
            db = SessionLocal()
            try:
                order = db.query(PaymentOrder).filter(PaymentOrder.razorpay_order_id == order_id).first()
                if order:
                    order.status = "failed"
                    order.updated_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
            
            raise

    def get_payment_methods_config(self) -> Dict[str, Any]:
        """Return comprehensive payment methods configuration for frontend"""
        return {
            "methods": {
                "card": True,
                "netbanking": True,
                "wallet": ["freecharge", "mobikwik", "olamoney", "payzapp", "airtelmoney", "amazonpay", "phonepe", "paytm", "jiomoney"],
                "upi": True,
                "emi": True,
                "paylater": ["simpl", "getsimpl", "icici", "hdfc"]
            },
            "theme": {
                "color": "#9ac026"  # Twelvr brand color
            },
            "modal": {
                "backdropclose": False,
                "escape": True,
                "handleback": True
            },
            "config": {
                "display": {
                    "language": "en"
                }
            }
        }

    async def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's active subscriptions"""
        try:
            db = SessionLocal()
            try:
                subscriptions = db.query(Subscription).filter(
                    Subscription.user_id == user_id,
                    Subscription.status == "active"
                ).order_by(Subscription.created_at.desc()).all()
                
                return [
                    {
                        "id": sub.id,
                        "plan_type": sub.plan_type,
                        "amount": sub.amount,
                        "status": sub.status,
                        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                        "auto_renew": sub.auto_renew
                    }
                    for sub in subscriptions
                ]
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error fetching subscriptions: {str(e)}")
            return []

    async def cancel_subscription(self, user_id: str, subscription_id: str) -> Dict[str, Any]:
        """Cancel user subscription"""
        try:
            db = SessionLocal()
            try:
                subscription = db.query(Subscription).filter(
                    Subscription.id == subscription_id,
                    Subscription.user_id == user_id
                ).first()
                
                if subscription:
                    subscription.status = "cancelled"
                    subscription.updated_at = datetime.utcnow()
                    db.commit()
                    
                    return {"status": "cancelled", "subscription_id": subscription_id}
                else:
                    raise ValueError("Subscription not found")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            raise
    
    def pause_subscription(self, user_id: str) -> Dict[str, Any]:
        """Pause user's active subscription"""
        try:
            with SessionLocal() as db:
                # Find active subscription
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == user_id,
                    Subscription.status == "active"
                ).first()
                
                if not subscription:
                    return {
                        "success": False,
                        "error": "No active subscription found"
                    }
                
                # Calculate remaining days
                now = datetime.utcnow()
                if subscription.current_period_end > now:
                    remaining_days = (subscription.current_period_end - now).days
                else:
                    remaining_days = 0
                
                # Update subscription to paused status
                subscription.status = "paused"
                subscription.paused_at = now
                subscription.paused_days_remaining = remaining_days
                subscription.pause_count += 1
                
                db.commit()
                
                logger.info(f"Paused subscription {subscription.id} for user {user_id} with {remaining_days} days remaining")
                
                return {
                    "success": True,
                    "message": "Subscription paused successfully",
                    "remaining_days": remaining_days,
                    "paused_at": now.isoformat(),
                    "can_resume": True
                }
                
        except Exception as e:
            logger.error(f"Error pausing subscription for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def resume_subscription(self, user_id: str) -> Dict[str, Any]:
        """Resume a paused subscription"""
        try:
            with SessionLocal() as db:
                # Find paused subscription
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == user_id,
                    Subscription.status == "paused"
                ).first()
                
                if not subscription:
                    return {
                        "success": False,
                        "error": "No paused subscription found"
                    }
                
                # Calculate new end date with remaining days
                now = datetime.utcnow()
                remaining_days = subscription.paused_days_remaining or 0
                
                # For Pro Regular, add remaining days to current period
                if subscription.plan_type == "pro_regular":
                    new_end_date = now + timedelta(days=30 + remaining_days)
                else:
                    # For Pro Exclusive, use original end date
                    new_end_date = subscription.current_period_end
                
                # Update subscription to active status
                subscription.status = "active"
                subscription.current_period_start = now
                subscription.current_period_end = new_end_date
                subscription.resumed_at = now
                subscription.paused_days_remaining = 0
                subscription.updated_at = now
                
                db.commit()
                
                logger.info(f"Resumed subscription {subscription.id} for user {user_id}")
                
                return {
                    "success": True,
                    "message": "Subscription resumed successfully",
                    "resumed_at": now.isoformat(),
                    "next_billing_date": new_end_date.isoformat(),
                    "bonus_days_added": remaining_days
                }
                
        except Exception as e:
            logger.error(f"Error resuming subscription for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_resume_payment_details(self, user_id: str) -> Dict[str, Any]:
        """Get payment details for resuming a paused subscription"""
        try:
            with SessionLocal() as db:
                # Find paused subscription
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == user_id,
                    Subscription.status == "paused"
                ).first()
                
                if not subscription:
                    return {
                        "success": False,
                        "error": "No paused subscription found"
                    }
                
                if subscription.plan_type != "pro_regular":
                    return {
                        "success": False,
                        "error": "Resume payment only required for Pro Regular subscriptions"
                    }
                
                balance_days = subscription.paused_days_remaining or 0
                plan_config = self.plans.get("pro_regular", {})
                
                return {
                    "success": True,
                    "subscription_id": subscription.id,
                    "plan_type": subscription.plan_type,
                    "amount": plan_config.get("amount", 149500),  # ₹1,495
                    "balance_days": balance_days,
                    "total_days_after_resume": 30 + balance_days,
                    "message": f"Resume Pro Regular subscription with {balance_days} balance days (Total: {30 + balance_days} days)"
                }
                
        except Exception as e:
            logger.error(f"Error getting resume payment details for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_resume_payment_order(self, user_id: str, user_email: str, user_name: str, user_phone: Optional[str] = None) -> Dict[str, Any]:
        """Create payment order for resuming paused subscription"""
        try:
            with SessionLocal() as db:
                # Find paused subscription
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == user_id,
                    Subscription.status == "paused"
                ).first()
                
                if not subscription:
                    return {
                        "success": False,
                        "error": "No paused subscription found"
                    }
                
                if subscription.plan_type != "pro_regular":
                    return {
                        "success": False,
                        "error": "Resume payment only required for Pro Regular subscriptions"
                    }
                
                balance_days = subscription.paused_days_remaining or 0
                plan_config = self.plans.get("pro_regular", {})
                amount = plan_config.get("amount", 149500)  # ₹1,495
                
                # Create Razorpay order
                razorpay_order = self.client.order.create({
                    "amount": amount,
                    "currency": "INR",
                    "payment_capture": 1,
                    "notes": {
                        "plan_type": "pro_regular",
                        "user_email": user_email,
                        "user_name": user_name,
                        "user_id": user_id,
                        "subscription_action": "resume",
                        "subscription_id": subscription.id,
                        "balance_days": balance_days
                    }
                })
                
                # Store order in database
                db_order = PaymentOrder(
                    razorpay_order_id=razorpay_order["id"],
                    user_id=user_id,
                    plan_type="pro_regular",
                    amount=amount,
                    status="created"
                )
                db.add(db_order)
                db.commit()
                
                logger.info(f"Created resume payment order {razorpay_order['id']} for user {user_id}")
                
                return {
                    "success": True,
                    "id": razorpay_order["id"],
                    "order_id": razorpay_order["id"],
                    "amount": razorpay_order["amount"],
                    "currency": razorpay_order["currency"],
                    "key": os.getenv("RAZORPAY_KEY_ID"),
                    "plan_name": "Resume Pro Regular",
                    "description": f"Resume Pro Regular subscription with {balance_days} bonus days",
                    "prefill": {
                        "name": user_name,
                        "email": user_email,
                        "contact": user_phone or ""
                    },
                    "theme": {
                        "color": "#9ac026"
                    },
                    "resume_payment": True,
                    "balance_days": balance_days,
                    "total_days": 30 + balance_days
                }
                
        except Exception as e:
            logger.error(f"Error creating resume payment order for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def complete_resume_payment(self, payment_id: str, order_id: str, signature: str, user_id: str) -> Dict[str, Any]:
        """Complete resume payment and activate subscription with balance days"""
        try:
            with SessionLocal() as db:
                # Verify payment
                verification_result = self.verify_payment(payment_id, order_id, signature)
                
                if not verification_result.get("success"):
                    return {
                        "success": False,
                        "error": "Payment verification failed"
                    }
                
                # Find paused subscription
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == user_id,
                    Subscription.status == "paused"
                ).first()
                
                if not subscription:
                    return {
                        "success": False,
                        "error": "No paused subscription found"
                    }
                
                now = datetime.utcnow()
                balance_days = subscription.paused_days_remaining or 0
                
                # Calculate new expiry: current_date + 30_days + balance_days
                new_end_date = now + timedelta(days=30 + balance_days)
                
                # Update subscription to active status
                subscription.status = "active"
                subscription.current_period_start = now
                subscription.current_period_end = new_end_date
                subscription.paused_at = None
                subscription.paused_days_remaining = None
                
                # Record the payment transaction
                transaction = PaymentTransaction(
                    user_id=user_id,
                    razorpay_payment_id=payment_id,
                    razorpay_order_id=order_id,
                    amount=149500,  # ₹1,495
                    method="resume_subscription",
                    status="captured"
                )
                db.add(transaction)
                
                db.commit()
                
                logger.info(f"Completed resume payment for subscription {subscription.id} with {balance_days} balance days")
                
                return {
                    "success": True,
                    "message": "Subscription resumed successfully with payment",
                    "balance_days_added": balance_days,
                    "new_expiry": new_end_date.isoformat(),
                    "total_days": 30 + balance_days,
                    "amount_paid": 149500
                }
                
        except Exception as e:
            logger.error(f"Error completing resume payment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Get detailed subscription status including pause/resume info"""
        try:
            with SessionLocal() as db:
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == user_id
                ).order_by(Subscription.created_at.desc()).first()
                
                if not subscription:
                    return {
                        "success": True,
                        "has_subscription": False,
                        "subscription": None
                    }
                
                now = datetime.utcnow()
                
                return {
                    "success": True,
                    "has_subscription": True,
                    "subscription": {
                        "id": subscription.id,
                        "plan_type": subscription.plan_type,
                        "status": subscription.status,
                        "current_period_start": subscription.current_period_start.isoformat(),
                        "current_period_end": subscription.current_period_end.isoformat(),
                        "auto_renew": subscription.auto_renew,
                        "is_active": subscription.status == "active" and subscription.current_period_end > now,
                        "is_paused": subscription.status == "paused",
                        "can_pause": subscription.status == "active" and subscription.plan_type == "pro_regular",
                        "can_resume": subscription.status == "paused" and subscription.plan_type == "pro_regular",
                        "resume_requires_payment": subscription.status == "paused" and subscription.plan_type == "pro_regular",
                        "paused_at": subscription.paused_at.isoformat() if subscription.paused_at else None,
                        "paused_days_remaining": subscription.paused_days_remaining,
                        "pause_count": subscription.pause_count,
                        "days_remaining": (subscription.current_period_end - now).days if subscription.current_period_end > now else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting subscription status for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==========================================
    # RAZORPAY API INTEGRATION FOR DATA INTEGRITY
    # ==========================================
    
    def fetch_payment_details_from_razorpay(self, payment_id: str) -> Dict[str, Any]:
        """
        Fetch actual payment details from Razorpay API
        This ensures data integrity by using Razorpay as source of truth
        """
        try:
            logger.info(f"Fetching payment details from Razorpay API: {payment_id}")
            
            # Call Razorpay Payment API
            payment_details = self.client.payment.fetch(payment_id)
            
            logger.info(f"Razorpay payment details retrieved: {payment_details}")
            
            return {
                "success": True,
                "payment": {
                    "id": payment_details["id"],
                    "amount": payment_details["amount"],  # Amount in paise
                    "currency": payment_details["currency"],
                    "status": payment_details["status"],
                    "method": payment_details.get("method"),
                    "created_at": payment_details["created_at"],
                    "captured": payment_details.get("captured", False),
                    "order_id": payment_details.get("order_id"),
                    "email": payment_details.get("email"),
                    "contact": payment_details.get("contact"),
                    "description": payment_details.get("description"),
                    "notes": payment_details.get("notes", {}),
                    "fee": payment_details.get("fee"),
                    "tax": payment_details.get("tax"),
                    "refund_status": payment_details.get("refund_status"),
                    "amount_refunded": payment_details.get("amount_refunded", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch payment details from Razorpay: {payment_id}, Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "payment_id": payment_id
            }
    
    def fetch_order_details_from_razorpay(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch actual order details from Razorpay API
        This provides the original order amount and plan details
        """
        try:
            logger.info(f"Fetching order details from Razorpay API: {order_id}")
            
            # Call Razorpay Order API
            order_details = self.client.order.fetch(order_id)
            
            logger.info(f"Razorpay order details retrieved: {order_details}")
            
            return {
                "success": True,
                "order": {
                    "id": order_details["id"],
                    "amount": order_details["amount"],  # Original order amount in paise
                    "currency": order_details["currency"],
                    "status": order_details["status"],
                    "created_at": order_details["created_at"],
                    "notes": order_details.get("notes", {}),
                    "receipt": order_details.get("receipt"),
                    "attempts": order_details.get("attempts", 0),
                    "amount_paid": order_details.get("amount_paid", 0),
                    "amount_due": order_details.get("amount_due", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch order details from Razorpay: {order_id}, Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_id
            }
    
    async def verify_payment_integrity(self, payment_id: str, order_id: str, expected_amount: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive payment integrity verification using Razorpay API
        Ensures data integrity by comparing actual vs expected values
        """
        try:
            logger.info(f"Starting payment integrity verification: Payment={payment_id}, Order={order_id}")
            
            # Fetch actual payment and order data from Razorpay
            payment_result = self.fetch_payment_details_from_razorpay(payment_id)
            order_result = self.fetch_order_details_from_razorpay(order_id)
            
            if not payment_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to fetch payment details: {payment_result['error']}",
                    "verification_status": "failed_payment_fetch"
                }
            
            if not order_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to fetch order details: {order_result['error']}",
                    "verification_status": "failed_order_fetch"
                }
            
            payment_data = payment_result["payment"]
            order_data = order_result["order"]
            
            # Data integrity checks
            integrity_checks = {
                "payment_captured": payment_data["status"] == "captured",
                "payment_order_match": payment_data["order_id"] == order_id,
                "currency_valid": payment_data["currency"] == "INR",
                "amount_consistency": payment_data["amount"] == order_data["amount"],
                "no_refunds": payment_data["amount_refunded"] == 0,
                "expected_amount_match": True  # Default, will be updated if expected_amount provided
            }
            
            # Check expected amount if provided
            if expected_amount is not None:
                integrity_checks["expected_amount_match"] = payment_data["amount"] == expected_amount
            
            # Overall integrity status
            all_checks_passed = all(integrity_checks.values())
            
            # Determine plan type from actual payment amount
            actual_amount = payment_data["amount"]
            detected_plan = self._detect_plan_from_amount(actual_amount)
            
            # Check for referral discount
            referral_discount_applied = self._detect_referral_discount(actual_amount, detected_plan)
            
            logger.info(f"Payment integrity verification completed: {integrity_checks}")
            
            return {
                "success": True,
                "verification_status": "passed" if all_checks_passed else "failed",
                "integrity_checks": integrity_checks,
                "payment_data": payment_data,
                "order_data": order_data,
                "detected_plan": detected_plan,
                "referral_discount_applied": referral_discount_applied,
                "actual_amount_paid": actual_amount,
                "actual_amount_inr": actual_amount / 100,  # Convert paise to rupees
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Payment integrity verification failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "verification_status": "error"
            }
    
    def _detect_plan_from_amount(self, amount_in_paise: int) -> Dict[str, Any]:
        """
        Detect which plan was purchased based on actual amount paid
        Accounts for referral discounts (₹500 = 50000 paise)
        """
        amount = amount_in_paise
        referral_discount = 50000  # ₹500 in paise
        
        # Check exact matches (no discount)
        if amount == 149500:  # ₹1,495
            return {"plan_type": "pro_regular", "discount_applied": False, "original_amount": 149500}
        elif amount == 256500:  # ₹2,565
            return {"plan_type": "pro_exclusive", "discount_applied": False, "original_amount": 256500}
        
        # Check with referral discount applied
        elif amount == 149500 - referral_discount:  # ₹995 (₹1,495 - ₹500)
            return {"plan_type": "pro_regular", "discount_applied": True, "original_amount": 149500, "discount_amount": referral_discount}
        elif amount == 256500 - referral_discount:  # ₹2,065 (₹2,565 - ₹500)
            return {"plan_type": "pro_exclusive", "discount_applied": True, "original_amount": 256500, "discount_amount": referral_discount}
        
        # Unknown amount - return as detected but flag as unknown
        return {
            "plan_type": "unknown",
            "discount_applied": None,
            "original_amount": None,
            "actual_amount": amount,
            "note": f"Unknown payment amount: ₹{amount/100:.2f}"
        }
    
    def _detect_referral_discount(self, actual_amount: int, detected_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if referral discount was applied based on actual payment amount
        """
        if detected_plan["discount_applied"]:
            return {
                "applied": True,
                "discount_amount_paise": 50000,
                "discount_amount_inr": 500,
                "original_amount": detected_plan["original_amount"],
                "discounted_amount": actual_amount
            }
        else:
            return {
                "applied": False,
                "discount_amount_paise": 0,
                "discount_amount_inr": 0,
                "original_amount": actual_amount,
                "discounted_amount": actual_amount
            }

# Global instance
razorpay_service = RazorpayService()

# Alias for backward compatibility
PaymentService = RazorpayService