"""FastAPI routes for JARVIS backend."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from backend.app.agents.jarvis_agent import JarvisAgent
from backend.app.config import get_settings
from backend.app.providers.groq_provider import GroqProvider
from backend.app.memory.manager import MemoryManager
from backend.app.reminders.manager import ReminderManager
from backend.app.integrations.alexa.handler import handle_alexa_request
from backend.app.integrations.alexa.security import verify_alexa_request

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ──

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    session_id: Optional[str] = None
    is_alexa: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: str


class MemoryRequest(BaseModel):
    key: str
    value: str
    category: str = "general"
    user_id: str = "default"


class ReminderRequest(BaseModel):
    title: str
    due_at: Optional[str] = None
    description: str = ""
    user_id: str = "default"


# ── Health ──

@router.get("/health")
async def health():
    settings = get_settings()
    groq = GroqProvider()
    return {
        "status": "online",
        "app": settings.app_name,
        "version": settings.app_version,
        "groq_configured": groq.is_available,
        "model": settings.groq_model,
    }


# ── Chat ──

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    agent = JarvisAgent(
        user_id=request.user_id,
        session_id=request.session_id,
        is_alexa=request.is_alexa,
    )
    response = agent.chat(request.message)
    return ChatResponse(response=response, session_id=agent.session_id)


# ── Model Info ──

@router.get("/models")
async def list_models():
    groq = GroqProvider()
    models = groq.list_models()
    return {"models": models, "current": get_settings().groq_model}


@router.get("/models/check")
async def check_model(model_id: Optional[str] = None):
    groq = GroqProvider()
    return groq.check_model(model_id)


# ── Memory ──

@router.get("/memories")
async def list_memories(user_id: str = "default", category: Optional[str] = None):
    mgr = MemoryManager(user_id)
    return {"memories": mgr.recall(category)}


@router.post("/memories")
async def save_memory(request: MemoryRequest):
    mgr = MemoryManager(request.user_id)
    result = mgr.save(request.key, request.value, request.category)
    return result


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: int, user_id: str = "default"):
    mgr = MemoryManager(user_id)
    if not mgr.delete(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted"}


@router.delete("/memories")
async def clear_memories(user_id: str = "default"):
    mgr = MemoryManager(user_id)
    count = mgr.clear_all()
    return {"status": "cleared", "count": count}


# ── Reminders ──

@router.get("/reminders")
async def list_reminders(user_id: str = "default", include_done: bool = False):
    mgr = ReminderManager(user_id)
    return {"reminders": mgr.list_active(include_done)}


@router.post("/reminders")
async def create_reminder(request: ReminderRequest):
    from datetime import datetime
    mgr = ReminderManager(request.user_id)
    due = datetime.fromisoformat(request.due_at) if request.due_at else None
    result = mgr.create(request.title, due, request.description)
    return result


@router.put("/reminders/{reminder_id}/complete")
async def complete_reminder(reminder_id: int, user_id: str = "default"):
    mgr = ReminderManager(user_id)
    if not mgr.complete(reminder_id):
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "completed"}


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int, user_id: str = "default"):
    mgr = ReminderManager(user_id)
    if not mgr.delete(reminder_id):
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "deleted"}


# ── Conversation History ──

@router.get("/history")
async def get_history(user_id: str = "default", session_id: Optional[str] = None):
    if not session_id:
        return {"messages": [], "note": "Provide a session_id to retrieve history."}
    agent = JarvisAgent(user_id=user_id, session_id=session_id)
    return {"messages": agent.get_history(), "session_id": session_id}


# ── Alexa Skill Webhook ──

@router.post("/alexa")
async def alexa_webhook(request: Request):
    raw_body = await request.body()
    headers = dict(request.headers)
    is_valid, reason = verify_alexa_request(raw_body, headers)
    if not is_valid:
        logger.warning(f"Alexa verification failed: {reason}")
        raise HTTPException(status_code=400, detail=f"Invalid Alexa Request: {reason}")
    payload = await request.json()
    return handle_alexa_request(payload)
