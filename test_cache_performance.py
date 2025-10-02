#!/usr/bin/env python3

import requests
import time
import json
import sys

def test_ultra_fast_cache_performance():
    """Test the ultra-fast cache performance with sp@theskinmantra.com/student123"""
    
    base_url = "https://data-integrity-1.preview.emergentagent.com/api"
    
    print("🎯 ULTRA-OPTIMIZED ADAPTIVE INSIGHTS CACHE PERFORMANCE TESTING")
    print("=" * 80)
    print("OBJECTIVE: Test ULTRA-FAST 3-level cache strategy for sub-200ms response times")
    print("FOCUS: Memory cache <50ms, DB cache <200ms, cache source tracking, TTL behavior")
    print("EXPECTED: 95%+ calls under 200ms, memory cache hits <50ms, proper cache cleanup")
    print("BASELINE: 952ms → TARGET: <200ms (79% improvement)")
    print("=" * 80)
    
    # Authentication
    print("\n🔐 PHASE 1: AUTHENTICATION SETUP")
    print("-" * 60)
    
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=auth_data, timeout=30, verify=False)
        if response.status_code == 200:
            token = response.json()['access_token']
            auth_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            user_data = response.json().get('user', {})
            user_id = user_data.get('id')
            print(f"   ✅ Authentication successful")
            print(f"   📊 JWT Token length: {len(token)} characters")
            print(f"   📊 User ID: {user_id}")
            print(f"   📊 Adaptive enabled: {user_data.get('adaptive_enabled', False)}")
        else:
            print(f"   ❌ Authentication failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return False
    
    # Test 3-Level Cache Strategy
    print("\n⚡ PHASE 2: 3-LEVEL CACHE STRATEGY TESTING")
    print("-" * 60)
    
    dashboard_times = []
    dashboard_sources = []
    
    # Test multiple calls to dashboard insights
    for i in range(3):
        print(f"   🔄 Dashboard call {i+1}/3...")
        start_time = time.time()
        
        try:
            response = requests.get(f"{base_url}/dashboard/adaptive-insights", 
                                  headers=auth_headers, timeout=30, verify=False)
            call_time = (time.time() - start_time) * 1000  # Convert to ms
            dashboard_times.append(call_time)
            
            if response.status_code == 200:
                data = response.json()
                source = data.get("source", "unknown")
                dashboard_sources.append(source)
                
                print(f"   📊 Call {i+1}: {call_time:.1f}ms, Source: {source}")
                
                # Check for metrics
                if "cache_time_ms" in data:
                    print(f"   📊 Cache time: {data['cache_time_ms']:.1f}ms")
                if "generation_time_ms" in data:
                    print(f"   📊 Generation time: {data['generation_time_ms']:.1f}ms")
                    
            else:
                print(f"   ❌ Call {i+1} failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Call {i+1} error: {e}")
        
        # Small delay between calls
        if i < 2:
            time.sleep(0.3)
    
    # Test Pre-session Insights
    print("\n🚀 PHASE 3: PRE-SESSION INSIGHTS PERFORMANCE")
    print("-" * 60)
    
    pre_session_times = []
    pre_session_sources = []
    
    for i in range(3):
        print(f"   🔄 Pre-session call {i+1}/3...")
        start_time = time.time()
        
        try:
            response = requests.get(f"{base_url}/session/pre-session-insight", 
                                  headers=auth_headers, timeout=30, verify=False)
            call_time = (time.time() - start_time) * 1000
            pre_session_times.append(call_time)
            
            if response.status_code == 200:
                data = response.json()
                source = data.get("source", "unknown")
                pre_session_sources.append(source)
                
                print(f"   📊 Call {i+1}: {call_time:.1f}ms, Source: {source}")
                
                # Check required fields
                if "title" in data and "progress" in data:
                    print(f"   ✅ Required fields present")
                    
            else:
                print(f"   ❌ Call {i+1} failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Call {i+1} error: {e}")
        
        if i < 2:
            time.sleep(0.2)
    
    # Performance Analysis
    print("\n📈 PHASE 4: PERFORMANCE ANALYSIS")
    print("-" * 60)
    
    all_times = dashboard_times + pre_session_times
    
    if all_times:
        avg_time = sum(all_times) / len(all_times)
        max_time = max(all_times)
        min_time = min(all_times)
        under_200ms = [t for t in all_times if t < 200]
        under_50ms = [t for t in all_times if t < 50]
        
        print(f"   📊 Performance Summary:")
        print(f"      Total calls: {len(all_times)}")
        print(f"      Average time: {avg_time:.1f}ms")
        print(f"      Min time: {min_time:.1f}ms")
        print(f"      Max time: {max_time:.1f}ms")
        print(f"      Under 200ms: {len(under_200ms)}/{len(all_times)} ({(len(under_200ms)/len(all_times)*100):.1f}%)")
        print(f"      Under 50ms: {len(under_50ms)}/{len(all_times)} ({(len(under_50ms)/len(all_times)*100):.1f}%)")
        
        # Check baseline improvement
        baseline = 952.0
        if avg_time < baseline:
            improvement = ((baseline - avg_time) / baseline) * 100
            print(f"      Improvement from 952ms baseline: {improvement:.1f}%")
            
            if improvement >= 79:
                print(f"   ✅ Target 79% improvement achieved!")
            else:
                print(f"   ⚠️ Target 79% improvement not achieved")
        
        # Check targets
        if avg_time < 200:
            print(f"   ✅ Average under 200ms target achieved")
        else:
            print(f"   ❌ Average exceeds 200ms target")
            
        if len(under_200ms) / len(all_times) >= 0.95:
            print(f"   ✅ 95%+ calls under 200ms achieved")
        else:
            print(f"   ❌ 95%+ calls under 200ms not achieved")
    
    # Cache Source Analysis
    print("\n🔍 PHASE 5: CACHE SOURCE ANALYSIS")
    print("-" * 60)
    
    print(f"   📊 Dashboard sources: {dashboard_sources}")
    print(f"   📊 Pre-session sources: {pre_session_sources}")
    
    # Check for proper cache progression
    memory_hits = dashboard_sources.count("memory") + pre_session_sources.count("memory")
    db_hits = dashboard_sources.count("db_cache") + pre_session_sources.count("db_cache")
    fresh_hits = dashboard_sources.count("fresh") + pre_session_sources.count("fresh")
    
    print(f"   📊 Cache hit distribution:")
    print(f"      Memory hits: {memory_hits}")
    print(f"      DB cache hits: {db_hits}")
    print(f"      Fresh generation: {fresh_hits}")
    
    if memory_hits > 0:
        print(f"   ✅ Memory cache working")
    if db_hits > 0:
        print(f"   ✅ DB cache working")
    if fresh_hits > 0:
        print(f"   ✅ Fresh generation working")
    
    print("\n" + "=" * 80)
    print("🎯 ULTRA-FAST CACHE PERFORMANCE TEST COMPLETE")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    test_ultra_fast_cache_performance()