"""
Send Webinar Email Campaign - 50 Days to CAT
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_service import GmailService

def send_webinar_email(to_email: str) -> bool:
    """Send webinar announcement email in Twelvr brand style"""
    
    gmail = GmailService()
    
    # Authenticate Gmail service
    if not gmail.authenticate_service():
        print("❌ Failed to authenticate Gmail service")
        return False
    
    subject = "Founders' Session — 50 days to CAT"
    preheader = "Leverage AI for quants syllabus coverage. Free webinar this Sunday."
    
    plain_text = """
Hi,

With 50 days to CAT, I'm conducting a webinar this Sunday to share hacks and tools to use AI for quick coverage of quants. I'll also walk you through Twelvr and share tips on how to use it to customise the Quants prep for you basis where you stand today.

Twelvr Hacks — What we'll cover:
• Leverage AI for quants syllabus coverage in 50 days
• How to hack Twelvr so the engine learns you quickly
• What the adaptive engine really does

When: Sunday, 12th October, 11 AM IST
Where: Online (link will be shared upon RSVP)

RSVP Here: https://rsvp.link/founderscircle

This is specifically for those looking to leverage AI and smart strategies to maximize their prep in the final stretch. Looking forward to sharing what we've learned building Twelvr's adaptive system.

Warmly,
Sumedh
sumedh@twelvr.com

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
        .info-box {{
            background-color: #e8f5e8;
            border: 2px solid #9ac026;
            color: #545454;
            padding: 20px 25px;
            border-radius: 12px;
            margin: 25px 0;
            font-size: 15px;
        }}
        .info-box ul {{
            margin: 10px 0 0 0;
            padding-left: 20px;
        }}
        .info-box li {{
            margin-bottom: 8px;
        }}
        .details-box {{
            background-color: #f8f9fa;
            padding: 20px 25px;
            border-radius: 8px;
            margin: 25px 0;
            font-size: 15px;
            line-height: 1.8;
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
            <h1>Founders' Session — <span class="highlight">50 days to CAT</span></h1>
        </div>
        
        <div class="content">
            <p style="font-size: 15px; margin-bottom: 20px;">Hi,</p>
            
            <p style="font-size: 15px; margin-bottom: 20px;">With 50 days to CAT, I'm conducting a webinar this Sunday to share hacks and tools to use AI for quick coverage of quants. I'll also walk you through Twelvr and share tips on how to use it to customise the Quants prep for you basis where you stand today.</p>
            
            <div class="info-box">
                <strong style="font-size: 16px;">Twelvr Hacks — What we'll cover:</strong>
                <ul>
                    <li>Leverage AI for quants syllabus coverage in 50 days</li>
                    <li>How to hack Twelvr so the engine learns you quickly</li>
                    <li>What the adaptive engine really does</li>
                </ul>
            </div>
            
            <div class="logo-section">
                <img src="https://twelvr.com/favicon.png" alt="Twelvr" style="width: 50px; height: 50px; opacity: 0.8;">
            </div>
            
            <div class="details-box">
                <strong>When:</strong> Sunday, 12th October, 11 AM IST<br>
                <strong>Where:</strong> Online (link will be shared upon RSVP)
            </div>
            
            <div style="text-align: center;">
                <a href="https://rsvp.link/founderscircle" class="cta-button">RSVP Here</a>
            </div>
            
            <p style="font-size: 14px; margin-top: 30px; color: #666; line-height: 1.7;">This is specifically for those looking to leverage AI and smart strategies to maximize their prep in the final stretch. Looking forward to sharing what we've learned building Twelvr's adaptive system.</p>
        </div>
        
        <div class="footer">
            <p><strong>Warmly,</strong><br>
            <strong>Sumedh</strong><br>
            sumedh@twelvr.com</p>
            <p class="tagline">You, compounded.</p>
        </div>
    </div>
</body>
</html>
    """
    
    # Send email with custom HTML using MIME (same as glitch fix email)
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import base64
        
        msg = MIMEMultipart('alternative')
        msg['to'] = to_email
        msg['from'] = 'Sumedh <sumedh@twelvr.com>'
        msg['subject'] = subject
        
        # Create text and HTML parts
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message = {'raw': raw}
        
        gmail.service.users().messages().send(userId='me', body=message).execute()
        
        print(f"✅ Webinar email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending webinar email to {to_email}: {e}")
        return False

if __name__ == "__main__":
    recipient = "twelvrhelp@gmail.com"
    
    print("=" * 80)
    print("SENDING WEBINAR EMAIL CAMPAIGN")
    print("=" * 80)
    print(f"\nRecipient: {recipient}")
    print("Subject: Founders' Session — 50 days to CAT")
    print("\nSending...")
    
    success = send_webinar_email(recipient)
    
    if success:
        print("\n✅ EMAIL SENT SUCCESSFULLY!")
        print(f"   Webinar invitation delivered to {recipient}")
    else:
        print("\n❌ EMAIL FAILED TO SEND")
        print("   Check Gmail service authentication")
    
    print("\n" + "=" * 80)
