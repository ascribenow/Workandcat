#!/usr/bin/env python3

import sys
import os
import warnings
import urllib3

# Suppress SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    print("🚀 Starting Background Job Pipeline Verification Test")
    print("=" * 80)
    
    tester = CATBackendTester()
    
    try:
        result = tester.test_background_job_pipeline_verification()
        
        print("\n" + "=" * 80)
        if result:
            print("🎉 BACKGROUND JOB PIPELINE TEST: PASSED")
            sys.exit(0)
        else:
            print("❌ BACKGROUND JOB PIPELINE TEST: FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ TEST EXECUTION ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()