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
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from database import Base, SessionLocal
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Pydantic models for API requests
class CreateOrderRequest(BaseModel):
    plan_type: str  # "pro_lite" or "pro_regular"
    user_email: str
    user_name: str
    user_phone: Optional[str] = None

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

# Database Models
class PaymentOrder(Base):
    __tablename__ = "payment_orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    razorpay_order_id = Column(String, unique=True, nullable=False)
    plan_type = Column(String, nullable=False)  # "pro_lite" or "pro_regular"
    amount = Column(Integer, nullable=False)  # Amount in paise
    currency = Column(String, default="INR")
    status = Column(String, default="created")  # created, paid, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    razorpay_subscription_id = Column(String, unique=True, nullable=True)
    plan_type = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)  # Amount in paise
    status = Column(String, default="active")  # active, paused, cancelled, expired
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=False)
    paused_at = Column(DateTime, nullable=True)  # When subscription was paused
    paused_days_remaining = Column(Integer, nullable=True)  # Days remaining when paused
    pause_count = Column(Integer, default=0)  # Track number of times paused
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    razorpay_payment_id = Column(String, unique=True, nullable=False)
    razorpay_order_id = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String, default="INR")
    method = Column(String, nullable=True)  # card, netbanking, wallet, upi, etc.
    status = Column(String, nullable=False)  # captured, failed, refunded
    gateway_response = Column(Text, nullable=True)  # Store full response as JSON
    created_at = Column(DateTime, default=datetime.utcnow)

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
                "period": "fixed_date",  # Fixed end date: Nov 30, 2025
                "description": "Pro Exclusive - Unlimited sessions + Ask Twelvr till Nov 30, 2025",
                "auto_renew": False,
                "features": ["unlimited_sessions", "ask_twelvr"],
                "fixed_end_date": "2025-11-30 23:59:00"  # IST
            }
        }

    async def create_order(self, plan_type: str, user_email: str, user_name: str, user_id: str, user_phone: Optional[str] = None) -> Dict[str, Any]:
        """Create a Razorpay order for one-time payments"""
        try:
            if plan_type not in self.plans:
                raise ValueError(f"Invalid plan type: {plan_type}")
            
            plan_config = self.plans[plan_type]
            
            # Create Razorpay order with all payment methods enabled
            order_data = {
                "amount": plan_config["amount"],
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "plan_type": plan_type,
                    "user_email": user_email,
                    "user_name": user_name,
                    "user_id": user_id
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
                    amount=plan_config["amount"],
                    status="created"
                )
                db.add(db_order)
                db.commit()
            finally:
                db.close()
            
            return {
                "id": razorpay_order["id"],
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "key": os.getenv("RAZORPAY_KEY_ID"),  # Add the key for frontend
                "plan_name": plan_config["name"],
                "description": plan_config["description"],
                "prefill": {
                    "name": user_name,
                    "email": user_email,
                    "contact": user_phone or ""
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            raise

    async def create_subscription(self, plan_type: str, user_email: str, user_name: str, user_id: str, user_phone: Optional[str] = None) -> Dict[str, Any]:
        """Create a Razorpay subscription for recurring payments (Pro Lite)
        
        Note: If Razorpay subscriptions are not enabled for the account,
        this will create a one-time payment order instead with subscription-like handling
        """
        try:
            if plan_type != "pro_regular":
                raise ValueError("Subscriptions are only available for Pro Regular plan")
            
            plan_config = self.plans[plan_type]
            
            # Since Razorpay subscriptions require account activation, 
            # we'll implement Pro Regular as one-time payments with subscription-like UX
            logger.info(f"Creating Pro Regular payment (subscription-style) for user {user_id}")
            
            # Create as one-time payment but handle as subscription
            order_data = {
                "amount": plan_config["amount"],
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "plan_type": plan_type,
                    "user_email": user_email,
                    "user_name": user_name,
                    "user_id": user_id,
                    "billing_cycle": "monthly",
                    "subscription_type": "pro_regular_monthly"
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
                    amount=plan_config["amount"],
                    status="created"
                )
                db.add(db_order)
                db.commit()
                logger.info("Stored Pro Lite order in database")
            finally:
                db.close()
            
            return {
                "id": razorpay_order["id"],
                "order_id": razorpay_order["id"], 
                "amount": razorpay_order["amount"],
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
                "message": "Processing as monthly payment - 30 day access"
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
        """Verify Razorpay payment signature and update order status"""
        try:
            # Verify signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # This will raise an exception if signature is invalid
            self.client.utility.verify_payment_signature(params_dict)
            
            # Fetch payment details
            payment_details = self.client.payment.fetch(payment_id)
            
            # Update database (synchronous)
            db = SessionLocal()
            try:
                # Update order status
                order = db.query(PaymentOrder).filter(PaymentOrder.razorpay_order_id == order_id).first()
                if order:
                    order.status = "paid"
                    order.updated_at = datetime.utcnow()
                
                # Create transaction record
                transaction = PaymentTransaction(
                    user_id=user_id,
                    razorpay_payment_id=payment_id,
                    razorpay_order_id=order_id,
                    amount=payment_details["amount"],
                    method=payment_details.get("method"),
                    status=payment_details["status"],
                    gateway_response=str(payment_details)
                )
                db.add(transaction)
                
                # Create subscription record if order exists
                if order:
                    plan_type = order.plan_type
                    
                    # Set subscription periods based on plan type
                    current_period_start = datetime.utcnow()
                    
                    if plan_type == "pro_regular":
                        # 30 days from subscription date
                        current_period_end = current_period_start + timedelta(days=30)
                    elif plan_type == "pro_exclusive":
                        # Fixed end date: November 30, 2025 23:59 IST
                        import pytz
                        ist = pytz.timezone('Asia/Kolkata')
                        fixed_end = datetime(2025, 11, 30, 23, 59, 0)
                        current_period_end = ist.localize(fixed_end).astimezone(pytz.UTC).replace(tzinfo=None)
                    else:
                        # Default: 30 days
                        current_period_end = current_period_start + timedelta(days=30)
                    
                    subscription = Subscription(
                        user_id=user_id,
                        plan_type=plan_type,
                        amount=order.amount,
                        status="active",
                        current_period_start=current_period_start,
                        current_period_end=current_period_end,
                        auto_renew=(plan_type == "pro_regular")
                    )
                    db.add(subscription)
                
                db.commit()
            finally:
                db.close()
            
            return {
                "status": "success",
                "payment_id": payment_id,
                "order_id": order_id,
                "method": payment_details.get("method"),
                "amount": payment_details["amount"]
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
        """Resume user's paused subscription with balance days calculation"""
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
                
                now = datetime.utcnow()
                balance_days = subscription.paused_days_remaining or 0
                
                # Calculate new expiry: current_date + 30_days + balance_days
                if subscription.plan_type == "pro_regular":
                    new_end_date = now + timedelta(days=30 + balance_days)
                elif subscription.plan_type == "pro_exclusive":
                    # For Pro Exclusive, keep the fixed end date (Nov 30, 2025)
                    import pytz
                    ist = pytz.timezone('Asia/Kolkata')
                    fixed_end = datetime(2025, 11, 30, 23, 59, 0)
                    new_end_date = ist.localize(fixed_end).astimezone(pytz.UTC).replace(tzinfo=None)
                else:
                    new_end_date = now + timedelta(days=30 + balance_days)
                
                # Update subscription to active status
                subscription.status = "active"
                subscription.current_period_start = now
                subscription.current_period_end = new_end_date
                subscription.paused_at = None
                subscription.paused_days_remaining = None
                
                db.commit()
                
                logger.info(f"Resumed subscription {subscription.id} for user {user_id} with {balance_days} balance days")
                
                return {
                    "success": True,
                    "message": "Subscription resumed successfully",
                    "balance_days_added": balance_days,
                    "new_expiry": new_end_date.isoformat(),
                    "total_days": 30 + balance_days if subscription.plan_type == "pro_regular" else "Till Nov 30, 2025"
                }
                
        except Exception as e:
            logger.error(f"Error resuming subscription for user {user_id}: {e}")
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
                        "can_resume": subscription.status == "paused",
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

# Global instance
razorpay_service = RazorpayService()