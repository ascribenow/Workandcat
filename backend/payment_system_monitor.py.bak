"""
Payment System Health Monitoring
Monitors payment success rates, detects anomalies, and sends alerts
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from sqlalchemy import func, and_, desc
from collections import defaultdict

from database import SessionLocal, PaymentTransaction, PaymentOrder, Subscription, User
from payment_service import razorpay_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentSystemMonitor:
    """
    Real-time payment system health monitoring
    """
    
    def __init__(self):
        self.db_session = SessionLocal()
        self.monitoring_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": "unknown",
            "metrics": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Alert thresholds
        self.THRESHOLDS = {
            "success_rate_critical": 0.85,  # Below 85% success rate
            "success_rate_warning": 0.95,   # Below 95% success rate
            "failed_payments_per_hour": 5,  # More than 5 failures per hour
            "amount_discrepancy_threshold": 100,  # ₹1 discrepancy threshold
            "verification_failure_rate": 0.10,  # More than 10% verification failures
        }
    
    async def run_health_check(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Comprehensive payment system health check
        """
        try:
            logger.info(f"🏥 PAYMENT SYSTEM HEALTH CHECK - Last {hours_back} hours")
            logger.info("=" * 60)
            
            await self._check_payment_success_rates(hours_back)
            await self._check_verification_success_rates(hours_back)
            await self._check_amount_consistency(hours_back)
            await self._check_referral_system_health(hours_back)
            await self._check_subscription_activation_rates(hours_back)
            await self._check_email_delivery_rates(hours_back)
            
            # Determine overall health status
            self._determine_overall_health()
            
            # Generate recommendations
            await self._generate_health_recommendations()
            
            logger.info(f"🎯 OVERALL HEALTH STATUS: {self.monitoring_results['health_status'].upper()}")
            return self.monitoring_results
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Health check failed: {e}")
            self.monitoring_results["health_status"] = "critical_error"
            self.monitoring_results["alerts"].append({
                "level": "critical",
                "message": f"Health check system failure: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
            raise
        finally:
            self.db_session.close()
    
    async def _check_payment_success_rates(self, hours_back: int):
        """
        Monitor payment success vs failure rates
        """
        logger.info("📊 Checking payment success rates...")
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get payment orders from last N hours
            recent_orders = self.db_session.query(PaymentOrder).filter(
                PaymentOrder.created_at >= cutoff_time
            ).all()
            
            total_orders = len(recent_orders)
            paid_orders = len([order for order in recent_orders if order.status == "paid"])
            failed_orders = total_orders - paid_orders
            
            success_rate = paid_orders / total_orders if total_orders > 0 else 1.0
            
            self.monitoring_results["metrics"]["payment_success_rate"] = {
                "total_orders": total_orders,
                "successful_payments": paid_orders,
                "failed_payments": failed_orders,
                "success_rate": round(success_rate, 4),
                "time_period_hours": hours_back
            }
            
            # Check against thresholds
            if success_rate < self.THRESHOLDS["success_rate_critical"]:
                self.monitoring_results["alerts"].append({
                    "level": "critical",
                    "type": "low_success_rate",
                    "message": f"CRITICAL: Payment success rate dropped to {success_rate:.2%}",
                    "success_rate": success_rate,
                    "threshold": self.THRESHOLDS["success_rate_critical"]
                })
            elif success_rate < self.THRESHOLDS["success_rate_warning"]:
                self.monitoring_results["alerts"].append({
                    "level": "warning",
                    "type": "low_success_rate",
                    "message": f"WARNING: Payment success rate at {success_rate:.2%}",
                    "success_rate": success_rate,
                    "threshold": self.THRESHOLDS["success_rate_warning"]
                })
            
            logger.info(f"✅ Payment success rate: {success_rate:.2%} ({paid_orders}/{total_orders})")
            
        except Exception as e:
            logger.error(f"❌ Error checking payment success rates: {e}")
    
    async def _check_verification_success_rates(self, hours_back: int):
        """
        Monitor payment verification success rates
        """
        logger.info("🔐 Checking payment verification rates...")
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get payment transactions (successful verifications)
            verified_payments = self.db_session.query(PaymentTransaction).filter(
                PaymentTransaction.created_at >= cutoff_time
            ).count()
            
            # Get total payment orders that should have been verified
            total_payment_orders = self.db_session.query(PaymentOrder).filter(
                and_(
                    PaymentOrder.created_at >= cutoff_time,
                    PaymentOrder.status == "paid"
                )
            ).count()
            
            verification_rate = verified_payments / total_payment_orders if total_payment_orders > 0 else 1.0
            
            self.monitoring_results["metrics"]["verification_success_rate"] = {
                "total_paid_orders": total_payment_orders,
                "verified_payments": verified_payments,
                "verification_rate": round(verification_rate, 4),
                "time_period_hours": hours_back
            }
            
            # Check for verification failures
            verification_failure_rate = 1 - verification_rate
            if verification_failure_rate > self.THRESHOLDS["verification_failure_rate"]:
                self.monitoring_results["alerts"].append({
                    "level": "critical",
                    "type": "high_verification_failure",
                    "message": f"CRITICAL: {verification_failure_rate:.2%} of payments failing verification",
                    "verification_failure_rate": verification_failure_rate,
                    "threshold": self.THRESHOLDS["verification_failure_rate"]
                })
            
            logger.info(f"✅ Verification rate: {verification_rate:.2%} ({verified_payments}/{total_payment_orders})")
            
        except Exception as e:
            logger.error(f"❌ Error checking verification rates: {e}")
    
    async def _check_amount_consistency(self, hours_back: int):
        """
        Check for amount discrepancies between orders and transactions
        """
        logger.info("💰 Checking amount consistency...")
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Find recent transactions with potential amount issues
            transactions = self.db_session.query(PaymentTransaction).filter(
                PaymentTransaction.created_at >= cutoff_time
            ).all()
            
            amount_discrepancies = []
            total_checked = 0
            
            for transaction in transactions:
                total_checked += 1
                
                # Find corresponding order
                order = self.db_session.query(PaymentOrder).filter(
                    PaymentOrder.razorpay_order_id == transaction.razorpay_order_id
                ).first()
                
                if order and abs(order.amount - transaction.amount) > self.THRESHOLDS["amount_discrepancy_threshold"]:
                    discrepancy = {
                        "transaction_id": transaction.id,
                        "order_amount": order.amount / 100,
                        "transaction_amount": transaction.amount / 100,
                        "difference": (transaction.amount - order.amount) / 100
                    }
                    amount_discrepancies.append(discrepancy)
            
            self.monitoring_results["metrics"]["amount_consistency"] = {
                "total_checked": total_checked,
                "discrepancies_found": len(amount_discrepancies),
                "discrepancy_rate": len(amount_discrepancies) / total_checked if total_checked > 0 else 0,
                "discrepancies": amount_discrepancies[:5]  # Show max 5 examples
            }
            
            if amount_discrepancies:
                self.monitoring_results["alerts"].append({
                    "level": "warning",
                    "type": "amount_discrepancies",
                    "message": f"Found {len(amount_discrepancies)} amount discrepancies",
                    "count": len(amount_discrepancies)
                })
            
            logger.info(f"✅ Amount consistency: {len(amount_discrepancies)} discrepancies in {total_checked} transactions")
            
        except Exception as e:
            logger.error(f"❌ Error checking amount consistency: {e}")
    
    async def _check_referral_system_health(self, hours_back: int):
        """
        Monitor referral system performance
        """
        logger.info("🎁 Checking referral system health...")
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get recent orders with referral codes
            from referral_service import ReferralUsage
            
            recent_referral_uses = self.db_session.query(ReferralUsage).filter(
                ReferralUsage.used_at >= cutoff_time
            ).count()
            
            # Get total payments in the same period
            total_payments = self.db_session.query(PaymentTransaction).filter(
                PaymentTransaction.created_at >= cutoff_time
            ).count()
            
            referral_usage_rate = recent_referral_uses / total_payments if total_payments > 0 else 0
            
            self.monitoring_results["metrics"]["referral_system"] = {
                "referral_uses": recent_referral_uses,
                "total_payments": total_payments,
                "referral_usage_rate": round(referral_usage_rate, 4),
                "time_period_hours": hours_back
            }
            
            logger.info(f"✅ Referral usage rate: {referral_usage_rate:.2%} ({recent_referral_uses}/{total_payments})")
            
        except Exception as e:
            logger.error(f"❌ Error checking referral system: {e}")
    
    async def _check_subscription_activation_rates(self, hours_back: int):
        """
        Monitor subscription activation success rates
        """
        logger.info("📱 Checking subscription activation rates...")
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get successful payments
            successful_payments = self.db_session.query(PaymentTransaction).filter(
                and_(
                    PaymentTransaction.created_at >= cutoff_time,
                    PaymentTransaction.status == "captured"
                )
            ).count()
            
            # Get subscriptions created in the same period
            new_subscriptions = self.db_session.query(Subscription).filter(
                and_(
                    Subscription.created_at >= cutoff_time,
                    Subscription.status == "active"
                )
            ).count()
            
            activation_rate = new_subscriptions / successful_payments if successful_payments > 0 else 1.0
            
            self.monitoring_results["metrics"]["subscription_activation"] = {
                "successful_payments": successful_payments,
                "activated_subscriptions": new_subscriptions,
                "activation_rate": round(activation_rate, 4),
                "time_period_hours": hours_back
            }
            
            if activation_rate < 0.95:  # Less than 95% activation rate
                self.monitoring_results["alerts"].append({
                    "level": "warning",
                    "type": "low_activation_rate",
                    "message": f"Subscription activation rate at {activation_rate:.2%}",
                    "activation_rate": activation_rate
                })
            
            logger.info(f"✅ Subscription activation rate: {activation_rate:.2%} ({new_subscriptions}/{successful_payments})")
            
        except Exception as e:
            logger.error(f"❌ Error checking subscription activation rates: {e}")
    
    async def _check_email_delivery_rates(self, hours_back: int):
        """
        Monitor email confirmation delivery (placeholder for future implementation)
        """
        logger.info("📧 Checking email delivery rates...")
        
        # TODO: Implement email delivery tracking
        self.monitoring_results["metrics"]["email_delivery"] = {
            "status": "not_implemented",
            "note": "Email delivery tracking needs implementation"
        }
        
        logger.info("📧 Email delivery tracking not yet implemented")
    
    def _determine_overall_health(self):
        """
        Determine overall system health based on alerts
        """
        critical_alerts = len([alert for alert in self.monitoring_results["alerts"] if alert.get("level") == "critical"])
        warning_alerts = len([alert for alert in self.monitoring_results["alerts"] if alert.get("level") == "warning"])
        
        if critical_alerts > 0:
            self.monitoring_results["health_status"] = "critical"
        elif warning_alerts > 2:
            self.monitoring_results["health_status"] = "degraded"
        elif warning_alerts > 0:
            self.monitoring_results["health_status"] = "warning"
        else:
            self.monitoring_results["health_status"] = "healthy"
    
    async def _generate_health_recommendations(self):
        """
        Generate actionable recommendations based on monitoring results
        """
        recommendations = []
        
        # Check success rate recommendations
        metrics = self.monitoring_results["metrics"]
        
        if "payment_success_rate" in metrics:
            success_rate = metrics["payment_success_rate"]["success_rate"]
            if success_rate < 0.90:
                recommendations.append({
                    "priority": "high",
                    "category": "payment_processing",
                    "recommendation": "Investigate payment gateway configuration and error patterns",
                    "reason": f"Payment success rate at {success_rate:.2%}"
                })
        
        if "verification_success_rate" in metrics:
            verification_rate = metrics["verification_success_rate"]["verification_rate"]
            if verification_rate < 0.95:
                recommendations.append({
                    "priority": "high",
                    "category": "payment_verification",
                    "recommendation": "Review payment verification logic and error handling",
                    "reason": f"Verification rate at {verification_rate:.2%}"
                })
        
        if "amount_consistency" in metrics:
            discrepancy_count = metrics["amount_consistency"]["discrepancies_found"]
            if discrepancy_count > 0:
                recommendations.append({
                    "priority": "medium",
                    "category": "data_integrity",
                    "recommendation": "Run payment reconciliation to fix amount discrepancies",
                    "reason": f"{discrepancy_count} amount discrepancies found"
                })
        
        self.monitoring_results["recommendations"] = recommendations

# Global instance
payment_monitor = PaymentSystemMonitor()

# Function for scheduled health checks
async def run_hourly_health_check():
    """
    Hourly scheduled health check
    """
    try:
        logger.info("🕐 SCHEDULED HOURLY HEALTH CHECK")
        result = await payment_monitor.run_health_check(hours_back=1)
        
        # Send alerts if critical issues found
        critical_alerts = [alert for alert in result["alerts"] if alert.get("level") == "critical"]
        if critical_alerts:
            logger.error(f"🚨 CRITICAL ALERTS: {len(critical_alerts)} critical issues detected")
            # TODO: Send immediate admin notification
        
        return result
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Hourly health check failed: {e}")
        raise

if __name__ == "__main__":
    # Manual execution for testing
    import asyncio
    asyncio.run(payment_monitor.run_health_check(hours_back=24))