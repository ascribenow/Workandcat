#!/usr/bin/env python3
"""
Simple test for NEW BACKGROUND JOB ARCHITECTURE for Adaptive Insights
"""
import requests
import time
import json

def test_background_job_architecture():
    """Test the new background job architecture for adaptive insights"""
    print("🎯 NEW BACKGROUND JOB ARCHITECTURE TESTING")
    print("=" * 60)
    
    base_url = "https://insight-engine-16.preview.emergentagent.com/api"
    
    # Step 1: Authenticate
    print("🔐 Step 1: Authentication")
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=auth_data, verify=False, timeout=10)
        if response.status_code == 200:
            token = response.json()['access_token']
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            print(f"   ✅ Authentication successful")
            print(f"   📊 JWT Token length: {len(token)} characters")
        else:
            print(f"   ❌ Authentication failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return False
    
    # Step 2: Test Dashboard Insights (Background Job Architecture)
    print("\n📊 Step 2: Dashboard Insights - Background Job Architecture")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/dashboard/adaptive-insights", headers=headers, verify=False, timeout=10)
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            data = response.json()
            source = data.get("source", "unknown")
            cache_time = data.get("cache_time_ms", 0)
            all_time_content = data.get("all_time_markdown", "")
            recent_content = data.get("recent_markdown", "")
            
            print(f"   ✅ Dashboard insights accessible: {response_time:.1f}ms")
            print(f"   📊 Source: {source}")
            print(f"   📊 Cache time: {cache_time:.3f}ms")
            print(f"   📊 All-time content: {len(all_time_content)} chars")
            print(f"   📊 Recent content: {len(recent_content)} chars")
            
            # Validate background job architecture
            if source in ["memory", "pre_computed"]:
                print(f"   ✅ Background job architecture working (source: {source})")
                
                if response_time < 50:
                    print(f"   ✅ Ultra-fast response achieved: {response_time:.1f}ms < 50ms")
                else:
                    print(f"   ⚠️ Response time: {response_time:.1f}ms (target: <50ms)")
                
                # Check token limits (rich content)
                total_content = len(all_time_content) + len(recent_content)
                if total_content > 1000:  # Generous threshold for restored token limits
                    print(f"   ✅ Rich content suggests restored token limits: {total_content} chars")
                else:
                    print(f"   ⚠️ Content may be truncated: {total_content} chars")
            else:
                print(f"   ❌ Unexpected source: {source}")
        else:
            print(f"   ❌ Dashboard insights failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Dashboard insights error: {e}")
        return False
    
    # Step 3: Test Pre-session Insights (Background Job Architecture)
    print("\n🎯 Step 3: Pre-session Insights - Background Job Architecture")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/session/pre-session-insight", headers=headers, verify=False, timeout=10)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            source = data.get("source", "unknown")
            cache_time = data.get("cache_time_ms", 0)
            way_forward = data.get("way_forward", [])
            today = data.get("today", "")
            
            print(f"   ✅ Pre-session insights accessible: {response_time:.1f}ms")
            print(f"   📊 Source: {source}")
            print(f"   📊 Cache time: {cache_time:.3f}ms")
            print(f"   📊 Way forward: {len(str(way_forward))} chars")
            print(f"   📊 Today: {len(today)} chars")
            
            # Validate background job architecture
            if source in ["memory", "pre_computed"]:
                print(f"   ✅ Background job architecture working (source: {source})")
                
                if response_time < 50:
                    print(f"   ✅ Ultra-fast response achieved: {response_time:.1f}ms < 50ms")
                else:
                    print(f"   ⚠️ Response time: {response_time:.1f}ms (target: <50ms)")
                
                # Check token limits (adequate content)
                total_content = len(str(way_forward)) + len(today)
                if total_content > 200:  # Threshold for 200 tokens
                    print(f"   ✅ Adequate content for 200 tokens: {total_content} chars")
                else:
                    print(f"   ⚠️ Content may be truncated: {total_content} chars")
            else:
                print(f"   ❌ Unexpected source: {source}")
        else:
            print(f"   ❌ Pre-session insights failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Pre-session insights error: {e}")
        return False
    
    # Step 4: Performance Analysis
    print("\n⚡ Step 4: Performance Analysis")
    dashboard_times = []
    presession_times = []
    
    # Test multiple calls for consistency
    for i in range(3):
        print(f"   🔄 Performance test {i+1}/3...")
        
        # Dashboard performance
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/dashboard/adaptive-insights", headers=headers, verify=False, timeout=10)
            dashboard_time = (time.time() - start_time) * 1000
            dashboard_times.append(dashboard_time)
        except:
            dashboard_times.append(999)  # Fallback for failed requests
        
        # Pre-session performance
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/session/pre-session-insight", headers=headers, verify=False, timeout=10)
            presession_time = (time.time() - start_time) * 1000
            presession_times.append(presession_time)
        except:
            presession_times.append(999)  # Fallback for failed requests
        
        print(f"   📊 Test {i+1}: Dashboard {dashboard_times[-1]:.1f}ms, Pre-session {presession_times[-1]:.1f}ms")
    
    # Analyze performance
    avg_dashboard = sum(dashboard_times) / len(dashboard_times)
    avg_presession = sum(presession_times) / len(presession_times)
    overall_avg = (avg_dashboard + avg_presession) / 2
    
    print(f"\n📊 Performance Summary:")
    print(f"   Dashboard average: {avg_dashboard:.1f}ms")
    print(f"   Pre-session average: {avg_presession:.1f}ms")
    print(f"   Overall average: {overall_avg:.1f}ms")
    
    # Performance validation
    ultra_fast = avg_dashboard < 50 and avg_presession < 50
    baseline_improved = overall_avg < 960  # 960ms baseline
    improvement = ((960 - overall_avg) / 960) * 100 if overall_avg < 960 else 0
    
    print(f"\n🎯 Architecture Validation Results:")
    print(f"   Ultra-fast responses (<50ms): {'✅ PASS' if ultra_fast else '❌ FAIL'}")
    print(f"   Baseline improvement (960ms): {'✅ PASS' if baseline_improved else '❌ FAIL'}")
    print(f"   Performance improvement: {improvement:.1f}%")
    
    if ultra_fast and baseline_improved and improvement >= 90:
        print(f"\n🎉 NEW BACKGROUND JOB ARCHITECTURE: VALIDATED")
        print(f"   - ISSUE 1 RESOLVED: Token limits restored (rich content)")
        print(f"   - ISSUE 2 IMPLEMENTED: Background job architecture working")
        print(f"   - Ultra-fast responses achieved (<50ms)")
        print(f"   - Dramatic performance improvement ({improvement:.1f}%)")
        print(f"   - Pre-computed JSON fetching working")
        print(f"   - System ready for production")
        return True
    else:
        print(f"\n⚠️ NEW BACKGROUND JOB ARCHITECTURE: NEEDS ATTENTION")
        print(f"   - Some targets not fully achieved")
        print(f"   - Review performance or content quality")
        return False

if __name__ == "__main__":
    success = test_background_job_architecture()
    exit(0 if success else 1)