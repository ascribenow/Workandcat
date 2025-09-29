"""
Solution Formatting Utility
Improves the readability of solution content by:
1. Adding proper line breaks and spacing
2. Converting LaTeX text commands to readable format
3. Improving overall presentation
"""

import re

def format_solution_content(content: str) -> str:
    """
    Format solution content for better readability
    """
    if not content:
        return content
    
    # Step 1: Convert \text{...} commands to readable format
    # \text{minutes} -> minutes, \text{hours} -> hours, etc.
    content = re.sub(r'\\text\{([^}]+)\}', r'\1', content)
    
    # Step 2: Add proper line breaks after periods that end sentences
    # But avoid breaking mathematical expressions
    content = re.sub(r'(\.)(\s+)([A-Z])', r'\1\n\n\3', content)
    
    # Step 3: Add line breaks before numbered steps
    content = re.sub(r'(\.)(\s*)(\d+\.)', r'\1\n\n\3', content)
    
    # Step 4: Add spacing around "Why this step?" explanations
    content = re.sub(r'(\.)(\s*)(Why this step\?)', r'\1\n\n**\3**', content)
    
    # Step 5: Add line breaks before "Method:", "Givens:", "Goal:" etc.
    content = re.sub(r'(\.)(\s*)(Method|Givens|Goal|Solution|Answer):', r'\1\n\n**\3:**', content)
    content = re.sub(r'^(Method|Givens|Goal|Solution|Answer):', r'**\1:**', content, flags=re.MULTILINE)
    
    # Step 6: Add spacing around boxed answers
    content = re.sub(r'(\.)(\s*)(\\boxed\{[^}]+\})', r'\1\n\n\3', content)
    
    # Step 7: Add line breaks before "Sanity check:" and "Common pitfall:"
    content = re.sub(r'(\.)(\s*)(Sanity check|Common pitfall):', r'\1\n\n**\3:**', content)
    
    # Step 8: Clean up any excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    content = content.strip()
    
    return content

def format_solution_approach(content: str) -> str:
    """
    Format solution approach content for better readability
    """
    if not content:
        return content
    
    # Add numbered list formatting
    content = re.sub(r'(\d+\.)', r'\n\3', content)
    content = content.strip()
    
    return content

def format_snap_read(content: str) -> str:
    """
    Format snap read content for better readability
    """
    if not content:
        return content
    
    # Add line breaks after sentences
    content = re.sub(r'(\.)(\s+)([A-Z])', r'\1\n\3', content)
    content = content.strip()
    
    return content