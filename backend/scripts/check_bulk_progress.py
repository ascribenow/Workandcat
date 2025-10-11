"""
Check progress of bulk email send
"""
import os
import time

log_file = "/tmp/bulk_send_final.log"

print("=" * 80)
print("BULK EMAIL CAMPAIGN - PROGRESS MONITOR")
print("=" * 80)

if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
        
    # Count successful sends
    successful = [line for line in lines if '✅ Webinar email sent successfully' in line]
    failed = [line for line in lines if '✗' in line and 'Failed' in line]
    
    # Find latest batch
    batch_lines = [line for line in lines if 'Batch' in line and 'emails):' in line]
    
    print(f"\n📊 Status:")
    print(f"   Successful sends: {len(successful)}")
    print(f"   Failed sends: {len(failed)}")
    print(f"   Batches processed: {len(batch_lines)}")
    
    if batch_lines:
        print(f"\n📧 Latest batch: {batch_lines[-1].strip()}")
    
    # Show last 10 lines
    print(f"\n📝 Recent activity:")
    for line in lines[-10:]:
        print(f"   {line.rstrip()}")
    
    # Check if completed
    if 'CAMPAIGN SUMMARY' in ''.join(lines):
        print(f"\n✅ CAMPAIGN COMPLETED!")
    else:
        print(f"\n⏳ Campaign still running...")
        
else:
    print("❌ Log file not found!")

print("\n" + "=" * 80)
