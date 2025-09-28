# Adaptive Insights Operational Runbook

## 🚨 Troubleshooting Guide

### **Problem: Blank Card**
**Symptom**: Dashboard shows "Your adaptive insights are being generated..."
**Checks**:
1. `GET /api/insights/metrics` - Check cache age
2. `sudo supervisorctl status bg_worker` - Verify worker running
3. Check backend logs: `tail -f /var/log/supervisor/backend.*.log`

**Fix**:
```bash
# Trigger insight generation manually
curl -X POST "https://your-domain.com/api/insights/trigger" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"user_id": "USER_ID"}'
```

### **Problem: Stale Card**
**Symptom**: Card shows old date (>24h)
**Checks**:
1. `GET /api/insights/metrics` - Check insights_cache_age_seconds
2. Check if UPDATE_INSIGHTS jobs are processing

**Fix**:
```bash
# Manual trigger (same as above)
# Or restart background worker
sudo supervisorctl restart bg_worker
```

### **Problem: High Queue Depth**
**Symptom**: Long delays, many pending jobs
**Checks**:
1. Check PostgreSQL bg_jobs table: `SELECT count(*) FROM bg_jobs WHERE status='queued'`
2. Check worker logs for errors

**Fix**:
```bash
# Restart worker to clear stuck jobs
sudo supervisorctl restart bg_worker
```

## 🎛️ **Feature Flag Control**

### **Enable Global Fallback** (Emergency Cost Control)
```bash
# In backend/.env add:
INSIGHTS_FORCE_FALLBACK=true

# Restart backend
sudo supervisorctl restart backend
```

### **Disable Global Fallback**
```bash
# Remove or set to false in backend/.env:
INSIGHTS_FORCE_FALLBACK=false

# Restart backend
sudo supervisorctl restart backend
```

## 📊 **Manual Operations**

### **Trigger Single User Insights**
```python
# Run in backend directory
python -c "
from services.bg_job_queue import job_queue
import asyncio

async def trigger_insights():
    job_id = await job_queue.enqueue_job('UPDATE_INSIGHTS', 'USER_ID_HERE')
    print(f'Triggered job: {job_id}')

asyncio.run(trigger_insights())
"
```

### **Check Metrics**
```bash
curl https://your-domain.com/api/insights/metrics
```

### **Emergency Reset**
```bash
# Clear all background jobs (DANGER)
# Only use if queue is completely stuck
sudo -u postgres psql twelvr_db -c "DELETE FROM bg_jobs WHERE job_type='UPDATE_INSIGHTS';"
```

## 📝 **Key Endpoints**

- `GET /api/insights/metrics` - Health metrics
- `GET /api/dashboard/adaptive-insights` - Dashboard insights (cached)
- `GET /api/session/pre-session-insight` - Pre-session card (cached)

## ⚡ **Quick Status Check**
```bash
# All services running?
sudo supervisorctl status

# Recent errors?
tail -20 /var/log/supervisor/backend.err.log | grep -i error

# Cache health?
curl -s https://your-domain.com/api/insights/metrics | jq
```