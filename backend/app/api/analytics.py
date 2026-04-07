from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import AnalyticsEdgeRead, AnalyticsNodeRead, AnalyticsResponse, TrendPoint
from ..services.analytics import build_cns_trends, build_global_snapshot, build_user_snapshot
from ..services.user_visibility import require_visible_target_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


def default_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def serialize_snapshot(snapshot) -> AnalyticsResponse:
    return AnalyticsResponse(
        scope_type=snapshot.scope_type,
        period=snapshot.period,
        month=snapshot.month,
        total_papers=snapshot.total_papers,
        nodes=[AnalyticsNodeRead(key=node.node_key, label=node.label, weight=node.weight) for node in snapshot.nodes],
        edges=[AnalyticsEdgeRead(source=edge.source_key, target=edge.target_key, weight=edge.weight) for edge in snapshot.edges],
        series=[TrendPoint(**point) for point in snapshot.payload_json.get("series", [])],
        summary=snapshot.payload_json.get("summary", {}),
    )


@router.get("/global", response_model=AnalyticsResponse)
def global_analytics(
    period: str = "weekly",
    month: Optional[str] = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    return serialize_snapshot(build_global_snapshot(db, period=period, month=month or default_month()))


@router.get("/cns-trends", response_model=list[TrendPoint])
def cns_trends(months: int = 12, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TrendPoint]:
    return [TrendPoint(**row) for row in build_cns_trends(db, months)]


@router.get("/users/{user_id}/favorites", response_model=AnalyticsResponse)
def user_favorite_analytics(
    user_id: int,
    period: str = "weekly",
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot access other users analytics")
    if current_user.role == "admin" and current_user.id != user_id:
        require_visible_target_user(db, current_user, user_id)
    return serialize_snapshot(build_user_snapshot(db, user_id=user_id, period=period, month=month or default_month()))
