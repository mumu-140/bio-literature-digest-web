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
import { AuthUser, fetchAuthUser, login, logout } from "./dataClient";
import { AdminImportsPage } from "./features/admin/AdminImportsPage";
import { AdminUsersPage } from "./features/admin/AdminUsersPage";
import { DigestPage } from "./features/digest/DigestPage";
import {
  rememberRoute,
  restoreRememberedRoute,
  sanitizeRememberedRoute,
} from "./features/digest/browserState";
import { ExportsPage } from "./features/exports/ExportsPage";
import { FavoritesPage } from "./features/favorites/FavoritesPage";
import { PushInboxPage } from "./features/pushes/PushInboxPage";

const APP_HOSTNAME = import.meta.env.VITE_APP_HOSTNAME || "localhost";

const navItems = [
  { to: "/papers/published", label: "发布日期文献", shortLabel: "文献" },
  { to: "/pushes", label: "推送文献", shortLabel: "推送" },
  { to: "/favorites", label: "收藏文献", shortLabel: "收藏" },
  { to: "/exports", label: "批量导出", shortLabel: "导出" },
];

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuthUser()
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
              <Route path="/" element={<Navigate to={restoreRememberedRoute() || "/papers/published"} replace />} />
              <Route path="/digests/today" element={<Navigate to="/papers/published" replace />} />
              <Route path="/papers/published" element={<DigestPage user={user!} />} />
              <Route path="/pushes" element={<PushInboxPage user={user!} />} />
              <Route path="/favorites" element={<FavoritesPage user={user!} />} />
              <Route path="/exports" element={<ExportsPage user={user!} />} />
              <Route path="/admin/users" element={user?.role === "admin" ? <AdminUsersPage /> : <Navigate to="/papers/published" replace />} />
              <Route path="/admin/imports" element={user?.role === "admin" ? <AdminImportsPage /> : <Navigate to="/papers/published" replace />} />
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

  useEffect(() => {
    rememberRoute(`${location.pathname}${location.search}`);
  }, [location.pathname, location.search]);

  if (!user) {
    return <Navigate to={`/login?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`} replace />;
  }

  async function handleLogout() {
    await logout();
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
            Local import workspace
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
          {user.role === "admin" ? (
            <NavLink to="/admin/imports" className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
              导入管理
            </NavLink>
          ) : null}
        </nav>
        <div className="sidebar-footer">
          <p className="small-copy">
            用统一视图查看本地导入文献、收藏和低频人工备注。
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
          {children}
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
          {user.role === "admin" ? (
            <NavLink to="/admin/imports" className={({ isActive }) => `mobile-tablink${isActive ? " is-active" : ""}`}>
              <span className="mobile-tabicon">导</span>
              <span className="mobile-tabcopy">导入</span>
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
  const [form, setForm] = useState({ email: searchParams.get("email") || "", name: "" });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setForm((current) => (current.email === hintedEmail ? current : { ...current, email: hintedEmail }));
  }, [hintedEmail]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const response = await login(form);
      onLogin(response.user);
      navigate(sanitizeRememberedRoute(searchParams.get("next")) || restoreRememberedRoute() || "/papers/published", {
        replace: true,
      });
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
        <h1>Bio Literature Digest</h1>
        <p className="muted">
          登录以访问本地导入文献、收藏、人工备注和批量导出。
        </p>
        {hintedEmail ? <p className="muted">本邮件链接对应账户：{hintedEmail}</p> : null}
        <form className="stack" onSubmit={submit}>
          <label>
            邮箱
            <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          <label>
            昵称（可选）
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
          {error ? <p className="error-text">{error}</p> : null}
          <button className="primary-button" type="submit" disabled={pending}>
            {pending ? "登录中…" : "登录"}
          </button>
        </form>
      </div>
    </div>
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
      title: "收藏与人工备注",
      description: "把个人收藏沉淀为稳定样本，便于后续导出、比对和少量人工备注。",
    };
  }
  if (pathname.startsWith("/exports")) {
    return {
      eyebrow: "Export Studio",
      title: "批量导出配置",
      description: "按字段映射组装定制化导出表，避免每次手动整理论文元数据。",
    };
  }
  if (pathname.startsWith("/admin/imports")) {
    return {
      eyebrow: "Import Control",
      title: "导入与重导入",
      description: "查看 producer SQLite 的最新可用运行，并手动触发导入或重导入到本地工作台数据面。",
    };
  }
  if (pathname.startsWith("/admin")) {
    return {
      eyebrow: "Admin Control",
      title: "账户与权限",
      description: "维护成员账户与角色状态，确保研究控制台可持续运作。",
    };
  }

  return {
    eyebrow: "Published Library",
    title: "发布日期文献库",
    description: `${user.role === "admin" ? "管理并分发" : "浏览并收藏"} 按发布日期整理的论文，支持筛选、导出和快速查看摘要。`,
  };
}

export default App;
