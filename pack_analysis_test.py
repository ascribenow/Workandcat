#!/usr/bin/env python3

import requests
import json
import uuid
import time
import sys
import os

# Add backend path for imports
sys.path.append('/app/backend')

class PackDataAnalyzer:
    def __init__(self):
        # Use the frontend URL from .env
        with open('/app/frontend/.env', 'r') as f:
            env_content = f.read()
            if 'REACT_APP_BACKEND_URL=' in env_content:
                backend_url = env_content.split('REACT_APP_BACKEND_URL=')[1].split('\n')[0].strip()
                if backend_url:
                    self.base_url = f"{backend_url}/api"
                else:
                    self.base_url = "https://smart-blueprint.preview.emergentagent.com/api"
            else:
                self.base_url = "https://smart-blueprint.preview.emergentagent.com/api"
        
        print(f"🌐 Using backend URL: {self.base_url}")
        
    def authenticate(self):
        """Authenticate and get JWT token"""
        print("\n🔐 AUTHENTICATION")
        print("-" * 50)
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json=auth_data,
                headers={'Content-Type': 'application/json'},
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                user_data = data.get('user', {})
                
                print(f"✅ Authentication successful")
                print(f"📊 JWT Token length: {len(token)} characters")
                print(f"📊 User ID: {user_data.get('id')}")
                print(f"📊 Adaptive enabled: {user_data.get('adaptive_enabled')}")
                
                return {
                    'token': token,
                    'user_id': user_data.get('id'),
                    'headers': {
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json'
                    }
                }
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None
    
    def create_session(self, auth_info):
        """Create a session to get pack data"""
        print("\n🎯 SESSION CREATION")
        print("-" * 50)
        
        session_id = str(uuid.uuid4())
        user_id = auth_info['user_id']
        
        plan_data = {
            "user_id": user_id,
            "last_session_id": "S0",
            "next_session_id": session_id
        }
        
        headers = auth_info['headers'].copy()
        headers['Idempotency-Key'] = f"{user_id}:S0:{session_id}"
        
        print(f"📊 Creating session: {session_id}")
        
        try:
            response = requests.post(
                f"{self.base_url}/adapt/plan-next",
                json=plan_data,
                headers=headers,
                timeout=60,
                verify=False
            )
            
            if response.status_code in [200, 202]:
                data = response.json()
                print(f"✅ Session creation initiated")
                print(f"📊 Status: {data.get('status')}")
                print(f"📊 Session ID: {data.get('session_id', session_id)}")
                
                # Wait a bit for session to be planned
                print("⏳ Waiting for session planning to complete...")
                time.sleep(3)
                
                return session_id
            else:
                print(f"❌ Session creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return None
    
    def fetch_pack_data(self, auth_info, session_id):
        """Fetch pack data and analyze structure"""
        print("\n📦 PACK DATA RETRIEVAL")
        print("-" * 50)
        
        user_id = auth_info['user_id']
        pack_url = f"{self.base_url}/adapt/pack?user_id={user_id}&session_id={session_id}"
        
        print(f"📋 Fetching pack from: {pack_url}")
        
        try:
            response = requests.get(
                pack_url,
                headers=auth_info['headers'],
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                pack_data = data.get('pack', [])
                
                print(f"✅ Pack data retrieved successfully")
                print(f"📊 Pack size: {len(pack_data)} questions")
                
                if len(pack_data) > 0:
                    return pack_data
                else:
                    print("❌ Pack is empty")
                    return None
            else:
                print(f"❌ Pack retrieval failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Pack retrieval error: {e}")
            return None
    
    def analyze_pack_structure(self, pack_data):
        """Analyze the pack data structure in detail"""
        print("\n🔍 PACK DATA STRUCTURE ANALYSIS")
        print("=" * 80)
        
        if not pack_data or len(pack_data) == 0:
            print("❌ No pack data to analyze")
            return
        
        sample_question = pack_data[0]
        
        # Get all unique fields across all questions
        all_fields = set()
        field_types = {}
        field_samples = {}
        
        for question in pack_data:
            for key, value in question.items():
                all_fields.add(key)
                if key not in field_types:
                    field_types[key] = type(value).__name__
                    field_samples[key] = value
        
        print(f"📊 Total questions analyzed: {len(pack_data)}")
        print(f"📊 Total unique fields found: {len(all_fields)}")
        
        print(f"\n📋 COMPLETE FIELD STRUCTURE:")
        print("-" * 80)
        
        for field in sorted(all_fields):
            field_type = field_types.get(field, 'unknown')
            sample_value = field_samples.get(field, 'N/A')
            
            # Truncate long values for display
            if isinstance(sample_value, str) and len(sample_value) > 150:
                display_value = sample_value[:150] + "..."
            elif isinstance(sample_value, list) and len(sample_value) > 3:
                display_value = f"[{len(sample_value)} items] {sample_value[:3]}..."
            else:
                display_value = sample_value
            
            print(f"{field:<25} ({field_type:<10}) = {display_value}")
        
        print(f"\n🎯 FRONTEND FIELD MAPPING ANALYSIS:")
        print("=" * 80)
        
        # Check for question text fields
        question_text_candidates = ['stem', 'why', 'question', 'question_text', 'content']
        question_text_field = None
        
        print(f"\n📝 QUESTION TEXT FIELD:")
        for field in question_text_candidates:
            if field in sample_question:
                value = sample_question[field]
                if value and isinstance(value, str) and len(value.strip()) > 0:
                    question_text_field = field
                    print(f"   ✅ Found '{field}' field with content")
                    print(f"   📊 Sample: {value[:200]}...")
                    break
                else:
                    print(f"   ⚠️ Found '{field}' field but it's empty")
        
        if not question_text_field:
            print(f"   ❌ No suitable question text field found!")
        
        # Check for the specific 'why' field mentioned in the review request
        print(f"\n🔍 SPECIFIC 'WHY' FIELD CHECK:")
        if 'why' in sample_question:
            why_value = sample_question['why']
            if why_value and isinstance(why_value, str) and len(why_value.strip()) > 0:
                print(f"   ✅ 'why' field EXISTS and has content")
                print(f"   📊 Content: {why_value[:300]}...")
            else:
                print(f"   ⚠️ 'why' field exists but is empty/null")
        else:
            print(f"   ❌ 'why' field does NOT exist (explains frontend issue)")
        
        # Check for options structure
        print(f"\n📋 OPTIONS STRUCTURE:")
        option_fields = ['option_a', 'option_b', 'option_c', 'option_d']
        options_exist = all(field in sample_question for field in option_fields)
        
        if options_exist:
            print(f"   ✅ Standard A/B/C/D option fields found:")
            for opt_field in option_fields:
                print(f"      {opt_field}: {sample_question[opt_field]}")
        else:
            print(f"   ❌ Standard option fields missing")
            # Check for alternative options structure
            if 'options' in sample_question:
                print(f"   📊 Alternative 'options' field: {sample_question['options']}")
        
        # Check for answer field
        print(f"\n✅ CORRECT ANSWER FIELD:")
        answer_fields = ['answer', 'correct_answer', 'right_answer']
        answer_field = None
        
        for field in answer_fields:
            if field in sample_question:
                value = sample_question[field]
                if value:
                    answer_field = field
                    print(f"   ✅ Found '{field}' field: {value}")
                    break
        
        if not answer_field:
            print(f"   ❌ No answer field found!")
        
        # Check for ID field
        print(f"\n🆔 QUESTION ID FIELD:")
        id_fields = ['id', 'question_id', 'item_id']
        id_field = None
        
        for field in id_fields:
            if field in sample_question:
                value = sample_question[field]
                if value:
                    id_field = field
                    print(f"   ✅ Found '{field}' field: {value}")
                    break
        
        if not id_field:
            print(f"   ❌ No ID field found!")
        
        # Check for category/subcategory
        print(f"\n📂 CATEGORY/SUBCATEGORY FIELDS:")
        if 'category' in sample_question:
            print(f"   ✅ Category: {sample_question['category']}")
        if 'subcategory' in sample_question:
            print(f"   ✅ Subcategory: {sample_question['subcategory']}")
        
        # Frontend mapping recommendations
        print(f"\n💡 FRONTEND MAPPING RECOMMENDATIONS:")
        print("=" * 80)
        
        print(f"🔧 CURRENT ISSUE:")
        print(f"   Frontend uses: packItem.why || 'Question content unavailable'")
        print(f"   'why' field exists: {'YES' if 'why' in sample_question else 'NO'}")
        
        print(f"\n🔧 RECOMMENDED FIXES:")
        
        if question_text_field:
            print(f"   📝 Question Text:")
            print(f"      CHANGE FROM: packItem.why || 'Question content unavailable'")
            print(f"      CHANGE TO:   packItem.{question_text_field} || 'Question content unavailable'")
        
        if options_exist:
            print(f"   📋 Options:")
            print(f"      Use: {{")
            print(f"        A: packItem.option_a,")
            print(f"        B: packItem.option_b,")
            print(f"        C: packItem.option_c,")
            print(f"        D: packItem.option_d")
            print(f"      }}")
        
        if answer_field:
            print(f"   ✅ Correct Answer:")
            print(f"      Use: packItem.{answer_field}")
        
        if id_field:
            print(f"   🆔 Question ID:")
            print(f"      Use: packItem.{id_field}")
        
        # Show complete sample question structure
        print(f"\n📋 SAMPLE COMPLETE QUESTION STRUCTURE:")
        print("=" * 80)
        print(json.dumps(sample_question, indent=2))
        
        return {
            'question_text_field': question_text_field,
            'why_field_exists': 'why' in sample_question,
            'options_structure': 'standard' if options_exist else 'non-standard',
            'answer_field': answer_field,
            'id_field': id_field,
            'total_fields': len(all_fields),
            'sample_question': sample_question
        }

def main():
    print("🎯 PACK DATA STRUCTURE ANALYSIS")
    print("=" * 80)
    print("OBJECTIVE: Analyze actual pack data structure for frontend field mapping")
    print("FOCUS: Question fields, options structure, answer format, metadata")
    print("EXPECTED: Complete field documentation for frontend integration")
    print("=" * 80)
    
    analyzer = PackDataAnalyzer()
    
    # Step 1: Authenticate
    auth_info = analyzer.authenticate()
    if not auth_info:
        print("❌ Authentication failed - cannot proceed")
        return False
    
    # Step 2: Create session
    session_id = analyzer.create_session(auth_info)
    if not session_id:
        print("❌ Session creation failed - cannot proceed")
        return False
    
    # Step 3: Fetch pack data
    pack_data = analyzer.fetch_pack_data(auth_info, session_id)
    if not pack_data:
        print("❌ Pack data retrieval failed - cannot proceed")
        return False
    
    # Step 4: Analyze structure
    analysis_result = analyzer.analyze_pack_structure(pack_data)
    
    # Summary
    print(f"\n🎯 ANALYSIS SUMMARY:")
    print("=" * 80)
    
    if analysis_result:
        print(f"✅ Pack structure analysis completed successfully")
        print(f"📊 Question text field: {analysis_result['question_text_field'] or 'NOT FOUND'}")
        print(f"📊 'why' field exists: {analysis_result['why_field_exists']}")
        print(f"📊 Options structure: {analysis_result['options_structure']}")
        print(f"📊 Answer field: {analysis_result['answer_field'] or 'NOT FOUND'}")
        print(f"📊 ID field: {analysis_result['id_field'] or 'NOT FOUND'}")
        print(f"📊 Total fields analyzed: {analysis_result['total_fields']}")
        
        print(f"\n🔑 KEY FINDING FOR REVIEW REQUEST:")
        if not analysis_result['why_field_exists']:
            print(f"❌ The 'why' field does NOT exist in pack items")
            print(f"💡 This explains why frontend shows 'Question content unavailable'")
            if analysis_result['question_text_field']:
                print(f"✅ Use '{analysis_result['question_text_field']}' field instead")
        else:
            print(f"✅ The 'why' field exists and can be used")
        
        return True
    else:
        print(f"❌ Pack structure analysis failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)