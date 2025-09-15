# TWELVR.COM PRODUCTION HOTPATCH - COMPLETE PACKAGE

## 🎯 SUMMARY
This package contains everything needed to fix the "blank session" issue at twelvr.com by implementing an edge proxy that routes `/api/*` calls to the correct backend.

## 🚨 ROOT CAUSE
- Production frontend at twelvr.com serves stale CRA bundle with hardcoded wrong API URL
- Bundle calls `https://adaptive-quant.emergent.host/api` (WRONG)
- Should call `https://twelvr-debugger.preview.emergentagent.com/api` (CORRECT)

## 🚀 SOLUTION
**Immediate**: Edge proxy at Nginx level routes `/api/*` to correct backend
**Permanent**: Deploy new CRA build with relative API calls

## 📦 PACKAGE CONTENTS

### CONFIGURATION FILES
- `nginx_twelvr_complete.conf` - Complete Nginx configuration with all safety measures
- `logrotate_twelvr_api` - Log rotation for API access logs
- `twelvr_health.sh` - Health monitoring script for cron
- `verify_deployment.sh` - Deployment verification script
- `permanent_build_ci_guard.sh` - CI guard against wrong API hosts

### DEPLOYMENT SCRIPTS
- `deploy_hotpatch.sh` - One-click deployment script

### PERMANENT BUILD
- `/app/frontend/build/` - New CRA build with relative API calls (ready to deploy)

## 🔧 QUICK START

### IMMEDIATE FIX (5 minutes)
```bash
cd /app/production_deployment
./deploy_hotpatch.sh
```

### MANUAL STEPS REQUIRED
1. **Edit Nginx config**: Add contents from `nginx_twelvr_complete.conf` to your twelvr.com server block
2. **Update health script**: Replace PROD_TOKEN in `twelvr_health.sh` with actual token
3. **Setup cron**: Add health monitoring to crontab

### VERIFICATION
```bash
./verify_deployment.sh
```

## 🎯 EXPECTED RESULTS

### IMMEDIATE (after proxy)
- ✅ Login at twelvr.com works normally
- ✅ "Preparing next session..." resolves to actual questions
- ✅ All API calls hit `https://twelvr.com/api/...` (same-origin)
- ✅ No more 404 errors on adaptive endpoints

### PERMANENT (after bundle update)
- ✅ No hardcoded API hosts in frontend
- ✅ Relative API calls forever (`/api` instead of full URLs)
- ✅ CI guards prevent regression

## 🚨 SAFETY FEATURES

### ROLLBACK
- Kill switch: `curl -H 'X-Hotpatch-Off: 1' https://twelvr.com/api/health`
- Instant disable of proxy without config changes

### MONITORING
- Dedicated API access logs with upstream status and response times
- Health checks every minute with alerting
- Log rotation to prevent disk fill

### SECURITY
- Rate limiting (10 req/s per IP, burst 20)
- Security headers (HSTS, CSP, X-Frame-Options)
- Proper SSL/SNI handling for upstream

## 📋 IMPLEMENTATION CHECKLIST

### IMMEDIATE HOTPATCH
- [ ] Apply Nginx configuration from `nginx_twelvr_complete.conf`
- [ ] Test configuration: `sudo nginx -t`
- [ ] Reload Nginx: `sudo nginx -s reload`
- [ ] Run verification: `./verify_deployment.sh`
- [ ] Test user flow at https://twelvr.com

### OPERATIONAL SETUP
- [ ] Setup log rotation: Copy `logrotate_twelvr_api` to `/etc/logrotate.d/`
- [ ] Install health monitoring: Copy `twelvr_health.sh` to `/usr/local/bin/`
- [ ] Update health script with production token
- [ ] Add health check to crontab

### PERMANENT DEPLOYMENT (when ready)
- [ ] Deploy new build from `/app/frontend/build/` to production
- [ ] Remove service worker kill location after 24h
- [ ] Add CI guard script to deployment pipeline
- [ ] Update frontend to use relative API calls permanently

## 🎉 SUCCESS CRITERIA
After deployment:
1. Users can login at twelvr.com without issues
2. Sessions load with 12 questions instead of infinite "Preparing..."
3. Network tab shows all requests hitting `twelvr.com/api/*`
4. Backend logs show successful session creation and pack generation
5. No 404 errors in browser console

## 🆘 ROLLBACK PLAN
If anything goes wrong:
1. **Immediate**: Use killswitch header to disable proxy
2. **Full rollback**: `sudo cp /etc/nginx/sites-available/twelvr.com.backup.* /etc/nginx/sites-available/twelvr.com && sudo nginx -s reload`
3. **Emergency**: Contact development team with error details

---

**This hotpatch will unblock users immediately while preserving all existing functionality.**