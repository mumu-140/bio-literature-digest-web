import { useEffect, useState } from "react";
import { fetchAdminUsers, UserItem } from "../../dataClient";
import { PaperPushItem } from "../pushes/pushClient";

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
      <summary aria-label={placeholder}>{summary}</summary>
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
        <button type="button" className="table-link" onClick={() => onChange(allValues)}>全选</button>
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
