"""POST /api/chat and GET /api/chat/history."""

from fastapi import APIRouter, Depends, Request

import db
from app.dependencies import get_current_user

from .schemas import ChatRequest
from .service import handle_chat

DISPLAY_LIMIT = 50


def create_chat_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat")
    async def chat(
        body: ChatRequest, request: Request, user_id: str = Depends(get_current_user)
    ) -> dict:
        return await handle_chat(request.app.state, user_id, body.message)

    @router.get("/chat/history")
    def history(user_id: str = Depends(get_current_user)) -> dict:
        return {"messages": db.list_chat_messages(user_id, limit=DISPLAY_LIMIT)}

    return router
