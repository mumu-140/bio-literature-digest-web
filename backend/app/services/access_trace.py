from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Request

from ..config import get_settings
from ..models import User


def _safe_segment(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return normalized.strip("._") or "unknown"


def _trace_directory_for_user(user: User) -> Path:
    settings = get_settings()
    root = Path(settings.access_trace_dir)
    user_dir_name = f"user-{user.id:04d}_{_safe_segment(user.email)}"
    return root / user_dir_name


def _request_ip_bundle(request: Request) -> dict[str, object]:
    x_forwarded_for = [item.strip() for item in request.headers.get("x-forwarded-for", "").split(",") if item.strip()]
    return {
        "request_client_ip": request.client.host if request.client else "",
        "cf_connecting_ip": request.headers.get("cf-connecting-ip", ""),
        "x_real_ip": request.headers.get("x-real-ip", ""),
        "x_forwarded_for": x_forwarded_for,
    }


def _request_location_bundle(request: Request) -> dict[str, object]:
    return {
        "country_code": request.headers.get("cf-ipcountry", ""),
        "region": request.headers.get("cf-region", ""),
        "region_code": request.headers.get("cf-region-code", ""),
        "city": request.headers.get("cf-city", ""),
        "postal_code": request.headers.get("cf-postal-code", ""),
        "metro_code": request.headers.get("cf-metro-code", ""),
        "timezone": request.headers.get("cf-timezone", "") or request.headers.get("x-browser-timezone", ""),
        "browser_language": request.headers.get("x-browser-language", ""),
        "browser_platform": request.headers.get("sec-ch-ua-platform", ""),
        "browser_mobile": request.headers.get("sec-ch-ua-mobile", ""),
        "latitude": request.headers.get("cf-latitude", ""),
        "longitude": request.headers.get("cf-longitude", ""),
    }


def write_access_trace(*, user: User, request: Request, event_type: str) -> Path:
    trace_dir = _trace_directory_for_user(user)
    trace_dir.mkdir(parents=True, exist_ok=True)

    captured_at = datetime.now(timezone.utc)
    trace_payload = {
        "captured_at_utc": captured_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
        "request": {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query or ""),
            "host": request.headers.get("host", ""),
            "origin": request.headers.get("origin", ""),
            "referer": request.headers.get("referer", ""),
            "user_agent": request.headers.get("user-agent", ""),
            "accept_language": request.headers.get("accept-language", ""),
            "cf_ray": request.headers.get("cf-ray", ""),
            "cf_visitor": request.headers.get("cf-visitor", ""),
            "ip": _request_ip_bundle(request),
            "location": _request_location_bundle(request),
        },
    }

    filename = f"{captured_at.strftime('%Y%m%dT%H%M%SZ')}_{event_type}_{uuid4().hex}.json"
    output_path = trace_dir / filename
    output_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
