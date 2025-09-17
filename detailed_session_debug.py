#!/usr/bin/env python3
"""
Detailed Session Creation Debug
Trace through each step of the adaptive session logic to find where questions are being limited to 3
"""

import requests
import json
import time

class DetailedSessionDebugger:
    def __init__(self):
        self.base_url = "https://learning-tutor.preview.emergentagent.com/api"
        self.admin_token = None
        
    def authenticate_admin(self):
        """Authenticate admin user"""
        print("🔐 Authenticating admin user...")
        
        login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                user = data.get('user', {})
                print(f"✅ Admin authenticated: {user.get('email')}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def analyze_question_subcategories(self):
        """Analyze the subcategories of questions in the database"""
        print("\n📊 Analyzing question subcategories...")
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{self.base_url}/questions?limit=50", headers=headers)
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                active_questions = [q for q in questions if q.get('is_active', False)]
                
                print(f"   Total questions: {len(questions)}")
                print(f"   Active questions: {len(active_questions)}")
                
                # Analyze subcategories
                subcategory_counts = {}
                for q in active_questions:
                    subcat = q.get('subcategory', 'Unknown')
                    subcategory_counts[subcat] = subcategory_counts.get(subcat, 0) + 1
                
                print(f"\n   Subcategory distribution:")
                for subcat, count in sorted(subcategory_counts.items()):
                    print(f"     {subcat}: {count} questions")
                
                # Check canonical taxonomy mapping
                canonical_subcategories = {
                    "A-Arithmetic": [
                        "Time–Speed–Distance (TSD)", "Time & Work", "Ratio–Proportion–Variation",
                        "Percentages", "Averages & Alligation", "Profit–Loss–Discount (PLD)",
                        "Simple & Compound Interest (SI–CI)", "Mixtures & Solutions"
                    ],
                    "B-Algebra": [
                        "Linear Equations", "Quadratic Equations", "Inequalities", "Progressions",
                        "Functions & Graphs", "Logarithms & Exponents", "Special Algebraic Identities"
                    ],
                    "C-Geometry & Mensuration": [
                        "Triangles", "Circles", "Polygons", "Coordinate Geometry",
                        "Mensuration (2D & 3D)", "Trigonometry in Geometry"
                    ],
                    "D-Number System": [
                        "Divisibility", "HCF–LCM", "Remainders & Modular Arithmetic",
                        "Base Systems", "Digit Properties"
                    ],
                    "E-Modern Math": [
                        "Permutation–Combination (P&C)", "Probability", "Set Theory & Venn Diagrams"
                    ]
                }
                
                print(f"\n   Canonical taxonomy mapping:")
                category_mapping = {}
                unmapped_subcategories = []
                
                for subcat in subcategory_counts.keys():
                    mapped = False
                    for category, canonical_subcats in canonical_subcategories.items():
                        if subcat in canonical_subcats:
                            if category not in category_mapping:
                                category_mapping[category] = []
                            category_mapping[category].append((subcat, subcategory_counts[subcat]))
                            mapped = True
                            break
                    
                    if not mapped:
                        unmapped_subcategories.append((subcat, subcategory_counts[subcat]))
                
                for category, subcats in category_mapping.items():
                    total_questions = sum(count for _, count in subcats)
                    print(f"     {category}: {total_questions} questions")
                    for subcat, count in subcats:
                        print(f"       - {subcat}: {count}")
                
                if unmapped_subcategories:
                    print(f"     UNMAPPED SUBCATEGORIES:")
                    for subcat, count in unmapped_subcategories:
                        print(f"       - {subcat}: {count} questions")
                
                return {
                    'total_active': len(active_questions),
                    'subcategory_counts': subcategory_counts,
                    'category_mapping': category_mapping,
                    'unmapped': unmapped_subcategories
                }
            else:
                print(f"   ❌ Failed to get questions: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Error analyzing subcategories: {e}")
            return None
    
    def test_multiple_sessions(self, count=5):
        """Test multiple session creations to see if the pattern is consistent"""
        print(f"\n🔄 Testing {count} session creations...")
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        session_data = {"target_minutes": 30}
        results = []
        
        for i in range(count):
            try:
                response = requests.post(f"{self.base_url}/sessions/start", json=session_data, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    session_id = data.get('session_id')
                    total_questions = data.get('total_questions')
                    session_type = data.get('session_type')
                    personalization = data.get('personalization', {})
                    
                    result = {
                        'session_id': session_id,
                        'total_questions': total_questions,
                        'session_type': session_type,
                        'personalization_applied': personalization.get('applied'),
                        'learning_stage': personalization.get('learning_stage'),
                        'difficulty_distribution': personalization.get('difficulty_distribution'),
                        'category_distribution': personalization.get('category_distribution')
                    }
                    results.append(result)
                    
                    print(f"   Session {i+1}: {total_questions} questions, Type: {session_type}")
                    print(f"     Personalization: {personalization.get('applied')}")
                    print(f"     Category distribution: {personalization.get('category_distribution')}")
                    
                else:
                    print(f"   Session {i+1}: Failed with status {response.status_code}")
                    
            except Exception as e:
                print(f"   Session {i+1}: Error - {e}")
        
        # Analyze results
        question_counts = [r['total_questions'] for r in results if r['total_questions']]
        if question_counts:
            avg_questions = sum(question_counts) / len(question_counts)
            print(f"\n   Average questions per session: {avg_questions:.1f}")
            print(f"   Question count range: {min(question_counts)} - {max(question_counts)}")
            
            if all(count == 3 for count in question_counts):
                print("   ❌ CONSISTENT ISSUE: All sessions have exactly 3 questions")
            elif all(count == 12 for count in question_counts):
                print("   ✅ All sessions have 12 questions as expected")
            else:
                print("   ⚠️ INCONSISTENT: Session question counts vary")
        
        return results
    
    def investigate_category_distribution_issue(self):
        """Investigate if the issue is in category distribution logic"""
        print("\n🔍 Investigating category distribution logic...")
        
        # The base category distribution from adaptive_session_logic.py
        base_category_distribution = {
            "A-Arithmetic": 4,           # 33% - Most important for CAT
            "B-Algebra": 3,              # 25% - Core mathematical concepts
            "C-Geometry & Mensuration": 2, # 17% - Spatial reasoning
            "D-Number System": 2,        # 17% - Fundamental concepts
            "E-Modern Math": 1           # 8% - Advanced topics
        }
        
        print(f"   Expected base distribution: {base_category_distribution}")
        print(f"   Total expected questions: {sum(base_category_distribution.values())}")
        
        # Check if the issue is that questions don't map to these categories
        analysis = self.analyze_question_subcategories()
        if analysis:
            category_mapping = analysis['category_mapping']
            unmapped = analysis['unmapped']
            
            print(f"\n   Available questions by category:")
            available_by_category = {}
            for category, subcats in category_mapping.items():
                total = sum(count for _, count in subcats)
                available_by_category[category] = total
                print(f"     {category}: {total} questions available")
            
            print(f"\n   Can we fulfill the base distribution?")
            can_fulfill = True
            for category, needed in base_category_distribution.items():
                available = available_by_category.get(category, 0)
                status = "✅" if available >= needed else "❌"
                print(f"     {category}: Need {needed}, Have {available} {status}")
                if available < needed:
                    can_fulfill = False
            
            if not can_fulfill:
                print(f"\n   ❌ ISSUE IDENTIFIED: Cannot fulfill base category distribution")
                print(f"   This could cause the session logic to fail and return fewer questions")
            else:
                print(f"\n   ✅ Sufficient questions available for all categories")
            
            if unmapped:
                total_unmapped = sum(count for _, count in unmapped)
                print(f"\n   ⚠️ {total_unmapped} questions in unmapped subcategories:")
                for subcat, count in unmapped:
                    print(f"     - {subcat}: {count} questions")
                print(f"   These questions may not be included in session creation")
        
        return analysis
    
    def run_detailed_debug(self):
        """Run complete detailed debug analysis"""
        print("🔍 DETAILED SESSION CREATION DEBUG")
        print("=" * 60)
        print("Tracing through adaptive session logic to find 3-question limitation")
        print("=" * 60)
        
        # Step 1: Authenticate
        if not self.authenticate_admin():
            return False
        
        # Step 2: Analyze question subcategories and mapping
        analysis = self.investigate_category_distribution_issue()
        
        # Step 3: Test multiple sessions
        session_results = self.test_multiple_sessions(3)
        
        # Step 4: Final analysis
        print("\n" + "=" * 60)
        print("DETAILED DEBUG CONCLUSIONS")
        print("=" * 60)
        
        if analysis:
            category_mapping = analysis.get('category_mapping', {})
            unmapped = analysis.get('unmapped', [])
            
            # Check if the issue is category mapping
            base_distribution = {
                "A-Arithmetic": 4, "B-Algebra": 3, "C-Geometry & Mensuration": 2,
                "D-Number System": 2, "E-Modern Math": 1
            }
            
            missing_categories = []
            insufficient_categories = []
            
            for category, needed in base_distribution.items():
                if category not in category_mapping:
                    missing_categories.append(category)
                else:
                    available = sum(count for _, count in category_mapping[category])
                    if available < needed:
                        insufficient_categories.append((category, needed, available))
            
            if missing_categories:
                print(f"❌ MISSING CATEGORIES: {missing_categories}")
                print("   These categories have no questions, causing distribution failure")
            
            if insufficient_categories:
                print(f"❌ INSUFFICIENT QUESTIONS IN CATEGORIES:")
                for category, needed, available in insufficient_categories:
                    print(f"   {category}: Need {needed}, Have {available}")
            
            if unmapped:
                print(f"⚠️ UNMAPPED SUBCATEGORIES: {len(unmapped)} subcategories not in canonical taxonomy")
                print("   These questions are excluded from intelligent session creation")
            
            # Root cause analysis
            if missing_categories or insufficient_categories:
                print(f"\n🎯 ROOT CAUSE IDENTIFIED:")
                print(f"   The adaptive session logic expects questions in specific canonical categories")
                print(f"   When categories are missing or insufficient, the logic may fail gracefully")
                print(f"   by returning only the questions it can find, resulting in 3 questions instead of 12")
                
                print(f"\n💡 SOLUTIONS:")
                print(f"   1. Update question subcategories to match canonical taxonomy")
                print(f"   2. Modify adaptive logic to handle unmapped subcategories")
                print(f"   3. Add fallback logic when category distribution fails")
                print(f"   4. Create more questions in missing/insufficient categories")
            else:
                print(f"✅ Category mapping appears sufficient - issue may be elsewhere in logic")
        
        return True

if __name__ == "__main__":
    debugger = DetailedSessionDebugger()
    debugger.run_detailed_debug()