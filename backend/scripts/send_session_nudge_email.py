"""
Script to send session nudge email to Twelvr users.
Personalized with each user's completed session count.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_service import gmail_service
from database import SessionLocal
from sqlalchemy import text
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def create_email_content(user_email, session_count):
    """Create the email content with HTML and plain text versions"""
    
    subject = "45 days to CAT — let's make your next session count"
    
    # Preheader
    preheader = "You've completed [X] sessions. Every session brings you closer to full Quant coverage."
    
    # Personalized session message
    if session_count == 0:
        session_message = "You've taken the first step by signing up — and that already puts you ahead."
    else:
        session_message = f"You've completed {session_count} sessions — now is the time for a sprint!"
    
    # Plain text version
    plain_text = f"""
Hi,

{session_message}

Just 45 days to CAT, and every session counts now.
Twelvr's adaptive AI helps you cover Quant syllabus like magic. Maximise your strengths and just the right things to sharpen your weak areas.

If you're unsure how to start or feel stuck, book a quick one-on-one with me.
No pressure — just a chat to help you use Twelvr right.

👉 Book here: https://calendly.com/hello-twelvr/new-meeting

Let's make your next session count.

Warmly,
Sumedh
Co-founder, Twelvr
www.twelvr.com
    """.strip()
    
    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Preheader text -->
    <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: Lato, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
        {preheader}
    </div>
    <style>
        body {{
            font-family: 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.7;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            padding: 0;
            border-radius: 0;
        }}
        .content {{
            padding: 40px 30px 40px 30px;
        }}
        .content p {{
            font-size: 16px;
            line-height: 1.7;
            margin-bottom: 20px;
            color: #333;
        }}
        .highlight-box {{
            background-color: #f8f9fa;
            border-left: 4px solid #9ac026;
            padding: 20px;
            margin: 25px 0;
            border-radius: 4px;
        }}
        .highlight-box p {{
            margin: 0;
            color: #555;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #9ac026;
            color: #ffffff !important;
            padding: 14px 28px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 16px;
            margin: 20px 0;
        }}
        .cta-button:hover {{
            background-color: #8bb024;
        }}
        .signature {{
            margin-top: 30px;
            padding-top: 25px;
            border-top: 1px solid #e9ecef;
        }}
        .signature p {{
            margin: 5px 0;
            font-size: 15px;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 25px 30px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <p>Hi,</p>
            
            <p>{session_message}</p>
            
            <p>Just <strong>45 days to CAT</strong>, and every session counts now.<br>
            Twelvr's adaptive AI helps you cover Quant syllabus like magic. Maximise your strengths and just the right things to sharpen your weak areas.</p>
            
            <div class="highlight-box">
                <p style="font-size: 17px; font-weight: 600; margin-bottom: 12px; color: #333;">💬 Need help using Twelvr?</p>
                <p style="font-size: 15px;">If you're unsure how to start or feel stuck, book a quick one-on-one with me.<br>
                No pressure — just a chat to help you use Twelvr right.</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://calendly.com/hello-twelvr/new-meeting" class="cta-button">📅 Book here</a>
            </div>
            
            <p>Let's make your next session count.</p>
            
            <div class="signature">
                <p style="margin-bottom: 2px; font-weight: 500;">Warmly,</p>
                <p style="margin-bottom: 2px;"><strong>Sumedh</strong></p>
                <p style="margin-bottom: 2px; color: #666;">Co-founder, Twelvr</p>
                <p style="margin-bottom: 0;"><a href="https://www.twelvr.com" style="color: #9ac026; text-decoration: none;">www.twelvr.com</a></p>
            </div>
        </div>
        
        <div class="footer">
            <p style="margin: 0; color: #999; font-size: 13px;">You received this email because you're a valued member of the Twelvr community.</p>
        </div>
    </div>
</body>
</html>
    """
    
    return subject, plain_text, html_content, preheader


def send_email_from_sumedh(to_email, subject, plain_text, html_content):
    """Send email from Sumedh's email address"""
    
    if not gmail_service.service:
        print("❌ Gmail service not authenticated")
        return False
    
    try:
        # Create multipart message
        msg = MIMEMultipart('alternative')
        msg['From'] = 'Twelvr <hello@twelvr.com>'
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text and HTML parts
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message = {'raw': raw}
        
        result = gmail_service.service.users().messages().send(userId='me', body=message).execute()
        print(f"✅ Email sent successfully to {to_email}")
        print(f"   Message ID: {result.get('id')}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def get_user_session_count(user_email):
    """Get completed session count for a user"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT u.id, u.email, u.full_name, COUNT(s.session_id) as session_count
            FROM users u
            LEFT JOIN sessions s ON CAST(u.id AS TEXT) = s.user_id AND s.status = 'completed'
            WHERE u.email = :email
            GROUP BY u.id, u.email, u.full_name
        """)
        
        result = db.execute(query, {"email": user_email}).fetchone()
        
        if result:
            return {
                "user_id": result[0],
                "email": result[1],
                "name": result[2],
                "session_count": result[3]
            }
        return None
        
    finally:
        db.close()


def get_all_users_with_session_counts():
    """Get all users with their session counts"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT u.id, u.email, u.full_name, COUNT(s.session_id) as session_count
            FROM users u
            LEFT JOIN sessions s ON CAST(u.id AS TEXT) = s.user_id AND s.status = 'completed'
            GROUP BY u.id, u.email, u.full_name
            ORDER BY u.created_at DESC
        """)
        
        result = db.execute(query).fetchall()
        users = [
            {
                "user_id": row[0],
                "email": row[1],
                "name": row[2],
                "session_count": row[3]
            }
            for row in result
        ]
        
        return users
        
    finally:
        db.close()


def send_test_email():
    """Send test email to twelvrhelp@gmail.com"""
    print("\n" + "="*60)
    print("SENDING TEST EMAIL")
    print("="*60)
    
    test_email = "twelvrhelp@gmail.com"
    
    # Get session count for test user
    user_data = get_user_session_count(test_email)
    
    if not user_data:
        print(f"❌ User {test_email} not found in database")
        return False
    
    session_count = user_data['session_count']
    
    print(f"\n📧 Sending test email to: {test_email}")
    print(f"   User: {user_data['name']}")
    print(f"   Session count: {session_count}")
    print(f"👤 From: Twelvr <hello@twelvr.com>")
    
    subject, plain_text, html_content, preheader = create_email_content(test_email, session_count)
    
    print(f"📬 Subject: {subject}")
    print(f"\n⏳ Sending...")
    
    success = send_email_from_sumedh(test_email, subject, plain_text, html_content)
    
    if success:
        print("\n✅ TEST EMAIL SENT SUCCESSFULLY!")
        print("\nPlease check twelvrhelp@gmail.com and approve before sending to all users.")
        print("\nTo send to all users after approval, run:")
        print("  python send_session_nudge_email.py --send-all")
    else:
        print("\n❌ TEST EMAIL FAILED!")
    
    print("\n" + "="*60 + "\n")
    return success


def send_to_all_users():
    """Send email to all users in batches"""
    print("\n" + "="*60)
    print("SENDING TO ALL USERS")
    print("="*60)
    
    # Get all users
    print("\n📊 Fetching all users with session counts...")
    users = get_all_users_with_session_counts()
    
    if not users:
        print("❌ No users found")
        return
    
    print(f"\n✅ Found {len(users)} users:")
    for i, user in enumerate(users[:10], 1):
        print(f"   {i}. {user['email']:45} | {user['name'] or 'N/A':20} | {user['session_count']} sessions")
    
    if len(users) > 10:
        print(f"   ... and {len(users) - 10} more users")
    
    # Show session distribution
    print(f"\n📊 Session distribution:")
    zero_sessions = sum(1 for u in users if u['session_count'] == 0)
    one_session = sum(1 for u in users if u['session_count'] == 1)
    two_five = sum(1 for u in users if 2 <= u['session_count'] <= 5)
    six_plus = sum(1 for u in users if u['session_count'] >= 6)
    
    print(f"   0 sessions: {zero_sessions} users")
    print(f"   1 session: {one_session} users")
    print(f"   2-5 sessions: {two_five} users")
    print(f"   6+ sessions: {six_plus} users")
    
    # Send emails in batches
    import time
    
    subject_template, _, _, _ = create_email_content("", 0)
    
    success_count = 0
    failed_count = 0
    batch_size = 5
    cooldown_seconds = 60
    
    print(f"\n📧 Sending emails to {len(users)} users in batches of {batch_size}")
    print(f"⏱️  60-second cooldown between batches")
    print("="*60)
    
    for i, user in enumerate(users, 1):
        print(f"\n[{i}/{len(users)}] Sending to {user['email']} ({user['session_count']} sessions)...")
        
        # Create personalized email
        subject, plain_text, html_content, _ = create_email_content(user['email'], user['session_count'])
        
        success = send_email_from_sumedh(user['email'], subject, plain_text, html_content)
        
        if success:
            success_count += 1
            print(f"   ✅ Sent successfully")
        else:
            failed_count += 1
            print(f"   ❌ Failed to send")
        
        # Add cooldown after every batch
        if i % batch_size == 0 and i < len(users):
            print(f"\n⏸️  Batch of {batch_size} sent. Waiting {cooldown_seconds} seconds...")
            print(f"   Progress: {i}/{len(users)} emails sent ({success_count} successful, {failed_count} failed)")
            time.sleep(cooldown_seconds)
            print(f"   ✅ Cooldown complete. Resuming...\n")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✅ Successfully sent: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Total: {len(users)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    import sys
    
    # Check if gmail service is authenticated
    if not gmail_service.service:
        print("\n❌ ERROR: Gmail service not authenticated")
        print("Please ensure Gmail credentials are set up correctly")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--send-all":
        send_to_all_users()
    else:
        send_test_email()
