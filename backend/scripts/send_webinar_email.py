"""
Send Webinar Email Campaign - 50 Days to CAT
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_service import GmailService

def send_webinar_email(to_email: str) -> bool:
    """Send webinar announcement email"""
    
    gmail = GmailService()
    
    # Authenticate Gmail service
    if not gmail.authenticate_service():
        print("❌ Failed to authenticate Gmail service")
        return False
    
    subject = "Founders' Session — 50 days to CAT"
    
    # HTML email with Twelvr branding - Clean & Classy
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Founders' Session — 50 Days to CAT</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #ffffff;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        
        <!-- Main Content -->
        <tr>
            <td style="padding: 60px 40px 40px 40px;">
                
                <!-- Title -->
                <h1 style="color: #333333; margin: 0 0 30px 0; font-size: 28px; font-weight: 400; line-height: 1.3;">
                    Founders' Session — <span style="color: #9ac026;">Using AI to cover quant syllabus</span>
                </h1>
                
                <!-- Intro -->
                <p style="color: #555555; font-size: 16px; line-height: 1.7; margin: 0 0 25px 0;">
                    Hi,
                </p>
                
                <p style="color: #555555; font-size: 16px; line-height: 1.7; margin: 0 0 25px 0;">
                    With 50 days to CAT, I'm conducting a webinar this Sunday to share hacks and tools to use AI for quick coverage of quants. 
                    I'll also walk you through an AI tool that I've built for this purpose — <em>it's free</em>.
                </p>
                
                <!-- Highlighted Box -->
                <div style="background-color: #f8faf5; border-left: 3px solid #9ac026; padding: 25px; margin: 30px 0;">
                    <p style="color: #333333; font-size: 16px; line-height: 1.7; margin: 0 0 15px 0; font-weight: 600;">
                        Twelvr Hacks — What we'll cover:
                    </p>
                    <ul style="color: #555555; font-size: 15px; line-height: 1.8; margin: 0; padding-left: 25px;">
                        <li style="margin-bottom: 10px;">Leverage AI for quants syllabus coverage in 50 days</li>
                        <li style="margin-bottom: 10px;">How to hack Twelvr so the engine learns you quickly</li>
                        <li>What the adaptive engine really does</li>
                    </ul>
                </div>
                
                <!-- Webinar Details -->
                <p style="color: #555555; font-size: 16px; line-height: 1.7; margin: 25px 0;">
                    <strong>When:</strong> This Sunday<br>
                    <strong>Where:</strong> Online (link will be shared upon RSVP)<br>
                    <strong>Cost:</strong> Free
                </p>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 40px 0;">
                    <a href="https://rsvp.link/founderscircle" 
                       style="display: inline-block; background-color: #9ac026; color: #ffffff; 
                              text-decoration: none; padding: 14px 40px; border-radius: 4px; 
                              font-size: 16px; font-weight: 500;">
                        RSVP Here
                    </a>
                </div>
                
                <!-- Closing -->
                <p style="color: #555555; font-size: 16px; line-height: 1.7; margin: 25px 0 40px 0;">
                    This is specifically for those looking to leverage AI and smart strategies to maximize their prep in the final stretch. 
                    Looking forward to sharing what we've learned building Twelvr's adaptive system.
                </p>
                
                <!-- Signature -->
                <p style="color: #555555; font-size: 16px; line-height: 1.7; margin: 0 0 5px 0;">
                    Warm regards,
                </p>
                <p style="color: #555555; font-size: 16px; line-height: 1.7; margin: 0 0 5px 0;">
                    Twelvr Support
                </p>
                <p style="color: #9ac026; font-size: 16px; line-height: 1.7; margin: 0;">
                    <a href="mailto:hello@twelvr.com" style="color: #9ac026; text-decoration: none;">hello@twelvr.com</a>
                </p>
                
            </td>
        </tr>
        
        <!-- Footer -->
        <tr>
            <td style="padding: 30px 40px; text-align: center; border-top: 1px solid #e8e8e8;">
                <p style="color: #9ac026; font-size: 14px; font-style: italic; margin: 0;">
                    You, compounded.
                </p>
            </td>
        </tr>
        
    </table>
</body>
</html>
    """
    
    # Plain text version
    plain_text = """
Founders' Session — Using AI to cover quant syllabus

Hi,

With 50 days to CAT, I'm conducting a webinar this Sunday to share hacks and tools to use AI for quick coverage of quants. I'll also walk you through an AI tool that I've built for this purpose — it's free.

Twelvr Hacks — What we'll cover:
• Leverage AI for quants syllabus coverage in 50 days
• How to hack Twelvr so the engine learns you quickly
• What the adaptive engine really does

When: This Sunday
Where: Online (link will be shared upon RSVP)
Cost: Free

RSVP Here: https://rsvp.link/founderscircle

This is specifically for those looking to leverage AI and smart strategies to maximize their prep in the final stretch. Looking forward to sharing what we've learned building Twelvr's adaptive system.

Warm regards,
Twelvr Support
hello@twelvr.com

You, compounded.
    """
    
    # Send email using the internal method
    try:
        return gmail._send_html_email(to_email, subject, html_content, plain_text)
    except AttributeError:
        # If _send_html_email doesn't exist, use send_generic_email
        return gmail.send_generic_email(to_email, subject, plain_text)

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
