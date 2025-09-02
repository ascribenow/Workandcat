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
        self.sender_email = 'costodigital@gmail.com'
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

# Global instance
gmail_service = GmailService()