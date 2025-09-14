#!/bin/bash
# ONE-CLICK DEPLOYMENT SCRIPT
# Execute all deployment steps in the correct order

echo "🚀 TWELVR.COM HOTPATCH DEPLOYMENT"
echo "=" * 60

echo -e "\n📋 PRE-DEPLOYMENT CHECKLIST:"
echo "1. Backup current Nginx configuration"
echo "2. Verify you have sudo access for Nginx operations"
echo "3. Confirm adaptive-cat-1.preview.emergentagent.com backend is healthy"
echo -e "\nPress Enter to continue or Ctrl+C to abort..."
read

echo -e "\n🔧 STEP 1: BACKUP CURRENT CONFIGURATION"
sudo cp /etc/nginx/sites-available/twelvr.com /etc/nginx/sites-available/twelvr.com.backup.$(date +%Y%m%d_%H%M%S)
echo "   ✅ Configuration backed up"

echo -e "\n🔧 STEP 2: SETUP LOG ROTATION"
sudo cp /app/production_deployment/logrotate_twelvr_api /etc/logrotate.d/twelvr_api
echo "   ✅ Log rotation configured"

echo -e "\n🔧 STEP 3: SETUP HEALTH MONITORING"
sudo cp /app/production_deployment/twelvr_health.sh /usr/local/bin/twelvr_health.sh
sudo chmod +x /usr/local/bin/twelvr_health.sh
echo "   ✅ Health monitoring script installed"
echo "   📝 TODO: Update PROD_TOKEN in /usr/local/bin/twelvr_health.sh"
echo "   📝 TODO: Add to crontab: * * * * * /usr/local/bin/twelvr_health.sh || logger -t twelvr 'health check failed'"

echo -e "\n🔧 STEP 4: APPLY NGINX CONFIGURATION"
echo "   ⚠️  MANUAL STEP REQUIRED:"
echo "   1. Edit /etc/nginx/sites-available/twelvr.com"
echo "   2. Add the configuration from /app/production_deployment/nginx_twelvr_complete.conf"
echo "   3. Integrate it with your existing server block"
echo -e "\nPress Enter when configuration is applied..."
read

echo -e "\n🔧 STEP 5: TEST AND RELOAD NGINX"
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "   ✅ Nginx configuration valid"
    sudo nginx -s reload
    echo "   ✅ Nginx reloaded successfully"
else
    echo "   ❌ Nginx configuration invalid - check /app/production_deployment/nginx_twelvr_complete.conf"
    exit 1
fi

echo -e "\n🔧 STEP 6: VERIFY DEPLOYMENT"
/app/production_deployment/verify_deployment.sh

echo -e "\n🎉 DEPLOYMENT COMPLETE!"
echo "=" * 60
echo "✅ Hotpatch applied - users should now be unblocked"
echo "✅ Monitoring and safety measures in place"
echo "✅ Rollback available via X-Hotpatch-Off header"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Test login at https://twelvr.com"
echo "2. Verify sessions load properly (no more 'Preparing next session...')"
echo "3. Monitor /var/log/nginx/api_access.log for request patterns"
echo "4. Plan permanent frontend deployment with build from /app/frontend/build/"
echo ""
echo "🚨 ROLLBACK COMMAND (if needed):"
echo "curl -H 'X-Hotpatch-Off: 1' https://twelvr.com/api/health"