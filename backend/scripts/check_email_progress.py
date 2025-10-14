"""
Script to check the progress of email sending
"""

import time
import re

log_file = "/tmp/email_sending.log"

try:
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Count successful and failed emails
    successful = content.count("✅ Sent successfully")
    failed = content.count("❌ Failed to send")
    
    # Find batch progress messages
    batch_messages = re.findall(r'Progress: (\d+)/(\d+) emails sent', content)
    
    # Find summary if completed
    summary_match = re.search(r'SUMMARY.*?Successfully sent: (\d+).*?Failed: (\d+).*?Total: (\d+)', content, re.DOTALL)
    
    print("\n" + "="*60)
    print("EMAIL SENDING PROGRESS")
    print("="*60)
    
    if summary_match:
        print("\n✅ SENDING COMPLETED!")
        print(f"   Successfully sent: {summary_match.group(1)}")
        print(f"   Failed: {summary_match.group(2)}")
        print(f"   Total: {summary_match.group(3)}")
    elif batch_messages:
        last_progress = batch_messages[-1]
        print(f"\n📧 Currently sending emails...")
        print(f"   Progress: {last_progress[0]}/{last_progress[1]}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        
        # Calculate estimated time remaining
        sent = int(last_progress[0])
        total = int(last_progress[1])
        remaining = total - sent
        batches_remaining = remaining // 5
        estimated_minutes = (batches_remaining * 60) // 60
        
        print(f"\n⏱️  Estimated time remaining: ~{estimated_minutes} minutes")
        print(f"   (Sending in batches of 5 with 60-second cooldown)")
    else:
        print(f"\n📧 Emails sent so far: {successful}")
        print(f"   Failed: {failed}")
        print("\n⏳ Still sending...")
    
    print("\n" + "="*60)
    print(f"Last 10 lines of log:\n")
    lines = content.split('\n')
    for line in lines[-10:]:
        if line.strip():
            print(f"   {line}")
    
    print("\n" + "="*60 + "\n")
    
except FileNotFoundError:
    print("❌ Log file not found. Email sending may not have started yet.")
except Exception as e:
    print(f"❌ Error reading log: {e}")
