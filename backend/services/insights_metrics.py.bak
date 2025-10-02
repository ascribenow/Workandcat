"""
Minimal insights observability - just two metrics
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from database import SessionLocal, UserDashboardInsights, UserPreSessionInsights

logger = logging.getLogger(__name__)

class InsightsMetrics:
    def __init__(self):
        self.refresh_failures = 0  # In-memory counter (simple)
    
    def increment_refresh_failures(self):
        """Track refresh failures"""
        self.refresh_failures += 1
        logger.warning(f"Insights refresh failure count: {self.refresh_failures}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get minimal metrics for observability"""
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            
            # Get dashboard cache age
            dashboard_entry = db.query(UserDashboardInsights).order_by(
                UserDashboardInsights.last_updated_at.desc()
            ).first()
            
            dashboard_age_seconds = 0
            if dashboard_entry:
                age_delta = now - dashboard_entry.last_updated_at.replace(tzinfo=timezone.utc)
                dashboard_age_seconds = age_delta.total_seconds()
            
            # Get pre-session cache age
            presession_entry = db.query(UserPreSessionInsights).order_by(
                UserPreSessionInsights.last_updated_at.desc()
            ).first()
            
            presession_age_seconds = 0
            if presession_entry:
                age_delta = now - presession_entry.last_updated_at.replace(tzinfo=timezone.utc)
                presession_age_seconds = age_delta.total_seconds()
            
            return {
                "insights_cache_age_seconds": {
                    "dashboard": dashboard_age_seconds,
                    "pre_session": presession_age_seconds
                },
                "insights_refresh_failures_total": self.refresh_failures
            }
            
        except Exception as e:
            logger.error(f"Error getting insights metrics: {e}")
            return {
                "insights_cache_age_seconds": {"dashboard": 0, "pre_session": 0},
                "insights_refresh_failures_total": self.refresh_failures
            }
        finally:
            db.close()

# Global instance
insights_metrics = InsightsMetrics()