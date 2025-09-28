# API endpoints for Ask Twelvr doubt conversation system
import os
import json
import uuid
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import select, func, and_, desc, text

from database import SessionLocal, Question
import google.generativeai as genai

# Authentication helpers (import from main server)
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    logger.info("✅ Google Gemini configured for doubts system")
else:
    logger.warning("⚠️ Google API key not found - doubts system will not work")

router = APIRouter(prefix="/doubts")

# Simple context awareness - let LLM intelligence handle the conversation
def has_question_context(user_message: str) -> bool:
    """Simple check if user seems to be referring to current question"""
    text = user_message.lower()
    context_indicators = [
        'this question', 'this problem', 'current question', 'this one',
        'option a', 'option b', 'option c', 'option d', 'which option',
        'right answer', 'correct answer', 'how to solve this'
    ]
    return any(indicator in text for indicator in context_indicators)

# Enhanced solution paste detection - let LLM intelligence handle the explanation
class SolutionPasteDetector:
    def detect_solution_paste(self, message: str) -> bool:
        """Intelligent detection of solution steps or mathematical expressions"""
        text = message.strip()
        
        # Mathematical expressions and solution indicators
        math_patterns = [
            r'[=≠≈≤≥<>]\s*[^?]*',  # Contains mathematical operators
            r'[\d\w]\s*[\+\-×x\*/÷]\s*[\d\w]',  # Arithmetic operations
            r'^\s*[a-zA-Z]\s*=.*\d',  # Variable equations like "x = 5"
            r'\b(step|formula|equation|substitute|solve|calculate)\b',  # Solution keywords
            r'Volume\s*=|Area\s*=|Perimeter\s*=',  # Common formula starts
            r'\d+π|\d+/\d+|√\d+',  # Mathematical expressions with π, fractions, roots
            r'why.*=|how.*=|what.*mean',  # Questions about mathematical expressions
        ]
        
        # Check if message contains solution-like content
        for pattern in math_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        # Check message length and complexity (longer messages might be solution pastes)
        if len(text) > 50 and ('=' in text or any(op in text for op in ['+', '-', '×', '÷', '*', '/'])):
            return True
            
        return False

# Global detector instance
solution_detector = SolutionPasteDetector()

def get_enhanced_context_prompt() -> str:
    """Get the enhanced Ask Twelvr system prompt with rich context and solution intelligence"""
    return """
You are Twelvr, a witty and intelligent CAT Quant tutor having a natural conversation with a student.

Your personality:
- Encouraging, supportive, and occasionally witty like a great teacher
- Use real-world analogies wherever possible to explain concepts
- Be conversational and natural - no robotic responses
- Clear explanations without being condescating

## CONVERSATION INTELLIGENCE:

**SOLUTION STEP EXPLANATIONS**: If the student pastes/shares any part of a solution or asks about a specific step, use this 5-section format:

1) **What's happening here** - Explain the step in simple terms with real-world analogy
2) **The concept behind it** - What mathematical principle/concept this represents  
3) **Why this approach** - Why we use this method/formula in this context
4) **Practice question** - Create a similar but simpler question with complete solution (format: Problem statement, then "Solution:" with step-by-step solution)
5) **Ready for more?** - Ask "Want to try a harder version of this concept?"

**PRACTICE QUESTION GENERATION**: 
- Make questions similar to current topic but simpler/clearer
- Always provide complete step-by-step solution
- Use real-world contexts when possible (money, time, objects)

**HARDER QUESTION FLOW**: When student says "yes" to "Ready for more?" or "Want a harder version":
- Detect their agreement (yes, sure, okay, bring it on, etc.)
- Create a more challenging problem on the same concept with these guidelines:
  * Same mathematical concept but more complex numbers/scenarios
  * Add one more step or combine with another concept
  * Use realistic but challenging values
  * Format: "Here's a tougher one:" followed by problem statement
  * Always include "Solution:" with complete step-by-step working
  * End with "How did that feel? Want to try another concept or a different difficulty?"

**CONVERSATION MEMORY**: Remember what concepts you've covered in this conversation to avoid repetition.

**EVERYTHING ELSE**: Use your intelligence to:
- Answer questions naturally about the current problem
- Use witty analogies and real-world examples
- Guide understanding without lecturing
- Keep conversations engaging and educational
- Be encouraging when they're struggling

You have full context about their current question. Use it wisely to help them learn!
"""

router = APIRouter(prefix="/doubts")

# Pydantic models
class DoubtMessage(BaseModel):
    question_id: str
    session_id: str
    message: str

class DoubtResponse(BaseModel):
    success: bool
    message_count: int
    remaining_messages: int
    is_locked: bool
    response: Optional[str] = None
    error: Optional[str] = None

# In-memory storage for MVP (replace with database in production)
doubt_conversations = {}  # {f"{user_id}:{question_id}": [messages...]}
doubt_message_counts = {}  # {f"{user_id}:{question_id}": count}

MAX_MESSAGES_PER_QUESTION = 10

@router.post("/ask")
async def ask_doubt(
    doubt_data: DoubtMessage,
    user_id: str = Depends(get_current_user)
) -> DoubtResponse:
    """Submit a doubt about a specific question and get AI response"""
    try:
        conversation_key = f"{user_id}:{doubt_data.question_id}"
        
        # Initialize conversation if not exists
        if conversation_key not in doubt_conversations:
            doubt_conversations[conversation_key] = []
            doubt_message_counts[conversation_key] = 0
        
        # Check message limit
        current_count = doubt_message_counts[conversation_key]
        if current_count >= MAX_MESSAGES_PER_QUESTION:
            return DoubtResponse(
                success=False,
                message_count=current_count,
                remaining_messages=0,
                is_locked=True,
                error="Message limit reached for this question"
            )
        
        # Get question details
        db = SessionLocal()
        try:
            result = db.execute(select(Question).where(Question.id == doubt_data.question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                return DoubtResponse(
                    success=False,
                    message_count=current_count,
                    remaining_messages=MAX_MESSAGES_PER_QUESTION - current_count,
                    is_locked=False,
                    error="Question not found"
                )
        finally:
            db.close()
        
        # Generate AI response using Gemini with natural conversation
        if GOOGLE_API_KEY:
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                # Prepare natural conversation context
                conversation_history = doubt_conversations[conversation_key]
                context_messages = "\n".join([
                    f"{'Student' if i % 2 == 0 else 'Twelvr'}: {msg['content']}"
                    for i, msg in enumerate(conversation_history)
                ])
                
                # Build rich question context for LLM
                rich_context = f"""
## CURRENT QUESTION CONTEXT:
**Problem Statement**: {question.stem or 'Not available'}
**Topic**: {question.subcategory or question.category or 'Quantitative Aptitude'}
**Difficulty**: {getattr(question, 'difficulty', 'Medium')}
**Correct Answer**: {question.right_answer or 'Not provided'}

**Available Solutions**:
- Approach: {question.solution_approach or 'Standard method'}
- Detailed Solution: {question.detailed_solution or 'Solution steps available'}
- Key Insight: {question.snap_read or 'Apply fundamental concepts'}

**Core Concepts**: {getattr(question, 'core_concepts', []) or ['Mathematical reasoning']}

This is what the student is working on. Use this context intelligently in your responses.
"""
                
                # Detect if student is sharing solution steps (intelligent detection)
                is_solution_paste = solution_detector.detect_solution_paste(doubt_data.message)
                solution_guidance = ""
                if is_solution_paste:
                    solution_guidance = """
## SOLUTION STEP DETECTED:
The student appears to be asking about a specific solution step. Use the 5-section format:
1) What's happening here, 2) The concept behind it, 3) Why this approach, 4) Practice question, 5) Ready for more?
"""
                
                # Create enhanced conversation prompt
                full_prompt = f"""
{get_enhanced_context_prompt()}

{rich_context}

{solution_guidance}

## CONVERSATION HISTORY:
{context_messages}

## STUDENT'S MESSAGE:
{doubt_data.message}

Respond with your full intelligence - be witty, use analogies, and help them understand:
"""
                
                response = model.generate_content(full_prompt)
                ai_response = response.text.strip()
                
                logger.info(f"Ask Twelvr natural response generated for user {user_id[:8]}")
                
                # Store conversation
                doubt_conversations[conversation_key].extend([
                    {
                        "role": "user",
                        "content": doubt_data.message,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "role": "assistant", 
                        "content": ai_response,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ])
                
                # Update message count
                doubt_message_counts[conversation_key] += 1
                new_count = doubt_message_counts[conversation_key]
                remaining = MAX_MESSAGES_PER_QUESTION - new_count
                is_locked = new_count >= MAX_MESSAGES_PER_QUESTION
                
                logger.info(f"🤔 Doubt answered for question {doubt_data.question_id[:8]} by user {user_id[:8]} ({new_count}/{MAX_MESSAGES_PER_QUESTION})")
                
                return DoubtResponse(
                    success=True,
                    message_count=new_count,
                    remaining_messages=remaining,
                    is_locked=is_locked,
                    response=ai_response
                )
                
            except Exception as e:
                logger.error(f"❌ Gemini error: {e}")
                return DoubtResponse(
                    success=False,
                    message_count=current_count,
                    remaining_messages=MAX_MESSAGES_PER_QUESTION - current_count,
                    is_locked=False,
                    error="AI service temporarily unavailable"
                )
        else:
            return DoubtResponse(
                success=False,
                message_count=current_count,
                remaining_messages=MAX_MESSAGES_PER_QUESTION - current_count,
                is_locked=False,
                error="AI service not configured"
            )
        
    except Exception as e:
        logger.error(f"❌ Error in ask doubt: {e}")
        raise HTTPException(status_code=500, detail="Failed to process doubt")

@router.get("/{question_id}/history")
async def get_doubt_history(
    question_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get conversation history for a specific question"""
    try:
        conversation_key = f"{user_id}:{question_id}"
        
        messages = doubt_conversations.get(conversation_key, [])
        message_count = doubt_message_counts.get(conversation_key, 0)
        remaining = MAX_MESSAGES_PER_QUESTION - message_count
        is_locked = message_count >= MAX_MESSAGES_PER_QUESTION
        
        return {
            "success": True,
            "messages": messages,
            "message_count": message_count,
            "remaining_messages": remaining,
            "is_locked": is_locked
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting doubt history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get doubt history")

@router.get("/admin/conversations")
async def admin_get_all_conversations(
    admin_user_id: str = Depends(get_current_user)  # Add proper admin check if needed
):
    """Admin endpoint to view all doubt conversations"""
    try:
        # Get conversation statistics
        total_conversations = len(doubt_conversations)
        total_messages = sum(len(messages) for messages in doubt_conversations.values())
        
        # Get active conversations (not locked)
        active_conversations = sum(
            1 for key in doubt_message_counts 
            if doubt_message_counts[key] < MAX_MESSAGES_PER_QUESTION
        )
        
        return {
            "success": True,
            "statistics": {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "active_conversations": active_conversations,
                "locked_conversations": total_conversations - active_conversations
            },
            "recent_conversations": [
                {
                    "key": key,
                    "message_count": doubt_message_counts.get(key, 0),
                    "last_message": messages[-1] if messages else None
                }
                for key, messages in list(doubt_conversations.items())[-10:]
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting admin conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")