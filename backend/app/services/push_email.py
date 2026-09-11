from __future__ import annotations

import html
import json
import subprocess

from ..config import get_settings
from ..models import ImportedLiteratureItem, User


class PushEmailError(RuntimeError):
    """Raised when the push notification email cannot be queued."""


def send_push_email(*, recipient: User, sender: User, paper: ImportedLiteratureItem, note: str) -> None:
    """Queue one literature notification through the existing Agently account."""
    settings = get_settings()
    _send_message(
        recipient=recipient,
        subject=f"[Bio Digest] 文献推送：{paper.title_zh or paper.title_en}",
        body=_build_single_body(
            recipient=recipient,
            sender=sender,
            paper=paper,
            note=note,
            web_base_url=settings.web_base_url,
        ),
    )


def send_push_email_batch(
    *,
    recipient: User,
    sender: User,
    papers: list[ImportedLiteratureItem],
    note: str,
) -> None:
    """Queue one summary email for a recipient's literature push batch."""
    if not papers:
        raise PushEmailError("批量邮件缺少文献")
    settings = get_settings()
    _send_message(
        recipient=recipient,
        subject=f"[Bio Digest] 批量文献推送：{len(papers)} 篇",
        body=_build_batch_body(
            recipient=recipient,
            sender=sender,
            papers=papers,
            note=note,
            web_base_url=settings.web_base_url,
        ),
    )


def _send_message(*, recipient: User, subject: str, body: str) -> None:
    command = [
        "/root/.local/bin/agently-cli",
        "message",
        "+send",
        "--to",
        recipient.email,
        "--subject",
        subject,
        "--body",
        body,
    ]
    first = _run(command)
    data = first.get("data") if isinstance(first.get("data"), dict) else {}
    token = str(data.get("confirmation_token", "")).strip()
    if not token:
        raise PushEmailError("邮件服务未返回确认令牌")
    final = _run([*command, "--confirmation-token", token])
    final_data = final.get("data") if isinstance(final.get("data"), dict) else {}
    if not (final.get("queued") or final_data.get("queued")):
        raise PushEmailError("邮件服务未确认进入发送队列")


def _run(command: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command, text=True, capture_output=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise PushEmailError("邮件服务调用超时") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise PushEmailError(f"邮件服务调用失败：{detail or completed.returncode}")
    start, end = completed.stdout.find("{"), completed.stdout.rfind("}")
    if start < 0 or end < start:
        raise PushEmailError("邮件服务返回格式异常")
    try:
        payload = json.loads(completed.stdout[start:end + 1])
    except json.JSONDecodeError as exc:
        raise PushEmailError("邮件服务返回格式异常") from exc
    if not isinstance(payload, dict):
        raise PushEmailError("邮件服务返回格式异常")
    return payload


def _build_single_body(
    *,
    recipient: User,
    sender: User,
    paper: ImportedLiteratureItem,
    note: str,
    web_base_url: str,
) -> str:
    title_en = html.escape(paper.title_en or "")
    title_zh = html.escape(paper.title_zh or "")
    return (
        f"<p>{html.escape(recipient.name)}，您好：</p>"
        f"<p>{html.escape(sender.name)} 向您推送了一篇文献。</p>"
        f"<h2>{title_zh or title_en}</h2><p>{title_en}</p>"
        f"<p><strong>期刊：</strong>{html.escape(paper.journal or '')}</p>"
        f"<p><strong>备注：</strong>{html.escape(note or '无备注')}</p>"
        f"<p><a href=\"{html.escape(paper.article_url or '')}\">查看原文</a> · "
        f"<a href=\"{_inbox_url(web_base_url)}\">打开站内收件箱</a></p>"
    )


def _build_batch_body(
    *,
    recipient: User,
    sender: User,
    papers: list[ImportedLiteratureItem],
    note: str,
    web_base_url: str,
) -> str:
    items = "".join(
        "<li>"
        f"<a href=\"{html.escape(paper.article_url or '')}\">"
        f"{html.escape(paper.title_zh or paper.title_en or '未命名文献')}</a>"
        f"<br><small>{html.escape(paper.journal or '')}</small>"
        "</li>"
        for paper in papers
    )
    return (
        f"<p>{html.escape(recipient.name)}，您好：</p>"
        f"<p>{html.escape(sender.name)} 向您批量推送了 {len(papers)} 篇文献。</p>"
        f"<p><strong>备注：</strong>{html.escape(note or '无备注')}</p>"
        f"<ol>{items}</ol>"
        f"<p><a href=\"{_inbox_url(web_base_url)}\">打开站内收件箱</a></p>"
    )


def _inbox_url(web_base_url: str) -> str:
    return html.escape(web_base_url.rstrip("/") + "/pushes")
