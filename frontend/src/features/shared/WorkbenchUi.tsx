import React, { useEffect, useState } from "react";
import { fetchAdminUsers, UserItem } from "../../dataClient";
import { PaperPushItem } from "../pushes/pushClient";
import { IconArrowUp, IconCheck, IconCopy, IconExternalLink, IconSparkles } from "./Icons";

export function useAdminUsers(enabled: boolean) {
  const [users, setUsers] = useState<UserItem[]>([]);

  useEffect(() => {
    if (!enabled) {
      setUsers([]);
      return;
    }
    fetchAdminUsers()
      .then(setUsers)
      .catch(() => setUsers([]));
  }, [enabled]);

  return users;
}

export function InterestBadge({ level }: { level: string }) {
  const normalized = (level || "").trim();
  let tier = "is-low";
  let showSparkle = false;

  if (normalized === "非常感兴趣") {
    tier = "is-high";
    showSparkle = true;
  } else if (normalized === "感兴趣") {
    tier = "is-mid";
  } else if (normalized === "一般") {
    tier = "is-low";
  } else if (normalized === "非常一般") {
    tier = "is-vlow";
  }

  return (
    <span className={`interest-badge ${tier}`} title={`兴趣评级：${normalized || "未分级"}`}>
      {showSparkle ? (
        <IconSparkles size={11} className="interest-badge-icon" />
      ) : (
        <span className="interest-badge-dot" />
      )}
      <span>{normalized || "未分级"}</span>
    </span>
  );
}

export function MetricTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="metric-tile">
      <span className="metric-label">{label}</span>
      <strong className="metric-val">{value}</strong>
      {hint ? <small className="metric-hint">{hint}</small> : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  compact = false,
  action,
}: {
  title: string;
  description: string;
  compact?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <div className={`empty-state${compact ? " is-compact" : ""}`}>
      <div className="empty-state-icon-wrap" aria-hidden="true">
        <span className="empty-state-glyph">📑</span>
      </div>
      <strong>{title}</strong>
      <p>{description}</p>
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}

export function AuthorList({
  authors,
  maxVisible = 3,
}: {
  authors?: string[];
  maxVisible?: number;
}) {
  if (!authors || !authors.length) {
    return null;
  }
  const cleanAuthors = authors.map((a) => a.trim()).filter(Boolean);
  if (!cleanAuthors.length) {
    return null;
  }
  const fullText = cleanAuthors.join(", ");
  const visible = cleanAuthors.slice(0, maxVisible);
  const hasMore = cleanAuthors.length > maxVisible;

  return (
    <span className="paper-authors" title={fullText}>
      {visible.join(", ")}
      {hasMore ? <span className="authors-et-al"> 等 {cleanAuthors.length} 位作者</span> : null}
    </span>
  );
}

export function CopyDoiButton({ doi }: { doi: string }) {
  const [copied, setCopied] = useState(false);
  const normalized = normalizeDoi(doi);
  if (!normalized) return null;

  async function handleCopy(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(normalized);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = normalized;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // ignore
    }
  }

  return (
    <button
      type="button"
      className={`doi-copy-btn${copied ? " is-copied" : ""}`}
      onClick={handleCopy}
      title={copied ? "DOI 已复制到剪贴板！" : `复制 DOI：${normalized}`}
      aria-label="复制 DOI"
    >
      {copied ? <IconCheck size={12} /> : <IconCopy size={12} />}
      <span className="doi-copy-text">{copied ? "已复制" : "复制"}</span>
    </button>
  );
}

export function DoiField({ doi }: { doi: string }) {
  const normalized = normalizeDoi(doi);
  if (!normalized) {
    return <span className="muted">[无 DOI]</span>;
  }
  return (
    <span className="doi-field">
      <a
        className="doi-link"
        href={buildDoiUrl(normalized)}
        target="_blank"
        rel="noreferrer"
        title="跳转至 DOI 原文"
      >
        <span>{normalized}</span>
        <IconExternalLink size={10} className="doi-link-icon" />
      </a>
      <CopyDoiButton doi={normalized} />
    </span>
  );
}

export function BackToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function onScroll() {
      setVisible(window.scrollY > 400);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      className="back-to-top-btn"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      title="回到顶部"
      aria-label="回到顶部"
    >
      <IconArrowUp size={18} />
      <span className="back-to-top-label">顶部</span>
    </button>
  );
}

export function UserSelect({
  users,
  value,
  onChange,
  placeholder,
}: {
  users: UserItem[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <select aria-label={placeholder} name="target_user" value={value} onChange={(event) => onChange(event.target.value)}>
      {!value ? <option value="">{placeholder}</option> : null}
      {users.map((user) => (
        <option key={user.id} value={String(user.id)}>
          {user.id} · {user.name || user.email}
        </option>
      ))}
    </select>
  );
}

export function UserMultiSelect({
  users,
  values,
  onChange,
  placeholder,
  maxSelected = 20,
}: {
  users: UserItem[];
  values: string[];
  onChange: (values: string[]) => void;
  placeholder: string;
  maxSelected?: number;
}) {
  const activeUsers = users.filter((user) => user.is_active);
  const activeIds = new Set(activeUsers.map((user) => String(user.id)));
  const selectedValues = values.filter((value) => activeIds.has(value));
  const summary = selectedValues.length ? "已选 " + String(selectedValues.length) + " 人" : placeholder;

  return (
    <details className="multi-user-select">
      <summary aria-label={"接收人：" + summary}>
        <span>{summary}</span>
      </summary>
      <MultiUserOptions
        users={activeUsers}
        values={selectedValues}
        onChange={onChange}
        maxSelected={maxSelected}
      />
    </details>
  );
}

function MultiUserOptions({
  users,
  values,
  onChange,
  maxSelected,
}: {
  users: UserItem[];
  values: string[];
  onChange: (values: string[]) => void;
  maxSelected: number;
}) {
  const valueSet = new Set(values);
  const allValues = users.slice(0, maxSelected).map((user) => String(user.id));
  const selectAllLabel = users.length > maxSelected
    ? "全选前 " + String(maxSelected) + " 人"
    : "全选";
  const toggleUser = (userId: string) => {
    if (valueSet.has(userId)) {
      onChange(values.filter((value) => value !== userId));
    } else if (values.length < maxSelected) {
      onChange([...values, userId]);
    }
  };

  return (
    <div className="multi-user-popover">
      <div className="multi-user-actions">
        <span>{users.length} 名可用接收人</span>
        <button type="button" className="table-link" onClick={() => onChange(allValues)}>
          {selectAllLabel}
        </button>
        <button type="button" className="table-link" onClick={() => onChange([])}>清空</button>
      </div>
      <div className="multi-user-options" role="group" aria-label="接收账户">
        {users.map((user) => {
          const userId = String(user.id);
          const checked = valueSet.has(userId);
          return (
            <label className="multi-user-option" key={user.id}>
              <input
                type="checkbox"
                checked={checked}
                disabled={!checked && values.length >= maxSelected}
                onChange={() => toggleUser(userId)}
              />
              <span>
                <strong>{user.name || user.email}</strong>
                <small>{user.email}</small>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

export function formatReviewDecision(value: string) {
  return {
    keep: "保留",
    follow_up: "继续跟进",
    archive: "归档",
    exclude: "排除",
  }[value] || value;
}

export function formatDigestDate(value: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" }).format(date);
}

export function formatPushEmailStatus(status: PaperPushItem["email_notification_status"]) {
  return {
    not_requested: "未请求",
    pending: "等待发送",
    retrying: "正在重试",
    sent: "已发送",
    failed: "发送失败",
  }[status] || status;
}

export function normalizeDoi(doi: string) {
  return String(doi || "")
    .trim()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//i, "")
    .replace(/\s+/g, "");
}

export function buildDoiUrl(doi: string) {
  const normalized = normalizeDoi(doi);
  return normalized ? `https://doi.org/${encodeURI(normalized)}` : "";
}
