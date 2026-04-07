from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..models import Favorite, Paper, User
from ..schemas import FavoriteCreate, FavoriteRead, FavoriteReviewOptions, FavoriteReviewUpdate
from ..services.audit import record_action
from ..services.favorite_review_exports import get_review_options, normalize_favorite_review_payload
from ..services.user_visibility import require_visible_target_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


def resolve_target_user_id(current_user: User, requested_user_id: Optional[int]) -> int:
    if requested_user_id is None or requested_user_id == current_user.id:
        return current_user.id
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other users' favorites")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Target user must be resolved with database context")


def resolve_target_user(current_user: User, requested_user_id: Optional[int], db: Session) -> User:
    if requested_user_id is None or requested_user_id == current_user.id:
        return current_user
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other users' favorites")
    return require_visible_target_user(db, current_user, requested_user_id)


def serialize_favorite(favorite: Favorite) -> FavoriteRead:
    first_entry = min((entry.digest_date for entry in favorite.paper.daily_entries), default=None)
    return FavoriteRead(
        id=favorite.id,
        user_id=favorite.user_id,
        paper_id=favorite.paper_id,
        digest_date=str(first_entry) if first_entry else None,
        doi=favorite.paper.doi,
        journal=favorite.paper.journal,
        publish_date=favorite.paper.publish_date,
        category=favorite.paper.category,
        interest_level=favorite.paper.interest_level,
        interest_tag=favorite.paper.interest_tag,
        title_en=favorite.paper.title_en,
        title_zh=favorite.paper.title_zh,
        article_url=favorite.paper.article_url,
        favorited_at=favorite.favorited_at,
        review_interest_level=favorite.review_interest_level,
        review_interest_tag=favorite.review_interest_tag,
        review_final_decision=favorite.review_final_decision,
        review_final_category=favorite.review_final_category,
        reviewer_notes=favorite.reviewer_notes,
        review_updated_at=favorite.review_updated_at,
    )


@router.get("/review-options", response_model=FavoriteReviewOptions)
def favorite_review_options(current_user: User = Depends(get_current_user)) -> FavoriteReviewOptions:
    _ = current_user
    return FavoriteReviewOptions(**get_review_options())


@router.get("", response_model=list[FavoriteRead])
def list_favorites(
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FavoriteRead]:
    target_user = resolve_target_user(current_user, user_id, db)
    statement = (
        select(Favorite)
        .options(joinedload(Favorite.paper).joinedload(Paper.daily_entries))
        .where(Favorite.user_id == target_user.id)
        .order_by(Favorite.favorited_at.desc())
    )
    items = list(db.execute(statement).unique().scalars())
    items.sort(key=lambda favorite: favorite.review_updated_at or favorite.favorited_at, reverse=True)
    return [serialize_favorite(favorite) for favorite in items]


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteRead:
    target_user = resolve_target_user(current_user, payload.user_id, db)
    paper = db.get(Paper, payload.paper_id)
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    existing = db.scalar(select(Favorite).where(Favorite.user_id == target_user.id, Favorite.paper_id == paper.id))
    if existing:
        favorite = db.execute(
            select(Favorite)
            .options(joinedload(Favorite.paper).joinedload(Paper.daily_entries))
            .where(Favorite.id == existing.id)
        ).unique().scalar_one()
        return serialize_favorite(favorite)
    favorite = Favorite(user_id=target_user.id, paper_id=paper.id)
    db.add(favorite)
    record_action(
        db,
        action_type="favorite_add",
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        entity_type="paper",
        entity_id=paper.id,
        detail={"canonical_key": paper.canonical_key},
    )
    db.commit()
    favorite = db.execute(
        select(Favorite)
        .options(joinedload(Favorite.paper).joinedload(Paper.daily_entries))
        .where(Favorite.id == favorite.id)
    ).unique().scalar_one()
    return serialize_favorite(favorite)


@router.patch("/{paper_id}", response_model=FavoriteRead)
def update_favorite_review(
    paper_id: int,
    payload: FavoriteReviewUpdate,
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteRead:
    target_user = resolve_target_user(current_user, user_id, db)
    favorite = db.execute(
        select(Favorite)
        .options(joinedload(Favorite.paper).joinedload(Paper.daily_entries))
        .where(Favorite.user_id == target_user.id, Favorite.paper_id == paper_id)
    ).unique().scalar_one_or_none()
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    normalized = normalize_favorite_review_payload(
        favorite,
        review_interest_level=payload.review_interest_level,
        review_interest_tag=payload.review_interest_tag,
        review_final_decision=payload.review_final_decision,
        review_final_category=payload.review_final_category,
        reviewer_notes=payload.reviewer_notes,
    )
    favorite.review_interest_level = normalized["review_interest_level"]
    favorite.review_interest_tag = normalized["review_interest_tag"]
    favorite.review_final_decision = normalized["review_final_decision"]
    favorite.review_final_category = normalized["review_final_category"]
    favorite.reviewer_notes = normalized["reviewer_notes"]
    favorite.review_updated_at = datetime.utcnow() if any(normalized.values()) else None
    record_action(
        db,
        action_type="favorite_review_update",
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        entity_type="paper",
        entity_id=favorite.paper_id,
        detail={
            "review_interest_level": favorite.review_interest_level,
            "review_interest_tag": favorite.review_interest_tag,
            "review_final_decision": favorite.review_final_decision,
            "review_final_category": favorite.review_final_category,
            "has_notes": bool(favorite.reviewer_notes),
        },
    )
    db.commit()
    return serialize_favorite(favorite)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    paper_id: int,
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    target_user = resolve_target_user(current_user, user_id, db)
    favorite = db.scalar(select(Favorite).where(Favorite.user_id == target_user.id, Favorite.paper_id == paper_id))
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    record_action(
        db,
        action_type="favorite_remove",
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        entity_type="paper",
        entity_id=favorite.paper_id,
        detail={},
    )
    db.delete(favorite)
    db.commit()
