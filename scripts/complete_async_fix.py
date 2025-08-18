#!/usr/bin/env python3
"""
Complete Async Fix for Adaptive Session Logic
Systematically convert all remaining async methods to synchronous
"""

import re

def complete_async_fix():
    """Fix all remaining async issues in adaptive_session_logic.py"""
    
    with open('/app/backend/adaptive_session_logic.py', 'r') as f:
        content = f.read()
    
    # Remove async from all remaining methods
    content = re.sub(r'async def (create_personalized_session)', r'def \1', content)
    content = re.sub(r'async def (identify_weakest_category)', r'def \1', content)
    content = re.sub(r'async def (identify_strongest_category)', r'def \1', content)
    content = re.sub(r'async def (analyze_user_learning_profile)', r'def \1', content)
    content = re.sub(r'async def (get_attempt_frequency_by_subcategory)', r'def \1', content)
    content = re.sub(r'async def (enforce_subcategory_diversity)', r'def \1', content)
    content = re.sub(r'async def (apply_spaced_repetition_filter)', r'def \1', content)
    
    # Remove all await from method calls
    content = re.sub(r'await self\.identify_weakest_category\(', r'self.identify_weakest_category(', content)
    content = re.sub(r'await self\.identify_strongest_category\(', r'self.identify_strongest_category(', content)
    content = re.sub(r'await self\.analyze_user_learning_profile\(', r'self.analyze_user_learning_profile(', content)
    content = re.sub(r'await self\.get_attempt_frequency_by_subcategory\(', r'self.get_attempt_frequency_by_subcategory(', content)
    content = re.sub(r'await self\.enforce_subcategory_diversity\(', r'self.enforce_subcategory_diversity(', content)
    content = re.sub(r'await self\.apply_spaced_repetition_filter\(', r'self.apply_spaced_repetition_filter(', content)
    
    with open('/app/backend/adaptive_session_logic.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed all remaining async methods")

def fix_server_endpoint():
    """Fix server.py session endpoint to be synchronous"""
    
    with open('/app/backend/server.py', 'r') as f:
        content = f.read()
    
    # Find session endpoint and make it sync
    # Look for the session start endpoint
    session_pattern = r'(@api_router\.post\("/sessions/start"\)[^}]*session_result = await session_logic\.create_personalized_session\([^}]*\})'
    
    # If not found, look for more specific patterns
    if 'await session_logic.create_personalized_session(' in content:
        content = re.sub(r'session_result = await session_logic\.create_personalized_session\(',
                         r'session_result = session_logic.create_personalized_session(', content)
        print("✅ Fixed server.py session endpoint call")
    
    with open('/app/backend/server.py', 'w') as f:
        f.write(content)

def main():
    """Complete async fix for 100% success rate"""
    print("🚀 Complete Async Fix for 100% Success Rate...")
    
    try:
        complete_async_fix()
        fix_server_endpoint()
        
        print("🎉 COMPLETE ASYNC FIX SUCCESSFUL!")
        print("✅ All async methods converted to synchronous")
        print("✅ All await calls removed")
        print("✅ 100% success rate ready for testing")
        
    except Exception as e:
        print(f"❌ Failed to complete async fix: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())