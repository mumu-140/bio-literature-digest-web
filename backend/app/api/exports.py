from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_shared_db
from ..models import User
from ..schemas import ExportJobRead, ExportRequest
from ..services.exports import create_export_job, csv_from_rows, fetch_items_for_export, items_to_rows
from ..shared_models import SharedActor, SharedExportJob

router = APIRouter(prefix="/exports", tags=["exports"])


def resolve_actor(db: Session, user: User) -> SharedActor | None:
    return db.scalar(select(SharedActor).where(SharedActor.actor_key == user.email.lower()))


def serialize_job(job: SharedExportJob) -> ExportJobRead:
    return ExportJobRead(
        id=job.id,
        kind=job.kind,
        status=job.status,
        output_name=job.output_name,
        content_type=job.content_type,
        created_at=job.created_at,
        finished_at=job.finished_at,
        download_url=f"/api/exports/{job.id}?download=1",
    )


@router.post("/metadata", response_model=ExportJobRead)
def export_metadata(
    payload: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
) -> ExportJobRead:
    items = fetch_items_for_export(db, payload.date)
    columns = [
        ("id", "id"),
        ("doi", "doi"),
        ("journal", "journal"),
        ("publish_date", "publish_date"),
        ("category", "category"),
        ("interest_level", "interest_level"),
        ("interest_tag", "interest_tag"),
        ("title_en", "title_en"),
        ("title_zh", "title_zh"),
        ("summary_zh", "summary_zh"),
        ("abstract", "abstract"),
        ("article_url", "article_url"),
        ("tags", "tags"),
    ]
    content = csv_from_rows(items_to_rows(items), columns)
    actor = resolve_actor(db, current_user)
    job = create_export_job(
        db,
        actor=actor,
        requested_by_key=current_user.email.lower(),
        kind="metadata",
        output_name="metadata.csv",
        content_type="text/csv",
        content_text=content,
        params=payload.model_dump(),
    )
    return serialize_job(job)


@router.post("/doi-list", response_model=ExportJobRead)
def export_doi_list(
    payload: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
) -> ExportJobRead:
    items = fetch_items_for_export(db, payload.date)
    dois = sorted({item.doi for item in items if item.doi})
    actor = resolve_actor(db, current_user)
    job = create_export_job(
        db,
        actor=actor,
        requested_by_key=current_user.email.lower(),
        kind="doi-list",
        output_name="doi-list.txt",
        content_type="text/plain",
        content_text="\n".join(dois) + ("\n" if dois else ""),
        params=payload.model_dump(),
    )
    return serialize_job(job)


@router.post("/custom-table", response_model=ExportJobRead)
def export_custom_table(
    payload: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
) -> ExportJobRead:
    if not payload.columns:
        raise HTTPException(status_code=400, detail="Custom export requires at least one column mapping")
    items = fetch_items_for_export(db, payload.date)
    rows = items_to_rows(items)
    columns = [(column.source, column.label) for column in payload.columns]
    content = csv_from_rows(rows, columns)
    actor = resolve_actor(db, current_user)
    job = create_export_job(
        db,
        actor=actor,
        requested_by_key=current_user.email.lower(),
        kind="custom-table",
        output_name="custom-table.csv",
        content_type="text/csv",
        content_text=content,
        params=payload.model_dump(),
    )
    return serialize_job(job)


@router.get("/{job_id}", response_model=ExportJobRead)
def get_export_job(
    job_id: int,
    download: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    job = db.get(SharedExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    if current_user.role != "admin" and job.requested_by_key != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Cannot access this export")
    if download:
        return Response(
            content=job.content_text,
            media_type=job.content_type,
            headers={"Content-Disposition": f'attachment; filename="{job.output_name}"'},
        )
    return serialize_job(job)
