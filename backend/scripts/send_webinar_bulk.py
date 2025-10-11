"""
Send Webinar Email to All Users - Rate Limited
Sends in batches of 5 with 1 minute gap between batches
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from sqlalchemy import text
from send_webinar_email import send_webinar_email

def get_all_user_emails():
    """Get all user emails from database"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT email 
            FROM users 
            WHERE email IS NOT NULL 
            AND email != ''
            GROUP BY email
            ORDER BY MIN(created_at) DESC
        """))
        emails = [row[0] for row in result.fetchall()]
        return emails
    finally:
        db.close()

def send_bulk_webinar_emails():
    """Send webinar email to all users with rate limiting"""
    
    print("=" * 80)
    print("BULK WEBINAR EMAIL CAMPAIGN")
    print("=" * 80)
    
    # Get all user emails
    print("\n📊 Fetching user emails from database...")
    emails = get_all_user_emails()
    
    total_users = len(emails)
    print(f"✓ Found {total_users} users")
    
    if total_users == 0:
        print("❌ No users found in database!")
        return
    
    # Confirm before sending
    print(f"\n⚠️  About to send webinar email to {total_users} users")
    print(f"   Batches: 5 emails at a time")
    print(f"   Gap: 1 minute between batches")
    print(f"   Estimated time: {(total_users // 5) + 1} minutes")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    # Send in batches
    batch_size = 5
    total_sent = 0
    total_failed = 0
    failed_emails = []
    
    print("\n" + "=" * 80)
    print("SENDING EMAILS...")
    print("=" * 80)
    
    for i in range(0, total_users, batch_size):
        batch_number = (i // batch_size) + 1
        batch = emails[i:i + batch_size]
        
        print(f"\n📧 Batch {batch_number} ({len(batch)} emails):")
        print(f"   Progress: {i + len(batch)}/{total_users} ({((i + len(batch)) / total_users * 100):.1f}%)")
        
        # Send emails in this batch
        for email in batch:
            try:
                success = send_webinar_email(email)
                if success:
                    total_sent += 1
                    print(f"   ✓ {email}")
                else:
                    total_failed += 1
                    failed_emails.append(email)
                    print(f"   ✗ {email} - Failed")
                
                # Small delay between individual emails in batch
                time.sleep(0.5)
                
            except Exception as e:
                total_failed += 1
                failed_emails.append(email)
                print(f"   ✗ {email} - Error: {str(e)[:50]}")
        
        # Wait 1 minute before next batch (except for last batch)
        if i + batch_size < total_users:
            print(f"\n⏳ Waiting 60 seconds before next batch...")
            print(f"   Next batch will be sent at {datetime.now().strftime('%I:%M:%S %p')}")
            time.sleep(60)
    
    # Final summary
    print("\n" + "=" * 80)
    print("CAMPAIGN SUMMARY")
    print("=" * 80)
    print(f"\n✅ Successfully sent: {total_sent}/{total_users}")
    print(f"❌ Failed: {total_failed}/{total_users}")
    print(f"📊 Success rate: {(total_sent / total_users * 100):.1f}%")
    
    if failed_emails:
        print(f"\n❌ Failed emails ({len(failed_emails)}):")
        for email in failed_emails:
            print(f"   - {email}")
    else:
        print(f"\n🎉 All emails sent successfully!")
    
    print("\n" + "=" * 80)
    print(f"Campaign completed at {datetime.now().strftime('%I:%M:%S %p')}")
    print("=" * 80)

if __name__ == "__main__":
    send_bulk_webinar_emails()
