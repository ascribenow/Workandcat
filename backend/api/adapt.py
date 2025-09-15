#!/usr/bin/env python3
"""
Adaptive Session API Endpoints - V2 CUTOVER COMPLETE

V2 Implementation Active:
- Clean pipeline with no legacy paths
- Performance target: <10s (was 98.7s)  
- Deterministic candidate selection
- 15s LLM timeout with fallback
"""

# V2 CUTOVER: Import V2 router
from api.v2_adapt import router

# V2 CUTOVER COMPLETE - All endpoints now use V2 implementation