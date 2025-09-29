#!/usr/bin/env python3
"""
Direct test of the Gemini API integration for insights
"""

import os
import sys
sys.path.append('/app/backend')

def test_gemini_api():
    """Test direct Gemini API call"""
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            print("❌ Google API key not found in environment variables")
            return False
        
        print(f"✅ Google API key found: {google_api_key[:10]}...")
        
        # Configure Gemini
        genai.configure(api_key=google_api_key)
        
        # Initialize Gemini model
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            system_instruction="You are a strict data analyst for CAT preparation. You MUST analyze the provided JSON data and return specific numerical insights with concept names and exact performance numbers."
        )
        
        # Test prompt
        test_prompt = """
CRITICAL: Analyze the JSON data below and provide SPECIFIC numerical insights. Do NOT write generic motivational text.

DATA TO ANALYZE:
{"sessions": [{"accuracy": 0.42}, {"accuracy": 0.38}], "concepts": ["Arithmetic", "Algebra"]}

RESPONSE RULES:
- Use "about X out of 10 correct" format
- Mention specific concept names and their exact accuracies
- NO phrases like "consistent practice" or "building foundations"

ANALYZE AND RESPOND:
        """
        
        # Generate content
        response = model.generate_content(
            test_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1200,
                temperature=0.3,
            )
        )
        
        if response and response.text:
            print(f"✅ Gemini API call successful")
            print(f"📊 Response length: {len(response.text)} chars")
            print(f"📝 Response: {response.text[:200]}...")
            return True
        else:
            print(f"❌ No response text from Gemini")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_insight_generator_service():
    """Test the insight generator service directly"""
    try:
        from services.insight_generator_service import insight_generator_service
        
        # Test data slice
        test_slice = {
            "user_id": "test-user",
            "total_sessions": 5,
            "accuracy_series": [0.42, 0.38, 0.45, 0.50, 0.48],
            "concepts_journey": [
                {"concept": "Arithmetic", "accuracy": 0.6},
                {"concept": "Algebra", "accuracy": 0.4}
            ]
        }
        
        print("🧠 Testing insight generator service...")
        
        # Test all-time markdown generation
        all_time_result = insight_generator_service.gen_all_time_markdown(test_slice)
        print(f"✅ All-time markdown generated: {len(all_time_result)} chars")
        print(f"📝 Sample: {all_time_result[:200]}...")
        
        # Test recent markdown generation
        recent_result = insight_generator_service.gen_recent_markdown(test_slice)
        print(f"✅ Recent markdown generated: {len(recent_result)} chars")
        print(f"📝 Sample: {recent_result[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Insight generator service test failed: {e}")
        return False

def main():
    """Main test execution"""
    print("🧪 TESTING GEMINI API INTEGRATION FOR INSIGHTS")
    print("=" * 60)
    
    # Test 1: Direct Gemini API
    print("\n1. TESTING DIRECT GEMINI API...")
    gemini_success = test_gemini_api()
    
    # Test 2: Insight Generator Service
    print("\n2. TESTING INSIGHT GENERATOR SERVICE...")
    service_success = test_insight_generator_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("🧪 GEMINI API INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Direct Gemini API: {'✅ PASS' if gemini_success else '❌ FAIL'}")
    print(f"Insight Generator Service: {'✅ PASS' if service_success else '❌ FAIL'}")
    
    overall_success = gemini_success and service_success
    print(f"\nOverall: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)