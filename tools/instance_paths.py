#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _first_existing_path(*candidates: Path) -> Path:
    resolved = [candidate.resolve() for candidate in candidates]
    for candidate in resolved:
        if candidate.exists():
            return candidate
    return resolved[0]


def _default_workspace_root(project_root: Path) -> Path:
    if project_root.parent.name == "skills":
        return project_root.parent.parent.resolve()
    return project_root.parent.resolve()


def _default_producer_root(project_root: Path) -> Path:
    if project_root.parent.name == "skills":
        return (project_root.parent / "bio-literature-digest").resolve()
    return (_default_workspace_root(project_root) / "bio-literature-digest").resolve()


@dataclass(frozen=True)
class InstancePaths:
    project_root: Path
    workspace_root: Path
    instance_root: Path
    web_env_dir: Path
    web_data_dir: Path
    web_runtime_dir: Path
    web_tunnel_dir: Path
    producer_env_dir: Path
    producer_root: Path
    producer_archive_dir: Path
    producer_email_config: Path
    producer_users_config: Path
    producer_database_file: Path

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
    workspace_root = _default_workspace_root(resolved_project_root)
    instance_root = Path(
        os.environ.get(
            "BIO_DIGEST_WEB_INSTANCE_ROOT",
            str(resolved_project_root / "bio-literature-config"),
        )
    ).resolve()
    producer_root = Path(
        os.environ.get(
            "BIO_DIGEST_PRODUCER_ROOT",
            str(_default_producer_root(resolved_project_root)),
        )
    ).resolve()
    default_archive_dir = _first_existing_path(
        producer_root / "var" / "archives" / "daily-digests",
        producer_root / "archives" / "daily-digests",
    )
    producer_archive_dir = Path(
        os.environ.get(
            "BIO_DIGEST_PRODUCER_ARCHIVE_DIR",
            str(default_archive_dir),
        )
    ).resolve()
    default_producer_email_config = _first_existing_path(
        producer_root / "local" / "integrations" / "email_config.yaml",
        instance_root / "env" / "producer" / "email_config.local.yaml",
    )
    producer_email_config = Path(
        os.environ.get(
            "BIO_DIGEST_PRODUCER_EMAIL_CONFIG",
            str(default_producer_email_config),
        )
    ).resolve()
    default_producer_users_config = _first_existing_path(
        producer_root / "local" / "integrations" / "users.yaml",
        instance_root / "env" / "producer" / "users.local.yaml",
    )
    producer_users_config = Path(
        os.environ.get(
            "BIO_DIGEST_PRODUCER_USERS_CONFIG",
            str(default_producer_users_config),
        )
    ).resolve()
    default_producer_database_file = _first_existing_path(
        producer_root / "var" / "db" / "bio_digest.sqlite3",
        producer_root / "bio-literature-config" / "data" / "shared" / "bio_digest.sqlite3",
    )
    producer_database_file = Path(
        os.environ.get(
            "BIO_DIGEST_PRODUCER_DATABASE_FILE",
            str(default_producer_database_file),
        )
    ).resolve()

    return InstancePaths(
        project_root=resolved_project_root,
        workspace_root=workspace_root,
        instance_root=instance_root,
        web_env_dir=(instance_root / "env" / "web").resolve(),
        web_data_dir=(instance_root / "data" / "web").resolve(),
        web_runtime_dir=(instance_root / "runtime" / "web").resolve(),
        web_tunnel_dir=(instance_root / "tunnel" / "web").resolve(),
        producer_env_dir=(instance_root / "env" / "producer").resolve(),
        producer_root=producer_root,
        producer_archive_dir=producer_archive_dir,
        producer_email_config=producer_email_config,
        producer_users_config=producer_users_config,
        producer_database_file=producer_database_file,
    )
