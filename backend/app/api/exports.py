from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import ExportJob, User
from ..schemas import ExportJobRead, ExportRequest
from ..services.exports import create_export_job, csv_from_rows, fetch_favorites_for_export, fetch_papers_for_export, papers_to_rows

router = APIRouter(prefix="/exports", tags=["exports"])


def serialize_job(job: ExportJob) -> ExportJobRead:
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
    db: Session = Depends(get_db),
) -> ExportJobRead:
    papers = fetch_papers_for_export(db, payload.date)
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
    content = csv_from_rows(papers_to_rows(papers), columns)
    job = create_export_job(
        db,
        requested_by=current_user,
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
    db: Session = Depends(get_db),
) -> ExportJobRead:
    papers = fetch_papers_for_export(db, payload.date)
    dois = sorted({paper.doi for paper in papers if paper.doi})
    job = create_export_job(
        db,
        requested_by=current_user,
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
    db: Session = Depends(get_db),
) -> ExportJobRead:
    if not payload.columns:
        raise HTTPException(status_code=400, detail="Custom export requires at least one column mapping")
    papers = fetch_papers_for_export(db, payload.date)
    rows = papers_to_rows(papers)
    columns = [(column.source, column.label) for column in payload.columns]
    content = csv_from_rows(rows, columns)
    job = create_export_job(
        db,
        requested_by=current_user,
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
    db: Session = Depends(get_db),
):
    job = db.get(ExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    if current_user.role != "admin" and job.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this export")
    if download:
        return Response(
            content=job.content_text,
            media_type=job.content_type,
            headers={"Content-Disposition": f'attachment; filename="{job.output_name}"'},
        )
    return serialize_job(job)
