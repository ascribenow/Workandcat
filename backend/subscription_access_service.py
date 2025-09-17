"""
Subscription Access Control Service
Handles feature access based on user subscription status
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SubscriptionAccessService:
    """Service to manage subscription-based feature access"""
    
    def __init__(self):
        self.plan_features = {
            "free_tier": {
                "session_limit": None,  # Special logic: 10 initial + 2/week with carry forward
                "unlimited_sessions": False,
                "ask_twelvr": True,  # FREE TIER HAS ASK TWELVR
                "features": ["ask_twelvr", "adaptive_sessions"]
            },
            "pro_regular": {
                "session_limit": None,  # Unlimited
                "unlimited_sessions": True,
                "ask_twelvr": True,  # PRO REGULAR HAS ASK TWELVR  
                "features": ["unlimited_sessions", "ask_twelvr"],
                "available_after": "2025-12-31 23:59:59"  # Available after Dec 31, 2025
            },
            "pro_exclusive": {
                "session_limit": None,  # Unlimited
                "unlimited_sessions": True,
                "ask_twelvr": True,  # PRO EXCLUSIVE HAS ASK TWELVR
                "features": ["unlimited_sessions", "ask_twelvr"],
                "available_until": "2025-12-31 23:59:59"  # Available until Dec 31, 2025
            }
        }
    
    def get_user_access_level(self, user_id: str, user_email: str, db: Session) -> Dict[str, Any]:
        """Get user's current access level based on subscriptions and privileges"""
        try:
            from database import Subscription, PrivilegedEmail
            
            # Check if user is in privileged emails (admin-granted unlimited access)
            privileged_result = db.execute(
                select(PrivilegedEmail).where(PrivilegedEmail.email == user_email.lower())
            )
            is_privileged = privileged_result.scalar() is not None
            
            if is_privileged:
                return {
                    "access_type": "privileged",
                    "plan_type": "privileged",
                    "session_limit": None,
                    "unlimited_sessions": True,
                    "ask_twelvr": True,
                    "features": ["unlimited_sessions", "ask_twelvr", "privileged_access"],
                    "subscription_status": "privileged",
                    "expires_at": None
                }
            
            # Check for active subscriptions
            active_subscription = self._get_active_subscription(user_id, db)
            
            if active_subscription:
                plan_type = active_subscription.plan_type
                plan_config = self.plan_features.get(plan_type, self.plan_features["free_trial"])
                
                return {
                    "access_type": "subscription",
                    "plan_type": plan_type,
                    "session_limit": plan_config["session_limit"],
                    "unlimited_sessions": plan_config["unlimited_sessions"],
                    "ask_twelvr": plan_config["ask_twelvr"],
                    "features": plan_config["features"],
                    "subscription_status": active_subscription.status,
                    "subscription_id": active_subscription.id,
                    "expires_at": active_subscription.current_period_end.isoformat() if active_subscription.current_period_end else None,
                    "auto_renew": active_subscription.auto_renew
                }
            
            # Default to free trial
            plan_config = self.plan_features["free_trial"]
            return {
                "access_type": "free_trial",
                "plan_type": "free_trial",
                "session_limit": plan_config["session_limit"],
                "unlimited_sessions": plan_config["unlimited_sessions"],
                "ask_twelvr": plan_config["ask_twelvr"],
                "features": plan_config["features"],
                "subscription_status": "none",
                "expires_at": None
            }
            
        except Exception as e:
            logger.error(f"Error getting user access level: {e}")
            # Return safe defaults on error
            plan_config = self.plan_features["free_trial"]
            return {
                "access_type": "free_trial",
                "plan_type": "free_trial",
                "session_limit": plan_config["session_limit"],
                "unlimited_sessions": plan_config["unlimited_sessions"],
                "ask_twelvr": plan_config["ask_twelvr"],
                "features": plan_config["features"],
                "subscription_status": "error",
                "expires_at": None
            }
    
    def _get_active_subscription(self, user_id: str, db: Session) -> Optional[Any]:
        """Get user's active subscription"""
        try:
            from database import Subscription
            
            # Get active subscriptions that haven't expired (paused subscriptions don't grant access)
            now = datetime.utcnow()
            
            result = db.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",  # Only active subscriptions grant access
                    Subscription.current_period_end > now
                ).order_by(Subscription.created_at.desc())
            )
            
            return result.scalar()  # Returns most recent active subscription
            
        except Exception as e:
            logger.error(f"Error getting active subscription for user {user_id}: {e}")
            return None
    
    def check_session_access(self, user_id: str, user_email: str, completed_sessions: int, db: Session) -> Dict[str, Any]:
        """Check if user can start a new session"""
        access_level = self.get_user_access_level(user_id, user_email, db)
        
        if access_level["unlimited_sessions"]:
            return {
                "can_start_session": True,
                "sessions_remaining": None,
                "limit_reached": False,
                "access_level": access_level
            }
        
        # For free trial users
        session_limit = access_level["session_limit"]
        sessions_remaining = max(0, session_limit - completed_sessions)
        limit_reached = completed_sessions >= session_limit
        
        return {
            "can_start_session": not limit_reached,
            "sessions_remaining": sessions_remaining,
            "limit_reached": limit_reached,
            "access_level": access_level
        }
    
    def check_feature_access(self, user_id: str, user_email: str, feature_name: str, db: Session) -> Dict[str, Any]:
        """Check if user has access to a specific feature"""
        access_level = self.get_user_access_level(user_id, user_email, db)
        
        has_access = feature_name in access_level["features"] or access_level.get(feature_name, False)
        
        return {
            "has_access": has_access,
            "feature": feature_name,
            "plan_type": access_level["plan_type"],
            "access_type": access_level["access_type"],
            "subscription_status": access_level["subscription_status"]
        }
    
    def expire_subscriptions(self, db: Session) -> Dict[str, Any]:
        """Expire subscriptions that have passed their end date (run as background job)"""
        try:
            from database import Subscription
            
            now = datetime.utcnow()
            
            # Find expired active subscriptions
            expired_result = db.execute(
                select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.current_period_end <= now
                )
            )
            expired_subscriptions = expired_result.scalars().all()
            
            expired_count = 0
            auto_renewed_count = 0
            
            for subscription in expired_subscriptions:
                if subscription.auto_renew and subscription.plan_type == "pro_regular":
                    # Auto-renew Pro Regular (monthly) subscriptions
                    subscription.current_period_start = now
                    subscription.current_period_end = now + timedelta(days=30)
                    auto_renewed_count += 1
                    logger.info(f"Auto-renewed subscription {subscription.id} for user {subscription.user_id}")
                else:
                    # Expire non-renewable or Pro Exclusive subscriptions
                    subscription.status = "expired"
                    expired_count += 1
                    logger.info(f"Expired subscription {subscription.id} for user {subscription.user_id}")
            
            db.commit()
            
            return {
                "success": True,
                "expired_count": expired_count,
                "auto_renewed_count": auto_renewed_count,
                "processed_at": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error expiring subscriptions: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "expired_count": 0,
                "auto_renewed_count": 0
            }

# Global instance
subscription_access_service = SubscriptionAccessService()