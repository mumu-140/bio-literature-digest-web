import { useEffect, useState } from "react";

import { AuthUser, listPushes, PaperPushItem, updatePush } from "../../dataClient";
import {
  EmptyState,
  formatPushEmailStatus,
  MetricTile,
  useAdminUsers,
  UserSelect,
} from "../shared/WorkbenchUi";

export function PushInboxPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [pushes, setPushes] = useState<PaperPushItem[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));

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

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">管理员推送</p>
          <h2>推送文献收件箱</h2>
        </div>
        {user.role === "admin" ? (
          <UserSelect users={adminUsers} value={targetUserId} onChange={setTargetUserId} placeholder="选择查看账户" />
        ) : null}
      </div>
      <div className="stats-strip">
        <MetricTile label="推送总数" value={String(pushes.length)} />
        <MetricTile label="未读" value={String(pushes.filter((item) => !item.is_read).length)} />
      </div>
      <div className="table-shell">
        {pushes.length === 0 ? <EmptyState title="当前没有推送记录" description="管理员推送后会在这里汇总，支持直接标记已读。" /> : null}
        <div className="mobile-only">
          <div className="mobile-stack">
            {pushes.map((push) => (
              <article className="mobile-card" key={push.id}>
                <div className="mobile-card-head">
                  <div>
                    <p className="eyebrow">{push.sender_name}</p>
                    <strong>{push.pushed_at}</strong>
                  </div>
                  <span className={`status-pill ${push.is_read ? "is-idle" : "is-live"}`}>{push.is_read ? "已读" : "未读"}</span>
                </div>
                <h3 className="title-strong title-strong-en">{push.title_en}</h3>
                <p className="mobile-summary title-strong title-strong-zh">{push.title_zh}</p>
                <p className="small-copy">{push.journal} · {push.publish_date}</p>
                <p className="small-copy">{push.note || "无备注"}</p>
                <p className="small-copy">邮件：{formatPushEmailStatus(push.email_notification_status)}</p>
                <div className="mobile-card-actions">
                  {!push.is_read ? <button className="table-link" onClick={() => void markRead(push, true)}>标记已读</button> : null}
                  {push.is_read ? <button className="table-link" onClick={() => void markRead(push, false)}>恢复未读</button> : null}
                  <a className="table-link link-button" href={push.article_url} target="_blank" rel="noreferrer">Open</a>
                </div>
              </article>
            ))}
          </div>
        </div>
        <div className="desktop-only">
          <table>
            <thead>
              <tr>
                <th>状态</th>
                <th>时间</th>
                <th>推送人</th>
                <th>文献</th>
                <th>备注</th>
                <th>动作</th>
              </tr>
            </thead>
            <tbody>
              {pushes.map((push) => (
                <tr key={push.id}>
                  <td><span className={`status-pill ${push.is_read ? "is-idle" : "is-live"}`}>{push.is_read ? "已读" : "未读"}</span></td>
                  <td>{push.pushed_at}</td>
                  <td>{push.sender_name}</td>
                  <td>
                    <div className="table-title table-title-en">{push.title_en}</div>
                    <div className="table-title table-title-zh">{push.title_zh}</div>
                    <div className="small-copy table-subcopy">{push.journal} · {push.publish_date}</div>
                    <div className="small-copy table-subcopy">邮件：{formatPushEmailStatus(push.email_notification_status)}</div>
                  </td>
                  <td>{push.note || "无备注"}</td>
                  <td>
                    {!push.is_read ? <button className="table-link" onClick={() => void markRead(push, true)}>标记已读</button> : null}
                    {push.is_read ? <button className="table-link" onClick={() => void markRead(push, false)}>恢复未读</button> : null}
                    <a className="inline-link" href={push.article_url} target="_blank" rel="noreferrer">Open</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
