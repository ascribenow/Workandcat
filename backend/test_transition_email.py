#!/usr/bin/env python3
"""
Test script to send free tier transition email
"""
import sys
sys.path.append('/app/backend')

from gmail_service import gmail_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_send_transition_email():
    """Send test email to hello@twelvr.com"""
    
    print("\n" + "=" * 80)
    print("TESTING FREE TIER TRANSITION EMAIL")
    print("=" * 80)
    
    test_email = "hello@twelvr.com"
    test_name = "Test User"
    
    print(f"\nSending test email to: {test_email}")
    print(f"User name: {test_name}")
    print("\n" + "-" * 80)
    
    success = gmail_service.send_free_tier_transition_email(
        to_email=test_email,
        user_name=test_name
    )
    
    print("-" * 80 + "\n")
    
    if success:
        print("✅ TEST EMAIL SENT SUCCESSFULLY!")
        print(f"   Check inbox at: {test_email}")
        print("\nEmail Content Includes:")
        print("  - Thank you message for completing 5 sessions")
        print("  - Information about 4 weekly free sessions")
        print("  - Upgrade to Pro Exclusive CTA")
        print("  - Feedback form link: https://forms.gle/VMoD5F47oT8QwDE5A")
    else:
        print("❌ TEST EMAIL FAILED")
        print("   Check logs for errors")
    
    print("\n" + "=" * 80)
    
    return success

if __name__ == "__main__":
    test_send_transition_email()
