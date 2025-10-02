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
        
    def emit_coverage_session_metrics(self, user_id: str, session_data: Dict):
        """Emit coverage session metrics with computed diversity"""
        
        # Timing metrics
        pipeline_telemetry = session_data.get("pipeline_telemetry", {})
        self.emit_metric("coverage.summarizer_ms", pipeline_telemetry.get("summarizer_ms", 0))
        self.emit_metric("coverage.planner_ms", pipeline_telemetry.get("planner_ms", 0))
        self.emit_metric("coverage.build_ms_total", pipeline_telemetry.get("total_ms", 0))
        
        # Coverage audit metrics (accurate from final pack)
        audit = session_data.get("audit", {})
        
        # Shape metrics (3-6-3 validation)
        shape = audit.get("shape", {})
        self.emit_metric("coverage.pack.easy_count", shape.get("easy", 0))
        self.emit_metric("coverage.pack.medium_count", shape.get("medium", 0))
        self.emit_metric("coverage.pack.hard_count", shape.get("hard", 0))
        
        # PACK-LEVEL PYQ metrics (from final pack)
        pyq = audit.get("pyq", {})
        self.emit_metric("coverage.pyq.pack_level_count_1_5", pyq.get("1_5", 0))  
        self.emit_metric("coverage.pyq.pack_level_count_1_0", pyq.get("1_0", 0))
        
        # Borrow metrics (track scarcity per band)
        borrow = audit.get("borrow", {})
        self.emit_metric("coverage.borrow.easy", borrow.get("easy", 0))
        self.emit_metric("coverage.borrow.medium", borrow.get("medium", 0))
        self.emit_metric("coverage.borrow.hard", borrow.get("hard", 0))
        
        # Cap relaxation metrics (from your fix)
        cap_relax = audit.get("cap_relaxations", {})
        self.emit_metric("coverage.cap_relax.easy", cap_relax.get("easy", 0))
        self.emit_metric("coverage.cap_relax.medium", cap_relax.get("medium", 0))
        self.emit_metric("coverage.cap_relax.hard", cap_relax.get("hard", 0))
        
        # Force fill + shape compromise indicators
        self.emit_metric("coverage.pack.force_fill", audit.get("force_fill", 0))
        self.emit_metric("coverage.shape_compromised", 1 if audit.get("shape_compromised_due_to_inventory") else 0)
        
        # COMPUTE and emit diversity metric from actual pack
        pack = session_data.get("pack", [])
        unique_subtypes = set()
        for item in pack:
            subtype = f"{item.get('subcategory', 'Unknown')}|{item.get('type_of_question', 'Unknown')}"
            unique_subtypes.add(subtype)
        
        distinct_subtype_count = len(unique_subtypes)
        self.emit_metric("coverage.distinct_subtype_in_pack", distinct_subtype_count)
        
        # Planner model usage tracking
        planner_model = pipeline_telemetry.get("planner_model", "unknown")
        self.emit_metric("coverage.planner.model_used", tags={"model": planner_model})
        
        # Pack size validation (should always be 12)
        pack_size = len(pack)
        self.emit_metric("coverage.pack.size", pack_size)
        if pack_size != 12:
            self.emit_metric("coverage.pack.size_error", tags={"actual_size": str(pack_size)})
        
        logger.info(f"📊 Coverage telemetry emitted for user {user_id[:8]}: {distinct_subtype_count} distinct subtypes, {planner_model} planner")

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