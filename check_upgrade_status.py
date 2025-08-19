#!/usr/bin/env python3
"""
Check the status of the upgrade process
"""

import os
import re

def check_upgrade_status():
    try:
        with open('/app/upgrade_log.txt', 'r') as f:
            content = f.read()
        
        # Find progress indicators
        assessment_matches = re.findall(r'\[(\d+)/(\d+)\] Assessing quality', content)
        upgrade_matches = re.findall(r'\[(\d+)/(\d+)\] Upgrading', content)
        
        # Find issue counts
        dollar_signs = content.count('Contains $ signs')
        missing_explanation = content.count('Explanation missing or too short')
        short_approach = content.count('Approach too short')
        similar_content = content.count('too similar')
        
        # Find completion status
        phase1_complete = 'PHASE 1: QUALITY ASSESSMENT' in content and 'PHASE 2: UPGRADING' in content
        phase2_complete = 'COMPREHENSIVE UPGRADE COMPLETED!' in content
        
        print("📊 UPGRADE STATUS REPORT")
        print("=" * 50)
        
        if assessment_matches:
            last_assessment = assessment_matches[-1]
            print(f"Assessment Progress: {last_assessment[0]}/{last_assessment[1]} questions")
            progress_pct = int(last_assessment[0]) / int(last_assessment[1]) * 100
            print(f"Assessment: {progress_pct:.1f}% complete")
        
        if upgrade_matches:
            last_upgrade = upgrade_matches[-1]
            print(f"Upgrade Progress: {last_upgrade[0]}/{last_upgrade[1]} questions")
        
        print(f"\nIssues Found So Far:")
        print(f"  Questions with $ signs: {dollar_signs}")
        print(f"  Missing explanations: {missing_explanation}")
        print(f"  Short approaches: {short_approach}")
        print(f"  Similar content: {similar_content}")
        
        print(f"\nPhase Status:")
        print(f"  Phase 1 (Assessment): {'✅ Complete' if phase1_complete else '🔄 In Progress'}")
        print(f"  Phase 2 (Upgrades): {'✅ Complete' if phase2_complete else '⏳ Pending/In Progress'}")
        
        if phase2_complete:
            # Extract final results
            if 'Successful upgrades:' in content:
                success_match = re.search(r'Successful upgrades: (\d+)', content)
                failed_match = re.search(r'Failed upgrades: (\d+)', content)
                success_rate_match = re.search(r'Upgrade success rate: ([\d.]+)%', content)
                
                if success_match:
                    print(f"\n🎉 UPGRADE COMPLETED!")
                    print(f"  Successful upgrades: {success_match.group(1)}")
                    if failed_match:
                        print(f"  Failed upgrades: {failed_match.group(1)}")
                    if success_rate_match:
                        print(f"  Success rate: {success_rate_match.group(1)}%")
        
        # Show last few lines for current status
        lines = content.strip().split('\n')
        print(f"\nLatest Activity:")
        for line in lines[-3:]:
            if 'INFO' in line:
                # Extract just the message part
                if ' - ' in line:
                    message = line.split(' - ', 2)[-1]
                    print(f"  {message}")
        
    except Exception as e:
        print(f"Error checking status: {e}")

if __name__ == "__main__":
    check_upgrade_status()