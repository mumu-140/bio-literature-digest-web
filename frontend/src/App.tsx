import { FormEvent, ReactNode, useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";

const APP_HOSTNAME = import.meta.env.VITE_APP_HOSTNAME || "localhost";

type AuthUser = {
  id: number;
  email: string;
  name: string;
  role: "admin" | "member";
  must_change_password: boolean;
  is_active: boolean;
  session_auth_method: "password" | "email_link";
};

type PaperItem = {
  id: number;
  digest_date: string;
  doi: string;
  journal: string;
  publish_date: string;
  category: string;
  interest_level: string;
  interest_score: number;
  interest_tag: string;
  title_en: string;
  title_zh: string;
  summary_zh: string;
  abstract: string;
  article_url: string;
  publication_stage: string;
  tags: string[];
  is_favorited: boolean;
};

type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

type FavoriteItem = {
  id: number;
  user_id: number;
  paper_id: number;
  digest_date?: string | null;
  doi: string;
  journal: string;
  publish_date: string;
  category: string;
  interest_level: string;
  interest_tag: string;
  title_en: string;
  title_zh: string;
  article_url: string;
  favorited_at: string;
  review_interest_level: string;
  review_interest_tag: string;
  review_final_decision: string;
  review_final_category: string;
  reviewer_notes: string;
  review_updated_at?: string | null;
};

type FavoriteReviewOptions = {
  interest_levels: string[];
  interest_tags: string[];
  review_final_decisions: string[];
  review_final_categories: string[];
};

type FavoriteReviewDraft = {
  review_interest_level: string;
  review_interest_tag: string;
  review_final_decision: string;
  review_final_category: string;
  reviewer_notes: string;
};

type UserItem = {
  id: number;
  email: string;
  name: string;
  role: "admin" | "member";
  user_group: "internal" | "outsider";
  owner_admin_user_id?: number | null;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
  last_login_at?: string | null;
};

type TrendPoint = {
  label: string;
  value: number;
  journal?: string | null;
};

type AnalyticsResponse = {
  scope_type: string;
  period: string;
  month: string;
  total_papers: number;
  nodes: Array<{ key: string; label: string; weight: number }>;
  edges: Array<{ source: string; target: string; weight: number }>;
  series: TrendPoint[];
  summary: Record<string, unknown>;
};

type ExportJob = {
  id: number;
  kind: string;
  status: string;
  output_name: string;
  content_type: string;
  created_at: string;
  finished_at?: string | null;
  download_url: string;
};

type PaperPushItem = {
  id: number;
  paper_id: number;
  recipient_user_id: number;
  sent_by_user_id: number;
  note: string;
  is_read: boolean;
  pushed_at: string;
  read_at?: string | null;
  title_en: string;
  title_zh: string;
  journal: string;
  publish_date: string;
  article_url: string;
  sender_name: string;
  recipient_name: string;
};

type PaperFilters = {
  query: string;
  date: string;
  category: string;
  tag: string;
};

const apiBase = "";

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

function browserLanguage(): string {
  if (typeof navigator === "undefined") {
    return "";
  }
  return navigator.language || "";
}

const navItems = [
  { to: "/digests/today", label: "今日文献", shortLabel: "今日" },
  { to: "/pushes", label: "推送文献", shortLabel: "推送" },
  { to: "/favorites", label: "收藏统计", shortLabel: "收藏" },
  { to: "/analytics", label: "网络图与趋势", shortLabel: "趋势" },
  { to: "/exports", label: "批量导出", shortLabel: "导出" },
];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const timezone = browserTimezone();
  const language = browserLanguage();
  const response = await fetch(`${apiBase}${path}`, {
    credentials: "include",
    headers: {
      "content-type": "application/json",
      ...(timezone ? { "x-browser-timezone": timezone } : {}),
      ...(language ? { "x-browser-language": language } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(extractErrorMessage(payload));
  }
  return payload as T;
}

function extractErrorMessage(payload: unknown): string {
  if (typeof payload === "string") {
    return payload;
  }
  if (!payload || typeof payload !== "object") {
    return "Request failed";
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const collected = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return item.msg;
        }
        return "";
      })
      .filter(Boolean);
    if (collected.length) {
      return collected.join("；");
    }
  }
  try {
    return JSON.stringify(payload);
  } catch {
    return "Request failed";
  }
}

function useAdminUsers(enabled: boolean) {
  const [users, setUsers] = useState<UserItem[]>([]);

  useEffect(() => {
    if (!enabled) {
      setUsers([]);
      return;
    }
    request<UserItem[]>("/api/admin/users")
      .then(setUsers)
      .catch(() => setUsers([]));
  }, [enabled]);

  return users;
}

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    request<AuthUser>("/api/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="shell-loading">Loading workspace…</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginScreen onLogin={setUser} />} />
      <Route
        path="*"
        element={
          <ProtectedLayout user={user} onUserChange={setUser}>
            <Routes>
              <Route path="/" element={<Navigate to="/digests/today" replace />} />
              <Route path="/digests/today" element={<DigestPage user={user!} />} />
              <Route path="/pushes" element={<PushInboxPage user={user!} />} />
              <Route path="/favorites" element={<FavoritesPage user={user!} />} />
              <Route path="/analytics" element={<AnalyticsPage user={user!} />} />
              <Route path="/exports" element={<ExportsPage user={user!} />} />
              <Route path="/admin/users" element={user?.role === "admin" ? <AdminUsersPage /> : <Navigate to="/digests/today" replace />} />
            </Routes>
          </ProtectedLayout>
        }
      />
    </Routes>
  );
}

function ProtectedLayout({
  user,
  onUserChange,
  children,
}: {
  user: AuthUser | null;
  onUserChange: (user: AuthUser | null) => void;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const location = useLocation();

  if (!user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  async function handleLogout() {
    await request("/api/auth/logout", { method: "POST" });
    onUserChange(null);
    navigate("/login");
  }

  const pageMeta = getPageMeta(location.pathname, user);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div>
            <p className="eyebrow">Bio Literature Digest</p>
            <h1>Research Console</h1>
            <p className="muted">{user.name} · {user.role}</p>
          </div>
          <div className="sidebar-status">
            <span className="status-dot" />
            Shared digest workspace
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
              {item.label}
            </NavLink>
          ))}
          {user.role === "admin" ? (
            <NavLink to="/admin/users" className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
              账户管理
            </NavLink>
          ) : null}
        </nav>
        <div className="sidebar-footer">
          <p className="small-copy">
            用统一视图查看共享文献池、收藏行为和月度趋势。
          </p>
          <button className="ghost-button sidebar-logout" onClick={handleLogout}>退出登录</button>
        </div>
      </aside>
      <main className="main-panel">
        <div className="mobile-topbar">
          <div className="mobile-topbar-copy">
            <p className="eyebrow">Bio Literature Digest</p>
            <strong>Research Console</strong>
            <span className="muted">{user.name}</span>
          </div>
          <div className="mobile-top-meta">
            <span className="status-pill is-live">{user.role}</span>
            <button className="ghost-button mobile-logout" onClick={handleLogout}>退出</button>
          </div>
        </div>
        <div className="main-frame">
          <header className="page-hero">
            <div>
              <p className="eyebrow">{pageMeta.eyebrow}</p>
              <h2>{pageMeta.title}</h2>
              <p className="muted hero-copy">{pageMeta.description}</p>
            </div>
            <div className="hero-badge">{user.role === "admin" ? "Admin Console" : "Member Console"}</div>
          </header>
          {user.must_change_password && user.session_auth_method === "password" ? (
            <PasswordGate onResolved={onUserChange} user={user} />
          ) : (
            children
          )}
        </div>
        <nav className="mobile-tabbar">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `mobile-tablink${isActive ? " is-active" : ""}`}>
              <span className="mobile-tabicon">{item.shortLabel.slice(0, 1)}</span>
              <span className="mobile-tabcopy">{item.shortLabel}</span>
            </NavLink>
          ))}
          {user.role === "admin" ? (
            <NavLink to="/admin/users" className={({ isActive }) => `mobile-tablink${isActive ? " is-active" : ""}`}>
              <span className="mobile-tabicon">管</span>
              <span className="mobile-tabcopy">账户</span>
            </NavLink>
          ) : null}
        </nav>
      </main>
    </div>
  );
}

function LoginScreen({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const hintedEmail = searchParams.get("email") || "";
  const emailToken = searchParams.get("token") || "";
  const [form, setForm] = useState({ email: searchParams.get("email") || "", password: "" });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setForm((current) => (current.email === hintedEmail ? current : { ...current, email: hintedEmail }));
  }, [hintedEmail]);

  useEffect(() => {
    if (!hintedEmail || !emailToken) {
      return;
    }
    let cancelled = false;
    async function performEmailLogin() {
      setPending(true);
      setError("");
      try {
        const response = await request<{ user: AuthUser }>("/api/auth/email-login", {
          method: "POST",
          body: JSON.stringify({ email: hintedEmail, password: emailToken }),
        });
        if (cancelled) {
          return;
        }
        onLogin(response.user);
        navigate(searchParams.get("next") || "/digests/today", { replace: true });
      } catch (submitError) {
        if (!cancelled) {
          setError(submitError instanceof Error ? submitError.message : "邮件登录失败");
        }
      } finally {
        if (!cancelled) {
          setPending(false);
        }
      }
    }
    void performEmailLogin();
    return () => {
      cancelled = true;
    };
  }, [emailToken, hintedEmail, navigate, onLogin, searchParams]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const response = await request<{ user: AuthUser }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(form),
      });
      onLogin(response.user);
      navigate(searchParams.get("next") || "/digests/today", { replace: true });
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-panel">
        <p className="eyebrow">{APP_HOSTNAME}</p>
        <h1>Bio Literature Digest Web</h1>
        <p className="muted">
          统一查看今日文献、收藏、月度网络图、CNS 趋势和批量导出。
        </p>
        {hintedEmail ? <p className="muted">本邮件链接对应账户：{hintedEmail}</p> : null}
        {emailToken ? <p className="muted">检测到邮件专属登录链接，正在尝试免密登录。</p> : null}
        <form className="stack" onSubmit={submit}>
          <label>
            邮箱
            <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          <label>
            密码
            <input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
          </label>
          {error ? <p className="error-text">{error}</p> : null}
          <button className="primary-button" type="submit" disabled={pending}>
            {pending ? (emailToken ? "免密登录中…" : "登录中…") : "登录"}
          </button>
        </form>
      </div>
    </div>
  );
}

function PasswordGate({ user, onResolved }: { user: AuthUser; onResolved: (user: AuthUser) => void }) {
  const [form, setForm] = useState({ current_password: "", new_password: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const canSkipCurrentPassword = user.session_auth_method === "email_link" && user.must_change_password;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const updated = await request<AuthUser>("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setMessage("密码已更新。");
      onResolved(updated);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "修改密码失败");
    }
  }

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">首次登录</p>
          <h2>{user.name}，请先修改密码</h2>
        </div>
      </div>
      <form className="inline-form" onSubmit={submit}>
        {canSkipCurrentPassword ? null : (
          <label>
            当前密码
            <input type="password" value={form.current_password} onChange={(event) => setForm({ ...form, current_password: event.target.value })} />
          </label>
        )}
        <label>
          新密码
          <input type="password" value={form.new_password} onChange={(event) => setForm({ ...form, new_password: event.target.value })} />
        </label>
        <button className="primary-button" type="submit">提交</button>
      </form>
      {canSkipCurrentPassword ? <p className="small-copy">当前是邮件专属登录，会直接为这个账户设置新密码，不需要输入旧密码。</p> : null}
      {message ? <p className="success-text">{message}</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}

function DigestPage({ user }: { user: AuthUser }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const adminUsers = useAdminUsers(user.role === "admin");
  const [allPapers, setAllPapers] = useState<PaperItem[]>([]);
  const [allDates, setAllDates] = useState<string[]>([]);
  const [filters, setFilters] = useState<PaperFilters>(() => ({
    query: searchParams.get("q") || "",
    date: searchParams.get("date") || "",
    category: searchParams.get("category") || "",
    tag: searchParams.get("tag") || "",
  }));
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [pushTargetUserId, setPushTargetUserId] = useState("");
  const [pushNote, setPushNote] = useState("");
  const [pushMessage, setPushMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [expandedDates, setExpandedDates] = useState<string[]>(() => parseExpandedDates(searchParams.get("expand")));
  const [exportMessage, setExportMessage] = useState("");
  const [activeRailDate, setActiveRailDate] = useState(searchParams.get("date") || "");

  async function load() {
    setLoading(true);
    const allRecords = await fetchAllPaperDirectory();
    const validKeys = new Set(allRecords.map(getPaperSelectionKey));
    setAllPapers(allRecords);
    setAllDates(collectUniqueValues(allRecords.map((item) => item.digest_date)));
    setSelectedKeys((current) => current.filter((key) => validKeys.has(key)));
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (user.role === "admin" && adminUsers.length && !pushTargetUserId) {
      setPushTargetUserId(String(adminUsers[0].id));
    }
  }, [adminUsers, pushTargetUserId, user.role]);

  useEffect(() => {
    const nextFilters = {
      query: searchParams.get("q") || "",
      date: searchParams.get("date") || "",
      category: searchParams.get("category") || "",
      tag: searchParams.get("tag") || "",
    };
    setFilters((current) =>
      current.query === nextFilters.query &&
      current.date === nextFilters.date &&
      current.category === nextFilters.category &&
      current.tag === nextFilters.tag
        ? current
        : nextFilters,
    );
    const nextExpanded = parseExpandedDates(searchParams.get("expand"));
    setExpandedDates((current) => (sameStringArray(current, nextExpanded) ? current : nextExpanded));
    setActiveRailDate(searchParams.get("date") || "");
  }, [searchParams]);

  useEffect(() => {
    const next = new URLSearchParams();
    if (filters.query.trim()) next.set("q", filters.query.trim());
    if (filters.date) next.set("date", filters.date);
    if (filters.category) next.set("category", filters.category);
    if (filters.tag) next.set("tag", filters.tag);
    if (expandedDates.length) next.set("expand", expandedDates.join(","));
    setSearchParams(next, { replace: true });
  }, [expandedDates, filters, setSearchParams]);

  async function toggleFavorite(item: PaperItem) {
    if (item.is_favorited) {
      await request(`/api/favorites/${item.id}`, { method: "DELETE" });
    } else {
      await request("/api/favorites", {
        method: "POST",
        body: JSON.stringify({ paper_id: item.id }),
      });
    }
    await load();
  }

  function togglePaperSelection(item: PaperItem) {
    const key = getPaperSelectionKey(item);
    setSelectedKeys((current) => (current.includes(key) ? current.filter((value) => value !== key) : [...current, key]));
  }

  function togglePaperBatch(items: PaperItem[]) {
    const keys = items.map(getPaperSelectionKey);
    setSelectedKeys((current) => {
      const currentSet = new Set(current);
      const shouldSelect = keys.some((key) => !currentSet.has(key));
      for (const key of keys) {
        if (shouldSelect) {
          currentSet.add(key);
        } else {
          currentSet.delete(key);
        }
      }
      return Array.from(currentSet);
    });
  }

  function runSelectedExport(kind: "metadata" | "doi-list") {
    const selected = allPapers.filter((item) => selectedKeys.includes(getPaperSelectionKey(item)));
    if (!selected.length) {
      setExportMessage("先选择要导出的文献。");
      return;
    }
    exportSelectedPapers(selected, kind);
    setExportMessage(`已导出 ${selected.length} 条${kind === "metadata" ? "元数据" : " DOI"}。`);
  }

  async function pushPaper(item: PaperItem) {
    if (user.role !== "admin") {
      return;
    }
    if (!pushTargetUserId.trim()) {
      setPushMessage("先填写接收账户 ID。");
      return;
    }
    await request("/api/admin/pushes", {
      method: "POST",
      body: JSON.stringify({
        paper_id: item.id,
        recipient_user_id: Number(pushTargetUserId),
        note: pushNote,
      }),
    });
    setPushMessage(`已将《${item.title_en}》推送给账户 ${pushTargetUserId}。`);
  }

  const selectedKeySet = new Set(selectedKeys);
  const filteredPapers = allPapers.filter((paper) => matchesPaperFilters(paper, filters));
  const categoryOptions = collectUniqueValues(allPapers.map((paper) => paper.category));
  const tagOptions = collectUniqueValues(allPapers.flatMap((paper) => paper.tags));
  const hasActiveFilters = Boolean(filters.query.trim() || filters.date || filters.category || filters.tag);
  const latestDate = allDates[0] || "";
  const visibleDates = filters.date ? [filters.date] : allDates.slice(0, 3);
  const groupedPapers = visibleDates
    .map((date) => ({
      date,
      items: filteredPapers.filter((paper) => paper.digest_date === date).sort(comparePaperPriority),
    }))
    .filter((group) => group.items.length > 0);
  const filteredSelectionKeys = groupedPapers.flatMap((group) => group.items.map(getPaperSelectionKey));
  const allFilteredSelected = filteredSelectionKeys.length > 0 && filteredSelectionKeys.every((key) => selectedKeySet.has(key));

  useEffect(() => {
    if (filters.date) {
      setActiveRailDate(filters.date);
      return;
    }
    if (groupedPapers.length && !groupedPapers.some((group) => group.date === activeRailDate)) {
      setActiveRailDate(groupedPapers[0].date);
    }
  }, [activeRailDate, filters.date, groupedPapers]);

  function scrollToDate(date: string) {
    setActiveRailDate(date);
    document.getElementById(`digest-day-${date}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearFilters() {
    setFilters({ query: "", date: "", category: "", tag: "" });
  }

  function clearSelection() {
    setSelectedKeys([]);
  }

  function toggleDayExpanded(date: string) {
    setExpandedDates((current) => (current.includes(date) ? current.filter((item) => item !== date) : [...current, date]));
  }

  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">共享订阅池</p>
            <h2>今日文献</h2>
          </div>
          <div className="actions">
            <button className="ghost-button" onClick={() => void load()}>刷新最近 3 天</button>
            <button className="ghost-button" onClick={clearFilters}>清空筛选</button>
          </div>
        </div>
        <div className="stats-strip">
          <MetricTile label="最近目录" value={allDates.length ? `${Math.min(3, allDates.length)} 天` : "0 天"} />
          <MetricTile label="筛选结果" value={String(filteredPapers.length)} />
          <MetricTile label="已选条目" value={String(selectedKeys.length)} />
        </div>
        {user.role === "admin" ? (
          <div className="push-bar">
            <UserSelect
              users={adminUsers}
              value={pushTargetUserId}
              onChange={setPushTargetUserId}
              placeholder="选择接收账户"
            />
            <input placeholder="推送备注" value={pushNote} onChange={(event) => setPushNote(event.target.value)} />
            {pushMessage ? <span className="success-text">{pushMessage}</span> : null}
          </div>
        ) : null}
        <div className="filter-row filter-grid-wide">
          <input
            placeholder="搜索标题、摘要、期刊、标签"
            value={filters.query}
            onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))}
          />
          <select value={filters.date} onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value }))}>
            <option value="">最近 3 天</option>
            {allDates.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
          <select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}>
            <option value="">全部分类</option>
            {categoryOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
          <select value={filters.tag} onChange={(event) => setFilters((current) => ({ ...current, tag: event.target.value }))}>
            <option value="">全部标签</option>
            {tagOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
        <div className="selection-toolbar">
          <label className="check-row">
            <input type="checkbox" checked={allFilteredSelected} onChange={() => togglePaperBatch(groupedPapers.flatMap((group) => group.items))} />
            <span>全选当前筛选</span>
          </label>
          <div className="actions">
            <span className="selection-copy">已选 {selectedKeys.length} 篇</span>
            <button className="ghost-button" onClick={clearSelection} disabled={!selectedKeys.length}>清空选择</button>
            <button className="ghost-button" onClick={() => runSelectedExport("metadata")} disabled={!selectedKeys.length}>导出选中元数据</button>
            <button className="ghost-button" onClick={() => runSelectedExport("doi-list")} disabled={!selectedKeys.length}>导出选中 DOI</button>
          </div>
        </div>
        {exportMessage ? <p className="success-text">{exportMessage}</p> : null}
        {loading ? <div className="small-copy">正在加载文献目录与历史日期…</div> : null}
        <div className="digest-layout">
          <aside className="date-rail desktop-only">
            {groupedPapers.map((group) => (
              <button
                className={`date-rail-item${group.date === activeRailDate ? " is-active" : ""}`}
                key={group.date}
                onClick={() => scrollToDate(group.date)}
              >
                <span className="date-rail-marker"><span /></span>
                <span className="date-rail-label">{formatDigestDate(group.date)}</span>
              </button>
            ))}
          </aside>
          <div className="digest-sections">
            <div className="mobile-day-strip mobile-only">
              {groupedPapers.map((group) => (
                <button
                  className={`date-chip${group.date === activeRailDate ? " is-active" : ""}`}
                  key={group.date}
                  onClick={() => scrollToDate(group.date)}
                >
                  {formatDigestDate(group.date)}
                </button>
              ))}
            </div>
            {groupedPapers.length === 0 ? <EmptyState title="最近 3 天没有符合条件的文献" description="调整搜索、日期、分类或标签筛选后再试。" /> : null}
            {groupedPapers.map((group) => {
              const shouldCollapse = group.date === latestDate && !hasActiveFilters && group.items.length > 10 && !expandedDates.includes(group.date);
              const visibleItems = shouldCollapse ? group.items.slice(0, 10) : group.items;
              const canToggle = group.date === latestDate && !hasActiveFilters && group.items.length > 10;
              return (
                <section className="day-section subpanel" key={group.date} id={`digest-day-${group.date}`}>
                  <div className="day-section-header">
                    <div>
                      <p className="eyebrow">{group.date === latestDate ? "今日" : "历史"}</p>
                      <h3>{formatDigestDate(group.date)}</h3>
                    </div>
                    <div className="day-section-meta">
                      <span className="status-pill is-idle">{group.items.length} 篇</span>
                      {canToggle ? <button className="table-link" onClick={() => toggleDayExpanded(group.date)}>{shouldCollapse ? "显示全部" : "收起今日"}</button> : null}
                    </div>
                  </div>
                  <PaperTable
                    papers={visibleItems}
                    selectedKeys={selectedKeySet}
                    onToggleSelect={togglePaperSelection}
                    onToggleSelectAll={togglePaperBatch}
                    onFavorite={toggleFavorite}
                    onPush={user.role === "admin" ? pushPaper : undefined}
                  />
                </section>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}

function PaperTable({
  papers,
  selectedKeys,
  onToggleSelect,
  onToggleSelectAll,
  onFavorite,
  onPush,
}: {
  papers: PaperItem[];
  selectedKeys: Set<string>;
  onToggleSelect: (item: PaperItem) => void;
  onToggleSelectAll: (items: PaperItem[]) => void;
  onFavorite: (item: PaperItem) => void;
  onPush?: (item: PaperItem) => void;
}) {
  const allSelected = papers.length > 0 && papers.every((paper) => selectedKeys.has(getPaperSelectionKey(paper)));

  return (
    <div className="table-shell">
      {papers.length === 0 ? <EmptyState title="当前没有可展示的文献" description="调整筛选条件后再刷新，或等待新的 digest 导入。" /> : null}
      <div className="mobile-only">
        <div className="mobile-stack">
          {papers.map((paper) => (
            <article className="mobile-card paper-card" key={`${paper.digest_date}-${paper.id}`}>
              <div className="mobile-card-head">
                <label className="check-row card-check">
                  <input type="checkbox" checked={selectedKeys.has(getPaperSelectionKey(paper))} onChange={() => onToggleSelect(paper)} />
                </label>
                <div>
                  <p className="eyebrow">{paper.journal}</p>
                  <strong>{paper.publish_date}</strong>
                </div>
                <span className={`status-pill ${paper.is_favorited ? "is-live" : "is-idle"}`}>
                  {paper.is_favorited ? "已收藏" : paper.interest_level}
                </span>
              </div>
              <h3>{paper.title_en}</h3>
              <p className="mobile-summary">{paper.title_zh}</p>
              <p className="small-copy">{paper.summary_zh}</p>
              <div className="mobile-meta-grid">
                <div>
                  <span className="meta-label">兴趣标签</span>
                  <strong>{paper.interest_tag}</strong>
                </div>
                <div>
                  <span className="meta-label">分类</span>
                  <strong>{paper.category || "未分类"}</strong>
                </div>
              </div>
              <div className="tag-list">
                {paper.tags.length ? paper.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>暂无标签</span>}
              </div>
              <div className="mobile-card-actions">
                <button className="table-link" onClick={() => onFavorite(paper)}>{paper.is_favorited ? "取消收藏" : "加入收藏"}</button>
                {onPush ? <button className="table-link" onClick={() => onPush(paper)}>推送</button> : null}
                <a className="table-link link-button" href={paper.article_url} target="_blank" rel="noreferrer">Open</a>
              </div>
            </article>
          ))}
        </div>
      </div>
      <div className="desktop-only">
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" checked={allSelected} onChange={() => onToggleSelectAll(papers)} /></th>
              <th>收藏</th>
              {onPush ? <th>推送</th> : null}
              <th>期刊</th>
              <th>评分</th>
              <th>标题</th>
              <th>中文</th>
              <th>标签</th>
              <th>链接</th>
            </tr>
          </thead>
          <tbody>
            {papers.map((paper) => (
              <tr key={`${paper.digest_date}-${paper.id}`}>
                <td><input type="checkbox" checked={selectedKeys.has(getPaperSelectionKey(paper))} onChange={() => onToggleSelect(paper)} /></td>
                <td><button className="table-link" onClick={() => onFavorite(paper)}>{paper.is_favorited ? "取消" : "收藏"}</button></td>
                {onPush ? <td><button className="table-link" onClick={() => onPush(paper)}>推送</button></td> : null}
                <td>{paper.journal}<br /><span className="muted">{paper.publish_date}</span></td>
                <td>{paper.interest_level}<br /><span className="muted">{paper.interest_tag}</span></td>
                <td>{paper.title_en}<div className="small-copy">{paper.summary_zh}</div></td>
                <td>{paper.title_zh}</td>
                <td>{paper.tags.join(", ")}</td>
                <td><a href={paper.article_url} target="_blank" rel="noreferrer">Open</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PushInboxPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [pushes, setPushes] = useState<PaperPushItem[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));

  async function load() {
    const suffix = user.role === "admin" ? `?user_id=${targetUserId}` : "";
    setPushes(await request<PaperPushItem[]>(`/api/pushes${suffix}`));
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
    await request<PaperPushItem>(`/api/pushes/${push.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_read: isRead }),
    });
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
                <h3>{push.title_en}</h3>
                <p className="mobile-summary">{push.title_zh}</p>
                <p className="small-copy">{push.journal} · {push.publish_date}</p>
                <p className="small-copy">{push.note || "无备注"}</p>
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
                    {push.title_en}
                    <div className="small-copy">{push.title_zh}</div>
                    <div className="small-copy">{push.journal} · {push.publish_date}</div>
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

function FavoritesPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [reviewOptions, setReviewOptions] = useState<FavoriteReviewOptions>({
    interest_levels: [],
    interest_tags: [],
    review_final_decisions: [],
    review_final_categories: [],
  });
  const [editingPaperId, setEditingPaperId] = useState<number | null>(null);
  const [draft, setDraft] = useState<FavoriteReviewDraft>({
    review_interest_level: "",
    review_interest_tag: "",
    review_final_decision: "",
    review_final_category: "",
    reviewer_notes: "",
  });
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const [savingPaperId, setSavingPaperId] = useState<number | null>(null);

  async function load() {
    const query = user.role === "admin" ? `?user_id=${targetUserId}` : "";
    const next = await request<FavoriteItem[]>(`/api/favorites${query}`);
    setFavorites(next);
    setSelectedIds((current) => current.filter((id) => next.some((favorite) => favorite.id === id)));
  }

  useEffect(() => {
    void load();
    setEditingPaperId(null);
    setSaveMessage("");
    setSaveError("");
  }, [targetUserId]);

  useEffect(() => {
    request<FavoriteReviewOptions>("/api/favorites/review-options")
      .then(setReviewOptions)
      .catch(() =>
        setReviewOptions({
          interest_levels: [],
          interest_tags: [],
          review_final_decisions: [],
          review_final_categories: [],
        }),
      );
  }, []);

  useEffect(() => {
    if (user.role === "admin" && adminUsers.length && !targetUserId) {
      setTargetUserId(String(adminUsers[0].id));
    }
  }, [adminUsers, targetUserId, user.role]);

  const allSelected = favorites.length > 0 && favorites.every((favorite) => selectedIds.includes(favorite.id));

  function toggleFavoriteSelection(favorite: FavoriteItem) {
    setSelectedIds((current) => (current.includes(favorite.id) ? current.filter((id) => id !== favorite.id) : [...current, favorite.id]));
  }

  function toggleFavoriteBatch(items: FavoriteItem[]) {
    const ids = items.map((item) => item.id);
    setSelectedIds((current) => {
      const currentSet = new Set(current);
      const shouldSelect = ids.some((id) => !currentSet.has(id));
      for (const id of ids) {
        if (shouldSelect) {
          currentSet.add(id);
        } else {
          currentSet.delete(id);
        }
      }
      return Array.from(currentSet);
    });
  }

  function exportFavorites(kind: "metadata" | "doi-list") {
    const selected = favorites.filter((favorite) => selectedIds.includes(favorite.id));
    if (!selected.length) {
      return;
    }
    exportSelectedFavorites(selected, kind);
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  function startEdit(favorite: FavoriteItem) {
    setEditingPaperId(favorite.paper_id);
    setDraft({
      review_interest_level: favorite.review_interest_level || favorite.interest_level,
      review_interest_tag: favorite.review_interest_tag || favorite.interest_tag,
      review_final_decision: favorite.review_final_decision || "",
      review_final_category: favorite.review_final_category || favorite.category,
      reviewer_notes: favorite.reviewer_notes || "",
    });
    setSaveMessage("");
    setSaveError("");
  }

  function cancelEdit() {
    setEditingPaperId(null);
    setSaveError("");
  }

  function updateDraft<K extends keyof FavoriteReviewDraft>(key: K, value: FavoriteReviewDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function saveFavoriteReview(favorite: FavoriteItem) {
    const query = user.role === "admin" ? `?user_id=${targetUserId}` : "";
    setSavingPaperId(favorite.paper_id);
    setSaveMessage("");
    setSaveError("");
    try {
      const updated = await request<FavoriteItem>(`/api/favorites/${favorite.paper_id}${query}`, {
        method: "PATCH",
        body: JSON.stringify(draft),
      });
      setFavorites((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setEditingPaperId(null);
      setSaveMessage("已保存，修改会延迟生效，系统会在每日 00:00 统一汇总到审查表。");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSavingPaperId(null);
    }
  }

  const activeTarget = user.role === "admin" ? adminUsers.find((item) => String(item.id) === targetUserId) : null;
  const targetLabel = activeTarget ? activeTarget.name : user.name;

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">个人收藏</p>
          <h2>收藏文献</h2>
        </div>
        {user.role === "admin" ? (
          <UserSelect users={adminUsers} value={targetUserId} onChange={setTargetUserId} placeholder="选择查看账户" />
        ) : null}
      </div>
      <div className="stats-strip">
        <MetricTile label="收藏数" value={String(favorites.length)} />
        <MetricTile label="查看账户" value={targetLabel} />
      </div>
      {saveMessage ? <div className="notice-banner is-success">{saveMessage}</div> : null}
      {saveError ? <div className="notice-banner is-error">{saveError}</div> : null}
      <div className="selection-toolbar">
        <label className="check-row">
          <input type="checkbox" checked={allSelected} onChange={() => toggleFavoriteBatch(favorites)} />
          <span>全选收藏结果</span>
        </label>
        <div className="actions">
          <span className="selection-copy">已选 {selectedIds.length} 篇</span>
          <button className="ghost-button" onClick={clearSelection} disabled={!selectedIds.length}>清空选择</button>
          <button className="ghost-button" onClick={() => exportFavorites("metadata")} disabled={!selectedIds.length}>导出选中元数据</button>
          <button className="ghost-button" onClick={() => exportFavorites("doi-list")} disabled={!selectedIds.length}>导出选中 DOI</button>
        </div>
      </div>
      <div className="table-shell">
        {favorites.length === 0 ? <EmptyState title="当前没有收藏记录" description="收藏后的论文会沉淀在这里，适合继续做二次筛选和导出。" /> : null}
        <div className="mobile-only">
          <div className="mobile-stack">
            {favorites.map((favorite) => (
              <article className="mobile-card" key={favorite.id}>
                <div className="mobile-card-head">
                  <label className="check-row card-check">
                    <input type="checkbox" checked={selectedIds.includes(favorite.id)} onChange={() => toggleFavoriteSelection(favorite)} />
                  </label>
                  <div>
                    <p className="eyebrow">{favorite.journal}</p>
                    <strong>{favorite.favorited_at}</strong>
                  </div>
                  <span className="status-pill is-live">{favorite.interest_level}</span>
                </div>
                <h3>{favorite.title_en}</h3>
                <p className="mobile-summary">{favorite.title_zh}</p>
                <div className="mobile-meta-grid">
                  <div>
                    <span className="meta-label">分类</span>
                    <strong>{favorite.category}</strong>
                  </div>
                  <div>
                    <span className="meta-label">标签</span>
                    <strong>{favorite.interest_tag}</strong>
                  </div>
                </div>
                <FavoriteReviewSummary favorite={favorite} />
                {editingPaperId === favorite.paper_id ? (
                  <FavoriteReviewEditor
                    draft={draft}
                    options={reviewOptions}
                    disabled={savingPaperId === favorite.paper_id}
                    onChange={updateDraft}
                    onCancel={cancelEdit}
                    onSave={() => void saveFavoriteReview(favorite)}
                  />
                ) : null}
                <div className="mobile-card-actions">
                  <button className="ghost-button" onClick={() => startEdit(favorite)}>修改</button>
                  <a className="table-link link-button" href={favorite.article_url} target="_blank" rel="noreferrer">Open</a>
                </div>
              </article>
            ))}
          </div>
        </div>
        <div className="desktop-only">
          <table>
            <thead>
              <tr>
                <th><input type="checkbox" checked={allSelected} onChange={() => toggleFavoriteBatch(favorites)} /></th>
                <th>收藏时间</th>
                <th>期刊</th>
                <th>标题</th>
                <th>当前调整</th>
                <th>链接</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {favorites.map((favorite) => (
                <tr key={favorite.id}>
                  <td><input type="checkbox" checked={selectedIds.includes(favorite.id)} onChange={() => toggleFavoriteSelection(favorite)} /></td>
                  <td>{favorite.favorited_at}</td>
                  <td>{favorite.journal}</td>
                  <td>{favorite.title_en}<div className="small-copy">{favorite.title_zh}</div></td>
                  <td>
                    <FavoriteReviewSummary favorite={favorite} />
                    {editingPaperId === favorite.paper_id ? (
                      <FavoriteReviewEditor
                        draft={draft}
                        options={reviewOptions}
                        disabled={savingPaperId === favorite.paper_id}
                        onChange={updateDraft}
                        onCancel={cancelEdit}
                        onSave={() => void saveFavoriteReview(favorite)}
                      />
                    ) : null}
                  </td>
                  <td><a href={favorite.article_url} target="_blank" rel="noreferrer">Open</a></td>
                  <td>
                    <button className="ghost-button" onClick={() => startEdit(favorite)}>修改</button>
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

function FavoriteReviewSummary({ favorite }: { favorite: FavoriteItem }) {
  const effectiveInterestLevel = favorite.review_interest_level || favorite.interest_level;
  const effectiveInterestTag = favorite.review_interest_tag || favorite.interest_tag;
  const effectiveGroup = favorite.review_final_category || favorite.category;

  return (
    <div className="favorite-review-summary">
      <div className="tag-list">
        <span>{effectiveInterestLevel}</span>
        <span>{effectiveInterestTag}</span>
        <span>{effectiveGroup}</span>
        {favorite.review_final_decision ? <span>{favorite.review_final_decision}</span> : null}
      </div>
      <div className="small-copy">
        {favorite.reviewer_notes ? favorite.reviewer_notes : "未提交人工审查修改。"}
      </div>
      {favorite.review_updated_at ? (
        <div className="small-copy">最近修改：{favorite.review_updated_at}</div>
      ) : (
        <div className="small-copy">保存后会延迟生效，并在每日 00:00 汇总到审查表。</div>
      )}
    </div>
  );
}

function FavoriteReviewEditor({
  draft,
  options,
  disabled,
  onChange,
  onCancel,
  onSave,
}: {
  draft: FavoriteReviewDraft;
  options: FavoriteReviewOptions;
  disabled: boolean;
  onChange: (key: keyof FavoriteReviewDraft, value: string) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <div className="favorite-review-editor">
      <div className="inline-form">
        <label>
          <span>标签强度</span>
          <select value={draft.review_interest_level} onChange={(event) => onChange("review_interest_level", event.target.value)}>
            <option value="">沿用当前</option>
            {options.interest_levels.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label>
          <span>兴趣标签</span>
          <select value={draft.review_interest_tag} onChange={(event) => onChange("review_interest_tag", event.target.value)}>
            <option value="">沿用当前</option>
            {options.interest_tags.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label>
          <span>审查结论</span>
          <select value={draft.review_final_decision} onChange={(event) => onChange("review_final_decision", event.target.value)}>
            <option value="">暂不指定</option>
            {options.review_final_decisions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label>
          <span>分组</span>
          <select value={draft.review_final_category} onChange={(event) => onChange("review_final_category", event.target.value)}>
            <option value="">沿用当前</option>
            {options.review_final_categories.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
      </div>
      <label>
        <span>备注</span>
        <textarea
          rows={4}
          value={draft.reviewer_notes}
          onChange={(event) => onChange("reviewer_notes", event.target.value)}
          placeholder="这里写人工判断、补充标签或后续处理意见。"
        />
      </label>
      <div className="favorite-review-actions">
        <button className="ghost-button" onClick={onCancel} disabled={disabled}>取消</button>
        <button className="primary-button" onClick={onSave} disabled={disabled}>{disabled ? "保存中…" : "保存修改"}</button>
      </div>
    </div>
  );
}

function AnalyticsPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [globalStats, setGlobalStats] = useState<AnalyticsResponse | null>(null);
  const [userStats, setUserStats] = useState<AnalyticsResponse | null>(null);
  const [cns, setCns] = useState<TrendPoint[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));

  async function load() {
    setGlobalStats(await request<AnalyticsResponse>(`/api/analytics/global?period=weekly&month=${month}`));
    setUserStats(await request<AnalyticsResponse>(`/api/analytics/users/${targetUserId}/favorites?period=weekly&month=${month}`));
    setCns(await request<TrendPoint[]>("/api/analytics/cns-trends?months=12"));
  }

  useEffect(() => {
    void load();
  }, [month, targetUserId]);

  useEffect(() => {
    if (user.role === "admin" && adminUsers.length && !targetUserId) {
      setTargetUserId(String(adminUsers[0].id));
    }
  }, [adminUsers, targetUserId, user.role]);

  const cnsGroups = groupSeriesByJournal(cns);

  return (
    <div className="content-stack">
      <section className="card analytics-overview">
        <div className="card-header">
          <div>
            <p className="eyebrow">统计快照</p>
            <h2>{month} 分析视图</h2>
          </div>
          <div className="actions">
            <input value={month} onChange={(event) => setMonth(event.target.value)} />
            {user.role === "admin" ? <UserSelect users={adminUsers} value={targetUserId} onChange={setTargetUserId} placeholder="选择统计账户" /> : null}
          </div>
        </div>
        <div className="stats-strip">
          <MetricTile label="全站文献" value={String(globalStats?.total_papers || 0)} />
          <MetricTile label="收藏样本" value={String(userStats?.total_papers || 0)} />
          <MetricTile label="CNS 点位" value={String(cns.length)} />
        </div>
      </section>
      <div className="split-grid analytics-grid">
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">统计周期</p>
            <h2>全站网络图</h2>
          </div>
          <span className="status-pill is-live">{month}</span>
        </div>
        <MetricRow label="纳入文献" value={String(globalStats?.total_papers || 0)} />
        <NodeCloud title="关键词节点" nodes={globalStats?.nodes || []} />
        <TrendList title="周趋势" series={globalStats?.series || []} variant="bar" />
      </section>
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">个人收藏统计</p>
            <h2>收藏网络与趋势</h2>
          </div>
          <span className="status-pill is-idle">user {targetUserId}</span>
        </div>
        <MetricRow label="收藏样本" value={String(userStats?.total_papers || 0)} />
        <NodeCloud title="收藏关键词" nodes={userStats?.nodes || []} />
        <TrendList title="收藏周趋势" series={userStats?.series || []} variant="bar" />
      </section>
      </div>
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">Cell / Nature / Science</p>
            <h2>CNS 月趋势</h2>
          </div>
        </div>
        <div className="journal-columns">
          {cnsGroups.map((group) => (
            <section className="subpanel" key={group.journal}>
              <TrendList title={group.journal} series={group.points} variant="bar" />
            </section>
          ))}
        </div>
      </section>
    </div>
  );
}

function NodeCloud({ title, nodes }: { title: string; nodes: Array<{ key: string; label: string; weight: number }> }) {
  return (
    <div className="subpanel">
      <h3>{title}</h3>
      <div className="node-cloud">
        {nodes.length === 0 ? <EmptyState title="暂无关键词" description="导入更多文献或调整周期后会生成节点权重。" compact /> : null}
        {nodes.slice(0, 24).map((node) => (
          <span key={node.key} style={{ fontSize: `${12 + Math.min(node.weight, 10) * 1.4}px` }}>
            {node.label}
            <strong>{node.weight}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function TrendList({
  title,
  series,
  variant = "default",
}: {
  title: string;
  series: TrendPoint[];
  variant?: "default" | "bar";
}) {
  const maxValue = Math.max(...series.map((point) => point.value), 1);

  return (
    <div className="subpanel">
      <h3>{title}</h3>
      {series.length === 0 ? <EmptyState title="暂无趋势数据" description="当前筛选范围内还没有可视化点位。" compact /> : null}
      <ul className="trend-list">
        {series.map((point, index) => (
          <li className={variant === "bar" ? "trend-item bar" : "trend-item"} key={`${point.label}-${point.journal || index}`}>
            <div className="trend-copy">
              <span>{point.label}{point.journal ? ` · ${point.journal}` : ""}</span>
              {variant === "bar" ? <div className="trend-meter"><span style={{ width: `${(point.value / maxValue) * 100}%` }} /></div> : null}
            </div>
            <strong>{point.value}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({
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

function UserSelect({
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
    <select value={value} onChange={(event) => onChange(event.target.value)}>
      {!value ? <option value="">{placeholder}</option> : null}
      {users.map((user) => (
        <option key={user.id} value={String(user.id)}>
          {user.id} · {user.name || user.email}
        </option>
      ))}
    </select>
  );
}

function AdminUsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "member", user_group: "internal" });

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
    setForm({ email: "", name: "", password: "", role: "member", user_group: "internal" });
    await load();
  }

  async function resetPassword(userId: number) {
    const password = window.prompt("输入新密码");
    if (!password) return;
    await request(`/api/admin/users/${userId}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    await load();
  }

  async function toggleUser(user: UserItem) {
    await request(`/api/admin/users/${user.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !user.is_active }),
    });
    await load();
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
          <input placeholder="初始密码" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
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
                    <button className="table-link" onClick={() => resetPassword(user.id)}>重置密码</button>
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
                      <button className="table-link" onClick={() => resetPassword(user.id)}>重置密码</button>
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

function ExportsPage({ user }: { user: AuthUser }) {
  const [mappings, setMappings] = useState([
    { source: "journal", label: "期刊" },
    { source: "title_en", label: "英文标题" },
    { source: "doi", label: "DOI" },
  ]);
  const [job, setJob] = useState<ExportJob | null>(null);

  async function exportCustom() {
    setJob(
      await request<ExportJob>("/api/exports/custom-table", {
        method: "POST",
        body: JSON.stringify({ columns: mappings, user_id: user.id }),
      }),
    );
  }

  function updateMapping(index: number, field: "source" | "label", value: string) {
    setMappings((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)));
  }

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">导出中心</p>
          <h2>自定义表格列名</h2>
        </div>
      </div>
      <div className="mapping-grid">
        {mappings.map((mapping, index) => (
          <div className="mapping-row" key={`${mapping.source}-${index}`}>
            <input value={mapping.source} onChange={(event) => updateMapping(index, "source", event.target.value)} />
            <input value={mapping.label} onChange={(event) => updateMapping(index, "label", event.target.value)} />
          </div>
        ))}
      </div>
      <div className="actions">
        <button className="ghost-button" onClick={() => setMappings((current) => [...current, { source: "", label: "" }])}>新增列</button>
        <button className="primary-button" onClick={() => void exportCustom()}>生成自定义导出</button>
      </div>
      {job ? (
        <p className="success-text">
          已生成 {job.output_name}：
          <a href={job.download_url}>下载</a>
        </p>
      ) : null}
    </section>
  );
}

function getPageMeta(pathname: string, user: AuthUser) {
  if (pathname.startsWith("/pushes")) {
    return {
      eyebrow: "Delivery Inbox",
      title: "推送文献工作台",
      description: "集中处理管理员分发的重点论文，快速区分未读、已读和待跟进条目。",
    };
  }
  if (pathname.startsWith("/favorites")) {
    return {
      eyebrow: "Personal Signal",
      title: "收藏行为回看",
      description: "把个人收藏沉淀为稳定样本，便于后续做统计、导出和重点复盘。",
    };
  }
  if (pathname.startsWith("/analytics")) {
    return {
      eyebrow: "Network Lens",
      title: "网络图与趋势分析",
      description: "从全站收录、个人收藏和 CNS 长周期变化三个维度观察研究热点。",
    };
  }
  if (pathname.startsWith("/exports")) {
    return {
      eyebrow: "Export Studio",
      title: "批量导出配置",
      description: "按字段映射组装定制化导出表，避免每次手动整理论文元数据。",
    };
  }
  if (pathname.startsWith("/admin")) {
    return {
      eyebrow: "Admin Control",
      title: "账户与权限",
      description: "维护成员账户、角色状态和初始密码策略，确保研究控制台可持续运作。",
    };
  }

  return {
    eyebrow: "Daily Intake",
    title: "今日文献池",
    description: `${user.role === "admin" ? "管理并分发" : "浏览并收藏"} 最新导入的共享论文，支持筛选、导出和快速查看摘要。`,
  };
}

function groupSeriesByJournal(series: TrendPoint[]) {
  const grouped = new Map<string, TrendPoint[]>();
  for (const point of series) {
    const journal = point.journal || "Unknown";
    const current = grouped.get(journal) || [];
    current.push(point);
    grouped.set(journal, current);
  }
  return Array.from(grouped.entries()).map(([journal, points]) => ({ journal, points }));
}

function parseExpandedDates(value: string | null) {
  return value
    ? value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];
}

function sameStringArray(left: string[], right: string[]) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

async function fetchAllPaperDirectory() {
  const collected: PaperItem[] = [];
  let page = 1;

  while (page <= 50) {
    const response = await request<Paginated<PaperItem>>(`/api/papers?page=${page}&page_size=200`);
    if (!response.items.length) {
      break;
    }
    collected.push(...response.items);
    if (collected.length >= response.total) {
      break;
    }
    page += 1;
  }

  return collected;
}

function collectUniqueValues(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value && value.trim()))));
}

function getPaperSelectionKey(item: PaperItem) {
  return `${item.digest_date}:${item.id}`;
}

function comparePaperPriority(left: PaperItem, right: PaperItem) {
  const levelDiff = getInterestPriority(left.interest_level) - getInterestPriority(right.interest_level);
  if (levelDiff !== 0) {
    return levelDiff;
  }
  if (right.interest_score !== left.interest_score) {
    return right.interest_score - left.interest_score;
  }
  return right.id - left.id;
}

function getInterestPriority(level: string) {
  if (level.includes("非常感兴趣")) return 0;
  if (level.includes("感兴趣")) return 1;
  if (level.includes("一般")) return 2;
  return 9;
}

function matchesPaperFilters(item: PaperItem, filters: PaperFilters) {
  if (filters.date && item.digest_date !== filters.date) {
    return false;
  }
  if (filters.category && item.category !== filters.category) {
    return false;
  }
  if (filters.tag && !item.tags.includes(filters.tag)) {
    return false;
  }
  const query = filters.query.trim().toLowerCase();
  if (!query) {
    return true;
  }
  return [
    item.title_en,
    item.title_zh,
    item.summary_zh,
    item.abstract,
    item.journal,
    item.category,
    item.interest_tag,
    item.tags.join(" "),
  ]
    .join(" ")
    .toLowerCase()
    .includes(query);
}

function formatDigestDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" }).format(date);
}

function exportSelectedPapers(items: PaperItem[], kind: "metadata" | "doi-list") {
  if (kind === "doi-list") {
    const content = Array.from(new Set(items.map((item) => item.doi).filter(Boolean))).join("\n");
    downloadFile(`selected-papers-doi-${Date.now()}.txt`, `${content}${content ? "\n" : ""}`, "text/plain;charset=utf-8");
    return;
  }

  const columns = [
    ["digest_date", "digest_date"],
    ["id", "id"],
    ["doi", "doi"],
    ["journal", "journal"],
    ["publish_date", "publish_date"],
    ["category", "category"],
    ["interest_level", "interest_level"],
    ["interest_tag", "interest_tag"],
    ["title_en", "title_en"],
    ["title_zh", "title_zh"],
    ["summary_zh", "summary_zh"],
    ["abstract", "abstract"],
    ["article_url", "article_url"],
    ["tags", "tags"],
  ] as const;

  const rows = items.map((item) =>
    columns.map(([key]) => {
      if (key === "tags") {
        return item.tags.join(" | ");
      }
      return String(item[key as keyof PaperItem] ?? "");
    }),
  );
  downloadFile(`selected-papers-metadata-${Date.now()}.csv`, buildCsv(columns.map(([, label]) => label), rows), "text/csv;charset=utf-8");
}

function exportSelectedFavorites(items: FavoriteItem[], kind: "metadata" | "doi-list") {
  if (kind === "doi-list") {
    const content = Array.from(new Set(items.map((item) => item.doi).filter(Boolean))).join("\n");
    downloadFile(`selected-favorites-doi-${Date.now()}.txt`, `${content}${content ? "\n" : ""}`, "text/plain;charset=utf-8");
    return;
  }

  const headers = [
    "favorite_id",
    "paper_id",
    "digest_date",
    "favorited_at",
    "doi",
    "journal",
    "publish_date",
    "category",
    "interest_level",
    "interest_tag",
    "review_interest_level",
    "review_interest_tag",
    "review_final_decision",
    "review_final_category",
    "reviewer_notes",
    "review_updated_at",
    "title_en",
    "title_zh",
    "article_url",
  ];
  const rows = items.map((item) => [
    item.id,
    item.paper_id,
    item.digest_date || "",
    item.favorited_at,
    item.doi,
    item.journal,
    item.publish_date,
    item.category,
    item.interest_level,
    item.interest_tag,
    item.review_interest_level,
    item.review_interest_tag,
    item.review_final_decision,
    item.review_final_category,
    item.reviewer_notes,
    item.review_updated_at || "",
    item.title_en,
    item.title_zh,
    item.article_url,
  ]);
  downloadFile(`selected-favorites-metadata-${Date.now()}.csv`, buildCsv(headers, rows), "text/csv;charset=utf-8");
}

function buildCsv(headers: string[], rows: Array<Array<string | number>>) {
  return [headers, ...rows]
    .map((row) =>
      row
        .map((value) => `"${String(value ?? "").replace(/"/g, "\"\"")}"`)
        .join(","),
    )
    .join("\n");
}

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default App;
