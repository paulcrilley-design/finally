"""Portfolio and trade endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

import db
from app.dependencies import get_current_user
from app.services import portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

User = Annotated[str, Depends(get_current_user)]


class TradeRequest(BaseModel):
    ticker: str
    side: str
    quantity: float | None = None  # shares
    amount: float | None = None  # US dollars; give exactly one of the two


@router.get("")
async def read_portfolio(request: Request, user_id: User) -> dict:
    return portfolio.get_portfolio(request.app.state, user_id)


@router.post("/trade")
async def trade(body: TradeRequest, request: Request, user_id: User) -> dict:
    return await portfolio.execute_trade(
        request.app.state, user_id, body.ticker, body.side, body.quantity, body.amount
    )


@router.get("/history")
async def history(user_id: User) -> dict:
    return {"history": db.list_snapshots(user_id)}
