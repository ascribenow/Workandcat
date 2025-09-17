"""
Free Tier Session Management Service
Handles the complex session allocation logic for free tier users:
- 10 initial sessions upon signup
- 2 sessions per 7-day cycle after initial 10
- Carry forward unused sessions to next cycle
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from database import User

logger = logging.getLogger(__name__)

# IST Timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class FreeTierSessionService:
    """Manages free tier session allocation with carry forward logic"""
    
    def __init__(self):
        self.initial_sessions = 10
        self.weekly_allocation = 2
        self.cycle_days = 7
    
    def get_user_session_status(self, user_id: str, user_email: str, db: Session) -> Dict[str, Any]:
        """
        Get comprehensive session status for free tier user
        
        Returns:
        {
            "sessions_available": int,
            "sessions_used_this_cycle": int,
            "cycle_start_date": str,
            "cycle_end_date": str, 
            "is_initial_period": bool,
            "carry_forward_sessions": int,
            "next_allocation_date": str,
            "upgrade_prompt_needed": bool
        }
        """
        try:
            # Get user signup date
            user_result = db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            signup_date = user.created_at
            
            # Convert to IST
            if signup_date.tzinfo is None:
                signup_date = signup_date.replace(tzinfo=timezone.utc)
            signup_date_ist = signup_date.astimezone(IST)
            
            current_time_ist = datetime.now(IST)
            
            # Count total completed sessions
            total_sessions_result = db.execute(text("""
                SELECT COUNT(*) as total
                FROM sessions 
                WHERE user_id = :user_id AND status = 'completed'
            """), {"user_id": user_id})
            
            total_sessions = total_sessions_result.fetchone().total
            
            # Check if still in initial 10 sessions period
            if total_sessions < self.initial_sessions:
                return {
                    "sessions_available": self.initial_sessions - total_sessions,
                    "sessions_used_this_cycle": total_sessions,
                    "cycle_start_date": signup_date_ist.isoformat(),
                    "cycle_end_date": None,
                    "is_initial_period": True,
                    "carry_forward_sessions": 0,
                    "next_allocation_date": None,
                    "upgrade_prompt_needed": False,
                    "status": "initial_period"
                }
            
            # Calculate current cycle after initial period
            days_since_initial = (current_time_ist - signup_date_ist).days
            initial_period_days = self._estimate_initial_period_duration(user_id, db)
            
            # Days since weekly cycles started
            days_since_weekly_start = max(0, days_since_initial - initial_period_days)
            
            # Calculate current cycle number and dates
            current_cycle = days_since_weekly_start // self.cycle_days
            days_into_current_cycle = days_since_weekly_start % self.cycle_days
            
            # Current cycle start date
            cycle_start = signup_date_ist + timedelta(days=initial_period_days + (current_cycle * self.cycle_days))
            cycle_end = cycle_start + timedelta(days=self.cycle_days)
            
            # Count sessions used in current cycle
            sessions_this_cycle_result = db.execute(text("""
                SELECT COUNT(*) as count
                FROM sessions 
                WHERE user_id = :user_id 
                AND status = 'completed'
                AND created_at >= :cycle_start
                AND created_at < :cycle_end
            """), {
                "user_id": user_id,
                "cycle_start": cycle_start.astimezone(timezone.utc),  # Convert back to UTC for DB
                "cycle_end": cycle_end.astimezone(timezone.utc)
            })
            
            sessions_used_this_cycle = sessions_this_cycle_result.fetchone().count
            
            # Calculate carry forward sessions
            carry_forward = self._calculate_carry_forward_sessions(
                user_id, signup_date_ist, current_cycle, db
            )
            
            # Total available = weekly allocation + carry forward - used this cycle
            base_allocation = self.weekly_allocation
            total_available = base_allocation + carry_forward - sessions_used_this_cycle
            sessions_available = max(0, total_available)
            
            # Check if upgrade prompt needed (after 10th session)
            upgrade_prompt_needed = total_sessions >= self.initial_sessions and not self._has_seen_upgrade_prompt(user_id, db)
            
            return {
                "sessions_available": sessions_available,
                "sessions_used_this_cycle": sessions_used_this_cycle,
                "cycle_start_date": cycle_start.isoformat(),
                "cycle_end_date": cycle_end.isoformat(),
                "is_initial_period": False,
                "carry_forward_sessions": carry_forward,
                "next_allocation_date": cycle_end.isoformat(),
                "upgrade_prompt_needed": upgrade_prompt_needed,
                "status": "weekly_cycle",
                "cycle_number": current_cycle + 1,
                "total_sessions_completed": total_sessions
            }
            
        except Exception as e:
            logger.error(f"Error getting free tier session status: {e}")
            # Return safe defaults
            return {
                "sessions_available": 0,
                "sessions_used_this_cycle": 0,
                "cycle_start_date": current_time_ist.isoformat(),
                "cycle_end_date": (current_time_ist + timedelta(days=7)).isoformat(),
                "is_initial_period": False,
                "carry_forward_sessions": 0,
                "next_allocation_date": (current_time_ist + timedelta(days=7)).isoformat(),
                "upgrade_prompt_needed": True,
                "status": "error"
            }
    
    def _estimate_initial_period_duration(self, user_id: str, db: Session) -> int:
        """Estimate how many days the initial 10 sessions took"""
        try:
            # Get the 10th completed session date
            result = db.execute(text("""
                SELECT created_at
                FROM sessions 
                WHERE user_id = :user_id AND status = 'completed'
                ORDER BY created_at ASC
                LIMIT 1 OFFSET 9
            """), {"user_id": user_id})
            
            tenth_session = result.fetchone()
            
            if tenth_session:
                # Get user signup date
                user_result = db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()
                
                if user:
                    signup_date = user.created_at
                    if signup_date.tzinfo is None:
                        signup_date = signup_date.replace(tzinfo=timezone.utc)
                    
                    tenth_session_date = tenth_session.created_at
                    if tenth_session_date.tzinfo is None:
                        tenth_session_date = tenth_session_date.replace(tzinfo=timezone.utc)
                    
                    days_taken = (tenth_session_date - signup_date).days
                    return max(1, days_taken)  # At least 1 day
            
            # Default to 30 days if we can't determine
            return 30
            
        except Exception as e:
            logger.warning(f"Could not estimate initial period duration: {e}")
            return 30  # Safe default
    
    def _calculate_carry_forward_sessions(self, user_id: str, signup_date_ist: datetime, current_cycle: int, db: Session) -> int:
        """Calculate total carry forward sessions from previous cycles"""
        carry_forward = 0
        
        try:
            # For each completed cycle, check if user got full allocation
            for cycle_num in range(current_cycle):
                cycle_start = signup_date_ist + timedelta(days=30 + (cycle_num * self.cycle_days))  # 30 days estimated initial period
                cycle_end = cycle_start + timedelta(days=self.cycle_days)
                
                # Count sessions used in this past cycle
                sessions_result = db.execute(text("""
                    SELECT COUNT(*) as count
                    FROM sessions 
                    WHERE user_id = :user_id 
                    AND status = 'completed'
                    AND created_at >= :cycle_start
                    AND created_at < :cycle_end
                """), {
                    "user_id": user_id,
                    "cycle_start": cycle_start.astimezone(timezone.utc),
                    "cycle_end": cycle_end.astimezone(timezone.utc)
                })
                
                sessions_used = sessions_result.fetchone().count
                unused_sessions = max(0, self.weekly_allocation - sessions_used)
                carry_forward += unused_sessions
            
            return carry_forward
            
        except Exception as e:
            logger.warning(f"Error calculating carry forward: {e}")
            return 0
    
    def _has_seen_upgrade_prompt(self, user_id: str, db: Session) -> bool:
        """Check if user has already been shown the upgrade prompt"""
        try:
            # You could store this in a user_preferences table or user flags
            # For now, assume they haven't seen it
            return False
        except Exception as e:
            logger.warning(f"Error checking upgrade prompt status: {e}")
            return False
    
    def can_start_session(self, user_id: str, user_email: str, db: Session) -> Dict[str, Any]:
        """Check if user can start a new session and update session count"""
        session_status = self.get_user_session_status(user_id, user_email, db)
        
        can_start = session_status["sessions_available"] > 0
        
        return {
            "can_start_session": can_start,
            "sessions_remaining": session_status["sessions_available"],
            "reason": "Available" if can_start else "No sessions remaining in current cycle",
            "upgrade_prompt_needed": session_status["upgrade_prompt_needed"],
            "cycle_info": {
                "cycle_end_date": session_status.get("cycle_end_date"),
                "next_allocation_date": session_status.get("next_allocation_date"),
                "carry_forward_sessions": session_status.get("carry_forward_sessions", 0)
            }
        }

# Global instance
free_tier_service = FreeTierSessionService()