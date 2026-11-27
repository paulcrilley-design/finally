"""Watchlist endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services import watchlist

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

User = Annotated[str, Depends(get_current_user)]


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("")
async def read_watchlist(request: Request, user_id: User) -> dict:
    return watchlist.get_watchlist(request.app.state, user_id)


@router.post("", status_code=201)
async def add(body: AddTickerRequest, request: Request, user_id: User) -> dict:
    return await watchlist.add_ticker(request.app.state, user_id, body.ticker)


@router.delete("/{ticker}", status_code=204)
async def remove(ticker: str, request: Request, user_id: User) -> Response:
    await watchlist.remove_ticker(request.app.state, user_id, ticker)
    return Response(status_code=204)
