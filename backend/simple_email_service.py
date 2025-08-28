#!/usr/bin/env python3
"""
Simple Email Service for Twelvr
Alternative to Gmail OAuth2 - uses SMTP with app passwords or other providers
"""

import smtplib
import secrets
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

class SimpleEmailService:
    """
    Simple email service using SMTP instead of Gmail OAuth2
    Can work with Gmail app passwords, SendGrid, or other SMTP providers
    """
    
    def __init__(self):
        # Email configuration from environment
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SENDER_EMAIL', 'costodigital@gmail.com')
        self.sender_password = os.getenv('SENDER_PASSWORD', '')
        self.sender_name = os.getenv('SENDER_NAME', 'Twelvr Team')
        
        # In-memory storage for verification codes (use database in production)
        self.verification_codes: Dict[str, Dict] = {}
        self.pending_users: Dict[str, Dict] = {}
        
        logger.info(f"📧 Simple Email Service initialized with SMTP: {self.smtp_server}:{self.smtp_port}")
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.sender_email and self.sender_password)
    
    def generate_verification_code(self, email: str) -> str:
        """Generate a 6-digit verification code for email"""
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store with expiry
        expiry_time = datetime.utcnow() + timedelta(minutes=15)
        self.verification_codes[email] = {
            'code': code,
            'expires_at': expiry_time,
            'attempts': 0
        }
        
        logger.info(f"📧 Generated verification code for {email}: {code}")
        return code
    
    def verify_code(self, email: str, code: str) -> bool:
        """Verify the verification code for an email"""
        if email not in self.verification_codes:
            return False
        
        stored_data = self.verification_codes[email]
        
        # Check if code is expired
        if datetime.utcnow() > stored_data['expires_at']:
            logger.warning(f"⏰ Verification code expired for {email}")
            del self.verification_codes[email]
            return False
        
        # Check attempts limit
        stored_data['attempts'] += 1
        if stored_data['attempts'] > 5:
            logger.warning(f"🚫 Too many attempts for {email}")
            del self.verification_codes[email]
            return False
        
        # Verify code
        if stored_data['code'] == code:
            logger.info(f"✅ Verification successful for {email}")
            del self.verification_codes[email]  # Clean up after successful verification
            return True
        
        logger.warning(f"❌ Invalid verification code for {email}")
        return False
    
    def cleanup_expired_codes(self):
        """Clean up expired verification codes"""
        current_time = datetime.utcnow()
        expired_emails = [
            email for email, data in self.verification_codes.items()
            if current_time > data['expires_at']
        ]
        
        for email in expired_emails:
            del self.verification_codes[email]
            logger.info(f"🧹 Cleaned up expired code for {email}")
    
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str = None) -> bool:
        """Send email using SMTP"""
        if not self.is_configured():
            logger.error("❌ Email service not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable encryption
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"📧 Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def send_verification_email(self, email: str, code: str) -> bool:
        """Send verification code email"""
        subject = "Verify Your Twelvr Account - Verification Code"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Twelvr Account</title>
            <style>
                body {{ font-family: 'Lato', Arial, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #9ac026 0%, #8bb024 100%); padding: 40px 20px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: bold; }}
                .content {{ padding: 40px 30px; }}
                .verification-code {{ background-color: #f8f9fa; border: 2px dashed #9ac026; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; }}
                .code {{ font-size: 32px; font-weight: bold; color: #545454; letter-spacing: 8px; font-family: 'Courier New', monospace; }}
                .footer {{ background-color: #545454; color: white; padding: 20px; text-align: center; font-size: 14px; }}
                .button {{ display: inline-block; background-color: #9ac026; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Twelvr</h1>
                    <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Complete Your Account Setup</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #545454; margin-bottom: 20px;">Verify Your Email Address</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        Welcome to Twelvr! Please use the verification code below to complete your account registration:
                    </p>
                    
                    <div class="verification-code">
                        <p style="margin: 0 0 10px 0; color: #545454; font-weight: bold;">Your Verification Code:</p>
                        <div class="code">{code}</div>
                        <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">This code expires in 15 minutes</p>
                    </div>
                    
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        If you didn't request this verification, please ignore this email.
                    </p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="color: #888; font-size: 14px;">
                            <strong>Security Note:</strong> Never share this code with anyone. The Twelvr team will never ask for your verification code.
                        </p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 Twelvr. Your CAT Preparation Partner.</p>
                    <p style="margin: 5px 0 0 0; font-size: 12px;">This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Verify Your Twelvr Account
        
        Welcome to Twelvr! 
        
        Your verification code is: {code}
        
        This code expires in 15 minutes.
        
        If you didn't request this verification, please ignore this email.
        
        © 2025 Twelvr. Your CAT Preparation Partner.
        """
        
        return self.send_email(email, subject, html_body, text_body)
    
    def send_password_reset_email(self, email: str, code: str) -> bool:
        """Send password reset email"""
        subject = "Reset Your Twelvr Password - Verification Code"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Twelvr Password</title>
            <style>
                body {{ font-family: 'Lato', Arial, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #ff6d4d 0%, #e55a40 100%); padding: 40px 20px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: bold; }}
                .content {{ padding: 40px 30px; }}
                .verification-code {{ background-color: #fff5f5; border: 2px dashed #ff6d4d; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; }}
                .code {{ font-size: 32px; font-weight: bold; color: #545454; letter-spacing: 8px; font-family: 'Courier New', monospace; }}
                .footer {{ background-color: #545454; color: white; padding: 20px; text-align: center; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 Twelvr</h1>
                    <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Password Reset Request</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #545454; margin-bottom: 20px;">Reset Your Password</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        You requested a password reset for your Twelvr account. Use the verification code below:
                    </p>
                    
                    <div class="verification-code">
                        <p style="margin: 0 0 10px 0; color: #545454; font-weight: bold;">Your Reset Code:</p>
                        <div class="code">{code}</div>
                        <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">This code expires in 15 minutes</p>
                    </div>
                    
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        If you didn't request this password reset, please ignore this email and your password will remain unchanged.
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Twelvr. Your CAT Preparation Partner.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Reset Your Twelvr Password
        
        You requested a password reset for your Twelvr account.
        
        Your reset code is: {code}
        
        This code expires in 15 minutes.
        
        If you didn't request this reset, please ignore this email.
        
        © 2025 Twelvr. Your CAT Preparation Partner.
        """
        
        return self.send_email(email, subject, html_body, text_body)

# Global instance
simple_email_service = SimpleEmailService()