# PERMANENT FRONTEND FIX - DEPLOYMENT GUIDE

## 🎯 OVERVIEW
This guide covers the permanent fix for the frontend build to use relative API calls, eliminating the need for hardcoded backend URLs.

## 📦 PREPARED BUILD
Location: `/app/frontend/build/`
- ✅ Uses relative API calls (`/api` instead of full URLs)
- ✅ Service worker unregistration included
- ✅ No hardcoded backend hosts
- ✅ Optimized production build

## 🔧 DEPLOYMENT STEPS

### 1. VERIFY BUILD QUALITY
```bash
cd /app/frontend
./production_deployment/permanent_build_ci_guard.sh
```

### 2. DEPLOY TO PRODUCTION
```bash
# Copy build to your production web root
# (Replace /var/www/twelvr.com with your actual web root)
sudo rsync -av --delete build/ /var/www/twelvr.com/

# Set proper permissions
sudo chown -R www-data:www-data /var/www/twelvr.com/
sudo chmod -R 644 /var/www/twelvr.com/
sudo find /var/www/twelvr.com/ -type d -exec chmod 755 {} \;
```

### 3. UPDATE CACHE HEADERS
Ensure your Nginx configuration has proper cache headers:

```nginx
# Never cache app shell
location = /index.html { 
    add_header Cache-Control "no-cache, must-revalidate"; 
    try_files $uri /index.html; 
}

# Long cache for hashed assets
location ~* \.(?:js|css|woff2?)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
}
```

### 4. KILL SERVICE WORKER (TEMPORARY)
Add to Nginx for 24 hours:

```nginx
location = /service-worker.js {
    add_header Cache-Control "no-store";
    return 200 '';
}
```

### 5. FORCE CACHE INVALIDATION
```bash
# If using CDN, purge all caches
# If direct server, restart Nginx to clear any internal caches
sudo nginx -s reload
```

## 🧪 VERIFICATION

### Build Verification
```bash
# Check bundle hash changed
curl -s https://twelvr.com/index.html | grep -o 'main\.[a-f0-9]*\.js'
# Should show: main.b7a14a6f.js (new) instead of main.55dedb51.js (old)

# Check API calls in bundle
curl -s https://twelvr.com/static/js/main.b7a14a6f.js | grep -o '"/api"'
# Should find relative API calls
```

### User Flow Verification
1. Clear browser cache completely
2. Visit https://twelvr.com
3. Login with sp@theskinmantra.com/student123
4. Verify session loads with questions (no "Preparing next session..." loop)
5. Check Network tab shows all requests to `twelvr.com/api/*`

## 📊 SUCCESS METRICS

### Before Fix
- ❌ Console: `Backend URL = "https://adaptive-quant.emergent.host"`
- ❌ Network: Requests to wrong API base
- ❌ UI: Infinite "Preparing next session..." loop
- ❌ Errors: 404 on `/api/adapt/pack`

### After Fix
- ✅ Console: `Backend URL = ""` (relative calls)
- ✅ Network: All requests to `twelvr.com/api/*`
- ✅ UI: Sessions load with 12 questions
- ✅ No errors: All adaptive endpoints working

## 🛡️ CI/CD INTEGRATION

Add to your deployment pipeline:

```yaml
# GitHub Actions example
- name: Guard against wrong API hosts
  run: |
    npm run build
    ./production_deployment/permanent_build_ci_guard.sh
    
- name: Deploy build
  run: |
    rsync -av --delete build/ user@server:/var/www/twelvr.com/
```

## 🔄 ROLLBACK PLAN

### If New Build Fails
1. **Immediate**: Revert to previous build directory
2. **Quick**: Use hotpatch proxy (already configured)
3. **Debug**: Check browser console for new errors

### If Proxy Fails
1. **Killswitch**: `curl -H 'X-Hotpatch-Off: 1' https://twelvr.com/api/health`
2. **Full revert**: Restore backup Nginx configuration
3. **Emergency**: Use original backend URLs in emergency build

## 📈 MONITORING

### Key Metrics to Watch
- API response times in `/var/log/nginx/api_access.log`
- Error rates from health checks
- User session completion rates
- Frontend console error patterns

### Alert Thresholds
- API response time > 30s (planner performance issue)
- Error rate > 5% (backend connectivity issue)  
- Health check failures > 3 consecutive (upstream down)

---

**This permanent fix ensures the frontend will work correctly regardless of backend URL changes or hosting migrations.**