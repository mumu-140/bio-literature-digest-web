from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...api_v1_schemas import ReportArtifactCreate, ReportTaskCreate
from ...deps import get_db
from ...models import ApiClient, ApiReportArtifact, ApiReportTask
from ...services.api_auth import require_api_scopes
from ...services.api_support import find_idempotent, record_api_audit, save_idempotent

router = APIRouter(prefix="/report-tasks", tags=["api-v1-reports"])


def serialize_task(db: Session, task: ApiReportTask) -> dict:
    artifacts = list(db.scalars(select(ApiReportArtifact).where(ApiReportArtifact.task_id == task.id).order_by(ApiReportArtifact.id)))
    return {
        "id": task.public_id,
        "report_type": task.report_type,
        "status": task.status,
        "parameters": task.parameters_json,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "artifacts": [{
            "id": item.public_id,
            "format": item.format,
            "content": item.content,
            "metadata": item.metadata_json,
            "created_at": item.created_at.isoformat(),
        } for item in artifacts],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_report_task(
    payload: ReportTaskCreate,
    request: Request,
    response: Response,
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    client: ApiClient = Depends(require_api_scopes("reports:write")),
    db: Session = Depends(get_db),
) -> dict:
    body = payload.model_dump()
    existing = find_idempotent(db, client=client, request=request, key=idempotency_key, payload=body)
    if existing:
        response.status_code = status.HTTP_200_OK
        return existing.response_json
    task = ApiReportTask(
        public_id=str(uuid.uuid4()),
        report_type=payload.report_type,
        parameters_json=payload.parameters,
        requested_by_client_id=client.id,
    )
    db.add(task)
    db.flush()
    result = serialize_task(db, task)
    save_idempotent(db, client=client, request=request, key=idempotency_key, payload=body, response=result, status_code=201)
    record_api_audit(db, request=request, client=client, action="report_task.create", entity_type="report_task", entity_key=task.public_id)
    db.commit()
    return result


@router.get("/{task_id}")
def get_report_task(
    task_id: str,
    _: ApiClient = Depends(require_api_scopes("reports:write")),
    db: Session = Depends(get_db),
) -> dict:
    task = db.scalar(select(ApiReportTask).where(ApiReportTask.public_id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Report task not found")
    return serialize_task(db, task)


@router.post("/{task_id}/artifacts", status_code=status.HTTP_201_CREATED)
def create_artifact(
    task_id: str,
    payload: ReportArtifactCreate,
    request: Request,
    response: Response,
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    client: ApiClient = Depends(require_api_scopes("reports:write")),
    db: Session = Depends(get_db),
) -> dict:
    body = payload.model_dump()
    existing = find_idempotent(db, client=client, request=request, key=idempotency_key, payload=body)
    if existing:
        response.status_code = 200
        return existing.response_json
    task = db.scalar(select(ApiReportTask).where(ApiReportTask.public_id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Report task not found")
    artifact = ApiReportArtifact(
        public_id=str(uuid.uuid4()), task_id=task.id, format=payload.format,
        content=payload.content, metadata_json=payload.metadata,
    )
    db.add(artifact)
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.flush()
    result = {"id": artifact.public_id, "task_id": task.public_id, "format": artifact.format, "content": artifact.content, "metadata": artifact.metadata_json}
    save_idempotent(db, client=client, request=request, key=idempotency_key, payload=body, response=result, status_code=201)
    record_api_audit(db, request=request, client=client, action="report_artifact.create", entity_type="report_task", entity_key=task.public_id)
    db.commit()
    return result
