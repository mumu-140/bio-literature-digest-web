#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def read_env_pairs(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def resolve_configured_path(raw_value: str, *, project_root: Path, instance_root: Path) -> Path:
    if raw_value.startswith("@project/"):
        return (project_root / raw_value.removeprefix("@project/")).resolve()
    if raw_value.startswith("@instance/"):
        return (instance_root / raw_value.removeprefix("@instance/")).resolve()
    path = Path(raw_value)
    if path.is_absolute():
        return path.resolve()
    return (instance_root / path).resolve()


@dataclass(frozen=True)
class InstancePaths:
    project_root: Path
    instance_root: Path
    paths_file: Path
    web_env_dir: Path
    web_data_dir: Path
    web_runtime_dir: Path
    web_tunnel_dir: Path
    producer_env_dir: Path
    producer_root: Path
    producer_archive_dir: Path
    producer_email_config: Path

    @property
    def backend_env_file(self) -> Path:
        return self.web_env_dir / "backend.env.local"

    @property
    def backend_env_example_file(self) -> Path:
        return self.web_env_dir / "backend.env.local.example"

    @property
    def deploy_env_file(self) -> Path:
        return self.web_env_dir / "deploy.env.local"

    @property
    def deploy_env_example_file(self) -> Path:
        return self.web_env_dir / "deploy.env.local.example"

    @property
    def tunnel_config_file(self) -> Path:
        return self.web_tunnel_dir / "config.yml"

    @property
    def tunnel_config_example_file(self) -> Path:
        return self.web_tunnel_dir / "config.yml.example"

    @property
    def database_file(self) -> Path:
        return self.web_data_dir / "bio_digest_web.db"

    @property
    def access_trace_dir(self) -> Path:
        return self.web_data_dir / "access-traces"

    @property
    def review_export_dir(self) -> Path:
        return self.web_data_dir / "review-tables"


def get_instance_paths(project_root: Path | None = None) -> InstancePaths:
    resolved_project_root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    default_instance_root = resolved_project_root / "bio-literature-config"
    instance_root = Path(os.environ.get("BIO_DIGEST_WEB_INSTANCE_ROOT", default_instance_root)).resolve()
    paths_file = Path(os.environ.get("BIO_DIGEST_WEB_PATHS_FILE", instance_root / "paths.env")).resolve()
    config = read_env_pairs(paths_file)

    web_env_dir = resolve_configured_path(config.get("WEB_ENV_DIR", "@instance/env/web"), project_root=resolved_project_root, instance_root=instance_root)
    web_data_dir = resolve_configured_path(config.get("WEB_DATA_DIR", "@instance/data/web"), project_root=resolved_project_root, instance_root=instance_root)
    web_runtime_dir = resolve_configured_path(config.get("WEB_RUNTIME_DIR", "@instance/runtime/web"), project_root=resolved_project_root, instance_root=instance_root)
    web_tunnel_dir = resolve_configured_path(config.get("WEB_TUNNEL_DIR", "@instance/tunnel/web"), project_root=resolved_project_root, instance_root=instance_root)
    producer_env_dir = resolve_configured_path(config.get("PRODUCER_ENV_DIR", "@instance/env/producer"), project_root=resolved_project_root, instance_root=instance_root)
    producer_root = resolve_configured_path(config.get("PRODUCER_ROOT", "@project/../bio-literature-digest"), project_root=resolved_project_root, instance_root=instance_root)
    producer_archive_dir = resolve_configured_path(config.get("PRODUCER_ARCHIVE_DIR", "@project/../bio-literature-digest/archives/daily-digests"), project_root=resolved_project_root, instance_root=instance_root)
    producer_email_config = resolve_configured_path(config.get("PRODUCER_EMAIL_CONFIG", "@instance/env/producer/email_config.local.yaml"), project_root=resolved_project_root, instance_root=instance_root)

    return InstancePaths(
        project_root=resolved_project_root,
        instance_root=instance_root,
        paths_file=paths_file,
        web_env_dir=web_env_dir,
        web_data_dir=web_data_dir,
        web_runtime_dir=web_runtime_dir,
        web_tunnel_dir=web_tunnel_dir,
        producer_env_dir=producer_env_dir,
        producer_root=producer_root,
        producer_archive_dir=producer_archive_dir,
        producer_email_config=producer_email_config,
    )
