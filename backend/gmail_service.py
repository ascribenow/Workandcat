import os
import json
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import httplib2

class GmailService:
    def __init__(self):
        self.scopes = ['https://mail.google.com/']
        self.credentials_file = '/app/backend/gmail_credentials.json'
        self.sender_email = 'hello@twelvr.com'
        self.sender_name = 'Twelvr'  # Display name for emails
        self.service = None
        # In production, use proper database
        self.verification_codes: Dict[str, Dict] = {}
        self.pending_users: Dict[str, Dict] = {}
    
    def get_authorization_url(self) -> str:
        """Get OAuth2 authorization URL for user to authorize Gmail access"""
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=self.scopes,
            redirect_uri='https://www.twelvr.com'
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            login_hint=self.sender_email
        )
        
        return auth_url
    
    def exchange_code_for_tokens(self, authorization_code: str) -> bool:
        """Exchange authorization code for access tokens"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes,
                redirect_uri='https://www.twelvr.com'
            )
            
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Store credentials (in production, use secure storage)
            self._store_credentials(credentials)
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=credentials)
            return True
            
        except Exception as e:
            print(f"Error exchanging code for tokens: {e}")
            return False
    
    def _store_credentials(self, credentials: Credentials):
        """Store credentials securely (simplified for demo)"""
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open('/app/backend/gmail_token.json', 'w') as f:
            json.dump(creds_data, f)
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load stored credentials"""
        try:
            if os.path.exists('/app/backend/gmail_token.json'):
                with open('/app/backend/gmail_token.json', 'r') as f:
                    creds_data = json.load(f)
                
                credentials = Credentials(
                    token=creds_data['token'],
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data['token_uri'],
                    client_id=creds_data['client_id'],
                    client_secret=creds_data['client_secret'],
                    scopes=creds_data['scopes']
                )
                
                # Refresh if expired
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    self._store_credentials(credentials)
                
                return credentials
        except Exception as e:
            print(f"Error loading credentials: {e}")
        
        return None
    
    def authenticate_service(self) -> bool:
        """Authenticate Gmail service with stored credentials"""
        credentials = self._load_credentials()
        if credentials and credentials.valid:
            self.service = build('gmail', 'v1', credentials=credentials)
            return True
        return False
    
    def send_generic_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send a generic email with custom subject and body"""
        if not self.service:
            print("Gmail service not authenticated")
            return False
        
        try:
            # Create email content
            plain_text = body
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{subject}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 32px;
            font-weight: bold;
            color: #9ac026;
        }}
        .content {{
            white-space: pre-line;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Twelvr</div>
            <p>CAT Preparation Platform</p>
        </div>
        <div class="content">{body}</div>
    </div>
</body>
</html>
            """
            
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
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
            
            self.service.users().messages().send(userId='me', body=message).execute()
            print(f"Generic email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"Error sending generic email: {e}")
            return False

    def send_password_reset_email(self, to_email: str, code: str) -> bool:
        """Send password reset code email"""
        if not self.service:
            print("Gmail service not authenticated")
            return False
        
        try:
            # Create email content
            subject = "Password Reset Code - Twelvr"
            
            plain_text = f"""
Password Reset Request - Twelvr

Your password reset code is: {code}

This code will expire in 15 minutes. Please enter this code to reset your password.

If you didn't request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
The Twelvr Team
            """.strip()
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Password Reset - Twelvr</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }}
        .content {{
            padding: 30px;
        }}
        .code {{
            font-size: 36px;
            font-weight: bold;
            color: #ef4444;
            text-align: center;
            background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
            padding: 25px;
            border-radius: 8px;
            margin: 25px 0;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #f39c12;
        }}
        .security {{
            background-color: #f3f4f6;
            border: 1px solid #d1d5db;
            color: #374151;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #6b7280;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 14px;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .logo {{
            color: #ef4444;
            font-weight: bold;
            font-size: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Twelvr</div>
            <h1>🔐 Password Reset</h1>
        </div>
        <div class="content">
            <p>You requested to reset your password for your <strong>Twelvr</strong> account.</p>
            <p>Your password reset code is:</p>
            <div class="code">{code}</div>
            <p>This code will expire in <strong>15 minutes</strong>. Please enter this code to reset your password.</p>
            <div class="security">
                <strong>🔒 Security Notice:</strong> If you didn't request a password reset, please ignore this email and your password will remain unchanged.
            </div>
        </div>
        <div class="footer">
            <p>Best regards,<br><strong>The Twelvr Team</strong></p>
            <p>🛡️ Keep your account secure!</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Create message
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['from'] = self.sender_email
            message['subject'] = subject
            
            # Add parts
            text_part = MIMEText(plain_text, 'plain')
            html_part = MIMEText(html_content, 'html')
            message.attach(text_part)
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            print(f"Password reset email sent successfully. Message ID: {send_message.get('id')}")
            return True
            
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False

    def send_verification_email(self, to_email: str, code: str) -> bool:
        """Send verification code email"""
        if not self.service:
            print("Gmail service not authenticated")
            return False
        
        try:
            # Create email content
            subject = "Email Verification Code - Twelvr"
            
            plain_text = f"""
Welcome to Twelvr!

Your verification code is: {code}

This code will expire in 15 minutes. Please enter this code to complete your registration.

If you didn't request this verification, please ignore this email.

Best regards,
The Twelvr Team
            """.strip()
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Email Verification - Twelvr</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }}
        .content {{
            padding: 30px;
        }}
        .code {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 8px;
            margin: 25px 0;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #f39c12;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 14px;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .logo {{
            color: #667eea;
            font-weight: bold;
            font-size: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Twelvr</div>
            <h1>Email Verification</h1>
        </div>
        <div class="content">
            <p>Welcome to <strong>Twelvr</strong> - Your AI-powered CAT Quantitative Aptitude preparation platform!</p>
            <p>Your verification code is:</p>
            <div class="code">{code}</div>
            <p>This code will expire in <strong>15 minutes</strong>. Please enter this code to complete your registration and start your adaptive learning journey.</p>
            <div class="warning">
                <strong>🛡️ Security Notice:</strong> If you didn't request this verification, please ignore this email. Never share this code with anyone.
            </div>
        </div>
        <div class="footer">
            <p>Best regards,<br><strong>The Twelvr Team</strong></p>
            <p>🚀 Prepare smarter, not harder!</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Create message
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['from'] = self.sender_email
            message['subject'] = subject
            
            # Add parts
            text_part = MIMEText(plain_text, 'plain')
            html_part = MIMEText(html_content, 'html')
            message.attach(text_part)
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            print(f"Email sent successfully. Message ID: {send_message.get('id')}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def generate_verification_code(self, email: str) -> str:
        """Generate a 6-digit verification code"""
        code = f"{secrets.randbelow(1000000):06d}"
        expiry_time = datetime.utcnow() + timedelta(minutes=15)
        
        self.verification_codes[email] = {
            'code': code,
            'created_at': datetime.utcnow(),
            'expires_at': expiry_time,
            'verified': False
        }
        
        return code
    
    def verify_code(self, email: str, provided_code: str) -> bool:
        """Verify the provided code against stored code"""
        if email not in self.verification_codes:
            return False
        
        stored_data = self.verification_codes[email]
        
        # Check if code has expired
        if datetime.utcnow() > stored_data['expires_at']:
            del self.verification_codes[email]
            return False
        
        # Check if code matches
        if stored_data['code'] == provided_code and not stored_data['verified']:
            self.verification_codes[email]['verified'] = True
            return True
        
        return False
    
    def store_pending_user(self, email: str, user_data: dict):
        """Store pending user data temporarily"""
        self.pending_users[email] = {
            'user_data': user_data,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=30)  # 30 min for signup completion
        }
    
    def get_pending_user(self, email: str) -> Optional[dict]:
        """Get pending user data"""
        if email in self.pending_users:
            pending_data = self.pending_users[email]
            
            # Check if expired
            if datetime.utcnow() > pending_data['expires_at']:
                del self.pending_users[email]
                return None
            
            return pending_data['user_data']
        
        return None
    
    def remove_pending_user(self, email: str):
        """Remove pending user after successful signup"""
        if email in self.pending_users:
            del self.pending_users[email]
        if email in self.verification_codes:
            del self.verification_codes[email]
    
    def cleanup_expired_codes(self):
        """Remove expired codes and pending users"""
        current_time = datetime.utcnow()
        
        # Clean up expired verification codes
        expired_codes = [
            email for email, data in self.verification_codes.items()
            if current_time > data['expires_at']
        ]
        for email in expired_codes:
            del self.verification_codes[email]
        
        # Clean up expired pending users
        expired_users = [
            email for email, data in self.pending_users.items()
            if current_time > data['expires_at']
        ]
        for email in expired_users:
            del self.pending_users[email]

    def send_referral_code_email(self, to_email: str, full_name: str, referral_code: str) -> bool:
        """Send referral code email to new user"""
        if not self.service:
            print("Gmail service not authenticated")
            return False
        
        try:
            # Create email content with preheader for deliverability
            subject = "🎯 Welcome to Twelvr! Your Exclusive Referral Code & ₹500 Rewards Inside"
            preheader = "₹500 for them. ₹500 for you. One code, once."
            
            plain_text = f"""
{preheader}

Welcome to Twelvr, {full_name}!

Adaptive CAT prep that compounds. Your referral rewards await!

🎯 YOUR EXCLUSIVE REFERRAL CODE: {referral_code}

💰 REFERRAL REWARDS:
• Your Friends Save: ₹500 discount on any Pro subscription
• You Earn: ₹500 cashback for each friend's successful subscription

🔥 HOW IT WORKS:
1. Share your code: {referral_code}
2. Friend subscribes with your code and gets ₹500 discount
3. ₹500 cashback is processed after every successful use of your referral code

💡 PERFECT FOR:
• Pro Regular (₹1,495): Monthly subscription → ₹995 after your code
• Pro Exclusive (₹2,565): One-time till Dec 2025 → ₹2,065 after your code

📋 IMPORTANT TERMS:
• One-time usage: Each person can use only one referral code ever
• No self-referral: Cannot use your own code  
• Successful payments only: Discount applied only on completed transactions
• Cashback processing: ₹500 cashback is processed after every successful use of your referral code
• Valid plans: Pro Regular and Pro Exclusive only

T&Cs apply: https://twelvr.com/terms

Start your 12: https://twelvr.com

Questions? Reply to this email or reach us at hello@twelvr.com

Best regards,
The Twelvr Team
hello@twelvr.com
You, Compounded.
            """.strip()
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to Twelvr - Your Referral Rewards</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if !mso]><!-->
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--<![endif]-->
    <!-- Preheader text for better deliverability -->
    <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: Arial, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
        {preheader}
    </div>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        .container {{
            background-color: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #9ac026 0%, #667eea 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .tagline {{
            margin: 10px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        .content {{
            padding: 35px 30px;
        }}
        .referral-code {{
            background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
            color: white;
            text-align: center;
            padding: 25px;
            border-radius: 12px;
            margin: 25px 0;
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 3px;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
        }}
        .benefits {{
            display: flex;
            justify-content: space-between;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .benefit {{
            flex: 1;
            text-align: center;
            padding: 20px 15px;
            margin: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            min-width: 200px;
        }}
        .benefit h3 {{
            margin: 0 0 10px 0;
            font-size: 24px;
        }}
        .benefit p {{
            margin: 0;
            opacity: 0.9;
        }}
        .how-it-works {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 12px;
            border-left: 5px solid #9ac026;
            margin: 25px 0;
        }}
        .steps {{
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        .step {{
            flex: 1;
            text-align: center;
            padding: 15px 10px;
            margin: 10px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            min-width: 150px;
        }}
        .step-number {{
            background: #9ac026;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .terms {{
            background-color: #fff8e1;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
            margin-top: 25px;
            font-size: 14px;
        }}
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #9ac026 0%, #667eea 100%);
            color: white;
            padding: 15px 35px;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            font-size: 16px;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(154, 192, 38, 0.3);
        }}
        .footer {{
            background-color: #f1f3f4;
            padding: 25px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        .legal-link {{
            color: #9ac026;
            text-decoration: none;
            font-weight: 500;
        }}
        .legal-link:hover {{
            text-decoration: underline;
        }}
        
        /* Mobile responsiveness */
        @media only screen and (max-width: 600px) {{
            .benefits {{
                flex-direction: column;
            }}
            .benefit {{
                margin: 5px 0;
            }}
            .steps {{
                flex-direction: column;
            }}
            .step {{
                margin: 5px 0;
            }}
            .content {{
                padding: 20px 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Welcome to Twelvr!</h1>
            <p class="tagline">You, Compounded.</p>
        </div>
        
        <div class="content">
            <h2>Hello {full_name},</h2>
            <p>Adaptive CAT prep that compounds. Your referral rewards await! 🚀</p>
            
            <div class="referral-code">
                {referral_code}
            </div>
            <p style="text-align: center; margin-top: -10px; color: #666; font-size: 14px;">
                <em>Your Exclusive Referral Code</em>
            </p>
            
            <div class="benefits">
                <div class="benefit">
                    <h3>₹500</h3>
                    <p>Your Friends Save</p>
                </div>
                <div class="benefit">
                    <h3>₹500</h3>
                    <p>You Earn Cashback</p>
                </div>
            </div>
            
            <div class="how-it-works">
                <h3>🔥 How Your Referral Program Works:</h3>
                <div class="steps">
                    <div class="step">
                        <div class="step-number">1</div>
                        <strong>Share Code</strong><br>
                        <small>Send {referral_code} to friends</small>
                    </div>
                    <div class="step">
                        <div class="step-number">2</div>
                        <strong>Friend Subscribes</strong><br>
                        <small>They get ₹500 discount</small>
                    </div>
                    <div class="step">
                        <div class="step-number">3</div>
                        <strong>You Get Paid</strong><br>
                        <small>₹500 cashback is processed after every successful use of your referral code</small>
                    </div>
                </div>
            </div>
            
            <h3>💡 Perfect for:</h3>
            <ul style="line-height: 1.8;">
                <li><strong>Pro Regular (₹1,495):</strong> Monthly subscription with pause/resume → <strong>₹995 after discount</strong></li>
                <li><strong>Pro Exclusive (₹2,565):</strong> One-time till Dec 2025 + Ask Twelvr → <strong>₹2,065 after discount</strong></li>
            </ul>
            
            <div class="terms">
                <h4>📋 Important Terms:</h4>
                <ul style="margin: 10px 0;">
                    <li><strong>One-time usage:</strong> Each person can use only one referral code ever</li>
                    <li><strong>No self-referral:</strong> Cannot use your own code</li>
                    <li><strong>Successful payments only:</strong> Discount applied only on completed transactions</li>
                    <li><strong>Cashback processing:</strong> Earn ₹500 cashback for each friend's successful subscription</li>
                    <li><strong>Valid plans:</strong> Pro Regular and Pro Exclusive only</li>
                </ul>
                <p style="margin-top: 15px;">
                    <a href="https://twelvr.com/terms" class="legal-link">T&Cs apply</a>
                </p>
            </div>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="https://twelvr.com" class="cta-button">Start your 12 🎯</a>
            </p>
            
            <p><strong>Questions?</strong> Reply to this email or reach us at <a href="mailto:hello@twelvr.com" style="color: #9ac026;">hello@twelvr.com</a></p>
        </div>
        
        <div class="footer">
            <p><strong>The Twelvr Team</strong><br>
            hello@twelvr.com<br>
            <em>You, Compounded.</em></p>
        </div>
    </div>
</body>
</html>            
            """
            
            # Send email using the same pattern as other email methods
            msg = MIMEMultipart('alternative')
            msg['to'] = to_email
            msg['from'] = f'{self.sender_name} <{self.sender_email}>'  # Proper display name format
            msg['subject'] = subject
            
            # Create text and HTML parts
            text_part = MIMEText(plain_text, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            message = {'raw': raw}
            
            self.service.users().messages().send(userId='me', body=message).execute()
            print(f"✅ Referral welcome email sent successfully to {to_email} with code {referral_code}")
            return True
            
        except Exception as e:
            print(f"Error sending referral code email: {e}")
            return False

    def send_payment_confirmation_email(self, to_email: str, plan_name: str, amount: str, payment_id: str, end_date: str = None) -> bool:
        """Send payment confirmation email after successful subscription"""
        if not self.service:
            print("Gmail service not authenticated")
            return False
        
        try:
            # Create email content
            subject = f"Payment Confirmed - {plan_name} Subscription - Twelvr"
            
            # Format end date nicely
            end_date_text = f" until {end_date}" if end_date else ""
            
            plain_text = f"""
Payment Confirmation - Twelvr

Thank you for your payment! Your {plan_name} subscription is now active{end_date_text}.

Payment Details:
- Plan: {plan_name}
- Amount: {amount}
- Payment ID: {payment_id}
- Status: Successfully Processed

Your subscription includes:
{self._get_plan_features(plan_name)}

You can now access all your premium features on the Twelvr dashboard.

Login to start your journey: https://twelvr.com

If you have any questions, feel free to reply to this email.

Best regards,
The Twelvr Team
hello@twelvr.com
            """.strip()
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Payment Confirmed - Twelvr</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #9ac026 0%, #7da21f 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .success-badge {{
            background-color: #4CAF50;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .payment-details {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .plan-features {{
            background-color: #e8f5e8;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #9ac026 0%, #7da21f 100%);
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: bold;
            margin: 20px 0;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Payment Confirmed!</h1>
            <p>Welcome to {plan_name}</p>
        </div>
        <div class="content">
            <div class="success-badge">✅ Successfully Processed</div>
            
            <p>Thank you for choosing Twelvr! Your {plan_name} subscription is now active{end_date_text}.</p>
            
            <div class="payment-details">
                <h3>Payment Details</h3>
                <p><strong>Plan:</strong> {plan_name}<br>
                <strong>Amount:</strong> {amount}<br>
                <strong>Payment ID:</strong> {payment_id}<br>
                <strong>Status:</strong> Successfully Processed</p>
            </div>
            
            <div class="plan-features">
                <h3>Your Subscription Includes:</h3>
                {self._get_plan_features_html(plan_name)}
            </div>
            
            <p>You can now access all your premium features on the Twelvr dashboard.</p>
            
            <a href="https://twelvr.com" class="cta-button">Start Your Journey</a>
            
            <p>If you have any questions about your subscription or need help getting started, feel free to reply to this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>
            The Twelvr Team<br>
            hello@twelvr.com</p>
        </div>
    </div>
</body>
</html>            
            """
            
            # Send email
            return self._send_html_email(to_email, subject, html_content, plain_text)
            
        except Exception as e:
            print(f"Error sending payment confirmation email: {e}")
            return False

    def _get_plan_features(self, plan_name: str) -> str:
        """Get plain text plan features"""
        if "Pro Regular" in plan_name:
            return """- Unlimited sessions for 30 days
- Full Adaptivity (Trend Matrix + Reflex Loop + Learning Impact)
- Progress dashboard & analytics
- Comprehensive performance reports
- Renews every month, pause anytime"""
        elif "Pro Exclusive" in plan_name:
            return """- Unlimited sessions till Dec 31, 2025
- Full Adaptivity (Trend Matrix + Reflex Loop + Learning Impact)  
- Progress dashboard & analytics
- Comprehensive performance reports
- Full syllabus coverage in 90 sessions (only for Quantitative Ability section)
- Ask Twelvr: Real-time doubt resolution per question"""
        else:
            return "- 10 adaptive sessions\n- Limited Adaptivity (Mindprint)\n- Progress dashboard & analytics\n- Ask Twelvr: Real-time doubt resolution per question"

    def _get_plan_features_html(self, plan_name: str) -> str:
        """Get HTML formatted plan features"""
        if "Pro Regular" in plan_name:
            return """<ul>
<li>✅ Unlimited sessions for 30 days</li>
<li>✅ Full Adaptivity (Trend Matrix + Reflex Loop + Learning Impact)</li>
<li>✅ Progress dashboard & analytics</li>
<li>✅ Comprehensive performance reports</li>
<li>✅ Renews every month, pause anytime</li>
</ul>"""
        elif "Pro Exclusive" in plan_name:
            return """<ul>
<li>✅ Unlimited sessions till Dec 31, 2025</li>
<li>✅ Full Adaptivity (Trend Matrix + Reflex Loop + Learning Impact)</li>
<li>✅ Progress dashboard & analytics</li>
<li>✅ Comprehensive performance reports</li>
<li>✅ Full syllabus coverage in 90 sessions (only for Quantitative Ability section)</li>
<li>✅ Ask Twelvr: Real-time doubt resolution per question</li>
</ul>"""
        else:
            return """<ul>
<li>✅ 10 adaptive sessions</li>
<li>✅ Limited Adaptivity (Mindprint)</li>
<li>✅ Progress dashboard & analytics</li>
<li>✅ Ask Twelvr: Real-time doubt resolution per question</li>
</ul>"""

# Global instance
gmail_service = GmailService()