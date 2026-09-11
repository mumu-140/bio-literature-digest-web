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
import {
  IconArrowDownTray,
  IconBookOpen,
  IconCloudArrowDown,
  IconSend,
  IconStar,
  IconUsers,
} from "./features/shared/Icons";
import { BackToTopButton } from "./features/shared/WorkbenchUi";

const APP_HOSTNAME = import.meta.env.VITE_APP_HOSTNAME || "localhost";

const navItems = [
  {
    to: "/papers/published",
    label: "发布日期文献",
    shortLabel: "文献",
    icon: IconBookOpen,
  },
  {
    to: "/pushes",
    label: "推送文献",
    shortLabel: "推送",
    icon: IconSend,
  },
  {
    to: "/favorites",
    label: "收藏与备注",
    shortLabel: "收藏",
    icon: IconStar,
  },
  {
    to: "/exports",
    label: "批量导出",
    shortLabel: "导出",
    icon: IconArrowDownTray,
  },
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

  // Global keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (
        event.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes((event.target as HTMLElement)?.tagName)
      ) {
        event.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>("input[name='paper_search']");
        if (searchInput) {
          searchInput.focus();
          searchInput.select();
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  if (loading) {
    return (
      <div className="shell-loading">
        <span className="loading-spinner shell-spinner" />
        <span>正在载入文献工作台…</span>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginScreen onLogin={setUser} />} />
      <Route
        path="*"
        element={
          <ProtectedLayout user={user} onUserChange={setUser}>
            <Routes>
              <Route
                path="/"
                element={<Navigate to={restoreRememberedRoute() || "/papers/published"} replace />}
              />
              <Route path="/digests/today" element={<Navigate to="/papers/published" replace />} />
              <Route path="/papers/published" element={<DigestPage user={user!} />} />
              <Route path="/pushes" element={<PushInboxPage user={user!} />} />
              <Route path="/favorites" element={<FavoritesPage user={user!} />} />
              <Route path="/exports" element={<ExportsPage user={user!} />} />
              <Route
                path="/admin/users"
                element={
                  user?.role === "admin" ? <AdminUsersPage /> : <Navigate to="/papers/published" replace />
                }
              />
              <Route
                path="/admin/imports"
                element={
                  user?.role === "admin" ? <AdminImportsPage /> : <Navigate to="/papers/published" replace />
                }
              />
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
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`}
        replace
      />
    );
  }

  async function handleLogout() {
    await logout();
    onUserChange(null);
    navigate("/login");
  }

  const pageMeta = getPageMeta(location.pathname, user);
  const userInitial = (user.name || user.email || "U")[0].toUpperCase();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <div className="brand-badge">
              <span className="brand-dot" />
              <span className="brand-domain">{APP_HOSTNAME}</span>
            </div>
            <h1 className="brand-heading">Bio Literature</h1>
            <p className="brand-sub">Research Console</p>
          </div>

          <div className="user-profile-card">
            <div className="user-avatar" aria-hidden="true">
              {userInitial}
            </div>
            <div className="user-details">
              <strong className="user-name">{user.name || user.email.split("@")[0]}</strong>
              <div className="user-role-badge">
                <span className={`role-pill role-${user.role}`}>
                  {user.role === "admin" ? "管理员" : "研究成员"}
                </span>
                <span className="user-status-dot" title="系统连接正常" />
              </div>
            </div>
          </div>
        </div>

        <nav className="nav-list">
          <div className="nav-group-label">主要导航</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}
              >
                <Icon size={18} className="nav-link-icon" />
                <span className="nav-link-label">{item.label}</span>
              </NavLink>
            );
          })}

          {user.role === "admin" ? (
            <>
              <div className="nav-group-label admin-group-label">系统管理</div>
              <NavLink
                to="/admin/users"
                className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}
              >
                <IconUsers size={18} className="nav-link-icon" />
                <span className="nav-link-label">账户与权限</span>
              </NavLink>
              <NavLink
                to="/admin/imports"
                className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}
              >
                <IconCloudArrowDown size={18} className="nav-link-icon" />
                <span className="nav-link-label">导入与同步</span>
              </NavLink>
            </>
          ) : null}
        </nav>

        <div className="sidebar-footer">
          <div className="system-status-indicator">
            <span className="status-indicator-dot" />
            <span>本地知识库在线</span>
          </div>
          <p className="small-copy sidebar-note">
            基于学术文献库的本地结构化检索、智能研讨与重点分发工作台。
          </p>
          <button
            className="ghost-button sidebar-logout"
            onClick={handleLogout}
            title="退出当前登录账户"
          >
            退出当前账户
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <div className="mobile-topbar">
          <div className="mobile-topbar-copy">
            <span className="brand-domain-mobile">{APP_HOSTNAME}</span>
            <strong>Bio Literature</strong>
            <span className="muted mobile-user-name">
              {user.name} ({user.role === "admin" ? "管理员" : "成员"})
            </span>
          </div>
          <div className="mobile-top-meta">
            <button className="ghost-button mobile-logout" onClick={handleLogout}>
              退出
            </button>
          </div>
        </div>

        <div className="main-frame">
          <header className="page-hero">
            <div>
              <p className="eyebrow">{pageMeta.eyebrow}</p>
              <h2>{pageMeta.title}</h2>
              <p className="muted hero-copy">{pageMeta.description}</p>
            </div>
            <div className="hero-badge">
              {user.role === "admin" ? "Admin Console" : "Member Console"}
            </div>
          </header>
          {children}
        </div>

        <BackToTopButton />

        {/* Mobile Tabbar with SVGs */}
        <nav className="mobile-tabbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `mobile-tablink${isActive ? " is-active" : ""}`}
              >
                <span className="mobile-tabicon">
                  <Icon size={18} />
                </span>
                <span className="mobile-tabcopy">{item.shortLabel}</span>
              </NavLink>
            );
          })}
          {user.role === "admin" ? (
            <NavLink
              to="/admin/users"
              className={({ isActive }) => `mobile-tablink${isActive ? " is-active" : ""}`}
            >
              <span className="mobile-tabicon">
                <IconUsers size={18} />
              </span>
              <span className="mobile-tabcopy">账户</span>
            </NavLink>
          ) : null}
          {user.role === "admin" ? (
            <NavLink
              to="/admin/imports"
              className={({ isActive }) => `mobile-tablink${isActive ? " is-active" : ""}`}
            >
              <span className="mobile-tabicon">
                <IconCloudArrowDown size={18} />
              </span>
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
      navigate(
        sanitizeRememberedRoute(searchParams.get("next")) ||
          restoreRememberedRoute() ||
          "/papers/published",
        {
          replace: true,
        },
      );
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-panel">
        <div className="login-header">
          <div className="brand-badge login-badge">
            <span className="brand-dot" />
            <span>{APP_HOSTNAME}</span>
          </div>
          <h1>Bio Literature Digest</h1>
          <p className="muted">
            学术文献研讨控制台：本地结构化归档、智能筛选、多篇研讨与重点推送。
          </p>
        </div>

        {hintedEmail ? (
          <div className="login-hint-banner">
            本邮件直达链接对应账户：<strong>{hintedEmail}</strong>
          </div>
        ) : null}

        <form className="stack login-form" onSubmit={submit}>
          <label>
            <span className="field-label">电子邮箱</span>
            <input
              type="email"
              required
              placeholder="name@example.com"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
          </label>
          <label>
            <span className="field-label">显示姓名（可选）</span>
            <input
              placeholder="例如：杨森"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
            />
          </label>
          {error ? <div className="notice-banner is-error">{error}</div> : null}
          <button className="primary-button login-submit-btn" type="submit" disabled={pending}>
            {pending ? (
              <>
                <span className="loading-spinner" />
                <span>正在验证登录…</span>
              </>
            ) : (
              <span>进入文献工作台</span>
            )}
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
      description: "把个人收藏沉淀为稳定学术样本，便于后续导出、比对和人工深度评审。",
    };
  }
  if (pathname.startsWith("/exports")) {
    return {
      eyebrow: "Export Studio",
      title: "批量导出配置",
      description: "按字段映射组装定制化导出表，一键获取精准的学术元数据报表。",
    };
  }
  if (pathname.startsWith("/admin/imports")) {
    return {
      eyebrow: "Import Control",
      title: "导入与同步管理",
      description: "查看 Producer SQLite 的最新可用运行，并手动触发导入或重导入到工作台数据面。",
    };
  }
  if (pathname.startsWith("/admin")) {
    return {
      eyebrow: "Admin Control",
      title: "账户与权限",
      description: "维护成员账户与订阅状态，保障文献系统与团队分发平稳运作。",
    };
  }

  return {
    eyebrow: "Published Library",
    title: "发布日期文献库",
    description: `${user.role === "admin" ? "管理并分发" : "浏览并收藏"} 按发布日期整理的论文，支持多维筛选、一键导出与 DeerFlow 研讨。`,
  };
}

export default App;
