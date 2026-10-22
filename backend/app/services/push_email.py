from __future__ import annotations

import html
import json
import os
import re
import smtplib
import subprocess
import time
from email.message import EmailMessage

from ..config import get_settings
from ..models import ImportedLiteratureItem, User


class PushEmailError(RuntimeError):
    """Raised when the push notification email cannot be queued."""


def send_otp_email(*, email: str, code: str, ttl_minutes: int, purpose: str = "register") -> None:
    """Queue one email verification code through the existing Agently account."""
    if purpose == "reset":
        subject = "[Bio Digest] 密码重置验证码"
        action_label = "重置登录密码"
    elif purpose == "login":
        subject = "[Bio Digest] 登录验证码"
        action_label = "登录"
    else:
        subject = "[Bio Digest] 注册邮箱验证码"
        action_label = "注册或激活账户"
    _send_raw_message(
        to=email,
        subject=subject,
        body=(
            "<p>您好：</p>"
            f"<p>您正在 Bio Literature Digest 进行{action_label}，本次验证码为 <strong>{html.escape(code)}</strong>"
            f"，{ttl_minutes} 分钟内有效。</p>"
            f"<p>验证码仅供本人{action_label}使用，请勿转发给任何人。"
            "若非本人操作，请忽略本邮件。</p>"
        ),
    )


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
    _send_raw_message(to=recipient.email, subject=subject, body=body)


def _send_raw_message(*, to: str, subject: str, body: str) -> None:
    command = [
        "/root/.local/bin/agently-cli",
        "message",
        "+send",
        "--to",
        to,
        "--subject",
        subject,
        "--body",
        body,
    ]
    last_error: PushEmailError | None = None
    for attempt in range(2):
        try:
            first = _run(command)
            data = first.get("data") if isinstance(first.get("data"), dict) else {}
            token = str(data.get("confirmation_token", "")).strip()
            if not token:
                raise PushEmailError("邮件服务未返回确认令牌")
            final = _run([*command, "--confirmation-token", token])
            final_data = final.get("data") if isinstance(final.get("data"), dict) else {}
            if not (final.get("queued") or final_data.get("queued")):
                raise PushEmailError("邮件服务未确认进入发送队列")
            return
        except PushEmailError as exc:
            last_error = exc
            print(f"[push_email] agently-cli attempt {attempt + 1} failed for {to}: {exc}", flush=True)
            if attempt == 0:
                time.sleep(0.8)

    if _send_via_smtp_fallback(to=to, subject=subject, body=body):
        return
    assert last_error is not None
    raise last_error


def _send_via_smtp_fallback(*, to: str, subject: str, body: str) -> bool:
    if to.strip().lower().endswith(("@example.com", "@example.org", "@example.net")):
        return False
    settings = get_settings()
    username = (settings.smtp_fallback_username or os.environ.get("SMTP_FALLBACK_USERNAME") or "").strip()
    password = (
        settings.smtp_fallback_password
        or os.environ.get("SMTP_FALLBACK_PASSWORD")
        or os.environ.get("QQ_MAIL_APP_PASSWORD")
        or ""
    ).strip()
    if not username or not password:
        return False

    plain_text = re.sub(r"<[^>]+>", "", body).strip() or subject
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_fallback_from_name} <{username}>"
    msg["To"] = to
    msg.set_content(plain_text)
    msg.add_alternative(body, subtype="html")
    try:
        with smtplib.SMTP_SSL(settings.smtp_fallback_host, settings.smtp_fallback_port, timeout=12) as server:
            server.login(username, password)
            server.send_message(msg)
        print(f"[push_email] SMTP fallback delivered email to {to} via {username}", flush=True)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[push_email] SMTP fallback failed for {to}: {exc}", flush=True)
        return False


def _run(command: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command, text=True, capture_output=True, check=False, timeout=12,
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
