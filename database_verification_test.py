#!/usr/bin/env python3
"""
Database Table and Endpoint Verification Test
Focused test to clarify the discrepancy between manual database check and API results
"""

import requests
import json
from datetime import datetime

class DatabaseVerificationTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.admin_headers = None

    def authenticate_admin(self):
        """Authenticate as admin user"""
        print("🔐 Authenticating as admin...")
        
        admin_login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login", 
                json=admin_login_data, 
                timeout=30, 
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                self.admin_headers = {
                    'Authorization': f'Bearer {self.admin_token}',
                    'Content-Type': 'application/json'
                }
                print(f"✅ Admin authentication successful")
                return True
            else:
                print(f"❌ Admin authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Admin authentication error: {e}")
            return False

    def test_pyq_questions_endpoint(self):
        """Test the PYQ questions endpoint and analyze the data structure"""
        print("\n📊 Testing GET /api/admin/pyq/questions endpoint...")
        
        if not self.admin_headers:
            print("❌ No admin authentication - cannot test")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/admin/pyq/questions",
                headers=self.admin_headers,
                timeout=30,
                verify=False
            )
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ PYQ Questions endpoint accessible")
                
                # Analyze response structure
                print(f"\n📋 Response Structure Analysis:")
                print(f"Response type: {type(data)}")
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Look for questions data
                questions = None
                if isinstance(data, dict):
                    questions = data.get('questions', data.get('data', data.get('pyq_questions', [])))
                elif isinstance(data, list):
                    questions = data
                
                if questions and len(questions) > 0:
                    print(f"\n📊 Questions Data Analysis:")
                    print(f"Total questions returned: {len(questions)}")
                    
                    # Analyze first question structure
                    first_question = questions[0]
                    print(f"First question type: {type(first_question)}")
                    
                    if isinstance(first_question, dict):
                        print(f"First question fields: {list(first_question.keys())}")
                        
                        # Check for enrichment-related fields
                        enrichment_fields = [
                            'quality_verified', 'category', 'subcategory', 
                            'type_of_question', 'difficulty_level', 'right_answer'
                        ]
                        
                        print(f"\n🔍 Enrichment Fields Analysis:")
                        for field in enrichment_fields:
                            if field in first_question:
                                value = first_question[field]
                                print(f"  ✅ {field}: {value} (type: {type(value)})")
                            else:
                                print(f"  ❌ {field}: NOT PRESENT")
                        
                        # Sample a few more questions for pattern analysis
                        print(f"\n📋 Sample Questions Analysis (first 5):")
                        for i, question in enumerate(questions[:5]):
                            if isinstance(question, dict):
                                q_id = question.get('id', f'Q{i+1}')
                                quality_verified = question.get('quality_verified')
                                category = question.get('category')
                                subcategory = question.get('subcategory')
                                type_of_question = question.get('type_of_question')
                                
                                print(f"  Question {i+1} (ID: {q_id}):")
                                print(f"    quality_verified: {quality_verified}")
                                print(f"    category: {category}")
                                print(f"    subcategory: {subcategory}")
                                print(f"    type_of_question: {type_of_question}")
                                
                                # Determine enrichment status
                                is_enriched = self.determine_enrichment_status(question)
                                print(f"    ENRICHED: {'✅ YES' if is_enriched else '❌ NO'}")
                                print()
                
                return data
            else:
                print(f"❌ PYQ Questions endpoint failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error testing PYQ questions endpoint: {e}")
            return None

    def test_pyq_enrichment_status_endpoint(self):
        """Test the PYQ enrichment status endpoint"""
        print("\n📊 Testing GET /api/admin/pyq/enrichment-status endpoint...")
        
        if not self.admin_headers:
            print("❌ No admin authentication - cannot test")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/admin/pyq/enrichment-status",
                headers=self.admin_headers,
                timeout=30,
                verify=False
            )
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ PYQ Enrichment Status endpoint accessible")
                
                # Analyze response structure
                print(f"\n📋 Enrichment Status Response Analysis:")
                print(f"Response type: {type(data)}")
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Look for enrichment statistics
                if isinstance(data, dict):
                    stats = data.get('enrichment_statistics', data.get('stats', {}))
                    if stats:
                        print(f"\n📊 Enrichment Statistics:")
                        for key, value in stats.items():
                            print(f"  {key}: {value}")
                    
                    # Look for other relevant data
                    for key, value in data.items():
                        if key not in ['enrichment_statistics', 'stats']:
                            print(f"  {key}: {value}")
                
                return data
            else:
                print(f"❌ PYQ Enrichment Status endpoint failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error testing PYQ enrichment status endpoint: {e}")
            return None

    def determine_enrichment_status(self, question):
        """Determine if a question is enriched based on available fields"""
        if not isinstance(question, dict):
            return False
        
        # Check quality_verified field first
        quality_verified = question.get('quality_verified')
        if quality_verified == True or quality_verified == 'true':
            return True
        
        # Check if category is present and not empty/null
        category = question.get('category')
        if category and category != '' and category != 'null' and category != None:
            return True
        
        # Check if subcategory is present and not empty/null
        subcategory = question.get('subcategory')
        if subcategory and subcategory != '' and subcategory != 'null' and subcategory != None:
            return True
        
        # Check if type_of_question is present and not empty/null
        type_of_question = question.get('type_of_question')
        if type_of_question and type_of_question != '' and type_of_question != 'null' and type_of_question != None:
            return True
        
        return False

    def analyze_discrepancy(self, questions_data, enrichment_status_data):
        """Analyze the discrepancy between endpoints"""
        print("\n🔍 DISCREPANCY ANALYSIS")
        print("=" * 60)
        
        # Extract data from endpoints
        questions = []
        if questions_data:
            if isinstance(questions_data, dict):
                questions = questions_data.get('questions', questions_data.get('data', questions_data.get('pyq_questions', [])))
            elif isinstance(questions_data, list):
                questions = questions_data
        
        enrichment_stats = {}
        if enrichment_status_data and isinstance(enrichment_status_data, dict):
            enrichment_stats = enrichment_status_data.get('enrichment_statistics', enrichment_status_data.get('stats', {}))
        
        print(f"📊 Data Summary:")
        print(f"  Questions from /pyq/questions: {len(questions)}")
        print(f"  Enrichment stats available: {'Yes' if enrichment_stats else 'No'}")
        
        if enrichment_stats:
            print(f"\n📊 Enrichment Status Endpoint Reports:")
            for key, value in enrichment_stats.items():
                print(f"  {key}: {value}")
        
        if questions:
            print(f"\n📊 Manual Analysis of Questions Data:")
            
            # Analyze enrichment status manually
            enriched_count = 0
            total_count = len(questions)
            
            field_analysis = {
                'quality_verified_true': 0,
                'quality_verified_false': 0,
                'quality_verified_null': 0,
                'category_present': 0,
                'category_empty': 0,
                'subcategory_present': 0,
                'subcategory_empty': 0,
                'type_of_question_present': 0,
                'type_of_question_empty': 0
            }
            
            for question in questions:
                if isinstance(question, dict):
                    # Check enrichment status
                    if self.determine_enrichment_status(question):
                        enriched_count += 1
                    
                    # Analyze individual fields
                    qv = question.get('quality_verified')
                    if qv == True or qv == 'true':
                        field_analysis['quality_verified_true'] += 1
                    elif qv == False or qv == 'false':
                        field_analysis['quality_verified_false'] += 1
                    else:
                        field_analysis['quality_verified_null'] += 1
                    
                    cat = question.get('category')
                    if cat and cat != '' and cat != 'null' and cat != None:
                        field_analysis['category_present'] += 1
                    else:
                        field_analysis['category_empty'] += 1
                    
                    subcat = question.get('subcategory')
                    if subcat and subcat != '' and subcat != 'null' and subcat != None:
                        field_analysis['subcategory_present'] += 1
                    else:
                        field_analysis['subcategory_empty'] += 1
                    
                    toq = question.get('type_of_question')
                    if toq and toq != '' and toq != 'null' and toq != None:
                        field_analysis['type_of_question_present'] += 1
                    else:
                        field_analysis['type_of_question_empty'] += 1
            
            print(f"  Total questions analyzed: {total_count}")
            print(f"  Enriched questions (manual count): {enriched_count}")
            print(f"  Unenriched questions (manual count): {total_count - enriched_count}")
            print(f"  Manual enrichment rate: {(enriched_count/total_count)*100:.1f}%")
            
            print(f"\n📊 Field Distribution Analysis:")
            for field, count in field_analysis.items():
                percentage = (count / total_count) * 100 if total_count > 0 else 0
                print(f"  {field}: {count}/{total_count} ({percentage:.1f}%)")
        
        # Compare with enrichment status endpoint
        if enrichment_stats and questions:
            print(f"\n🎯 COMPARISON ANALYSIS:")
            
            api_total = enrichment_stats.get('total_questions', enrichment_stats.get('total', 0))
            api_enriched = enrichment_stats.get('enriched_questions', enrichment_stats.get('enriched', 0))
            
            manual_total = len(questions)
            manual_enriched = sum(1 for q in questions if self.determine_enrichment_status(q))
            
            print(f"  API Reports:")
            print(f"    Total: {api_total}")
            print(f"    Enriched: {api_enriched}")
            print(f"    Unenriched: {api_total - api_enriched}")
            
            print(f"  Manual Analysis:")
            print(f"    Total: {manual_total}")
            print(f"    Enriched: {manual_enriched}")
            print(f"    Unenriched: {manual_total - manual_enriched}")
            
            print(f"  Discrepancy:")
            print(f"    Total difference: {abs(api_total - manual_total)}")
            print(f"    Enriched difference: {abs(api_enriched - manual_enriched)}")
            
            if api_enriched != manual_enriched:
                print(f"\n⚠️ DISCREPANCY DETECTED!")
                print(f"  API says {api_enriched} enriched, manual analysis says {manual_enriched}")
                print(f"  This suggests different enrichment criteria are being used")

    def run_verification(self):
        """Run the complete database verification test"""
        print("🔍 DATABASE TABLE AND ENDPOINT VERIFICATION")
        print("=" * 80)
        print("OBJECTIVE: Clarify the discrepancy between manual database check and API results")
        print("User says: Database manually checked and everything is intact")
        print("API shows: All 236 questions need enrichment")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate_admin():
            print("❌ Cannot proceed without admin authentication")
            return False
        
        # Step 2: Test PYQ questions endpoint
        questions_data = self.test_pyq_questions_endpoint()
        
        # Step 3: Test PYQ enrichment status endpoint
        enrichment_status_data = self.test_pyq_enrichment_status_endpoint()
        
        # Step 4: Analyze discrepancy
        self.analyze_discrepancy(questions_data, enrichment_status_data)
        
        # Step 5: Provide recommendations
        print("\n🎯 RECOMMENDATIONS")
        print("=" * 60)
        print("1. FIELD VERIFICATION:")
        print("   - Check which field the user is looking at manually")
        print("   - Verify if API is checking 'quality_verified' vs 'category' fields")
        print("")
        print("2. DATABASE QUERY:")
        print("   - Run: SELECT COUNT(*) FROM pyq_questions WHERE quality_verified = true;")
        print("   - Run: SELECT COUNT(*) FROM pyq_questions WHERE category IS NOT NULL AND category != '';")
        print("")
        print("3. ENRICHMENT CRITERIA:")
        print("   - Clarify what constitutes an 'enriched' question")
        print("   - Align manual check criteria with API criteria")
        print("")
        print("4. DATA SYNCHRONIZATION:")
        print("   - Check if API is using cached data")
        print("   - Verify recent database updates are reflected")
        
        return True

if __name__ == "__main__":
    tester = DatabaseVerificationTester()
    tester.run_verification()