import { useEffect, useMemo, useState } from "react";

import { AuthUser, toggleFavorite } from "../../dataClient";
import { listPushes, PaperPushItem, updatePush } from "./pushClient";
import {
  CopyDoiButton,
  EmptyState,
  formatDigestDate,
  formatPushEmailStatus,
  MetricTile,
  normalizeDoi,
  buildDoiUrl,
  useAdminUsers,
  UserSelect,
} from "../shared/WorkbenchUi";
import { buildDeerFlowDiscussionUrl } from "../digest/deerflowDiscussion";
import {
  IconChatBubble,
  IconCheck,
  IconExternalLink,
  IconStar,
} from "../shared/Icons";

export function PushInboxPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [pushes, setPushes] = useState<PaperPushItem[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));
  const [activeTab, setActiveTab] = useState<"all" | "unread" | "read">("all");
  const [favoriteSuccessMap, setFavoriteSuccessMap] = useState<Record<number, boolean>>({});

  async function load() {
    setPushes(await listPushes(user.role === "admin" ? targetUserId : undefined));
  }

  useEffect(() => {
    void load();
  }, [targetUserId]);

  useEffect(() => {
    if (user.role === "admin" && adminUsers.length && !targetUserId) {
      setTargetUserId(String(adminUsers[0].id));
    }
  }, [adminUsers, targetUserId, user.role]);

  async function markRead(push: PaperPushItem, isRead: boolean) {
    await updatePush(push.id, isRead);
    await load();
  }

  async function markAllUnreadAsRead() {
    const unread = pushes.filter((p) => !p.is_read);
    for (const item of unread) {
      await updatePush(item.id, true);
    }
    await load();
  }

  async function handleToggleFavorite(push: PaperPushItem) {
    try {
      await toggleFavorite(push.paper_id, false);
      setFavoriteSuccessMap((prev) => ({ ...prev, [push.paper_id]: true }));
      setTimeout(() => {
        setFavoriteSuccessMap((prev) => ({ ...prev, [push.paper_id]: false }));
      }, 2000);
    } catch {
      // ignore
    }
  }

  function discussPaper(push: PaperPushItem) {
    try {
      const url = buildDeerFlowDiscussionUrl([push.canonical_key]);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      // ignore
    }
  }

  const unreadCount = pushes.filter((item) => !item.is_read).length;
  const readCount = pushes.length - unreadCount;

  const filteredPushes = useMemo(() => {
    if (activeTab === "unread") return pushes.filter((p) => !p.is_read);
    if (activeTab === "read") return pushes.filter((p) => p.is_read);
    return pushes;
  }, [pushes, activeTab]);

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">推送收件箱</p>
          <h2>推送文献工作台</h2>
        </div>
        {user.role === "admin" ? (
          <UserSelect
            users={adminUsers}
            value={targetUserId}
            onChange={setTargetUserId}
            placeholder="选择查看账户"
          />
        ) : null}
      </div>

      <div className="stats-strip">
        <MetricTile label="推送文献总量" value={String(pushes.length)} hint="所有分发记录" />
        <MetricTile label="待跟进未读" value={String(unreadCount)} hint="建议优先阅读" />
        <MetricTile label="已完成阅读" value={String(readCount)} hint="已标为已读的条目" />
      </div>

      {/* Tabs bar */}
      <div className="push-tabs-bar">
        <div className="push-tabs">
          <button
            type="button"
            className={`push-tab-btn${activeTab === "all" ? " is-active" : ""}`}
            onClick={() => setActiveTab("all")}
          >
            全部 <span>({pushes.length})</span>
          </button>
          <button
            type="button"
            className={`push-tab-btn${activeTab === "unread" ? " is-active" : ""}`}
            onClick={() => setActiveTab("unread")}
          >
            未读 <span>({unreadCount})</span>
          </button>
          <button
            type="button"
            className={`push-tab-btn${activeTab === "read" ? " is-active" : ""}`}
            onClick={() => setActiveTab("read")}
          >
            已读 <span>({readCount})</span>
          </button>
        </div>

        {unreadCount > 0 ? (
          <button
            type="button"
            className="ghost-button mark-all-read-btn"
            onClick={() => void markAllUnreadAsRead()}
          >
            <IconCheck size={14} />
            <span>全部标为已读</span>
          </button>
        ) : null}
      </div>

      <div className="table-shell">
        {filteredPushes.length === 0 ? (
          <EmptyState
            title={activeTab === "unread" ? "太棒了！所有推送均已读完" : "当前没有推送记录"}
            description="管理员分发文献后会在此显示，包含推送附言与邮件送达状态。"
          />
        ) : null}

        {/* Mobile View */}
        <div className="mobile-only">
          <div className="mobile-stack">
            {filteredPushes.map((push) => {
              const doiCandidate = push.canonical_key?.startsWith("doi:")
                ? push.canonical_key.slice(4)
                : "";
              const normalizedDoi = normalizeDoi(doiCandidate);
              const isFavSuccess = favoriteSuccessMap[push.paper_id];

              return (
                <article
                  className={`mobile-card push-card${!push.is_read ? " is-unread" : ""}`}
                  key={push.id}
                >
                  <div className="mobile-card-head">
                    <div className="push-sender-meta">
                      <span className="push-sender-badge">{push.sender_name} 推送</span>
                      <span className="muted push-timestamp">{push.pushed_at}</span>
                    </div>
                    <span
                      className={`status-pill ${push.is_read ? "is-idle" : "is-live"}`}
                    >
                      {push.is_read ? "已读" : "未读"}
                    </span>
                  </div>

                  <h3 className="title-strong title-strong-en">
                    <a
                      href={push.article_url}
                      target="_blank"
                      rel="noreferrer"
                      className="paper-title-link"
                    >
                      {push.title_en}
                      <IconExternalLink size={12} className="title-jump-icon" />
                    </a>
                  </h3>

                  {push.title_zh ? (
                    <p className="mobile-summary title-strong title-strong-zh">
                      {push.title_zh}
                    </p>
                  ) : null}

                  <div className="mobile-paper-meta-row">
                    <span className="mobile-journal-name">{push.journal}</span>
                    <span className="muted mobile-date">
                      {formatDigestDate(push.publish_date)}
                    </span>
                    <span className={`email-status-tag status-${push.email_notification_status}`}>
                      邮件: {formatPushEmailStatus(push.email_notification_status)}
                    </span>
                  </div>

                  {normalizedDoi ? (
                    <div className="mobile-doi-row">
                      <span className="doi-pill">
                        <span className="doi-label">DOI</span>
                        <a
                          href={buildDoiUrl(normalizedDoi)}
                          target="_blank"
                          rel="noreferrer"
                          className="doi-link-compact"
                        >
                          {normalizedDoi}
                        </a>
                      </span>
                      <CopyDoiButton doi={normalizedDoi} />
                    </div>
                  ) : null}

                  {push.note ? (
                    <div className="push-note-box">
                      <span className="push-note-label">附言：</span>
                      <p className="push-note-text">{push.note}</p>
                    </div>
                  ) : null}

                  <div className="mobile-card-actions paper-card-actions">
                    {!push.is_read ? (
                      <button
                        className="table-link action-read-btn"
                        onClick={() => void markRead(push, true)}
                      >
                        <IconCheck size={13} />
                        <span>标记已读</span>
                      </button>
                    ) : (
                      <button
                        className="table-link"
                        onClick={() => void markRead(push, false)}
                      >
                        恢复未读
                      </button>
                    )}

                    <button
                      className="table-link action-favorite-btn"
                      onClick={() => void handleToggleFavorite(push)}
                    >
                      <IconStar size={13} filled={isFavSuccess} />
                      <span>{isFavSuccess ? "已收藏" : "加入收藏"}</span>
                    </button>

                    <button
                      className="table-link action-discuss-btn"
                      onClick={() => discussPaper(push)}
                    >
                      <IconChatBubble size={13} />
                      <span>讨论</span>
                    </button>

                    <a
                      className="table-link link-button"
                      href={push.article_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <IconExternalLink size={13} />
                      <span>Open</span>
                    </a>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        {/* Desktop View */}
        <div className="desktop-only">
          <table>
            <thead>
              <tr>
                <th style={{ width: "80px" }}>状态</th>
                <th style={{ width: "130px" }}>时间 / 发送人</th>
                <th style={{ width: "160px" }}>期刊 / 邮件</th>
                <th>文献标题与 DOI</th>
                <th style={{ width: "200px" }}>推送附言</th>
                <th style={{ width: "170px" }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredPushes.map((push) => {
                const doiCandidate = push.canonical_key?.startsWith("doi:")
                  ? push.canonical_key.slice(4)
                  : "";
                const normalizedDoi = normalizeDoi(doiCandidate);
                const isFavSuccess = favoriteSuccessMap[push.paper_id];

                return (
                  <tr key={push.id} className={!push.is_read ? "is-unread-row" : ""}>
                    <td>
                      <span
                        className={`status-pill ${push.is_read ? "is-idle" : "is-live"}`}
                      >
                        {push.is_read ? "已读" : "未读"}
                      </span>
                    </td>
                    <td>
                      <div className="push-time-cell">
                        <strong>{push.sender_name}</strong>
                        <span className="muted small-copy">{push.pushed_at}</span>
                      </div>
                    </td>
                    <td>
                      <div className="push-journal-cell">
                        <span className="journal-badge">{push.journal}</span>
                        <span className="muted small-copy">
                          {formatDigestDate(push.publish_date)}
                        </span>
                        <span
                          className={`email-status-tag status-${push.email_notification_status}`}
                        >
                          {formatPushEmailStatus(push.email_notification_status)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="paper-title-block">
                        <a
                          className="table-title table-title-en paper-title-link"
                          href={push.article_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <span>{push.title_en}</span>
                          <IconExternalLink size={12} className="title-jump-icon" />
                        </a>
                      </div>

                      {push.title_zh ? (
                        <div className="table-title table-title-zh">{push.title_zh}</div>
                      ) : null}

                      {normalizedDoi ? (
                        <div className="paper-doi-row">
                          <span className="doi-pill">
                            <span className="doi-label">DOI</span>
                            <a
                              className="doi-link-compact"
                              href={buildDoiUrl(normalizedDoi)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {normalizedDoi}
                            </a>
                          </span>
                          <CopyDoiButton doi={normalizedDoi} />
                        </div>
                      ) : null}
                    </td>
                    <td>
                      {push.note ? (
                        <div className="push-table-note">
                          <span className="push-note-quote">&ldquo;</span>
                          <span>{push.note}</span>
                        </div>
                      ) : (
                        <span className="muted small-copy">无附言</span>
                      )}
                    </td>
                    <td>
                      <div className="paper-actions-stack">
                        {!push.is_read ? (
                          <button
                            className="table-link action-read-btn"
                            onClick={() => void markRead(push, true)}
                          >
                            <IconCheck size={12} />
                            <span>标为已读</span>
                          </button>
                        ) : (
                          <button
                            className="table-link"
                            onClick={() => void markRead(push, false)}
                          >
                            恢复未读
                          </button>
                        )}

                        <button
                          className="table-link action-favorite-btn"
                          onClick={() => void handleToggleFavorite(push)}
                        >
                          <IconStar size={12} filled={isFavSuccess} />
                          <span>{isFavSuccess ? "已收藏" : "收藏"}</span>
                        </button>

                        <button
                          className="table-link action-discuss-btn"
                          onClick={() => discussPaper(push)}
                        >
                          <IconChatBubble size={12} />
                          <span>讨论</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
