"""
Script to send gratitude email to Twelvr users.
First sends test email to twelvrhelp@gmail.com for approval.
After approval, can send to all users who have crossed 10 sessions.
"""

import sys
import os

# Add parent directory to path so we can import from backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_service import gmail_service
from database import SessionLocal
from sqlalchemy import text
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def create_email_content():
    """Create the email content with HTML and plain text versions"""
    
    subject = "A small thank-you, plus a one-on-one if you need help"
    
    # Preheader (shows in email preview)
    preheader = "Free access for our first 50 learners — and a quick chat if you're stuck."
    
    # Plain text version
    plain_text = """
Hi,

It's been just a week since we launched Twelvr, and the response has been overwhelming — thank you for being part of it 🙏

It's been amazing watching so many of you already complete 10 sessions. To thank our earliest learners, we're opening up free full access for the first 50 who reach that milestone — our little way of giving back.

We built Twelvr to help CAT 2025 aspirants learn smarter and move faster — especially if you've started a little late or find Quant tough. The AI engine behind Twelvr learns from every answer you give, so each session becomes more tuned to your pace and pattern — helping you cover Quant quickly and effectively.

💬 Need help or feeling stuck?

If you're unsure how to use Twelvr best, or want to see how adaptivity can work for your prep style, you can book a quick one-on-one with me — no agenda, just a chat to help you get the most out of it.

👉 Book a quick session with me here: https://calendly.com/hello-twelvr/new-meeting

Thank you again for believing in what we're building.
You're helping us make prep more personal — one learner at a time.

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
            
            <p>It's been just a week since we launched Twelvr, and the response has been overwhelming — thank you for being part of it 🙏</p>
            
            <p>It's been amazing watching so many of you already complete 10 sessions. To thank our earliest learners, we're <strong>opening up free full access for the first 50 who reach that milestone</strong> — our little way of giving back.</p>
            
            <p>We built Twelvr to help CAT 2025 aspirants learn smarter and move faster — especially if you've started a little late or find Quant tough. The AI engine behind Twelvr learns from every answer you give, so each session becomes more tuned to your pace and pattern — helping you cover Quant quickly and effectively.</p>
            
            <div class="highlight-box">
                <p style="font-size: 17px; font-weight: 600; margin-bottom: 12px; color: #333;">💬 Need help or feeling stuck?</p>
                <p style="font-size: 15px;">If you're unsure how to use Twelvr best, or want to see how adaptivity can work for your prep style, you can book a quick one-on-one with me — no agenda, just a chat to help you get the most out of it.</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://calendly.com/hello-twelvr/new-meeting" class="cta-button">📅 Book a quick session with me here</a>
            </div>
            
            <p>Thank you again for believing in what we're building.<br>
            You're helping us make prep more personal — one learner at a time.</p>
            
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
        msg['From'] = 'Sumedh from Twelvr <sumedh@twelvr.com>'
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


def send_test_email():
    """Send test email to twelvrhelp@gmail.com"""
    print("\n" + "="*60)
    print("SENDING TEST EMAIL")
    print("="*60)
    
    subject, plain_text, html_content, preheader = create_email_content()
    
    test_email = "twelvrhelp@gmail.com"
    print(f"\n📧 Sending test email to: {test_email}")
    print(f"📬 Subject: {subject}")
    print(f"👤 From: Sumedh from Twelvr <sumedh@twelvr.com>")
    print(f"\n⏳ Sending...")
    
    success = send_email_from_sumedh(test_email, subject, plain_text, html_content)
    
    if success:
        print("\n✅ TEST EMAIL SENT SUCCESSFULLY!")
        print("\nPlease check twelvrhelp@gmail.com and approve before sending to all users.")
        print("\nTo send to all users after approval, run:")
        print("  python send_gratitude_email.py --send-all")
    else:
        print("\n❌ TEST EMAIL FAILED!")
    
    print("\n" + "="*60 + "\n")
    return success


def get_all_users():
    """Get all users in the system"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT u.email, u.full_name
            FROM users u
            ORDER BY u.created_at DESC
        """)
        
        result = db.execute(query).fetchall()
        users = [{"email": row[0], "name": row[1]} for row in result]
        
        return users
        
    finally:
        db.close()


def send_to_all_users():
    """Send email to all users with 10+ sessions (after approval)"""
    print("\n" + "="*60)
    print("SENDING TO ALL USERS")
    print("="*60)
    
    # Get all eligible users
    print("\n📊 Fetching users with 10+ sessions...")
    users = get_all_users_with_10_plus_sessions()
    
    if not users:
        print("❌ No users found with 10+ sessions")
        return
    
    print(f"\n✅ Found {len(users)} users eligible for the email:")
    for i, user in enumerate(users[:5], 1):
        print(f"   {i}. {user['email']} - {user['name']} ({user['session_count']} sessions)")
    
    if len(users) > 5:
        print(f"   ... and {len(users) - 5} more users")
    
    # Confirm before sending
    print("\n⚠️  WARNING: This will send emails to ALL eligible users!")
    confirm = input("\nType 'YES' to confirm and send emails: ")
    
    if confirm != "YES":
        print("\n❌ Email sending cancelled")
        return
    
    # Send emails
    subject, plain_text, html_content, preheader = create_email_content()
    
    success_count = 0
    failed_count = 0
    
    print(f"\n📧 Sending emails to {len(users)} users...")
    print("="*60)
    
    for i, user in enumerate(users, 1):
        print(f"\n[{i}/{len(users)}] Sending to {user['email']}...")
        
        success = send_email_from_sumedh(user['email'], subject, plain_text, html_content)
        
        if success:
            success_count += 1
            print(f"   ✅ Sent successfully")
        else:
            failed_count += 1
            print(f"   ❌ Failed to send")
    
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
