"""REST API cho CBD Chat (Conversation-Based Development)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db

router = APIRouter()

# In-memory sessions (production: dùng Redis)
_sessions: dict[str, "SessionData"] = {}


class SessionData:
    def __init__(self, session_id: str):
        self.session_id = session_id
        from backend.automation.cbd_agent import CBDSession

        self.cbd_session = CBDSession()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Gửi tin nhắn tới CBD Agent."""
    import uuid

    if not req.session_id or req.session_id not in _sessions:
        session_id = req.session_id or str(uuid.uuid4())
        _sessions[session_id] = SessionData(session_id)
    else:
        session_id = req.session_id

    session_data = _sessions[session_id]
    session_data.cbd_session.db = db

    from backend.automation.cbd_agent import CBDAgent

    agent = CBDAgent(db)

    try:
        reply = await agent.chat(session_data.cbd_session, req.message)
    except Exception as e:
        raise HTTPException(500, f"Agent lỗi: {str(e)}")

    return ChatResponse(reply=reply, session_id=session_id)


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """Xoá session hội thoại."""
    _sessions.pop(session_id, None)
    return {"cleared": True}


@router.get("/sessions")
async def list_sessions():
    """Liệt kê sessions đang hoạt động."""
    return {
        "sessions": [
            {
                "session_id": sid,
                "message_count": len(data.cbd_session.history),
            }
            for sid, data in _sessions.items()
        ]
    }
