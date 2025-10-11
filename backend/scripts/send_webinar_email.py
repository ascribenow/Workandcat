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
    
    subject = "🎯 Webinar: Master Quant in 50 Days with AI | Twelvr Hacks"
    
    # HTML email with Twelvr branding
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Webinar: 50 Days to CAT - Master Quant with AI</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <!-- Header -->
        <tr>
            <td style="background: linear-gradient(135deg, #9ac026 0%, #7da01e 100%); padding: 40px 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 36px; font-weight: 300; letter-spacing: 2px;">Twelvr</h1>
                <p style="color: #ffffff; margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">CAT Preparation Platform</p>
            </td>
        </tr>
        
        <!-- Urgent Banner -->
        <tr>
            <td style="background-color: #fef3c7; padding: 15px 30px; border-left: 4px solid #f59e0b;">
                <p style="margin: 0; color: #92400e; font-size: 16px; font-weight: 600;">
                    ⏰ Only 50 Days to CAT 2025
                </p>
            </td>
        </tr>
        
        <!-- Main Content -->
        <tr>
            <td style="padding: 40px 30px;">
                <h2 style="color: #1f2937; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                    🚀 Crack Quant Using AI – Free Webinar
                </h2>
                
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                    Hey there! 👋
                </p>
                
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                    With just <strong>50 days left</strong> until CAT 2025, every moment counts. That's why we're hosting a special <strong>Founders' Session</strong> this Sunday to share game-changing hacks that will help you master the Quant syllabus using AI.
                </p>
                
                <!-- What You'll Learn -->
                <div style="background-color: #f9fafb; border-left: 4px solid #9ac026; padding: 20px; margin: 25px 0; border-radius: 4px;">
                    <h3 style="color: #1f2937; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">
                        📚 What You'll Learn
                    </h3>
                    <ul style="color: #4b5563; font-size: 15px; line-height: 1.8; margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 10px;">
                            <strong>Leverage AI</strong> to cover the entire Quant syllabus in 50 days
                        </li>
                        <li style="margin-bottom: 10px;">
                            <strong>Twelvr Hacks</strong>: How to make the adaptive engine learn YOU faster
                        </li>
                        <li style="margin-bottom: 10px;">
                            <strong>Inside the Engine</strong>: What Twelvr's adaptive algorithm really does behind the scenes
                        </li>
                        <li>
                            <strong>Free AI Tool</strong>: Get access to the AI-powered prep tool I've built (completely free!)
                        </li>
                    </ul>
                </div>
                
                <!-- Webinar Details -->
                <div style="background-color: #eff6ff; border: 2px solid #9ac026; padding: 20px; margin: 25px 0; border-radius: 8px; text-align: center;">
                    <p style="color: #1f2937; font-size: 18px; font-weight: 600; margin: 0 0 10px 0;">
                        📅 This Sunday
                    </p>
                    <p style="color: #4b5563; font-size: 15px; margin: 0 0 5px 0;">
                        Limited seats available
                    </p>
                    <p style="color: #6b7280; font-size: 14px; margin: 0;">
                        Free • Online • Interactive
                    </p>
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://rsvp.link/founderscircle" 
                       style="display: inline-block; background: linear-gradient(135deg, #9ac026 0%, #7da01e 100%); 
                              color: #ffffff; text-decoration: none; padding: 16px 40px; 
                              border-radius: 8px; font-size: 18px; font-weight: 600; 
                              box-shadow: 0 4px 6px rgba(154, 192, 38, 0.3);">
                        🎯 Reserve Your Spot Now
                    </a>
                </div>
                
                <!-- Why Attend -->
                <div style="margin: 30px 0;">
                    <h3 style="color: #1f2937; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">
                        💡 Why This Matters
                    </h3>
                    <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin: 0;">
                        Traditional prep methods take months. With AI and smart strategies, you can cover the same ground in weeks. 
                        This isn't about shortcuts – it's about <strong>working smarter</strong> with technology that adapts to YOUR learning pace.
                    </p>
                </div>
                
                <!-- Personal Note -->
                <div style="background-color: #fef3c7; padding: 20px; border-radius: 8px; margin: 25px 0;">
                    <p style="color: #92400e; font-size: 15px; line-height: 1.6; margin: 0; font-style: italic;">
                        "I've spent months building Twelvr's adaptive engine. In this session, I'll pull back the curtain and show you exactly 
                        how to make it work for YOU – helping you identify weak areas faster and practice smarter, not harder."
                    </p>
                    <p style="color: #78350f; font-size: 14px; margin: 10px 0 0 0; font-weight: 600;">
                        – Twelvr Team
                    </p>
                </div>
                
                <!-- Final CTA -->
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 25px 0;">
                    Don't let these 50 days go to waste. Join us this Sunday and learn how to use AI to your advantage.
                </p>
                
                <div style="text-align: center; margin: 20px 0;">
                    <a href="https://rsvp.link/founderscircle" 
                       style="color: #9ac026; text-decoration: none; font-size: 16px; font-weight: 600;">
                        👉 RSVP Here: https://rsvp.link/founderscircle
                    </a>
                </div>
            </td>
        </tr>
        
        <!-- Footer -->
        <tr>
            <td style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0 0 10px 0;">
                    See you on Sunday! 🚀
                </p>
                <p style="color: #9ca3af; font-size: 13px; margin: 0;">
                    Twelvr – Your AI-Powered CAT Prep Partner<br>
                    <a href="https://www.twelvr.com" style="color: #9ac026; text-decoration: none;">www.twelvr.com</a>
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    
    # Plain text version
    plain_text = """
🎯 WEBINAR: Master Quant in 50 Days with AI

Hey there! 👋

With just 50 days left until CAT 2025, every moment counts. Join our special Founders' Session this Sunday to learn game-changing hacks for mastering Quant using AI.

📚 WHAT YOU'LL LEARN:
• Leverage AI to cover the entire Quant syllabus in 50 days
• Twelvr Hacks: How to make the adaptive engine learn YOU faster
• Inside the Engine: What Twelvr's adaptive algorithm really does
• Free AI Tool: Get access to the AI-powered prep tool I've built

📅 WHEN: This Sunday
💰 FREE • Online • Interactive

🎯 RSVP NOW: https://rsvp.link/founderscircle

WHY THIS MATTERS:
Traditional prep methods take months. With AI and smart strategies, you can cover the same ground in weeks. This isn't about shortcuts – it's about working smarter with technology that adapts to YOUR learning pace.

Don't let these 50 days go to waste. Join us this Sunday!

See you there! 🚀

– Twelvr Team
www.twelvr.com
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
    print("Subject: 🎯 Webinar: Master Quant in 50 Days with AI | Twelvr Hacks")
    print("\nSending...")
    
    success = send_webinar_email(recipient)
    
    if success:
        print("\n✅ EMAIL SENT SUCCESSFULLY!")
        print(f"   Webinar invitation delivered to {recipient}")
    else:
        print("\n❌ EMAIL FAILED TO SEND")
        print("   Check Gmail service authentication")
    
    print("\n" + "=" * 80)
