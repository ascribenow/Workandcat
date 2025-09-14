#!/bin/bash
# Twelvr Health Check Script
# Save as /usr/local/bin/twelvr_health.sh
# Make executable: chmod +x /usr/local/bin/twelvr_health.sh

set -e

# Production token (replace with actual token)
T="Bearer REPLACE_WITH_ACTUAL_PROD_TOKEN"

echo "$(date): Starting Twelvr health checks..." >> /var/log/twelvr_health.log

# Basic API health
curl -fsS "https://twelvr.com/api/auth/login" -X GET >/dev/null 2>&1 && \
    echo "$(date): Health check - Basic API: OK" >> /var/log/twelvr_health.log

# Adaptive endpoints health (requires valid token)
if [ "$T" != "Bearer REPLACE_WITH_ACTUAL_PROD_TOKEN" ]; then
    # Plan-next test
    curl -fsS -X POST "https://twelvr.com/api/adapt/plan-next" \
      -H "Authorization: $T" \
      -H "Idempotency-Key: health-$$" \
      -H "Content-Type: application/json" \
      -d '{"sess_seq":999,"reason":"health"}' >/dev/null 2>&1 && \
        echo "$(date): Health check - Plan-next: OK" >> /var/log/twelvr_health.log
    
    # Pack endpoint test  
    curl -fsS "https://twelvr.com/api/adapt/pack?sess_seq=999" \
      -H "Authorization: $T" >/dev/null 2>&1 && \
        echo "$(date): Health check - Pack fetch: OK" >> /var/log/twelvr_health.log
else
    echo "$(date): Health check - Skipping adaptive tests (no token)" >> /var/log/twelvr_health.log
fi

echo "$(date): Health checks completed" >> /var/log/twelvr_health.log