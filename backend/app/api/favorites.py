from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db, get_shared_db
from ..models import User
from ..schemas import FavoriteCreate, FavoriteRead, FavoriteReviewOptions, FavoriteReviewUpdate
from ..services.favorite_review_exports import get_review_options, normalize_favorite_review_payload
from ..services.user_visibility import require_visible_target_user
from ..shared_models import SharedActionLog, SharedActor, SharedActorFavorite, SharedLiteratureItem

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


def ensure_shared_actor(shared_db: Session, user: User) -> SharedActor:
    actor_key = user.email.lower()
    actor = shared_db.scalar(select(SharedActor).where(SharedActor.actor_key == actor_key))
    if actor is None:
        actor = SharedActor(actor_key=actor_key, email=actor_key, display_name=user.name)
        shared_db.add(actor)
        shared_db.flush()
    else:
        actor.email = actor_key
        actor.display_name = user.name
    return actor


def record_shared_action(
    shared_db: Session,
    *,
    actor: SharedActor,
    action_type: str,
    entity_type: str,
    entity_id: Optional[int],
    detail: dict,
) -> None:
    shared_db.add(
        SharedActionLog(
            actor_id=actor.id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            detail_json=detail,
        )
    )


def serialize_favorite(favorite: SharedActorFavorite) -> FavoriteRead:
    first_entry = min(
        (entry.digest_date for entry in favorite.item.memberships if entry.list_type == "digest"),
        default=None,
    )
    return FavoriteRead(
        id=favorite.id,
        user_id=0,
        paper_id=favorite.item_id,
        digest_date=str(first_entry) if first_entry else None,
        doi=favorite.item.doi,
        journal=favorite.item.journal,
        publish_date=favorite.item.publish_date,
        category=favorite.item.category,
        interest_level=favorite.item.interest_level,
        interest_tag=favorite.item.interest_tag,
        title_en=favorite.item.title_en,
        title_zh=favorite.item.title_zh,
        article_url=favorite.item.article_url,
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
    shared_db: Session = Depends(get_shared_db),
) -> list[FavoriteRead]:
    target_user = resolve_target_user(current_user, user_id, db)
    actor = ensure_shared_actor(shared_db, target_user)
    statement = (
        select(SharedActorFavorite)
        .options(joinedload(SharedActorFavorite.item).joinedload(SharedLiteratureItem.memberships))
        .where(SharedActorFavorite.actor_id == actor.id)
        .order_by(SharedActorFavorite.favorited_at.desc())
    )
    items = list(shared_db.execute(statement).unique().scalars())
    items.sort(key=lambda favorite: favorite.review_updated_at or favorite.favorited_at, reverse=True)
    rows = [serialize_favorite(favorite) for favorite in items]
    for row in rows:
        row.user_id = target_user.id
    return rows


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    shared_db: Session = Depends(get_shared_db),
) -> FavoriteRead:
    target_user = resolve_target_user(current_user, payload.user_id, db)
    actor = ensure_shared_actor(shared_db, target_user)
    item = shared_db.get(SharedLiteratureItem, payload.paper_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    existing = shared_db.scalar(
        select(SharedActorFavorite).where(
            SharedActorFavorite.actor_id == actor.id,
            SharedActorFavorite.item_id == item.id,
        )
    )
    if existing:
        favorite = shared_db.execute(
            select(SharedActorFavorite)
            .options(joinedload(SharedActorFavorite.item).joinedload(SharedLiteratureItem.memberships))
            .where(SharedActorFavorite.id == existing.id)
        ).unique().scalar_one()
        row = serialize_favorite(favorite)
        row.user_id = target_user.id
        return row
    favorite = SharedActorFavorite(actor_id=actor.id, item_id=item.id)
    shared_db.add(favorite)
    record_shared_action(
        shared_db,
        actor=actor,
        action_type="favorite_add",
        entity_type="paper",
        entity_id=item.id,
        detail={"canonical_key": item.canonical_key, "target_user_id": target_user.id},
    )
    shared_db.commit()
    favorite = shared_db.execute(
        select(SharedActorFavorite)
        .options(joinedload(SharedActorFavorite.item).joinedload(SharedLiteratureItem.memberships))
        .where(SharedActorFavorite.id == favorite.id)
    ).unique().scalar_one()
    row = serialize_favorite(favorite)
    row.user_id = target_user.id
    return row


@router.patch("/{paper_id}", response_model=FavoriteRead)
def update_favorite_review(
    paper_id: int,
    payload: FavoriteReviewUpdate,
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    shared_db: Session = Depends(get_shared_db),
) -> FavoriteRead:
    target_user = resolve_target_user(current_user, user_id, db)
    actor = ensure_shared_actor(shared_db, target_user)
    favorite = shared_db.execute(
        select(SharedActorFavorite)
        .options(joinedload(SharedActorFavorite.item).joinedload(SharedLiteratureItem.memberships))
        .where(
            SharedActorFavorite.actor_id == actor.id,
            SharedActorFavorite.item_id == paper_id,
        )
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
    record_shared_action(
        shared_db,
        actor=actor,
        action_type="favorite_review_update",
        entity_type="paper",
        entity_id=favorite.item_id,
        detail={
            "review_interest_level": favorite.review_interest_level,
            "review_interest_tag": favorite.review_interest_tag,
            "review_final_decision": favorite.review_final_decision,
            "review_final_category": favorite.review_final_category,
            "has_notes": bool(favorite.reviewer_notes),
            "target_user_id": target_user.id,
        },
    )
    shared_db.commit()
    row = serialize_favorite(favorite)
    row.user_id = target_user.id
    return row


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    paper_id: int,
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    shared_db: Session = Depends(get_shared_db),
) -> None:
    target_user = resolve_target_user(current_user, user_id, db)
    actor = ensure_shared_actor(shared_db, target_user)
    favorite = shared_db.scalar(
        select(SharedActorFavorite).where(
            SharedActorFavorite.actor_id == actor.id,
            SharedActorFavorite.item_id == paper_id,
        )
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    record_shared_action(
        shared_db,
        actor=actor,
        action_type="favorite_remove",
        entity_type="paper",
        entity_id=favorite.item_id,
        detail={"target_user_id": target_user.id},
    )
    shared_db.delete(favorite)
    shared_db.commit()
