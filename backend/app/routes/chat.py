"""The AI copilot conversation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.chat import chat_turn
from app.errors import ApiError
from app.identity import get_current_user
from app.llm import ModelError
from db import recent_messages

router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_MESSAGE = 1000
SHOWN = 50


class ChatRequest(BaseModel):
    message: str


@router.get("")
def history(request: Request, user_id: Annotated[str, Depends(get_current_user)]) -> dict:
    return {"messages": recent_messages(request.app.state.db_path, user_id, SHOWN)}


@router.post("")
async def send(
    body: ChatRequest,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    state = request.app.state
    question = body.message.strip()
    if not question or len(question) > MAX_MESSAGE:
        raise ApiError("invalid_message", f"Write between 1 and {MAX_MESSAGE:,} characters.")
    if user_id in state.chatting:  # one turn at a time, so actions cannot interleave
        raise ApiError("chat_busy", "Wait for the previous reply first.", 409)
    state.chatting.add(user_id)
    try:
        return {"messages": await chat_turn(state, user_id, question)}
    except ModelError as error:
        status = 503 if error.code in ("no_api_key", "bad_api_key") else 502
        raise ApiError(error.code, error.message, status) from error
    finally:
        state.chatting.discard(user_id)
