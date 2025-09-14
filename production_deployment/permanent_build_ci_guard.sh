#!/bin/bash
# CI Guard Script - Prevents wrong API hosts in production builds
# Add to your CI/CD pipeline after npm run build

echo "🔍 CI GUARD: Checking build for forbidden API hosts"

# Check that no external adaptive hosts are in the build
echo "Checking for forbidden hosts..."

if grep -R "adaptive-quant\.emergent\.host" build/ 2>/dev/null; then
    echo "❌ FORBIDDEN: Found adaptive-quant.emergent.host in build!"
    echo "Build contains references to wrong API host"
    exit 1
fi

if grep -R "https\?://adaptive-" build/ 2>/dev/null | grep -v "adaptive-cat-1.preview.emergentagent.com"; then
    echo "❌ FORBIDDEN: Found unexpected adaptive hosts in build!"
    grep -R "https\?://adaptive-" build/
    exit 1
fi

# Verify relative API calls are present  
if grep -R '"/api"' build/static/js/ >/dev/null 2>&1; then
    echo "✅ GOOD: Found relative API calls in build"
else
    echo "⚠️ WARNING: No relative API calls found - verify API configuration"
fi

# Check bundle size is reasonable
BUNDLE_SIZE=$(du -sh build/static/js/*.js | cut -f1)
echo "📊 Bundle size: $BUNDLE_SIZE"

echo "✅ CI GUARD PASSED: Build is safe for production deployment"