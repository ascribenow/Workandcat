#!/usr/bin/env python3
"""
Fix frequency_analysis_method references in server.py
This script removes all references to the deleted frequency_analysis_method field
"""

import re

def fix_server_py():
    """Fix server.py by removing frequency_analysis_method references"""
    
    # Read the current server.py file
    with open('/app/backend/server.py', 'r') as f:
        content = f.read()
    
    # Fix 1: Replace the frequency analysis method distribution query
    old_pattern1 = r'''        # Get frequency distribution by method
        method_distribution_query = await db\.execute\(
            select\(
                Question\.frequency_analysis_method,
                func\.count\(Question\.id\)\.label\('count'\),
                func\.avg\(Question\.pyq_frequency_score\)\.label\('avg_score'\)
            \)\.where\(
                and_\(
                    Question\.is_active == True,
                    Question\.frequency_analysis_method\.isnot\(None\)
                \)
            \)\.group_by\(Question\.frequency_analysis_method\)
        \)
        
        method_distribution = \{\}
        for row in method_distribution_query:
            method_distribution\[row\.frequency_analysis_method\] = \{
                "count": row\.count,
                "avg_score": round\(float\(row\.avg_score\), 4\) if row\.avg_score else 0
            \}'''
    
    new_replacement1 = '''        # Frequency analysis method distribution (field removed - using default)
        method_distribution = {
            "dynamic_conceptual_matching": {
                "count": frequency_stats.total_questions if frequency_stats else 0,
                "avg_score": round(float(frequency_stats.avg_frequency_score), 4) if frequency_stats and frequency_stats.avg_frequency_score else 0
            }
        }'''
    
    # Fix 2: Remove frequency_analysis_method from question data
    old_pattern2 = r'"analysis_method": q\.frequency_analysis_method'
    new_replacement2 = '"analysis_method": "dynamic_conceptual_matching"'
    
    # Fix 3: Remove frequency_analysis_method assignment
    old_pattern3 = r'question\.frequency_analysis_method = frequency_method'
    new_replacement3 = '# question.frequency_analysis_method = frequency_method  # Field removed'
    
    # Fix 4: Remove emergency fallback assignment
    old_pattern4 = r'question\.frequency_analysis_method = \'emergency_fallback\''
    new_replacement4 = '# question.frequency_analysis_method = \'emergency_fallback\'  # Field removed'
    
    # Apply fixes
    content = re.sub(old_pattern1, new_replacement1, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(old_pattern2, new_replacement2, content)
    content = re.sub(old_pattern3, new_replacement3, content)
    content = re.sub(old_pattern4, new_replacement4, content)
    
    # Write the fixed content back
    with open('/app/backend/server.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed frequency_analysis_method references in server.py")

if __name__ == "__main__":
    fix_server_py()