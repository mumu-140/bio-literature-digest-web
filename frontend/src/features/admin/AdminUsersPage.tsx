import { FormEvent, useEffect, useState } from "react";

import { request, UserItem } from "../../dataClient";

export function AdminUsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [form, setForm] = useState({ email: "", name: "", role: "member", user_group: "internal" });
  const [subscriptionForm, setSubscriptionForm] = useState({ email: "", name: "", user_group: "internal" });
  const [subscriptionMessage, setSubscriptionMessage] = useState("");
  const [subscriptionPending, setSubscriptionPending] = useState(false);

  async function load() {
    setUsers(await request<UserItem[]>("/api/admin/users"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function createUser(event: FormEvent) {
    event.preventDefault();
    await request("/api/admin/users", {
      method: "POST",
      body: JSON.stringify({ ...form, name: form.name || form.email.split("@")[0] || "" }),
    });
    setForm({ email: "", name: "", role: "member", user_group: "internal" });
    await load();
  }

  async function toggleUser(user: UserItem) {
    await request(`/api/admin/users/${user.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !user.is_active }),
    });
    await load();
  }

  async function createSubscription(event: FormEvent) {
    event.preventDefault();
    setSubscriptionPending(true);
    setSubscriptionMessage("");
    try {
      const result = await request<{ uid: string; email: string }>("/api/admin/subscriptions", {
        method: "POST",
        body: JSON.stringify(subscriptionForm),
      });
      setSubscriptionMessage(`已新增订阅邮箱 ${result.email}（${result.uid}）`);
      setSubscriptionForm({ email: "", name: "", user_group: "internal" });
      await load();
    } catch (error) {
      setSubscriptionMessage(error instanceof Error ? error.message : "新增订阅邮箱失败");
    } finally {
      setSubscriptionPending(false);
    }
  }

  return (
    <div className="split-grid">
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">管理员</p>
            <h2>创建账户</h2>
          </div>
        </div>
        <form className="stack" onSubmit={createUser}>
          <input placeholder="邮箱" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          <input placeholder="姓名" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
          <select value={form.user_group} onChange={(event) => setForm({ ...form, user_group: event.target.value })}>
            <option value="internal">internal</option>
            <option value="outsider">outsider</option>
          </select>
          <button className="primary-button" type="submit">创建</button>
        </form>
        <div className="subpanel stack">
          <div>
            <p className="eyebrow">文献邮件</p>
            <h3>新增订阅邮箱</h3>
          </div>
          <form className="stack" onSubmit={createSubscription}>
            <input name="subscription_email" type="email" required placeholder="订阅邮箱" value={subscriptionForm.email} onChange={(event) => setSubscriptionForm({ ...subscriptionForm, email: event.target.value })} />
            <input name="subscription_name" placeholder="姓名（可选）" value={subscriptionForm.name} onChange={(event) => setSubscriptionForm({ ...subscriptionForm, name: event.target.value })} />
            <select name="subscription_group" value={subscriptionForm.user_group} onChange={(event) => setSubscriptionForm({ ...subscriptionForm, user_group: event.target.value })}>
              <option value="internal">内部成员</option>
              <option value="outsider">外部订阅者</option>
            </select>
            <button className="primary-button" type="submit" disabled={subscriptionPending}>{subscriptionPending ? "新增中…" : "新增订阅邮箱"}</button>
            {subscriptionMessage ? <p className="small-copy">{subscriptionMessage}</p> : null}
          </form>
        </div>
      </section>
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">审计与代操作</p>
            <h2>用户列表</h2>
          </div>
        </div>
        <div className="table-shell">
          <div className="mobile-only">
            <div className="mobile-stack">
              {users.map((user) => (
                <article className="mobile-card" key={user.id}>
                  <div className="mobile-card-head">
                    <div>
                      <p className="eyebrow">#{user.id}</p>
                      <strong>{user.email}</strong>
                    </div>
                    <span className={`status-pill ${user.is_active ? "is-live" : "is-idle"}`}>{user.is_active ? "active" : "inactive"}</span>
                  </div>
                  <p className="mobile-summary">{user.name}</p>
                  <div className="mobile-meta-grid">
                    <div>
                      <span className="meta-label">角色</span>
                      <strong>{user.role}</strong>
                    </div>
                    <div>
                      <span className="meta-label">分组</span>
                      <strong>{user.user_group}</strong>
                    </div>
                    <div>
                      <span className="meta-label">最近登录</span>
                      <strong>{user.last_login_at || "never"}</strong>
                    </div>
                  </div>
                  <div className="mobile-card-actions">
                    <button className="table-link" onClick={() => toggleUser(user)}>{user.is_active ? "停用" : "启用"}</button>
                  </div>
                </article>
              ))}
            </div>
          </div>
          <div className="desktop-only">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>邮箱</th>
                  <th>角色</th>
                  <th>分组</th>
                  <th>状态</th>
                  <th>最近登录</th>
                  <th>动作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.email}<div className="small-copy">{user.name}</div></td>
                    <td>{user.role}</td>
                    <td>{user.user_group}</td>
                    <td>{user.is_active ? "active" : "inactive"}</td>
                    <td>{user.last_login_at || "never"}</td>
                    <td>
                      <button className="table-link" onClick={() => toggleUser(user)}>{user.is_active ? "停用" : "启用"}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
