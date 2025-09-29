#!/usr/bin/env python3
import os
import json
import google.generativeai as genai

# Set API key directly
google_api_key = "AIzaSyBf3YeOH09t1b2V038Rx9vyVahwKo8MvhE"

# Sample data for testing
test_data = {
    'sessions': [
        {'accuracy': 0.5, 'total_questions': 12},
        {'accuracy': 0.6, 'total_questions': 12}
    ],
    'concept_journey': [
        {'concept': 'Time-Speed-Distance', 'accuracy': 0.4, 'readiness': 'Weak'},
        {'concept': 'Algebra', 'accuracy': 0.7, 'readiness': 'Strong'}
    ]
}

# Create demanding prompt
demanding_prompt = f"""
Analyze this data and return JSON with specific numbers:

DATA: {json.dumps(test_data)}

Return JSON format:
{{"dashboard_all_time": "ANALYSIS: X sessions with Y% accuracy. Strongest: [concept] at Z%. Weakest: [concept] at W%.", "dashboard_recent": "Recent trend analysis", "pre_session_card": {{"title": "Analysis", "progress": "Performance summary", "way_forward": ["Specific action 1", "Specific action 2"], "today": "Focus areas"}}}}

Return ONLY JSON, no markdown.
"""

print(f'Testing demanding analytical prompt with Gemini...')

try:
    # Configure Gemini
    genai.configure(api_key=google_api_key)
    
    # Create model
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    print(f'Prompt length: {len(demanding_prompt)} chars')
    
    response = model.generate_content(demanding_prompt)
    
    print(f'Response received successfully')
    print(f'Response text: {response.text}')
    
    # Try to parse as JSON
    try:
        text = response.text.strip()
        parsed = json.loads(text)
        print(f'✅ Successfully parsed JSON!')
        print(f'Dashboard all-time: {parsed.get("dashboard_all_time", "")}')
        
        # Check for specific analysis
        all_text = str(parsed)
        has_numbers = any(char.isdigit() for char in all_text)
        has_analysis = 'ANALYSIS:' in all_text
        print(f'Contains numbers: {has_numbers}')
        print(f'Contains analysis: {has_analysis}')
        
        # Check for banned phrases
        banned_phrases = ['consistent practice', 'building foundations', 'trust the process']
        found_banned = [phrase for phrase in banned_phrases if phrase.lower() in all_text.lower()]
        if found_banned:
            print(f'❌ FOUND BANNED PHRASES: {found_banned}')
        else:
            print(f'✅ NO BANNED PHRASES FOUND!')
            
    except json.JSONDecodeError as je:
        print(f'❌ JSON parse error: {je}')
        print(f'Raw response: {response.text[:200]}...')
        
except Exception as e:
    print(f'API call failed: {e}')
    import traceback
    traceback.print_exc()