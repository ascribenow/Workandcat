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

def get_natural_system_prompt() -> str:
    """Get the natural, intelligent Ask Twelvr system prompt"""
    return """
You are Twelvr, a friendly and intelligent CAT Quant tutor. You're having a natural conversation with a student who's practicing for the CAT exam.

Your personality:
- Encouraging and supportive, like a good teacher
- Explain things clearly without being condescending  
- Use simple analogies when they help
- Be conversational, not robotic or overly structured

Guidelines:
- Answer naturally based on what the student asks
- If they ask about a specific problem, help them understand it
- If they ask random questions, chat briefly then gently guide back to studies
- If they share a solution step they're confused about, explain it clearly
- Keep responses reasonably short (under 200 words) since this is a chat modal
- Don't use rigid headings or forced structure - just be natural and helpful

You have access to their current question context when relevant. Just be yourself and help them learn!
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
        
        # Generate AI response using Gemini with enhanced mode detection
        if GOOGLE_API_KEY:
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                # Prepare enhanced context for AI
                conversation_history = doubt_conversations[conversation_key]
                context_messages = "\n".join([
                    f"{'User' if i % 2 == 0 else 'Twelvr'}: {msg['content']}"
                    for i, msg in enumerate(conversation_history)
                ])
                
                # Detect response mode
                has_question_context = bool(question.stem)
                mode = detect_ask_twelvr_mode(doubt_data.message, has_question_context)
                
                # Build enhanced context
                context = {
                    "current_question_stem": question.stem or "",
                    "current_question_category": question.category or "",
                    "current_question_subcategory": question.subcategory or "",
                    "core_concepts": getattr(question, 'core_concepts', []) or [],
                    "solution_approach": question.solution_approach or "",
                    "detailed_solution": question.detailed_solution or "",
                    "correct_answer": question.right_answer or "",
                    "snap_read": question.snap_read or ""
                }
                
                # Create mode-specific prompt
                system_prompt = get_enhanced_system_prompt()
                
                if mode == 1:  # Session-Related
                    specific_prompt = f"""
CONTEXT (current question details):
- Question: {context['current_question_stem']}
- Category: {context['current_question_category']} → {context['current_question_subcategory']}
- Core Concepts: {', '.join(context['core_concepts']) if context['core_concepts'] else 'Not specified'}
- Solution Approach: {context['solution_approach']}
- Correct Answer: {context['correct_answer']}

CONVERSATION HISTORY:
{context_messages}

STUDENT'S QUESTION: {doubt_data.message}

Use MODE 1 - SESSION-RELATED. Answer in context of the current question with simple explanations first, then math details.
"""
                elif mode == 2:  # Off-Topic
                    specific_prompt = f"""
STUDENT'S QUESTION: {doubt_data.message}
CURRENT CONTEXT: Working on {context['current_question_subcategory'] or 'a Quant'} problem

Use MODE 2 - OFF-TOPIC. Give a brief friendly answer, then wit back to their {context['current_question_subcategory'] or 'current'} problem.
"""
                else:  # mode == 3: Solution Step Explanation
                    specific_prompt = f"""
CONTEXT (may help with explanation):
- Question Category: {context['current_question_category']} → {context['current_question_subcategory']}
- Core Concepts: {', '.join(context['core_concepts']) if context['core_concepts'] else 'Mathematical concepts'}
- Solution Available: {context['detailed_solution'][:200] + '...' if len(context['detailed_solution']) > 200 else context['detailed_solution']}

STUDENT WANTS STEP EXPLAINED: {doubt_data.message}

CRITICAL: Use MODE 3 - SOLUTION STEP EXPLANATION. You MUST follow this EXACT 5-heading structure:

### What that step is doing
[Explain in layman terms first with an everyday analogy, then in math terms]

### The idea behind it  
[2-5 bullet points with simple analogies or real-life examples]

### Try this (quick practice)
[One short, non-MCQ task that takes ~60 seconds to solve]

### Solution (peek when ready)
[Complete worked solution in 4-8 lines]

### Next?
[Inviting line: "Want to try a slightly harder one?"]

IMPORTANT: Use these EXACT headings with ### markdown formatting. Start explanations with simple analogies before math details. Keep total response under 180 words.
"""
                
                full_prompt = system_prompt + "\n" + specific_prompt
                
                response = model.generate_content(full_prompt)
                ai_response = response.text.strip()
                
                logger.info(f"Ask Twelvr Mode {mode} response generated for user {user_id[:8]}")
                
                # Store conversation
                doubt_conversations[conversation_key].extend([
                    {
                        "role": "user",
                        "content": doubt_data.message,
                        "timestamp": datetime.utcnow().isoformat(),
                        "mode_detected": mode
                    },
                    {
                        "role": "assistant", 
                        "content": ai_response,
                        "timestamp": datetime.utcnow().isoformat(),
                        "response_mode": mode
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