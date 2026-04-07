from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = PROJECT_ROOT.parent
WORKSPACE_ROOT = SKILLS_ROOT.parent
CONFIG_ROOT = Path(os.environ.get("BIO_DIGEST_CONFIG_ROOT", str(PROJECT_ROOT / "bio-literature-config"))).resolve()
WEB_CONFIG_DIR = CONFIG_ROOT / "web"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(WEB_CONFIG_DIR / "backend.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Bio Literature Digest Web"
    api_prefix: str = "/api"
    frontend_origin: str = "http://127.0.0.1:8601"
    database_url: str = "sqlite:///./bio_digest_web.db"
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
    access_trace_dir: str = str(WEB_CONFIG_DIR / "access-traces")
    review_export_dir: str = str(WEB_CONFIG_DIR / "review-tables")
    producer_root: str = str(SKILLS_ROOT / "bio-literature-digest")
    producer_rules_path: str = str(SKILLS_ROOT / "bio-literature-digest" / "references" / "category_rules.yaml")
    producer_review_template_path: str = str(SKILLS_ROOT / "bio-literature-digest" / "assets" / "email_template.html")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
