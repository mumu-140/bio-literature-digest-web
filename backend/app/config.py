from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from instance_paths import get_instance_paths


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    app_name: str = "Bio Literature Digest Web"
    api_prefix: str = "/api"
    frontend_origin: str = "http://127.0.0.1:18001"
    session_cookie_name: str = "bio_digest_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 24 * 14
    session_secret: str = "change-me"
    cst_timezone: str = "Asia/Shanghai"
    web_base_url: str = "http://127.0.0.1:18001"
    initial_admin_email: str = "admin@example.com"
    initial_admin_name: str = "Admin"
    bootstrap_admin: bool = True
    page_size_default: int = 25
    page_size_max: int = 200
    export_inline_limit: int = Field(default=5000)
    data_retention_days: int = Field(default=30, ge=1)
    producer_sync_enabled: bool = True
    database_url: str = "sqlite:///./bio_digest_web.db"
    access_trace_dir: str = "access-traces"
    review_export_dir: str = "review-tables"
    producer_root: str = ""
    producer_rules_path: str = ""
    producer_review_template_path: str = ""


def _resolve_path(raw_value: str, *, base_dir: Path) -> str:
    if not raw_value:
        return str(base_dir.resolve())
    path = Path(raw_value)
    if path.is_absolute():
        return str(path.resolve())
    return str((base_dir / path).resolve())


def _resolve_existing_path(raw_value: str, *, base_dir: Path, fallbacks: list[str]) -> str:
    candidates = [raw_value, *fallbacks] if raw_value else list(fallbacks)
    for candidate in candidates:
        resolved = Path(_resolve_path(candidate, base_dir=base_dir))
        if resolved.exists():
            return str(resolved)
    primary = raw_value or (fallbacks[0] if fallbacks else "")
    return _resolve_path(primary, base_dir=base_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    paths = get_instance_paths(PROJECT_ROOT)
    settings = Settings(
        _env_file=str(paths.backend_env_file),
        _env_file_encoding="utf-8",
    )
    if settings.database_url.startswith("sqlite:///./"):
        relative_path = settings.database_url.removeprefix("sqlite:///./")
        settings.database_url = f"sqlite:///{(paths.web_data_dir / relative_path).resolve()}"
    settings.access_trace_dir = _resolve_path(settings.access_trace_dir, base_dir=paths.web_data_dir)
    settings.review_export_dir = _resolve_path(settings.review_export_dir, base_dir=paths.web_data_dir)
    settings.producer_root = _resolve_path(settings.producer_root, base_dir=paths.producer_root)
    producer_root = Path(settings.producer_root)
    settings.producer_rules_path = _resolve_existing_path(
        settings.producer_rules_path,
        base_dir=producer_root,
        fallbacks=[
            "references/category_rules.yaml",
            "config/content/category_rules.yaml",
        ],
    )
    settings.producer_review_template_path = _resolve_path(
        settings.producer_review_template_path or "assets/email_template.html",
        base_dir=producer_root,
    )
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
