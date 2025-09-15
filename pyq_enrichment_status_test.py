#!/usr/bin/env python3
"""
PYQ Questions Enrichment Status Check - Comprehensive Test
Testing the current status of PYQ questions enrichment as requested in the review.
"""

import requests
import json
from datetime import datetime
import sys

class PYQEnrichmentStatusTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def authenticate_admin(self):
        """Authenticate as admin user"""
        print("🔐 AUTHENTICATING AS ADMIN")
        print("-" * 50)
        
        login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                headers={'Content-Type': 'application/json'},
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                user_info = data.get('user', {})
                
                print(f"✅ Admin authentication successful")
                print(f"📊 User: {user_info.get('full_name')} ({user_info.get('email')})")
                print(f"📊 Admin privileges: {user_info.get('is_admin')}")
                print(f"📊 Token length: {len(self.admin_token)} characters")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def get_enrichment_status(self):
        """Get current PYQ enrichment status"""
        print("\n📊 GETTING CURRENT ENRICHMENT STATUS")
        print("-" * 50)
        
        if not self.admin_token:
            print("❌ No admin token available")
            return None
            
        try:
            headers = {
                'Authorization': f'Bearer {self.admin_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/admin/pyq/enrichment-status",
                headers=headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Enrichment status retrieved successfully")
                
                # Extract key statistics
                stats = data.get('enrichment_statistics', {})
                
                print(f"\n📈 CURRENT ENRICHMENT STATISTICS:")
                print(f"   Total PYQ Questions: {stats.get('total_questions', 0)}")
                print(f"   Active Questions: {stats.get('active_questions', 0)}")
                print(f"   Quality Verified: {stats.get('quality_verified', 0)}")
                print(f"   Concept Extracted: {stats.get('concept_extracted', 0)}")
                print(f"   Pending Enrichment: {stats.get('pending_enrichment', 0)}")
                print(f"   Failed Enrichment: {stats.get('failed_enrichment', 0)}")
                print(f"   Completion Rate: {stats.get('completion_rate', 0):.2f}%")
                print(f"   Average Difficulty Score: {stats.get('avg_difficulty_score', 0):.3f}")
                
                # Recent activity
                recent = data.get('recent_activity', {})
                if recent:
                    print(f"\n📅 RECENT ACTIVITY:")
                    print(f"   Last 24 Hours: {recent.get('last_24_hours', 0)} questions processed")
                
                # Difficulty distribution
                difficulty = data.get('difficulty_distribution', {})
                if difficulty:
                    print(f"\n📊 DIFFICULTY DISTRIBUTION:")
                    for level, count in difficulty.items():
                        print(f"   {level}: {count} questions")
                
                print(f"\n🎯 STATUS: {data.get('status', 'Unknown')}")
                print(f"💬 MESSAGE: {data.get('message', 'No message')}")
                
                return data
            else:
                print(f"❌ Failed to get enrichment status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting enrichment status: {e}")
            return None

    def get_sample_questions(self, limit=10):
        """Get sample PYQ questions for content verification"""
        print(f"\n🔍 GETTING SAMPLE QUESTIONS (limit={limit})")
        print("-" * 50)
        
        if not self.admin_token:
            print("❌ No admin token available")
            return None
            
        try:
            headers = {
                'Authorization': f'Bearer {self.admin_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/admin/pyq/questions?limit={limit}",
                headers=headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                
                print(f"✅ Retrieved {len(questions)} sample questions")
                print(f"📊 Total questions available: {data.get('total', 0)}")
                
                return questions
            else:
                print(f"❌ Failed to get sample questions: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting sample questions: {e}")
            return None

    def analyze_question_quality(self, questions):
        """Analyze the quality of enriched questions"""
        print(f"\n🧐 ANALYZING QUESTION ENRICHMENT QUALITY")
        print("-" * 50)
        
        if not questions:
            print("❌ No questions to analyze")
            return
        
        # Quality metrics
        total_questions = len(questions)
        quality_verified_count = 0
        has_category_count = 0
        has_subcategory_count = 0
        has_type_count = 0
        has_real_content_count = 0
        concept_extracted_count = 0
        
        print(f"📊 ANALYZING {total_questions} SAMPLE QUESTIONS:")
        print()
        
        for i, question in enumerate(questions[:5], 1):  # Analyze first 5 in detail
            q_id = question.get('id', 'Unknown')
            stem = question.get('stem', '')[:100] + "..." if len(question.get('stem', '')) > 100 else question.get('stem', '')
            
            category = question.get('category', '')
            subcategory = question.get('subcategory', '')
            type_of_question = question.get('type_of_question', '')
            quality_verified = question.get('quality_verified', False)
            concept_status = question.get('concept_extraction_status', '')
            core_concepts = question.get('core_concepts', [])
            difficulty_band = question.get('difficulty_band', '')
            difficulty_score = question.get('difficulty_score', 0)
            
            print(f"Question {i}:")
            print(f"   ID: {q_id}")
            print(f"   Stem: {stem}")
            print(f"   Category: {category or 'NOT SET'}")
            print(f"   Subcategory: {subcategory or 'NOT SET'}")
            print(f"   Type: {type_of_question or 'NOT SET'}")
            print(f"   Quality Verified: {'✅ YES' if quality_verified else '❌ NO'}")
            print(f"   Concept Status: {concept_status or 'NOT SET'}")
            print(f"   Core Concepts: {len(core_concepts) if isinstance(core_concepts, list) else 0} concepts")
            print(f"   Difficulty: {difficulty_band} ({difficulty_score})")
            
            # Count quality metrics
            if quality_verified:
                quality_verified_count += 1
            
            if category and category not in ['', 'To be classified by LLM', 'Unknown']:
                has_category_count += 1
                print(f"   ✅ Has proper category")
            else:
                print(f"   ❌ Missing or placeholder category")
            
            if subcategory and subcategory not in ['', 'To be classified by LLM', 'Unknown']:
                has_subcategory_count += 1
                print(f"   ✅ Has proper subcategory")
            else:
                print(f"   ❌ Missing or placeholder subcategory")
            
            if type_of_question and type_of_question not in ['', 'To be classified by LLM', 'Unknown']:
                has_type_count += 1
                print(f"   ✅ Has proper type classification")
            else:
                print(f"   ❌ Missing or placeholder type classification")
            
            if concept_status == 'completed':
                concept_extracted_count += 1
                print(f"   ✅ Concept extraction completed")
            else:
                print(f"   ⚠️ Concept extraction: {concept_status}")
            
            # Check for real enriched content
            if (category and category not in ['', 'To be classified by LLM', 'Unknown'] and
                subcategory and subcategory not in ['', 'To be classified by LLM', 'Unknown'] and
                type_of_question and type_of_question not in ['', 'To be classified by LLM', 'Unknown']):
                has_real_content_count += 1
                print(f"   ✅ Has real enriched content")
            else:
                print(f"   ❌ Has placeholder content")
            
            print()
        
        # Calculate overall quality metrics for all questions
        for question in questions:
            if question.get('quality_verified'):
                quality_verified_count += 1
            if question.get('category') and question.get('category') not in ['', 'To be classified by LLM', 'Unknown']:
                has_category_count += 1
            if question.get('subcategory') and question.get('subcategory') not in ['', 'To be classified by LLM', 'Unknown']:
                has_subcategory_count += 1
            if question.get('type_of_question') and question.get('type_of_question') not in ['', 'To be classified by LLM', 'Unknown']:
                has_type_count += 1
            if question.get('concept_extraction_status') == 'completed':
                concept_extracted_count += 1
        
        # Adjust counts (we double-counted the first 5)
        if total_questions > 5:
            quality_verified_count = sum(1 for q in questions if q.get('quality_verified'))
            has_category_count = sum(1 for q in questions if q.get('category') and q.get('category') not in ['', 'To be classified by LLM', 'Unknown'])
            has_subcategory_count = sum(1 for q in questions if q.get('subcategory') and q.get('subcategory') not in ['', 'To be classified by LLM', 'Unknown'])
            has_type_count = sum(1 for q in questions if q.get('type_of_question') and q.get('type_of_question') not in ['', 'To be classified by LLM', 'Unknown'])
            concept_extracted_count = sum(1 for q in questions if q.get('concept_extraction_status') == 'completed')
        
        print(f"📈 OVERALL QUALITY METRICS FOR {total_questions} QUESTIONS:")
        print(f"   Quality Verified: {quality_verified_count}/{total_questions} ({(quality_verified_count/total_questions)*100:.1f}%)")
        print(f"   Has Proper Category: {has_category_count}/{total_questions} ({(has_category_count/total_questions)*100:.1f}%)")
        print(f"   Has Proper Subcategory: {has_subcategory_count}/{total_questions} ({(has_subcategory_count/total_questions)*100:.1f}%)")
        print(f"   Has Proper Type: {has_type_count}/{total_questions} ({(has_type_count/total_questions)*100:.1f}%)")
        print(f"   Concept Extraction Complete: {concept_extracted_count}/{total_questions} ({(concept_extracted_count/total_questions)*100:.1f}%)")
        
        return {
            'total_questions': total_questions,
            'quality_verified_count': quality_verified_count,
            'has_category_count': has_category_count,
            'has_subcategory_count': has_subcategory_count,
            'has_type_count': has_type_count,
            'concept_extracted_count': concept_extracted_count
        }

    def run_comprehensive_test(self):
        """Run the comprehensive PYQ enrichment status test"""
        print("🎯 CURRENT PYQ QUESTIONS ENRICHMENT STATUS CHECK")
        print("=" * 80)
        print("OBJECTIVE: Check the real-time status of PYQ questions enrichment after all fixes")
        print("and triggering the enrichment process as requested in the review.")
        print()
        print("REVIEW REQUEST REQUIREMENTS:")
        print("1. Current Enrichment Status - Get latest count of total PYQ questions,")
        print("   how many have quality_verified=true vs false")
        print("2. Progress Update - Compare with earlier status")
        print("3. Content Verification - Check sample questions for proper enrichment")
        print("4. Processing Status - Check if enrichment is still active or completed")
        print()
        print("ENDPOINTS TO TEST:")
        print("- GET /api/admin/pyq/enrichment-status - for current statistics")
        print("- GET /api/admin/pyq/questions - for sample question data")
        print()
        print("AUTHENTICATION: sumedhprabhu18@gmail.com/admin2025")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate_admin():
            print("\n❌ CRITICAL FAILURE: Cannot authenticate as admin")
            return False
        
        # Step 2: Get enrichment status
        enrichment_data = self.get_enrichment_status()
        if not enrichment_data:
            print("\n❌ CRITICAL FAILURE: Cannot get enrichment status")
            return False
        
        # Step 3: Get sample questions
        sample_questions = self.get_sample_questions(10)
        if not sample_questions:
            print("\n❌ CRITICAL FAILURE: Cannot get sample questions")
            return False
        
        # Step 4: Analyze question quality
        quality_metrics = self.analyze_question_quality(sample_questions)
        
        # Step 5: Generate final report
        self.generate_final_report(enrichment_data, quality_metrics)
        
        return True

    def generate_final_report(self, enrichment_data, quality_metrics):
        """Generate final comprehensive report"""
        print("\n" + "=" * 80)
        print("🎉 PYQ ENRICHMENT STATUS CHECK - FINAL REPORT")
        print("=" * 80)
        
        stats = enrichment_data.get('enrichment_statistics', {})
        
        # Key findings
        total_questions = stats.get('total_questions', 0)
        quality_verified = stats.get('quality_verified', 0)
        pending_enrichment = stats.get('pending_enrichment', 0)
        completion_rate = stats.get('completion_rate', 0)
        
        print(f"📊 KEY FINDINGS:")
        print(f"   Total PYQ Questions in Database: {total_questions}")
        print(f"   Successfully Enriched (quality_verified=true): {quality_verified}")
        print(f"   Still Need Enrichment (quality_verified=false): {total_questions - quality_verified}")
        print(f"   Pending Enrichment: {pending_enrichment}")
        print(f"   Overall Completion Rate: {completion_rate:.2f}%")
        
        print(f"\n🎯 PROGRESS UPDATE:")
        if completion_rate >= 99:
            print(f"   ✅ EXCELLENT PROGRESS: {completion_rate:.1f}% completion rate")
            print(f"   ✅ Only {pending_enrichment} questions remaining")
            print(f"   🎉 Enrichment process is nearly complete!")
        elif completion_rate >= 90:
            print(f"   ✅ GOOD PROGRESS: {completion_rate:.1f}% completion rate")
            print(f"   ⚠️ {pending_enrichment} questions still pending")
        else:
            print(f"   ⚠️ MODERATE PROGRESS: {completion_rate:.1f}% completion rate")
            print(f"   🔧 {pending_enrichment} questions need attention")
        
        print(f"\n🔍 CONTENT VERIFICATION:")
        if quality_metrics:
            sample_size = quality_metrics['total_questions']
            category_rate = (quality_metrics['has_category_count'] / sample_size) * 100
            subcategory_rate = (quality_metrics['has_subcategory_count'] / sample_size) * 100
            type_rate = (quality_metrics['has_type_count'] / sample_size) * 100
            
            print(f"   Sample Size: {sample_size} questions analyzed")
            print(f"   Proper Categories: {category_rate:.1f}%")
            print(f"   Proper Subcategories: {subcategory_rate:.1f}%")
            print(f"   Proper Type Classification: {type_rate:.1f}%")
            
            if category_rate >= 90 and subcategory_rate >= 90 and type_rate >= 90:
                print(f"   ✅ EXCELLENT: Questions have high-quality enrichment")
            elif category_rate >= 70 and subcategory_rate >= 70 and type_rate >= 70:
                print(f"   ✅ GOOD: Questions have adequate enrichment")
            else:
                print(f"   ⚠️ NEEDS IMPROVEMENT: Some questions lack proper enrichment")
        
        print(f"\n⚡ PROCESSING STATUS:")
        status = enrichment_data.get('status', 'unknown')
        message = enrichment_data.get('message', '')
        
        if status == 'active':
            print(f"   🔄 ACTIVE: Enrichment process is currently running")
        else:
            print(f"   ⏸️ INACTIVE: Enrichment process is not currently running")
        
        print(f"   💬 System Message: {message}")
        
        # Final assessment
        print(f"\n🏆 FINAL ASSESSMENT:")
        
        if completion_rate >= 99 and quality_metrics and (quality_metrics['has_category_count'] / quality_metrics['total_questions']) >= 0.9:
            print(f"   🎉 SUCCESS: PYQ enrichment is nearly complete with high quality")
            print(f"   ✅ {quality_verified} questions successfully enriched")
            print(f"   ✅ Only {pending_enrichment} questions remaining")
            print(f"   ✅ Content quality verification passed")
            print(f"   🚀 READY FOR PRODUCTION USE")
        elif completion_rate >= 90:
            print(f"   ✅ GOOD PROGRESS: Enrichment is progressing well")
            print(f"   🔧 {pending_enrichment} questions still need processing")
            print(f"   📈 Continue monitoring progress")
        else:
            print(f"   ⚠️ NEEDS ATTENTION: Enrichment completion rate below 90%")
            print(f"   🔧 {pending_enrichment} questions require processing")
            print(f"   🚨 May need troubleshooting")
        
        print("\n" + "=" * 80)
        print("✅ PYQ ENRICHMENT STATUS CHECK COMPLETED")
        print("=" * 80)

def main():
    """Main function to run the test"""
    tester = PYQEnrichmentStatusTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 Test completed successfully!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())