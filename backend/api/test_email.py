"""
Test endpoint for sending transition email
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from gmail_service import gmail_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/test-transition-email")
async def send_test_transition_email():
    """
    Test endpoint to send transition email to hello@twelvr.com
    FOR TESTING ONLY - Remove in production
    """
    try:
        test_email = "hello@twelvr.com"
        test_name = "Test User"
        
        logger.info(f"Sending test transition email to {test_email}")
        
        success = gmail_service.send_free_tier_transition_email(
            to_email=test_email,
            user_name=test_name
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": f"Test email sent to {test_email}",
                "email": test_email
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
