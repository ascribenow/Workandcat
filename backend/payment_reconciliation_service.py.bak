"""
Payment Reconciliation Service
Ensures data integrity between Twelvr and Razorpay systems
Detects and fixes payment discrepancies automatically
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import sessionmaker

from database import SessionLocal, PaymentTransaction, PaymentOrder, Subscription, User
from payment_service import razorpay_service
from gmail_service import gmail_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentReconciliationService:
    """
    Automated payment reconciliation service
    Ensures data integrity between Twelvr and Razorpay
    """
    
    def __init__(self):
        self.db_session = SessionLocal()
        self.reconciliation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_checks": 0,
            "discrepancies_found": 0,
            "fixes_applied": 0,
            "manual_review_required": 0,
            "details": []
        }
    
    async def run_comprehensive_reconciliation(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Run comprehensive payment reconciliation for the last N days
        """
        try:
            logger.info(f"🔍 STARTING COMPREHENSIVE PAYMENT RECONCILIATION")
            logger.info(f"📊 Checking payments from last {days_back} days")
            logger.info("=" * 70)
            
            # Check for various types of discrepancies
            await self._check_paid_but_not_activated_subscriptions(days_back)
            await self._check_amount_discrepancies_with_razorpay(days_back)
            await self._check_missing_payment_confirmations(days_back)
            await self._check_duplicate_payments(days_back)
            await self._check_subscription_plan_mismatches(days_back)
            
            # Generate summary report
            await self._generate_reconciliation_report()
            
            logger.info("🎉 PAYMENT RECONCILIATION COMPLETED")
            return self.reconciliation_results
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Payment reconciliation failed: {e}")
            raise
        finally:
            self.db_session.close()
    
    async def _check_paid_but_not_activated_subscriptions(self, days_back: int):
        """
        Find payments that were successful in Razorpay but didn't activate subscriptions
        """
        logger.info("🔍 Checking for paid but not activated subscriptions...")
        
        try:
            # Get payment transactions from last N days
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            transactions = self.db_session.query(PaymentTransaction).filter(
                and_(
                    PaymentTransaction.created_at >= cutoff_date,
                    PaymentTransaction.status == "captured"
                )
            ).all()
            
            for transaction in transactions:
                self.reconciliation_results["total_checks"] += 1
                
                # Check if user has active subscription for this payment
                active_subscription = self.db_session.query(Subscription).filter(
                    and_(
                        Subscription.user_id == transaction.user_id,
                        Subscription.status == "active",
                        Subscription.amount == transaction.amount
                    )
                ).first()
                
                if not active_subscription:
                    logger.warning(f"⚠️ DISCREPANCY: Payment {transaction.razorpay_payment_id} captured but no active subscription")
                    
                    # Fetch actual payment data from Razorpay
                    payment_result = await razorpay_service.fetch_payment_details_from_razorpay(
                        transaction.razorpay_payment_id
                    )
                    
                    if payment_result["success"]:
                        razorpay_data = payment_result["payment"]
                        
                        if razorpay_data["status"] == "captured":
                            # Payment is genuinely captured in Razorpay, fix the subscription
                            await self._fix_missing_subscription_activation(transaction, razorpay_data)
                        else:
                            logger.info(f"✅ Payment {transaction.razorpay_payment_id} not actually captured in Razorpay")
                    
        except Exception as e:
            logger.error(f"❌ Error checking paid but not activated subscriptions: {e}")
    
    async def _check_amount_discrepancies_with_razorpay(self, days_back: int):
        """
        Compare subscription amounts with actual Razorpay payment amounts
        """
        logger.info("🔍 Checking for amount discrepancies with Razorpay...")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            subscriptions = self.db_session.query(Subscription).filter(
                and_(
                    Subscription.created_at >= cutoff_date,
                    Subscription.status == "active"
                )
            ).all()
            
            for subscription in subscriptions:
                self.reconciliation_results["total_checks"] += 1
                
                # Find corresponding payment transaction
                payment_transaction = self.db_session.query(PaymentTransaction).filter(
                    PaymentTransaction.user_id == subscription.user_id
                ).order_by(desc(PaymentTransaction.created_at)).first()
                
                if payment_transaction:
                    # Verify amount matches Razorpay
                    payment_result = await razorpay_service.fetch_payment_details_from_razorpay(
                        payment_transaction.razorpay_payment_id
                    )
                    
                    if payment_result["success"]:
                        actual_amount = payment_result["payment"]["amount"]
                        recorded_amount = subscription.amount
                        
                        if actual_amount != recorded_amount:
                            logger.warning(f"⚠️ AMOUNT DISCREPANCY: Subscription {subscription.id}")
                            logger.warning(f"   Razorpay: ₹{actual_amount/100:.2f}, System: ₹{recorded_amount/100:.2f}")
                            
                            await self._fix_amount_discrepancy(subscription, actual_amount, recorded_amount)
                
        except Exception as e:
            logger.error(f"❌ Error checking amount discrepancies: {e}")
    
    async def _check_missing_payment_confirmations(self, days_back: int):
        """
        Find successful payments that didn't receive confirmation emails
        """
        logger.info("🔍 Checking for missing payment confirmation emails...")
        
        try:
            # This would require email tracking implementation
            # For now, we'll log that this check is needed
            logger.info("📧 Email confirmation tracking not yet implemented")
            
        except Exception as e:
            logger.error(f"❌ Error checking missing payment confirmations: {e}")
    
    async def _check_duplicate_payments(self, days_back: int):
        """
        Find duplicate payments for the same user/plan
        """
        logger.info("🔍 Checking for duplicate payments...")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Find users with multiple active subscriptions (potential duplicates)
            from sqlalchemy import func
            
            duplicate_subscriptions = self.db_session.query(
                Subscription.user_id,
                func.count(Subscription.id).label('count')
            ).filter(
                and_(
                    Subscription.created_at >= cutoff_date,
                    Subscription.status == "active"
                )
            ).group_by(Subscription.user_id).having(func.count(Subscription.id) > 1).all()
            
            for user_id, count in duplicate_subscriptions:
                logger.warning(f"⚠️ DUPLICATE SUBSCRIPTIONS: User {user_id} has {count} active subscriptions")
                self.reconciliation_results["discrepancies_found"] += 1
                
                # Add to manual review list
                self.reconciliation_results["details"].append({
                    "type": "duplicate_subscriptions",
                    "user_id": user_id,
                    "count": count,
                    "action_required": "manual_cleanup"
                })
                
        except Exception as e:
            logger.error(f"❌ Error checking duplicate payments: {e}")
    
    async def _check_subscription_plan_mismatches(self, days_back: int):
        """
        Verify subscription plans match payment amounts
        """
        logger.info("🔍 Checking for subscription plan mismatches...")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            subscriptions = self.db_session.query(Subscription).filter(
                and_(
                    Subscription.created_at >= cutoff_date,
                    Subscription.status == "active"
                )
            ).all()
            
            for subscription in subscriptions:
                self.reconciliation_results["total_checks"] += 1
                
                # Detect expected plan from amount
                detected_plan = razorpay_service._detect_plan_from_amount(subscription.amount)
                
                if detected_plan["plan_type"] != subscription.plan_type:
                    logger.warning(f"⚠️ PLAN MISMATCH: Subscription {subscription.id}")
                    logger.warning(f"   Amount suggests: {detected_plan['plan_type']}, Recorded: {subscription.plan_type}")
                    
                    self.reconciliation_results["discrepancies_found"] += 1
                    self.reconciliation_results["details"].append({
                        "type": "plan_mismatch",
                        "subscription_id": subscription.id,
                        "detected_plan": detected_plan["plan_type"],
                        "recorded_plan": subscription.plan_type,
                        "amount": subscription.amount / 100,
                        "action_required": "manual_review"
                    })
                
        except Exception as e:
            logger.error(f"❌ Error checking subscription plan mismatches: {e}")
    
    async def _fix_missing_subscription_activation(self, transaction: PaymentTransaction, razorpay_data: Dict):
        """
        Fix a missing subscription activation
        """
        try:
            logger.info(f"🔧 FIXING: Missing subscription for payment {transaction.razorpay_payment_id}")
            
            # Detect plan from payment amount
            detected_plan = razorpay_service._detect_plan_from_amount(razorpay_data["amount"])
            
            # Create the missing subscription
            if detected_plan["plan_type"] == "pro_regular":
                end_date = datetime.utcnow() + timedelta(days=30)
            elif detected_plan["plan_type"] == "pro_exclusive":
                end_date = datetime(2025, 12, 31, 23, 59, 0)
            else:
                logger.error(f"❌ Unknown plan type detected: {detected_plan}")
                return
            
            subscription = Subscription(
                id=str(__import__('uuid').uuid4()),
                user_id=transaction.user_id,
                plan_type=detected_plan["plan_type"],
                amount=razorpay_data["amount"],
                status="active",
                current_period_start=datetime.utcnow(),
                current_period_end=end_date,
                auto_renew=detected_plan["plan_type"] == "pro_regular",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(subscription)
            self.db_session.commit()
            
            self.reconciliation_results["fixes_applied"] += 1
            logger.info(f"✅ FIXED: Created missing {detected_plan['plan_type']} subscription")
            
            # Send delayed confirmation email
            user = self.db_session.query(User).filter(User.id == transaction.user_id).first()
            if user:
                try:
                    gmail_service.send_payment_confirmation_email(
                        to_email=user.email,
                        plan_name=detected_plan["plan_type"].replace("_", " ").title(),
                        amount=f"₹{razorpay_data['amount'] / 100:.2f}",
                        payment_id=transaction.razorpay_payment_id,
                        end_date=end_date.strftime("%B %d, %Y")
                    )
                    logger.info(f"📧 Sent delayed confirmation email to {user.email}")
                except Exception as e:
                    logger.error(f"❌ Failed to send delayed confirmation email: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix missing subscription activation: {e}")
            self.db_session.rollback()
    
    async def _fix_amount_discrepancy(self, subscription: Subscription, actual_amount: int, recorded_amount: int):
        """
        Fix amount discrepancy between Razorpay and system records
        """
        try:
            logger.info(f"🔧 FIXING: Amount discrepancy for subscription {subscription.id}")
            
            # Update subscription amount to match Razorpay
            subscription.amount = actual_amount
            subscription.updated_at = datetime.utcnow()
            
            self.db_session.commit()
            self.reconciliation_results["fixes_applied"] += 1
            
            logger.info(f"✅ FIXED: Updated amount from ₹{recorded_amount/100:.2f} to ₹{actual_amount/100:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix amount discrepancy: {e}")
            self.db_session.rollback()
    
    async def _generate_reconciliation_report(self):
        """
        Generate comprehensive reconciliation report
        """
        logger.info("📊 RECONCILIATION SUMMARY REPORT")
        logger.info("=" * 50)
        logger.info(f"Total Checks: {self.reconciliation_results['total_checks']}")
        logger.info(f"Discrepancies Found: {self.reconciliation_results['discrepancies_found']}")
        logger.info(f"Fixes Applied: {self.reconciliation_results['fixes_applied']}")
        logger.info(f"Manual Review Required: {self.reconciliation_results['manual_review_required']}")
        
        if self.reconciliation_results["details"]:
            logger.info("\n📋 DETAILED ISSUES:")
            for detail in self.reconciliation_results["details"]:
                logger.info(f"   {detail['type']}: {detail}")
        else:
            logger.info("✅ No issues requiring attention found")

# Global instance
reconciliation_service = PaymentReconciliationService()

# Cron job function for scheduled reconciliation
async def run_daily_reconciliation():
    """
    Daily scheduled reconciliation job
    """
    try:
        logger.info("🕐 SCHEDULED DAILY PAYMENT RECONCILIATION STARTING")
        result = await reconciliation_service.run_comprehensive_reconciliation(days_back=1)
        
        # Send admin notification if issues found
        if result["discrepancies_found"] > 0:
            # TODO: Send admin alert email
            logger.warning(f"⚠️ ADMIN ALERT: {result['discrepancies_found']} payment discrepancies found")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Daily reconciliation failed: {e}")
        # TODO: Send critical alert to admin
        raise

if __name__ == "__main__":
    # Manual execution for testing
    import asyncio
    asyncio.run(reconciliation_service.run_comprehensive_reconciliation(days_back=7))