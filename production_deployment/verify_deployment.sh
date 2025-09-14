#!/bin/bash
# Complete Deployment Verification Script
# Run after applying Nginx configuration

echo "🔍 VERIFYING TWELVR.COM DEPLOYMENT"
echo "=" * 60

echo -e "\n1. TESTING NGINX CONFIGURATION:"
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "   ✅ Nginx configuration valid"
else
    echo "   ❌ Nginx configuration invalid - fix before proceeding"
    exit 1
fi

echo -e "\n2. TESTING API PROXY BASIC CONNECTIVITY:"
RESPONSE=$(curl -s -w "%{http_code}" -X GET https://twelvr.com/api/auth/login)
if [[ "$RESPONSE" == *"405"* ]]; then
    echo "   ✅ API proxy working - 405 Method Not Allowed (expected for GET on login)"
else
    echo "   ❌ API proxy not working - Response: $RESPONSE"
fi

echo -e "\n3. TESTING AUTHENTICATION ENDPOINT:"
AUTH_RESPONSE=$(curl -s -w "%{http_code}" -X POST https://twelvr.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"sp@theskinmantra.com","password":"student123"}')

if [[ "$AUTH_RESPONSE" == *"200"* ]]; then
    echo "   ✅ Authentication working through proxy"
else
    echo "   ❌ Authentication failed through proxy"
    echo "   Response: $AUTH_RESPONSE"
fi

echo -e "\n4. TESTING KILLSWITCH:"
KILLSWITCH_RESPONSE=$(curl -s -w "%{http_code}" -X GET https://twelvr.com/api/auth/login \
  -H "X-Hotpatch-Off: 1")
if [[ "$KILLSWITCH_RESPONSE" == *"502"* ]]; then
    echo "   ✅ Killswitch working - 502 Bad Gateway when X-Hotpatch-Off header present"
else
    echo "   ⚠️ Killswitch may not be configured - Response: $KILLSWITCH_RESPONSE"
fi

echo -e "\n5. CHECKING BUNDLE STATUS:"
BUNDLE_HASH=$(curl -s https://twelvr.com/index.html | grep -o 'main\.[a-f0-9]*\.js' | head -1)
echo "   Current bundle: $BUNDLE_HASH"

if [[ "$BUNDLE_HASH" == "main.55dedb51.js" ]]; then
    echo "   ⚠️ Still serving old bundle - permanent fix needed"
elif [[ "$BUNDLE_HASH" == "main.b7a14a6f.js" ]]; then
    echo "   ✅ Serving new bundle with relative API calls"
else
    echo "   ⚠️ Unknown bundle version: $BUNDLE_HASH"
fi

echo -e "\n6. TESTING SERVICE WORKER KILL:"
SW_RESPONSE=$(curl -s -w "%{http_code}" https://twelvr.com/service-worker.js)
if [[ "$SW_RESPONSE" == *"200"* ]]; then
    echo "   ✅ Service worker kill endpoint working"
else
    echo "   ⚠️ Service worker kill not configured"
fi

echo -e "\n7. CHECKING API LOGS:"
if [ -f "/var/log/nginx/api_access.log" ]; then
    echo "   ✅ API access log file exists"
    echo "   Last 3 API requests:"
    tail -3 /var/log/nginx/api_access.log 2>/dev/null || echo "   No recent requests"
else
    echo "   ⚠️ API access log not found - check configuration"
fi

echo -e "\n🎯 DEPLOYMENT VERIFICATION COMPLETE"
echo "Next steps:"
echo "1. If all checks pass, test login at https://twelvr.com"
echo "2. Verify 'Preparing next session...' resolves to actual questions"
echo "3. Monitor /var/log/nginx/api_access.log for request patterns"
echo "4. Plan permanent frontend deployment with relative API calls"