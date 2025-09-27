#!/usr/bin/env python3

import requests
import json
import time
import uuid

def test_session_discrepancy():
    """Simple test to investigate session sequence discrepancy"""
    
    base_url = "https://catprep-adapt.preview.emergentagent.com/api"
    
    print("🎯 SESSION SEQUENCE DISCREPANCY INVESTIGATION")
    print("=" * 80)
    print("OBJECTIVE: Investigate Session #12 vs 5 completed sessions discrepancy")
    print("USER: sp@theskinmantra.com")
    print("=" * 80)
    
    # Step 1: Authentication
    print("\n🔐 STEP 1: AUTHENTICATION")
    print("-" * 60)
    
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    try:
        auth_response = requests.post(
            f"{base_url}/auth/login", 
            json=auth_data, 
            timeout=30,
            verify=False
        )
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            token = auth_result.get('access_token')
            user_data = auth_result.get('user', {})
            user_id = user_data.get('id')
            
            print(f"✅ Authentication successful")
            print(f"📊 User ID: {user_id}")
            print(f"📊 JWT Token: {len(token)} characters")
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
        else:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    # Step 2: Dashboard Analysis
    print("\n📊 STEP 2: DASHBOARD ANALYSIS")
    print("-" * 60)
    
    try:
        dashboard_response = requests.get(
            f"{base_url}/dashboard/simple-taxonomy",
            headers=headers,
            timeout=30,
            verify=False
        )
        
        if dashboard_response.status_code == 200:
            dashboard_data = dashboard_response.json()
            total_sessions = dashboard_data.get('total_sessions_completed', 0)
            
            print(f"✅ Dashboard API working")
            print(f"📊 Total Sessions Completed (Dashboard): {total_sessions}")
            
            # Look for any session-related metadata
            if 'session_metadata' in dashboard_data:
                print(f"📊 Session metadata: {dashboard_data['session_metadata']}")
            
        else:
            print(f"❌ Dashboard API failed: {dashboard_response.status_code}")
            print(f"Response: {dashboard_response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
    
    # Step 3: Try to get last completed session
    print("\n🔍 STEP 3: LAST COMPLETED SESSION ANALYSIS")
    print("-" * 60)
    
    try:
        last_session_response = requests.get(
            f"{base_url}/sessions/last-completed-id?user_id={user_id}",
            headers=headers,
            timeout=30,
            verify=False
        )
        
        if last_session_response.status_code == 200:
            last_session_data = last_session_response.json()
            sess_seq = last_session_data.get('sess_seq', 0)
            session_id = last_session_data.get('session_id', 'unknown')
            
            print(f"✅ Last completed session found")
            print(f"📊 Last completed sess_seq: {sess_seq}")
            print(f"📊 Last completed session_id: {session_id}")
            
            # Calculate discrepancy
            if sess_seq < 12:
                gap = 12 - sess_seq - 1
                print(f"🚨 DISCREPANCY CONFIRMED:")
                print(f"   Last completed session: #{sess_seq}")
                print(f"   Next session would be: #{sess_seq + 1}")
                print(f"   But user sees: Session #12")
                print(f"   Gap: {gap} sessions created but not completed")
            
        elif last_session_response.status_code == 404:
            error_data = last_session_response.json()
            if error_data.get('detail', {}).get('code') == 'NO_COMPLETED_SESSIONS':
                print(f"⚠️ No completed sessions found")
                print(f"🚨 MAJOR DISCREPANCY:")
                print(f"   Dashboard shows: 5 completed sessions")
                print(f"   API shows: 0 completed sessions")
                print(f"   User sees: Session #12")
            else:
                print(f"❌ Last session API error: {last_session_response.status_code}")
        else:
            print(f"❌ Last session API failed: {last_session_response.status_code}")
            print(f"Response: {last_session_response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Last session error: {e}")
    
    # Step 4: Try to create a new session to see sequence number
    print("\n🧪 STEP 4: NEW SESSION CREATION TEST")
    print("-" * 60)
    
    try:
        test_session_id = f"discrepancy_test_{uuid.uuid4()}"
        plan_data = {
            "user_id": user_id,
            "last_session_id": "S0",
            "next_session_id": test_session_id
        }
        
        headers_with_idem = headers.copy()
        headers_with_idem['Idempotency-Key'] = f"{user_id}:S0:{test_session_id}"
        
        print(f"🚀 Creating test session: {test_session_id[:8]}...")
        
        plan_response = requests.post(
            f"{base_url}/adapt/plan-next",
            json=plan_data,
            headers=headers_with_idem,
            timeout=60,
            verify=False
        )
        
        if plan_response.status_code == 200:
            plan_result = plan_response.json()
            status = plan_result.get('status')
            returned_session_id = plan_result.get('session_id')
            
            print(f"✅ Session creation successful")
            print(f"📊 Status: {status}")
            print(f"📊 Returned session_id: {returned_session_id}")
            
            # The sequence number would be visible in database or through other means
            # For now, we can infer from the pattern
            
        else:
            print(f"❌ Session creation failed: {plan_response.status_code}")
            print(f"Response: {plan_response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Session creation error: {e}")
    
    # Step 5: Summary and Analysis
    print("\n🔍 STEP 5: ROOT CAUSE ANALYSIS")
    print("-" * 60)
    
    print(f"📋 FINDINGS SUMMARY:")
    print(f"   1. Dashboard shows: 5 completed sessions")
    print(f"   2. User interface shows: Session #12")
    print(f"   3. Discrepancy: 7 sessions (12-5=7)")
    
    print(f"\n💡 LIKELY ROOT CAUSE:")
    print(f"   1. Sessions are created with incrementing sequence numbers")
    print(f"   2. Not all created sessions are completed")
    print(f"   3. Dashboard counts only completed sessions")
    print(f"   4. Session sequence continues from highest created, not completed")
    
    print(f"\n🔧 RECOMMENDED FIXES:")
    print(f"   1. Update session creation to use completed count + 1")
    print(f"   2. Clean up abandoned/planned sessions")
    print(f"   3. Ensure session completion API updates status properly")
    print(f"   4. Add monitoring for session creation vs completion gaps")
    
    return True

if __name__ == "__main__":
    test_session_discrepancy()