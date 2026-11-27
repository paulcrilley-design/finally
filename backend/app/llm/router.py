"""POST /api/chat."""

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user

from .schemas import ChatRequest
from .service import handle_chat


def create_chat_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat")
    async def chat(
        body: ChatRequest, request: Request, user_id: str = Depends(get_current_user)
    ) -> dict:
        return await handle_chat(request.app.state, user_id, body.message)

    return router
