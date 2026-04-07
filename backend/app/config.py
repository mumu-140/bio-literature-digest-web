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

INSTANCE_PATHS = get_instance_paths(PROJECT_ROOT)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(INSTANCE_PATHS.backend_env_file),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Bio Literature Digest Web"
    api_prefix: str = "/api"
    frontend_origin: str = "http://127.0.0.1:8601"
    session_cookie_name: str = "bio_digest_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 24 * 14
    session_secret: str = "change-me"
    email_login_ttl_hours: int = 24 * 7
    cst_timezone: str = "Asia/Shanghai"
    web_base_url: str = "http://127.0.0.1:8601"
    initial_admin_email: str = "admin@example.com"
    initial_admin_password: str = "change-before-prod"
    initial_admin_name: str = "Admin"
    bootstrap_admin: bool = True
    page_size_default: int = 25
    page_size_max: int = 200
    export_inline_limit: int = Field(default=5000)
    data_retention_days: int = Field(default=30, ge=1)
    database_url: str = f"sqlite:///{INSTANCE_PATHS.database_file}"
    access_trace_dir: str = str(INSTANCE_PATHS.access_trace_dir)
    review_export_dir: str = str(INSTANCE_PATHS.review_export_dir)
    producer_root: str = str(INSTANCE_PATHS.producer_root)
    producer_rules_path: str = str(INSTANCE_PATHS.producer_root / "references" / "category_rules.yaml")
    producer_review_template_path: str = str(INSTANCE_PATHS.producer_root / "assets" / "email_template.html")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if settings.database_url.startswith("sqlite:///./"):
        relative_path = settings.database_url.removeprefix("sqlite:///./")
        settings.database_url = f"sqlite:///{(INSTANCE_PATHS.web_data_dir / relative_path).resolve()}"
    for field_name, base_dir in (
        ("access_trace_dir", INSTANCE_PATHS.web_data_dir),
        ("review_export_dir", INSTANCE_PATHS.web_data_dir),
        ("producer_root", PROJECT_ROOT),
        ("producer_rules_path", PROJECT_ROOT),
        ("producer_review_template_path", PROJECT_ROOT),
    ):
        raw_value = getattr(settings, field_name)
        if not Path(raw_value).is_absolute():
            setattr(settings, field_name, str((base_dir / raw_value).resolve()))
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
