#!/usr/bin/env python3
"""
Telemetry and Metrics Service
Handles observability for adaptive session orchestration
"""

import logging
import json
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TelemetryService:
    """Service for emitting metrics and telemetry data"""
    
    def __init__(self):
        self.metrics_log = logging.getLogger("metrics")
        
    def emit_metric(self, metric_name: str, value: Any = 1, tags: Dict[str, str] = None):
        """
        Emit a metric for monitoring
        
        Args:
            metric_name: Name of the metric
            value: Metric value  
            tags: Optional tags for filtering/grouping
        """
        tags = tags or {}
        
        metric_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "metric": metric_name,
            "value": value,
            "tags": tags
        }
        
        self.metrics_log.info(json.dumps(metric_data))
        
    def emit_session_planned(self, constraint_report: Dict[str, Any], cold_start: bool = False, pool_expanded: bool = False):
        """Emit metrics for session planning completion"""
        
        # Basic planning metrics
        self.emit_metric("adapt.pack.generated", tags={
            "cold_start": str(cold_start),
            "pool_expanded": str(pool_expanded)
        })
        
        # Relaxation metrics
        relaxed_items = constraint_report.get("relaxed", [])
        if relaxed_items:
            for item in relaxed_items:
                reason = item.get("name", "unknown")
                self.emit_metric("adapt.relaxation.count", tags={"type": reason})
        
        # Meta metrics
        meta = constraint_report.get("meta", {})
        
        if "processing_time_ms" in meta:
            self.emit_metric("adapt.latency.ms", value=meta["processing_time_ms"], tags={"stage": "planner"})
            
        if "tokens_used" in meta:
            self.emit_metric("adapt.tokens", value=meta["tokens_used"], tags={"stage": "planner"})
            
        if "retry_used" in meta:
            self.emit_metric("adapt.planner.retry_used", value=1 if meta["retry_used"] else 0)
            
    def emit_pyq_shortfall(self, shortfall_type: str, expected: int, actual: int):
        """Emit critical alert for PYQ constraint violations"""
        self.emit_metric("adapt.pyq.shortfall_events", value=1, tags={
            "shortfall_type": shortfall_type,
            "expected": str(expected),
            "actual": str(actual)
        })
        
        logger.critical(f"🚨 PYQ SHORTFALL: {shortfall_type} expected {expected}, got {actual}")

# Global telemetry service instance
telemetry_service = TelemetryService()