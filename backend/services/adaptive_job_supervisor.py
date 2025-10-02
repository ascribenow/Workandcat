"""
Enhanced Adaptive Job Supervisor
Provides intelligent supervision, monitoring, and failure recovery for the adaptive engine
"""

import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from database import SessionLocal
from sqlalchemy import text
from services.bg_job_queue import job_queue

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    
class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, block requests
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class JobMetrics:
    job_type: str
    total_jobs: int
    succeeded: int
    failed: int
    success_rate: float
    avg_processing_time_ms: Optional[float]
    recent_failures: List[str]

@dataclass
class CircuitBreaker:
    job_type: str
    state: CircuitBreakerState
    failure_count: int
    last_failure_time: Optional[datetime]
    failure_threshold: int = 5
    recovery_timeout_minutes: int = 10

class AdaptiveJobSupervisor:
    """
    Intelligent supervisor for adaptive engine background jobs
    Provides monitoring, circuit breakers, health checks, and failure recovery
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.job_types = ["SUMMARIZE_SESSION", "PLAN_NEXT_SESSION", "UPDATE_INSIGHTS"]
        self.monitoring_interval = 30  # seconds
        self.is_monitoring = False
        
        # Initialize circuit breakers
        for job_type in self.job_types:
            self.circuit_breakers[job_type] = CircuitBreaker(
                job_type=job_type,
                state=CircuitBreakerState.CLOSED,
                failure_count=0,
                last_failure_time=None
            )
    
    async def start_monitoring(self):
        """Start continuous monitoring of job health"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        logger.info("🔍 Adaptive Job Supervisor: Starting continuous monitoring")
        
        while self.is_monitoring:
            try:
                await self._monitor_job_health()
                await self._update_circuit_breakers()
                await self._perform_maintenance()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"❌ Supervisor monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.is_monitoring = False
        logger.info("⏹️ Adaptive Job Supervisor: Monitoring stopped")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report"""
        try:
            job_metrics = await self._collect_job_metrics()
            circuit_status = self._get_circuit_breaker_status()
            overall_health = await self._assess_overall_health()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": overall_health.value,
                "job_metrics": [
                    {
                        "job_type": metric.job_type,
                        "total_jobs": metric.total_jobs,
                        "success_rate": metric.success_rate,
                        "recent_failures": len(metric.recent_failures),
                        "avg_processing_time_ms": metric.avg_processing_time_ms
                    }
                    for metric in job_metrics
                ],
                "circuit_breakers": circuit_status,
                "recommendations": await self._generate_health_recommendations()
            }
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": HealthStatus.CRITICAL.value,
                "error": str(e)
            }
    
    async def _monitor_job_health(self):
        """Monitor job performance and detect issues"""
        db = SessionLocal()
        try:
            # Check for stuck jobs (running > 10 minutes)
            stuck_jobs = db.execute(text("""
                SELECT id, job_type, started_at
                FROM bg_jobs 
                WHERE status = 'running'
                AND started_at < NOW() - INTERVAL '10 minutes'
            """)).fetchall()
            
            if stuck_jobs:
                logger.warning(f"⚠️ Found {len(stuck_jobs)} stuck jobs")
                for job in stuck_jobs:
                    await self._handle_stuck_job(str(job.id), job.job_type)
            
            # Check for excessive failures
            recent_failures = db.execute(text("""
                SELECT job_type, COUNT(*) as failure_count
                FROM bg_jobs
                WHERE status = 'failed'
                AND created_at > NOW() - INTERVAL '1 hour'
                GROUP BY job_type
                HAVING COUNT(*) > 3
            """)).fetchall()
            
            for failure in recent_failures:
                await self._handle_excessive_failures(failure.job_type, failure.failure_count)
        
        finally:
            db.close()
    
    async def _update_circuit_breakers(self):
        """Update circuit breaker states based on recent job performance"""
        db = SessionLocal()
        try:
            for job_type in self.job_types:
                cb = self.circuit_breakers[job_type]
                
                # Get recent failure count (last 10 minutes)
                recent_failures = db.execute(text("""
                    SELECT COUNT(*) as failures
                    FROM bg_jobs
                    WHERE job_type = :job_type
                    AND status = 'failed'
                    AND created_at > NOW() - INTERVAL '10 minutes'
                """), {"job_type": job_type}).scalar()
                
                # Update circuit breaker state
                if cb.state == CircuitBreakerState.CLOSED:
                    if recent_failures >= cb.failure_threshold:
                        cb.state = CircuitBreakerState.OPEN
                        cb.last_failure_time = datetime.now(timezone.utc)
                        logger.warning(f"🔴 Circuit breaker OPENED for {job_type} (failures: {recent_failures})")
                
                elif cb.state == CircuitBreakerState.OPEN:
                    # Check if recovery timeout has passed
                    if (cb.last_failure_time and 
                        datetime.now(timezone.utc) - cb.last_failure_time > 
                        timedelta(minutes=cb.recovery_timeout_minutes)):
                        cb.state = CircuitBreakerState.HALF_OPEN
                        logger.info(f"🟡 Circuit breaker HALF-OPEN for {job_type} (testing recovery)")
                
                elif cb.state == CircuitBreakerState.HALF_OPEN:
                    # Check if recent attempt succeeded
                    recent_success = db.execute(text("""
                        SELECT COUNT(*) as successes
                        FROM bg_jobs
                        WHERE job_type = :job_type
                        AND status = 'succeeded'
                        AND created_at > NOW() - INTERVAL '5 minutes'
                    """), {"job_type": job_type}).scalar()
                    
                    if recent_success > 0:
                        cb.state = CircuitBreakerState.CLOSED
                        cb.failure_count = 0
                        logger.info(f"🟢 Circuit breaker CLOSED for {job_type} (recovery confirmed)")
                    elif recent_failures > 0:
                        cb.state = CircuitBreakerState.OPEN
                        cb.last_failure_time = datetime.now(timezone.utc)
                        logger.warning(f"🔴 Circuit breaker back to OPEN for {job_type}")
        
        finally:
            db.close()
    
    async def _perform_maintenance(self):
        """Perform routine maintenance tasks"""
        db = SessionLocal()
        try:
            # Clean up old completed jobs (older than 7 days)
            cleaned = db.execute(text("""
                DELETE FROM bg_jobs
                WHERE status IN ('succeeded', 'failed')
                AND created_at < NOW() - INTERVAL '7 days'
            """)).rowcount
            
            if cleaned > 0:
                logger.info(f"🧹 Cleaned up {cleaned} old job records")
                db.commit()
            
            # Reset jobs that have been stuck in 'running' state for too long
            reset_count = db.execute(text("""
                UPDATE bg_jobs
                SET status = 'queued', 
                    started_at = NULL,
                    next_attempt_at = NOW()
                WHERE status = 'running'
                AND started_at < NOW() - INTERVAL '15 minutes'
            """)).rowcount
            
            if reset_count > 0:
                logger.warning(f"⚠️ Reset {reset_count} stuck jobs back to queued")
                db.commit()
        
        finally:
            db.close()
    
    async def _collect_job_metrics(self) -> List[JobMetrics]:
        """Collect comprehensive job performance metrics"""
        db = SessionLocal()
        try:
            metrics = []
            
            for job_type in self.job_types:
                result = db.execute(text("""
                    SELECT 
                        COUNT(*) as total_jobs,
                        SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        AVG(CASE 
                            WHEN status = 'succeeded' AND started_at IS NOT NULL AND completed_at IS NOT NULL
                            THEN EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000
                            ELSE NULL 
                        END) as avg_processing_time_ms
                    FROM bg_jobs
                    WHERE job_type = :job_type
                    AND created_at > NOW() - INTERVAL '24 hours'
                """), {"job_type": job_type}).fetchone()
                
                # Get recent failure messages
                failures = db.execute(text("""
                    SELECT error_message
                    FROM bg_jobs
                    WHERE job_type = :job_type
                    AND status = 'failed'
                    AND created_at > NOW() - INTERVAL '1 hour'
                    ORDER BY created_at DESC
                    LIMIT 5
                """), {"job_type": job_type}).fetchall()
                
                total = result.total_jobs or 0
                succeeded = result.succeeded or 0
                failed = result.failed or 0
                success_rate = (succeeded / total * 100) if total > 0 else 100
                
                metrics.append(JobMetrics(
                    job_type=job_type,
                    total_jobs=total,
                    succeeded=succeeded,
                    failed=failed,
                    success_rate=success_rate,
                    avg_processing_time_ms=result.avg_processing_time_ms,
                    recent_failures=[f.error_message[:100] for f in failures]
                ))
            
            return metrics
        
        finally:
            db.close()
    
    def _get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current circuit breaker status"""
        return {
            job_type: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
            }
            for job_type, cb in self.circuit_breakers.items()
        }
    
    async def _assess_overall_health(self) -> HealthStatus:
        """Assess overall system health"""
        metrics = await self._collect_job_metrics()
        
        critical_issues = 0
        warning_issues = 0
        
        for metric in metrics:
            # Critical: Success rate < 70% or no recent jobs
            if metric.success_rate < 70 or metric.total_jobs == 0:
                critical_issues += 1
            # Warning: Success rate < 90%
            elif metric.success_rate < 90:
                warning_issues += 1
        
        # Check circuit breaker states
        open_circuits = sum(1 for cb in self.circuit_breakers.values() 
                           if cb.state == CircuitBreakerState.OPEN)
        
        if critical_issues > 0 or open_circuits > 1:
            return HealthStatus.CRITICAL
        elif warning_issues > 0 or open_circuits > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    async def _generate_health_recommendations(self) -> List[str]:
        """Generate actionable health recommendations"""
        recommendations = []
        metrics = await self._collect_job_metrics()
        
        for metric in metrics:
            if metric.success_rate < 70:
                recommendations.append(f"CRITICAL: {metric.job_type} has {metric.success_rate:.1f}% success rate - investigate immediately")
            elif metric.success_rate < 90:
                recommendations.append(f"WARNING: {metric.job_type} has {metric.success_rate:.1f}% success rate - monitor closely")
            
            if metric.avg_processing_time_ms and metric.avg_processing_time_ms > 60000:  # > 1 minute
                recommendations.append(f"PERFORMANCE: {metric.job_type} avg processing time is {metric.avg_processing_time_ms/1000:.1f}s - optimize")
        
        # Check for open circuit breakers
        open_circuits = [job_type for job_type, cb in self.circuit_breakers.items() 
                        if cb.state == CircuitBreakerState.OPEN]
        if open_circuits:
            recommendations.append(f"CIRCUIT BREAKER: {', '.join(open_circuits)} circuits are open - manual intervention required")
        
        if not recommendations:
            recommendations.append("✅ All systems operating normally")
        
        return recommendations
    
    async def _handle_stuck_job(self, job_id: str, job_type: str):
        """Handle jobs that are stuck in running state"""
        logger.warning(f"⚠️ Handling stuck job: {job_id[:8]} ({job_type})")
        
        db = SessionLocal()
        try:
            # Reset job to queued for retry
            db.execute(text("""
                UPDATE bg_jobs
                SET status = 'queued',
                    started_at = NULL,
                    next_attempt_at = NOW() + INTERVAL '1 minute'
                WHERE id = :job_id
            """), {"job_id": job_id})
            db.commit()
            logger.info(f"🔄 Reset stuck job {job_id[:8]} to queued")
        
        finally:
            db.close()
    
    async def _handle_excessive_failures(self, job_type: str, failure_count: int):
        """Handle job types with excessive failures"""
        logger.warning(f"⚠️ Excessive failures detected: {job_type} ({failure_count} failures in 1 hour)")
        
        # Update circuit breaker
        cb = self.circuit_breakers[job_type]
        cb.failure_count = failure_count
        
        # Could implement additional recovery strategies here:
        # - Restart specific workers
        # - Clear dead letter queue
        # - Send alerts to administrators
        # - Temporarily disable job type

# Global supervisor instance
adaptive_supervisor = AdaptiveJobSupervisor()

# Health check endpoint helper
async def get_supervisor_health():
    """Get supervisor health for API endpoint"""
    return await adaptive_supervisor.get_system_health()