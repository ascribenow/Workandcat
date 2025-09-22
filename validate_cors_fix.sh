#!/bin/bash

echo "🔧 CORS Fix Validation Script"
echo "================================"

echo ""
echo "📋 Testing CORS preflight for production edge..."

RESPONSE=$(curl -s -X OPTIONS https://www.twelvr.com/api/adapt/plan-next \
     -H "Origin: https://www.twelvr.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Authorization,Idempotency-Key,Content-Type" \
     -I)

echo "Response headers:"
echo "$RESPONSE"

echo ""
echo "🔍 Checking for Idempotency-Key in allowed headers..."

if echo "$RESPONSE" | grep -i "access-control-allow-headers" | grep -q "Idempotency-Key"; then
    echo "✅ SUCCESS: Idempotency-Key is now allowed!"
    echo "🎉 CORS fix has been applied correctly."
    exit 0
else
    echo "❌ FAILED: Idempotency-Key is still blocked."
    echo "🔧 Edge configuration still needs to be updated."  
    
    ALLOWED_HEADERS=$(echo "$RESPONSE" | grep -i "access-control-allow-headers" | cut -d':' -f2-)
    echo "Current allowed headers:$ALLOWED_HEADERS"
    exit 1
fi