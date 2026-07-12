from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..models import ImportedLiteratureItem, User, UserLiteratureFavorite, UserManualReview
from ..schemas import FavoriteCreate, FavoriteRead, FavoriteReviewOptions, FavoriteReviewUpdate
from ..services.audit import record_action
from ..services.favorite_review_exports import get_review_options, normalize_favorite_review_payload
from ..services.user_visibility import require_visible_target_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


def resolve_target_user(current_user: User, requested_user_id: Optional[int], db: Session) -> User:
    if requested_user_id is None or requested_user_id == current_user.id:
        return current_user
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other users' favorites")
    return require_visible_target_user(db, current_user, requested_user_id)


def _review_map(db: Session, *, user_id: int, keys: list[str]) -> dict[str, UserManualReview]:
    if not keys:
        return {}
    reviews = list(
        db.scalars(
            select(UserManualReview).where(
                UserManualReview.user_id == user_id,
                UserManualReview.literature_item_key.in_(keys),
            )
        )
    )
    return {review.literature_item_key: review for review in reviews}


def _serialize_favorite(
    favorite: UserLiteratureFavorite,
    *,
    review: UserManualReview | None,
) -> FavoriteRead:
    item = favorite.literature_item
    if item is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Favorite item missing local content")
    first_entry = min(
        (entry.digest_date for entry in item.memberships if entry.list_type == "digest"),
        default=None,
    )
    return FavoriteRead(
        id=favorite.id,
        user_id=favorite.user_id,
        paper_id=item.id,
        canonical_key=item.literature_item_key,
        digest_date=str(first_entry) if first_entry else None,
        doi=item.doi,
        journal=item.journal,
        publish_date=item.publish_date,
        category=item.category,
        interest_level=item.interest_level,
        interest_tag=item.interest_tag,
        title_en=item.title_en,
        title_zh=item.title_zh,
        article_url=item.article_url,
        favorited_at=favorite.favorited_at,
        review_interest_level=review.review_interest_level if review else "",
        review_interest_tag=review.review_interest_tag if review else "",
        review_final_decision=review.review_final_decision if review else "",
        review_final_category=review.review_final_category if review else "",
        reviewer_notes=review.reviewer_notes if review else "",
        review_updated_at=review.review_updated_at if review else None,
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
    favorites = list(
        db.execute(
            select(UserLiteratureFavorite)
            .options(joinedload(UserLiteratureFavorite.literature_item).joinedload(ImportedLiteratureItem.memberships))
            .where(UserLiteratureFavorite.user_id == target_user.id)
            .order_by(UserLiteratureFavorite.favorited_at.desc())
        )
        .unique()
        .scalars()
    )
    review_by_key = _review_map(
        db,
        user_id=target_user.id,
        keys=[favorite.literature_item_key for favorite in favorites],
    )
    rows = [_serialize_favorite(favorite, review=review_by_key.get(favorite.literature_item_key)) for favorite in favorites]
    rows.sort(key=lambda row: row.review_updated_at or row.favorited_at, reverse=True)
    return rows


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteRead:
    target_user = resolve_target_user(current_user, payload.user_id, db)
    item = db.get(ImportedLiteratureItem, payload.paper_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    favorite = db.scalar(
        select(UserLiteratureFavorite).where(
            UserLiteratureFavorite.user_id == target_user.id,
            UserLiteratureFavorite.literature_item_key == item.literature_item_key,
        )
    )
    if favorite is None:
        favorite = UserLiteratureFavorite(
            user_id=target_user.id,
            literature_item_id=item.id,
            literature_item_key=item.literature_item_key,
        )
        db.add(favorite)
        record_action(
            db,
            action_type="favorite_add",
            actor_user_id=current_user.id,
            target_user_id=target_user.id,
            entity_type="paper",
            entity_id=item.id,
            detail={"canonical_key": item.literature_item_key},
        )
        db.commit()
        db.refresh(favorite)
    else:
        favorite.literature_item_id = item.id
        db.commit()
    favorite = db.scalar(
        select(UserLiteratureFavorite)
        .options(joinedload(UserLiteratureFavorite.literature_item).joinedload(ImportedLiteratureItem.memberships))
        .where(UserLiteratureFavorite.id == favorite.id)
    )
    review = db.scalar(
        select(UserManualReview).where(
            UserManualReview.user_id == target_user.id,
            UserManualReview.literature_item_key == item.literature_item_key,
        )
    )
    return _serialize_favorite(favorite, review=review)


@router.patch("/{paper_id}", response_model=FavoriteRead)
def update_favorite_review(
    paper_id: int,
    payload: FavoriteReviewUpdate,
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteRead:
    target_user = resolve_target_user(current_user, user_id, db)
    item = db.get(ImportedLiteratureItem, paper_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    favorite = db.scalar(
        select(UserLiteratureFavorite)
        .options(joinedload(UserLiteratureFavorite.literature_item).joinedload(ImportedLiteratureItem.memberships))
        .where(
            UserLiteratureFavorite.user_id == target_user.id,
            UserLiteratureFavorite.literature_item_key == item.literature_item_key,
        )
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    review = db.scalar(
        select(UserManualReview).where(
            UserManualReview.user_id == target_user.id,
            UserManualReview.literature_item_key == item.literature_item_key,
        )
    )
    normalized = normalize_favorite_review_payload(
        item,
        review_interest_level=payload.review_interest_level,
        review_interest_tag=payload.review_interest_tag,
        review_final_decision=payload.review_final_decision,
        review_final_category=payload.review_final_category,
        reviewer_notes=payload.reviewer_notes,
    )
    has_review = any(normalized.values())
    if review is None:
        review = UserManualReview(
            user_id=target_user.id,
            literature_item_id=item.id,
            literature_item_key=item.literature_item_key,
        )
        db.add(review)
        db.flush()
    review.literature_item_id = item.id
    review.review_interest_level = normalized["review_interest_level"]
    review.review_interest_tag = normalized["review_interest_tag"]
    review.review_final_decision = normalized["review_final_decision"]
    review.review_final_category = normalized["review_final_category"]
    review.reviewer_notes = normalized["reviewer_notes"]
    review.review_updated_at = datetime.utcnow() if has_review else None
    record_action(
        db,
        action_type="favorite_review_update",
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        entity_type="paper",
        entity_id=item.id,
        detail={
            "canonical_key": item.literature_item_key,
            "review_interest_level": review.review_interest_level,
            "review_interest_tag": review.review_interest_tag,
            "review_final_decision": review.review_final_decision,
            "review_final_category": review.review_final_category,
            "has_notes": bool(review.reviewer_notes),
        },
    )
    db.commit()
    db.refresh(favorite)
    db.refresh(review)
    return _serialize_favorite(favorite, review=review)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    paper_id: int,
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    target_user = resolve_target_user(current_user, user_id, db)
    item = db.get(ImportedLiteratureItem, paper_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    favorite = db.scalar(
        select(UserLiteratureFavorite).where(
            UserLiteratureFavorite.user_id == target_user.id,
            UserLiteratureFavorite.literature_item_key == item.literature_item_key,
        )
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    record_action(
        db,
        action_type="favorite_remove",
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        entity_type="paper",
        entity_id=item.id,
        detail={"canonical_key": item.literature_item_key},
    )
    db.delete(favorite)
    db.commit()
