"""
Script to send glitch fix notification email to users
"""
import sys
sys.path.insert(0, '/app/backend')

from gmail_service import gmail_service
from database import SessionLocal
from sqlalchemy import text

def send_glitch_fix_email(to_email: str, is_test: bool = False) -> bool:
    """Send glitch fix notification email in Twelvr brand style"""
    
    subject = "Glitch fixed — your adaptive session is ready on Twelvr"
    preheader = "Your intelligent adaptive session is pre-packed and ready to go."
    
    plain_text = """
Hi,

There was a brief glitch yesterday night (around 9 PM) that caused the MCQ options to not display correctly in a few sessions. Our team caught and fixed the issue this morning — everything's now back to normal.

Your intelligent adaptive session is pre-packed and ready to go.

Just log in at www.twelvr.com and click "Today's Session."

Thank you for your patience and for being part of Twelvr's early journey — every bit of feedback helps us make the experience better for you and for everyone learning alongside you.

Warm regards,
Twelvr Support
hello@twelvr.com

You, compounded.
    """.strip()
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <!-- Preheader text for better deliverability -->
    <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: Lato, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
        {preheader}
    </div>
    <style>
        body {{
            font-family: 'Lato', sans-serif;
            line-height: 1.6;
            color: #545454;
            max-width: 600px;
            margin: 0 auto;
            padding: 0;
            background-color: #ffffff;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 0;
            overflow: hidden;
        }}
        .header {{
            background-color: #ffffff;
            color: #545454;
            padding: 40px 30px 20px 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 15px 0;
            font-size: 26px;
            font-weight: 600;
            color: #545454;
            line-height: 1.3;
        }}
        .highlight {{
            color: #9ac026;
            font-weight: 600;
        }}
        .content {{
            padding: 15px 30px 35px 30px;
        }}
        .logo-section {{
            text-align: center;
            margin: 25px 0;
        }}
        .status-badge {{
            background-color: #e8f5e8;
            border: 2px solid #9ac026;
            color: #545454;
            padding: 15px 20px;
            border-radius: 12px;
            margin: 25px 0;
            text-align: center;
            font-size: 15px;
            font-weight: 500;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #9ac026;
            color: #ffffff !important;
            padding: 12px 32px;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 600;
            font-size: 16px;
            margin: 25px 0 15px 0;
            transition: background-color 0.3s;
            box-shadow: 0 4px 12px rgba(154, 192, 38, 0.25);
        }}
        .cta-button:hover {{
            background-color: #8bb024;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 25px 30px;
            text-align: center;
            color: #545454;
            font-size: 14px;
            border-top: 1px solid #e9ecef;
        }}
        .tagline {{
            font-size: 14px;
            font-weight: 600;
            color: #9ac026;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Glitch fixed — <span class="highlight">your adaptive session is ready</span></h1>
        </div>
        
        <div class="content">
            <p style="font-size: 15px; margin-bottom: 20px;">Hi,</p>
            
            <p style="font-size: 15px; margin-bottom: 20px;">There was a brief glitch yesterday night (around 9 PM) that caused the MCQ options to not display correctly in a few sessions. Our team caught and fixed the issue this morning — everything's now back to normal.</p>
            
            <div class="status-badge">
                ✅ Your intelligent adaptive session is pre-packed and ready to go.
            </div>
            
            <div class="logo-section">
                <img src="https://twelvr.com/favicon.png" alt="Twelvr" style="width: 50px; height: 50px; opacity: 0.8;">
            </div>
            
            <p style="font-size: 15px; margin-bottom: 20px; text-align: center;">Just log in at <strong>www.twelvr.com</strong> and click <strong>"Today's Session."</strong></p>
            
            <div style="text-align: center;">
                <a href="https://www.twelvr.com" class="cta-button">Start Session</a>
            </div>
            
            <p style="font-size: 14px; margin-top: 30px; color: #666; line-height: 1.7;">Thank you for your patience and for being part of Twelvr's early journey — every bit of feedback helps us make the experience better for you and for everyone learning alongside you.</p>
        </div>
        
        <div class="footer">
            <p><strong>Warm regards,</strong><br>
            <strong>Twelvr Support</strong><br>
            hello@twelvr.com</p>
            <p class="tagline">You, compounded.</p>
        </div>
    </div>
</body>
</html>
    """
    
    # Send email with custom HTML using MIME
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import base64
        
        msg = MIMEMultipart('alternative')
        msg['to'] = to_email
        msg['from'] = f'{gmail_service.sender_name} <{gmail_service.sender_email}>'
        msg['subject'] = subject
        
        # Create text and HTML parts
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message = {'raw': raw}
        
        gmail_service.service.users().messages().send(userId='me', body=message).execute()
        
        test_flag = " [TEST EMAIL]" if is_test else ""
        print(f"✅ Glitch fix email sent successfully to {to_email}{test_flag}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending glitch fix email to {to_email}: {e}")
        return False

def get_all_user_emails():
    """Get all user emails from database"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT email 
            FROM users 
            WHERE email IS NOT NULL 
            AND email != ''
            ORDER BY email
        """))
        
        emails = [row[0] for row in result.fetchall()]
        return emails
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python send_glitch_fix_email.py test              # Send test to twelvrhelp@gmail.com")
        print("  python send_glitch_fix_email.py list              # List all user emails")
        print("  python send_glitch_fix_email.py send-all          # Send to all users")
        print("  python send_glitch_fix_email.py send <email>      # Send to specific email")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        print("Sending TEST email to twelvrhelp@gmail.com...")
        success = send_glitch_fix_email("twelvrhelp@gmail.com", is_test=True)
        if success:
            print("\n✅ Test email sent! Please check twelvrhelp@gmail.com and confirm.")
        else:
            print("\n❌ Failed to send test email.")
    
    elif command == "list":
        print("Fetching all user emails...")
        emails = get_all_user_emails()
        print(f"\nFound {len(emails)} users:\n")
        for i, email in enumerate(emails, 1):
            print(f"{i:3}. {email}")
        print(f"\nTotal: {len(emails)} users")
    
    elif command == "send-all":
        print("⚠️  WARNING: This will send emails to ALL users!")
        print("Getting user list...")
        emails = get_all_user_emails()
        print(f"Found {len(emails)} users")
        
        confirm = input(f"\nAre you sure you want to send to all {len(emails)} users? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled.")
            sys.exit(0)
        
        print(f"\nSending emails to {len(emails)} users...")
        sent_count = 0
        failed_count = 0
        
        for i, email in enumerate(emails, 1):
            print(f"[{i}/{len(emails)}] Sending to {email}...", end=" ")
            success = send_glitch_fix_email(email, is_test=False)
            if success:
                sent_count += 1
                print("✅")
            else:
                failed_count += 1
                print("❌")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {sent_count} sent, {failed_count} failed out of {len(emails)} total")
        print(f"{'='*60}")
    
    elif command == "send":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide email address")
            print("Usage: python send_glitch_fix_email.py send <email>")
            sys.exit(1)
        
        email = sys.argv[2]
        print(f"Sending email to {email}...")
        success = send_glitch_fix_email(email, is_test=False)
        if success:
            print(f"\n✅ Email sent to {email}")
        else:
            print(f"\n❌ Failed to send email to {email}")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: test, list, send-all, send <email>")
        sys.exit(1)
