#!/usr/bin/env python3

import sys
import os
sys.path.append('/app/backend')

def test_insight_generation_with_real_data():
    """Test insight generation with real database data"""
    print("🎯 TESTING INSIGHT GENERATION WITH REAL DATABASE DATA")
    print("=" * 80)
    
    try:
        # Test database connection first
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Test basic connection
            result = db.execute(text("SELECT 1")).fetchone()
            print("   ✅ Database connection successful")
            
            # Find a user with data
            users_result = db.execute(text("""
                SELECT u.id, u.email, COUNT(ae.id) as attempt_count
                FROM users u
                LEFT JOIN attempt_events ae ON ae.user_id = u.id
                WHERE u.adaptive_enabled = true
                GROUP BY u.id, u.email
                HAVING COUNT(ae.id) > 0
                ORDER BY COUNT(ae.id) DESC
                LIMIT 5
            """)).fetchall()
            
            if users_result:
                print(f"   ✅ Found {len(users_result)} users with attempt data")
                
                # Use the user with most attempts
                test_user = users_result[0]
                user_id = test_user[0]
                user_email = test_user[1]
                attempt_count = test_user[2]
                
                print(f"   📊 Testing with user: {user_email} ({attempt_count} attempts)")
                
                # Test the insight generation
                from services.insight_generator_service import insight_generator_service
                
                # Build comprehensive data
                comprehensive_data = {"user_id": user_id}
                
                # Test the prompt building (this should now work with real data)
                prompt = insight_generator_service._build_comprehensive_insights_prompt(comprehensive_data)
                
                print(f"   📊 Generated prompt length: {len(prompt)} characters")
                
                # Check for minimum attempt threshold indicators
                threshold_indicators = [
                    "minimum 3 attempts required",
                    "≥3 attempts",
                    "sufficient data",
                    "limited data",
                    "<3 attempts",
                    "few more attempts would help assess"
                ]
                
                found_indicators = []
                for indicator in threshold_indicators:
                    if indicator.lower() in prompt.lower():
                        found_indicators.append(indicator)
                
                print(f"   ✅ Found threshold indicators in prompt: {found_indicators}")
                
                # Look for specific sections in the prompt
                if "CONCEPTS WITH LIMITED DATA" in prompt:
                    print("   ✅ Limited data concepts section found")
                
                if "CONCEPTS NEEDING ATTENTION (≥3 attempts)" in prompt:
                    print("   ✅ Sufficient data concepts section found")
                
                if "DO NOT make strong claims about mastery" in prompt:
                    print("   ✅ Warning about strong claims found")
                
                # Test actual insight generation
                insights = insight_generator_service.generate_comprehensive_insights(comprehensive_data)
                
                if insights and isinstance(insights, dict):
                    print("   ✅ Insights generated successfully")
                    
                    all_time = insights.get("dashboard_all_time", "")
                    recent = insights.get("dashboard_recent", "")
                    
                    print(f"   📊 All-time insight length: {len(all_time)} chars")
                    print(f"   📊 Recent insight length: {len(recent)} chars")
                    
                    # Check for appropriate language
                    combined_text = (all_time + " " + recent).lower()
                    
                    # Check for inappropriate strong claims
                    strong_claims = ["excellent grasp", "strong mastery", "you've mastered"]
                    inappropriate_claims = [claim for claim in strong_claims if claim in combined_text]
                    
                    # Check for appropriate softer language
                    soft_language = ["few more attempts", "would help assess", "better idea of", "clearer picture"]
                    found_soft_language = [phrase for phrase in soft_language if phrase in combined_text]
                    
                    if not inappropriate_claims:
                        print("   ✅ No inappropriate strong claims detected")
                    else:
                        print(f"   ⚠️ Found potentially inappropriate claims: {inappropriate_claims}")
                    
                    if found_soft_language:
                        print(f"   ✅ Found appropriate soft language: {found_soft_language}")
                    else:
                        print("   ⚠️ No soft language detected")
                    
                    # Show sample insights
                    print(f"   📝 Sample all-time insight: {all_time[:200]}...")
                    print(f"   📝 Sample recent insight: {recent[:200]}...")
                    
                    return True
                else:
                    print("   ❌ Failed to generate insights")
                    return False
                    
            else:
                print("   ⚠️ No users with attempt data found")
                return False
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"   ❌ Error testing with real data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_insight_generation_with_real_data()
    sys.exit(0 if result else 1)