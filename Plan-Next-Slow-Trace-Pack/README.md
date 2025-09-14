# Plan-Next Slow Trace Pack - Diagnostic Summary

## Basic Information
- **user_email**: sp@theskinmantra.com
- **sess_seq**: 79 (auto-generated)
- **when_ist**: 2025-09-14 20:21:47 (Asia/Kolkata)
- **env**: learn-planner-1.preview.emergentagent.com
- **request_id**: 2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1:S0:a02efd6a-a4ea-4704-8c82-cff4855f5793

## Critical Finding - Performance Bottleneck Identified

**MAIN ISSUE**: Plan-next request took **98,684ms** (98.7 seconds) - far exceeding the 3-10 second target.

### Timing Breakdown:
- **Total Duration**: 98,684ms
- **LLM Planner**: ~95,000ms (96% of total time)
- **Database Write**: 1,233ms  
- **Pack Load**: 947ms
- **Other/Pipeline**: 96,504ms (includes LLM processing)

### Root Cause Analysis:
1. **LLM Planner Failure**: OpenAI GPT-4o-mini failed schema validation after 1 retry
2. **Schema Validation Error**: Missing `item_id` field in JSON response  
3. **Fallback System**: Successfully generated valid 12-question pack (3-6-3 distribution)
4. **Cold Start Mode**: User had 0 previous sessions, triggering cold-start pipeline

### Database Evidence:
- **Questions Available**: Easy: 87 total, Medium: 196 total, Hard: 105 total
- **PYQ Constraints Met**: pyq15: 17 available, pyq10: 346 available  
- **ORDER BY RANDOM()**: Causing expensive table scans (see EXPLAIN plans)

### LLM Performance:
- **Provider**: OpenAI GPT-4o-mini
- **Status**: SCHEMA_VALIDATION_FAILED after 1 retry
- **Fallback**: Success - deterministic planner generated valid pack
- **Processing Time**: ~95 seconds (extremely slow)

## Bundle Contents

### trace/
- `plan_next_trace.json` - Main slow request (98,684ms)
- `plan_next_trace_fast.json` - Cached/idempotent request (1,895ms)

### db/
- `availability_snapshot.sql.txt` - Question pool analysis
- `indexes.txt` - Current database indexes
- `sql_*.sql` files - Actual candidate selection queries  
- `plan_*.txt` files - EXPLAIN ANALYZE results
- `pack_row.json` - Saved session pack metadata

### llm/
- `planner_meta.json` - LLM failure details and schema issues

### frontend/
- `waterfall_plan_next.png` - Network timing screenshot
- `fe_config.json` - Frontend timeout configuration

### runtime/
- `limits.json` - Current timeout and infrastructure limits

## Recommended Fixes

1. **LLM Schema Fix**: Update system prompt to ensure `item_id` field is always present
2. **Query Optimization**: Replace `ORDER BY RANDOM()` with more efficient sampling
3. **Database Indexes**: Add covering indexes for candidate selection queries
4. **LLM Timeout**: Implement shorter timeout with faster fallback
5. **Performance Target**: Optimize to achieve 3-10 second response time

The bundle provides complete diagnostic data to pinpoint the exact performance bottleneck and implement targeted fixes.