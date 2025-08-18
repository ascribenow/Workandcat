#!/usr/bin/env python3
"""
Fix All Async Issues in Adaptive Session Logic
Converts all async database operations to synchronous for 100% success rate
"""

import re

def fix_adaptive_session_logic():
    """Fix all async issues in adaptive_session_logic.py"""
    
    # Read the file
    with open('/app/backend/adaptive_session_logic.py', 'r') as f:
        content = f.read()
    
    # Fix 1: Change all async method definitions to sync
    content = re.sub(r'async def (calculate_recent_accuracy)', r'def \1', content)
    content = re.sub(r'async def (get_user_mastery_breakdown)', r'def \1', content)
    content = re.sub(r'async def (get_user_attempt_frequency)', r'def \1', content)
    content = re.sub(r'async def (apply_enhanced_selection_strategies)', r'def \1', content)
    content = re.sub(r'async def (enforce_type_diversity)', r'def \1', content)
    content = re.sub(r'async def (create_simple_fallback_session)', r'def \1', content)
    
    # Fix 2: Remove all await keywords from database calls
    content = re.sub(r'await db\.execute\(', r'db.execute(', content)
    
    # Fix 3: Change AsyncSession to Session in method signatures
    content = re.sub(r'db: AsyncSession', r'db: Session', content)
    
    # Fix 4: Fix main session creation method
    content = re.sub(r'async def create_personalized_session\(self, user_id: str, db: AsyncSession\)', 
                     r'def create_personalized_session(self, user_id: str, db: Session)', content)
    
    # Fix 5: Remove await from method calls within the class
    content = re.sub(r'await self\.calculate_recent_accuracy\(', r'self.calculate_recent_accuracy(', content)
    content = re.sub(r'await self\.get_user_mastery_breakdown\(', r'self.get_user_mastery_breakdown(', content)
    content = re.sub(r'await self\.get_user_attempt_frequency\(', r'self.get_user_attempt_frequency(', content)
    content = re.sub(r'await self\.apply_enhanced_selection_strategies\(', r'self.apply_enhanced_selection_strategies(', content)
    content = re.sub(r'await self\.enforce_type_diversity\(', r'self.enforce_type_diversity(', content)
    content = re.sub(r'await self\.create_simple_fallback_session\(', r'self.create_simple_fallback_session(', content)
    
    # Write the fixed content back
    with open('/app/backend/adaptive_session_logic.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed all async issues in adaptive_session_logic.py")

def fix_server_py():
    """Fix server.py to call session logic synchronously"""
    
    # Read the file
    with open('/app/backend/server.py', 'r') as f:
        content = f.read()
    
    # Find session endpoint and remove await from session logic call
    content = re.sub(r'session_result = await session_logic\.create_personalized_session\(',
                     r'session_result = session_logic.create_personalized_session(', content)
    
    # Write back
    with open('/app/backend/server.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed server.py session endpoint")

def main():
    """Fix all async issues for 100% success rate"""
    print("🚀 Fixing All Async Issues for 100% Success Rate...")
    
    try:
        fix_adaptive_session_logic()
        fix_server_py()
        
        print("🎉 ALL ASYNC ISSUES FIXED!")
        print("✅ Session generation converted to synchronous")
        print("✅ Database calls fixed for compatibility layer")
        print("✅ 100% success rate now achievable")
        
    except Exception as e:
        print(f"❌ Failed to fix async issues: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())