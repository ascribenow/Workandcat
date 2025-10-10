#!/usr/bin/env python3
"""
DETAILED BATCH PROCESSING CHECK
Get more specific information about the current batch processing status
"""

import requests
import json
import sys
from datetime import datetime

class DetailedBatchChecker:
    def __init__(self):
        self.base_url = "https://study-optimizer-1.preview.emergentagent.com/api"
        self.admin_token = None
        
    def authenticate_admin(self):
        """Authenticate as admin"""
        try:
            login_data = {
                "email": "sumedhprabhu18@gmail.com",
                "password": "admin2025"
            }
            
            response = requests.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                return True
            else:
                print(f"❌ Admin authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_admin_headers(self):
        """Get headers with admin token"""
        if not self.admin_token:
            return None
        return {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
    
    def trigger_enrichment_and_check(self):
        """Trigger enrichment and check the response"""
        try:
            headers = self.get_admin_headers()
            if not headers:
                return None
                
            print("🚀 TRIGGERING PYQ ENRICHMENT...")
            response = requests.post(
                f"{self.base_url}/admin/pyq/trigger-enrichment",
                headers=headers,
                json={},
                timeout=30,
                verify=False
            )
            
            print(f"📊 Trigger response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("✅ Enrichment trigger successful")
                    print(f"📊 Response: {json.dumps(data, indent=2)}")
                    return data
                except:
                    print(f"✅ Enrichment triggered (no JSON response)")
                    return {"status": "triggered", "text": response.text}
            else:
                print(f"⚠️ Trigger response: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📊 Error details: {json.dumps(error_data, indent=2)}")
                    return error_data
                except:
                    print(f"📊 Error text: {response.text}")
                    return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            print(f"❌ Trigger error: {e}")
            return None
    
    def check_enrichment_progress(self):
        """Check enrichment progress multiple times"""
        try:
            headers = self.get_admin_headers()
            if not headers:
                return None
                
            print("\n📊 CHECKING ENRICHMENT PROGRESS...")
            
            # Check multiple times to see if there's progress
            for i in range(3):
                print(f"\n--- Check #{i+1} ---")
                
                response = requests.get(
                    f"{self.base_url}/admin/pyq/enrichment-status",
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    stats = data.get('enrichment_statistics', {})
                    
                    total = stats.get('total_questions', 0)
                    enriched = stats.get('enriched_questions', 0)
                    pending = stats.get('pending_questions', 0)
                    
                    print(f"📊 Total: {total}, Enriched: {enriched}, Pending: {pending}")
                    
                    if i == 0:
                        initial_enriched = enriched
                    elif enriched > initial_enriched:
                        print(f"✅ PROGRESS DETECTED: {enriched - initial_enriched} new questions enriched!")
                        return True
                else:
                    print(f"❌ Status check failed: {response.status_code}")
                
                if i < 2:  # Don't wait after last check
                    print("⏳ Waiting 10 seconds...")
                    import time
                    time.sleep(10)
            
            return False
                
        except Exception as e:
            print(f"❌ Progress check error: {e}")
            return None
    
    def check_specific_questions(self):
        """Check specific questions to see their enrichment status"""
        try:
            headers = self.get_admin_headers()
            if not headers:
                return None
                
            print("\n🔍 CHECKING SPECIFIC QUESTIONS...")
            
            response = requests.get(
                f"{self.base_url}/admin/pyq/questions?limit=10",
                headers=headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                
                print(f"📊 Analyzing {len(questions)} questions:")
                
                for i, q in enumerate(questions[:5]):  # Check first 5
                    qid = q.get('id', 'unknown')[:8]
                    category = q.get('category', 'None')
                    subcategory = q.get('subcategory', 'None')
                    right_answer = q.get('right_answer', 'None')
                    
                    # Check if enriched
                    is_enriched = (
                        category and category != 'To be classified by LLM' and
                        subcategory and subcategory != 'To be classified by LLM' and
                        right_answer and right_answer != 'To be generated by LLM'
                    )
                    
                    status = "✅ ENRICHED" if is_enriched else "❌ NOT ENRICHED"
                    print(f"  Q{i+1} ({qid}): {status}")
                    print(f"      Category: {category}")
                    print(f"      Subcategory: {subcategory}")
                    print(f"      Right Answer: {right_answer[:50]}..." if right_answer else "      Right Answer: None")
                
                return questions
            else:
                print(f"❌ Questions check failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Questions check error: {e}")
            return None
    
    def run_detailed_analysis(self):
        """Run the detailed analysis"""
        print("🔍 DETAILED BATCH PROCESSING ANALYSIS")
        print("=" * 80)
        print("Performing detailed analysis of current batch processing status")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate_admin():
            print("\n❌ CANNOT PROCEED: Admin authentication failed")
            return
        
        print("✅ Admin authentication successful")
        
        # Step 2: Trigger enrichment
        trigger_result = self.trigger_enrichment_and_check()
        
        # Step 3: Check for progress
        progress_detected = self.check_enrichment_progress()
        
        # Step 4: Check specific questions
        questions = self.check_specific_questions()
        
        # Step 5: Final assessment
        print("\n" + "=" * 80)
        print("🎯 DETAILED ANALYSIS RESULTS")
        print("=" * 80)
        
        if progress_detected:
            print("✅ ACTIVE PROCESSING DETECTED")
            print("• Background enrichment is actively processing questions")
            print("• Progress was observed during monitoring period")
            print("• Current batch will continue automatically")
            print("\n🎯 ANSWER: The remaining questions WILL be enriched automatically")
            print("• No manual intervention required")
            print("• Continue monitoring for completion")
            
        elif trigger_result and 'error' not in str(trigger_result).lower():
            print("⚠️ PROCESSING TRIGGERED BUT PROGRESS UNCLEAR")
            print("• Enrichment trigger was successful")
            print("• No immediate progress detected (may take time to start)")
            print("• Background processing may be initializing")
            print("\n🎯 ANSWER: Monitor for 15-30 minutes")
            print("• Processing may have been triggered successfully")
            print("• Check again in 30 minutes for progress")
            print("• If no progress, manual intervention may be needed")
            
        else:
            print("❌ PROCESSING ISSUES DETECTED")
            print("• Unable to trigger enrichment successfully")
            print("• No progress detected in monitoring period")
            print("• Background processing may be stuck or failed")
            print("\n🎯 ANSWER: Manual intervention REQUIRED")
            print("• Current batch is not processing automatically")
            print("• Check system logs for errors")
            print("• May need to restart enrichment process")

if __name__ == "__main__":
    checker = DetailedBatchChecker()
    checker.run_detailed_analysis()