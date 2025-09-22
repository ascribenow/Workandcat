# CORS Edge Configuration Issue - Technical Analysis & Resolution

## Issue Summary

**Problem**: `net::ERR_ABORTED` error when making POST requests to `/api/adapt/plan-next` from the production frontend at `www.twelvr.com`.

**Root Cause**: Edge/proxy layer CORS configuration is overriding the backend application's CORS headers, specifically blocking the `Idempotency-Key` header.

**Impact**: Users cannot start sessions via "Today's Session" button, preventing the core adaptive learning functionality.

## Current Backend Configuration (CORRECT)

The backend application at `https://adaptive-quant.emergent.host` has the correct CORS configuration:

```python
# File: /app/backend/server.py (Lines 58-65)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Idempotency-Key", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)
```

**Key Point**: The backend explicitly allows `Idempotency-Key` in the `allow_headers` list.

## Frontend Implementation (CORRECT)

The frontend correctly sends the `Idempotency-Key` header:

```javascript
// File: /app/frontend/src/components/Dashboard.js (Lines 253-257)
headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    'Idempotency-Key': `dashboard_start_${Date.now()}`
}
```

## Evidence of Edge-Level Override

Based on the investigation from current_work:

1. **Direct Backend Tests**: All API endpoints work correctly when tested directly against `adaptive-quant.emergent.host`
2. **Browser Behavior**: `net::ERR_ABORTED` occurs specifically when browsers send CORS preflight requests
3. **Header Analysis**: The edge layer at `www.twelvr.com` returns `Access-Control-Allow-Headers` that excludes `Idempotency-Key`

## Technical Root Cause

The issue is in the **Kubernetes ingress configuration** or **edge proxy layer** that sits between the browser and the application server. This layer is:

1. Intercepting CORS preflight OPTIONS requests
2. Overriding the application's CORS response headers
3. Excluding `Idempotency-Key` from the allowed headers list
4. Causing browsers to abort the actual POST request

## Required Fix: Edge-Level CORS Configuration

The platform team needs to update the edge/proxy/ingress configuration to include `Idempotency-Key` in the allowed headers.

### Specific Configuration Changes Required

#### If using Kubernetes Ingress with NGINX:

```yaml
# Add or update the CORS annotation in the ingress configuration
metadata:
  annotations:
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-headers: "Authorization,Idempotency-Key,Content-Type,Accept,Origin,X-Requested-With"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET,POST,PUT,DELETE,OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
```

#### If using Cloudflare or similar edge proxy:

Add `Idempotency-Key` to the allowed headers list in the CORS configuration.

#### If using custom proxy configuration:

Ensure the proxy adds these headers to CORS responses:
```
Access-Control-Allow-Headers: Authorization, Idempotency-Key, Content-Type, Accept, Origin, X-Requested-With
```

## Validation Steps

After making the configuration changes:

1. **CORS Preflight Test**:
   ```bash
   curl -X OPTIONS https://www.twelvr.com/api/adapt/plan-next \
        -H "Origin: https://www.twelvr.com" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Authorization,Idempotency-Key,Content-Type" \
        -v
   ```

2. **Expected Response**: Should include:
   ```
   Access-Control-Allow-Headers: Authorization, Idempotency-Key, Content-Type, Accept, Origin, X-Requested-With
   ```

3. **Frontend Test**: Login at `www.twelvr.com` and try clicking "Today's Session" button.

## Alternative Temporary Solutions (Not Recommended)

If edge configuration cannot be updated immediately:

1. **Header Renaming**: Change `Idempotency-Key` to a different header name (requires code changes)
2. **Query Parameter**: Move idempotency token to URL query parameter (less secure)

**Note**: These alternatives require application code changes and are not preferred.

## Priority: CRITICAL

This issue prevents the core functionality of the adaptive learning platform and should be resolved at the highest priority.

## Contact Information

For technical questions about this issue, please reach out to the development team with this document.

---

**Document Version**: 1.0  
**Date**: September 22, 2025  
**Issue Type**: Edge/Infrastructure Configuration  
**Affected Domain**: www.twelvr.com  
**Backend Domain**: adaptive-quant.emergent.host