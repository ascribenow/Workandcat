#!/bin/bash
# Verification script for twelvr.com API proxy hotpatch
# Run this after applying the Nginx configuration

echo "🔍 VERIFYING twelvr.com API PROXY HOTPATCH"
echo "=" * 60

echo -e "\n1. TESTING API ENDPOINT AVAILABILITY:"
echo "Testing /api/auth/login endpoint..."
RESPONSE=$(curl -s -w "%{http_code}" -X GET https://twelvr.com/api/auth/login)
if [[ "$RESPONSE" == *"405"* ]]; then
    echo "   ✅ API proxy working - 405 Method Not Allowed (expected for GET on login)"
else
    echo "   ❌ API proxy not working - Response: $RESPONSE"
fi

echo -e "\n2. TESTING BACKEND CONNECTIVITY:"
echo "Testing backend health through proxy..."
curl -s -w "Response Code: %{http_code}, Time: %{time_total}s\n" \
  https://twelvr.com/api/auth/login > /dev/null

echo -e "\n3. TESTING ADAPTIVE ENDPOINTS (requires authentication):"
echo "Note: Full adaptive endpoint testing requires valid JWT token"
echo "After login, these endpoints should return 200:"
echo "   POST /api/adapt/plan-next"
echo "   GET /api/adapt/pack" 
echo "   POST /api/adapt/mark-served"

echo -e "\n4. MONITORING API LOGS:"
echo "Monitor API requests with:"
echo "   tail -f /var/log/nginx/api_access.log"

echo -e "\n🎯 EXPECTED RESULT:"
echo "After login at twelvr.com, sessions should load normally instead of"
echo "getting stuck at 'Preparing next session...'"

echo -e "\n✅ Verification complete. Apply the Nginx configuration and test!"