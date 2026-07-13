import { useEffect, useState } from "react";
import { fetchAdminUsers, PaperPushItem, UserItem } from "../../dataClient";

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
  const normalized = level.trim();
  let tier = "is-low";
  if (normalized === "非常感兴趣") tier = "is-high";
  else if (normalized === "感兴趣") tier = "is-mid";
  else if (normalized === "一般") tier = "is-low";
  else if (normalized === "非常一般") tier = "is-vlow";
  return (
    <span className={`interest-badge ${tier}`}>
      <span className="interest-badge-dot" />
      {normalized || "未分级"}
    </span>
  );
}

export function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  compact = false,
}: {
  title: string;
  description: string;
  compact?: boolean;
}) {
  return (
    <div className={`empty-state${compact ? " is-compact" : ""}`}>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
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
