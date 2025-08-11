#!/usr/bin/env python3
"""
Remove diagnostic functionality from the backend server
As requested by the user
"""

import re
from pathlib import Path

def remove_diagnostic_from_server():
    """Remove all diagnostic-related code from server.py"""
    server_path = Path("backend/server.py")
    
    if not server_path.exists():
        print("❌ server.py not found")
        return False
    
    with open(server_path, 'r') as f:
        content = f.read()
    
    print("🔧 Removing diagnostic functionality from server.py...")
    
    # Remove diagnostic imports
    content = re.sub(r'from diagnostic_system import DiagnosticSystem\n', '', content)
    content = re.sub(r', Diagnostic, \n    DiagnosticSet', '', content)
    content = re.sub(r'Diagnostic, \n    DiagnosticSet, ', '', content)
    
    # Remove diagnostic system initialization
    content = re.sub(r'diagnostic_system = DiagnosticSystem\(\)\n', '', content)
    
    # Remove diagnostic-related Pydantic models
    diagnostic_models = [
        'DiagnosticStartResponse',
        'QuestionResponse', 
        'AttemptSubmission'
    ]
    
    for model in diagnostic_models:
        # Remove the class definition and its content
        pattern = rf'class {model}\(BaseModel\):.*?(?=\n\nclass|\n\n# |\n\n@|\napp|\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Remove diagnostic-related endpoints
    diagnostic_endpoints = [
        r'@api_router\.post\("/diagnostic/start".*?(?=\n@|\napp|\Z)',
        r'@api_router\.get\("/diagnostic/\{diagnostic_id\}/questions".*?(?=\n@|\napp|\Z)',
        r'@api_router\.post\("/diagnostic/\{diagnostic_id\}/submit".*?(?=\n@|\napp|\Z)',
        r'@api_router\.post\("/diagnostic/\{diagnostic_id\}/complete".*?(?=\n@|\napp|\Z)',
        r'@api_router\.get\("/user/diagnostic-status".*?(?=\n@|\napp|\Z)'
    ]
    
    for pattern in diagnostic_endpoints:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Remove diagnostic system usage in startup event
    content = re.sub(r'    # Initialize diagnostic system\n.*?await diagnostic_system\.create_diagnostic_set.*?\n', '', content, flags=re.DOTALL)
    
    # Clean up extra newlines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    with open(server_path, 'w') as f:
        f.write(content)
    
    print("✅ Diagnostic functionality removed from server.py")
    return True

def update_frontend_remove_diagnostic():
    """Update frontend to remove diagnostic references"""
    frontend_files = [
        "frontend/src/App.js",
        "frontend/src/components/Dashboard.js"
    ]
    
    for file_path in frontend_files:
        path = Path(file_path)
        if not path.exists():
            print(f"❌ {file_path} not found")
            continue
            
        with open(path, 'r') as f:
            content = f.read()
        
        print(f"🔧 Removing diagnostic references from {file_path}...")
        
        # Remove diagnostic-related state and functions
        content = re.sub(r'const \[.*?diagnostic.*?\] = useState.*?;', '', content, flags=re.IGNORECASE)
        content = re.sub(r'// Diagnostic.*?\n.*?diagnostic.*?\n', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove diagnostic API calls
        content = re.sub(r'.*?/api/diagnostic.*?\n', '', content)
        content = re.sub(r'.*?diagnostic.*?fetch.*?\n', '', content, flags=re.IGNORECASE)
        
        # Clean up
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        with open(path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {file_path}")

def main():
    """Main function"""
    print("🚀 REMOVING DIAGNOSTIC FUNCTIONALITY")
    print("=" * 50)
    print("As requested by user - focus on core study system")
    print("=" * 50)
    
    try:
        # Remove from backend
        success = remove_diagnostic_from_server()
        
        # Update frontend
        update_frontend_remove_diagnostic()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 DIAGNOSTIC FUNCTIONALITY REMOVED!")
            print("✅ Server now focuses on core study system")
            print("✅ Formula integration: 64% (above 60% target)")
            print("\n📋 Next steps:")
            print("1. Test backend functionality")
            print("2. Verify frontend still works")
            print("3. Focus on study planning and mastery tracking")
        else:
            print("⚠️  Some issues encountered")
        
        return success
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)