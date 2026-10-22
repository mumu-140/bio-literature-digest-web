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
import {
  AuthUser,
  fetchAuthUser,
  login,
  registerAccount,
  requestRegisterOtp,
  type LoginOtpIssued,
  logout,
} from "./dataClient";
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

const COMMON_EMAIL_DOMAIN_TYPOS: Record<string, string> = {
  "qq.ocm": "qq.com",
  "qq.con": "qq.com",
  "qq.cm": "qq.com",
  "qq.co": "qq.com",
  "qq.cmo": "qq.com",
  "163.ocm": "163.com",
  "163.con": "163.com",
  "163.cm": "163.com",
  "126.ocm": "126.com",
  "126.con": "126.com",
  "gmail.ocm": "gmail.com",
  "gmail.con": "gmail.com",
  "gamil.com": "gmail.com",
  "gmial.com": "gmail.com",
  "outlook.ocm": "outlook.com",
  "outlook.con": "outlook.com",
  "hotmail.ocm": "hotmail.com",
  "icloud.ocm": "icloud.com",
  "foxmail.ocm": "foxmail.com",
};

function getSuggestedEmailForTypo(rawEmail: string): string | null {
  const trimmed = rawEmail.trim();
  const atIndex = trimmed.lastIndexOf("@");
  if (atIndex <= 0) {
    return null;
  }
  const localPart = trimmed.slice(0, atIndex);
  const domain = trimmed.slice(atIndex + 1).toLowerCase();
  const fixedDomain = COMMON_EMAIL_DOMAIN_TYPOS[domain];
  if (fixedDomain) {
    return `${localPart}@${fixedDomain}`;
  }
  return null;
}

function LoginScreen({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const hintedEmail = searchParams.get("email") || "";
  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const [mode, setMode] = useState<"login" | "register" | "reset">(initialMode);
  const [email, setEmail] = useState(hintedEmail);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [issued, setIssued] = useState<LoginOtpIssued | null>(null);
  const [resendIn, setResendIn] = useState(0);
  const [otpSending, setOtpSending] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (hintedEmail) {
      setEmail(hintedEmail);
    }
  }, [hintedEmail]);

  useEffect(() => {
    if (resendIn <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setResendIn((value) => (value <= 1 ? 0 : value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendIn]);

  function switchMode(nextMode: "login" | "register" | "reset") {
    setMode(nextMode);
    setError("");
    setIssued(null);
    setCode("");
    setPassword("");
    setConfirmPassword("");
  }

  function finishAuth(authenticatedUser: AuthUser) {
    onLogin(authenticatedUser);
    navigate(
      sanitizeRememberedRoute(searchParams.get("next")) ||
        restoreRememberedRoute() ||
        "/papers/published",
      {
        replace: true,
      },
    );
  }

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const response = await login({ email: email.trim(), password });
      finishAuth(response.user);
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setPending(false);
    }
  }

  const isSameIssuedEmail = Boolean(
    issued && issued.email.toLowerCase() === email.trim().toLowerCase(),
  );
  const activeCooldown = isSameIssuedEmail ? resendIn : 0;
  const suggestedEmail = getSuggestedEmailForTypo(email);

  async function handleSendOtp() {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError("请先输入电子邮箱地址");
      return;
    }
    if (suggestedEmail) {
      setError(`邮箱后缀疑似拼写错误，请检查是否应为 ${suggestedEmail}`);
      return;
    }
    if (activeCooldown > 0 || otpSending) {
      return;
    }
    setOtpSending(true);
    setError("");
    try {
      const purpose = mode === "reset" ? "reset" : "register";
      const nextIssued = await requestRegisterOtp(trimmedEmail, purpose);
      setIssued(nextIssued);
      setResendIn(Math.max(nextIssued.resend_after, 1));
    } catch (sendError) {
      setError((sendError as Error).message);
    } finally {
      setOtpSending(false);
    }
  }

  async function submitRegisterOrReset(event: FormEvent) {
    event.preventDefault();
    if (password.trim().length < 6) {
      setError("登录密码长度至少为 6 位");
      return;
    }
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致，请重新确认");
      return;
    }
    if (!code.trim()) {
      setError("请输入邮箱收到的 6 位验证码");
      return;
    }
    setPending(true);
    setError("");
    try {
      const purpose = mode === "reset" ? "reset" : "register";
      const response = await registerAccount({
        email: email.trim(),
        code: code.trim(),
        password,
        name: mode === "register" ? name.trim() : undefined,
        purpose,
      });
      finishAuth(response.user);
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setPending(false);
    }
  }

  const canGuideToRegister =
    mode === "login" &&
    Boolean(error) &&
    (error.includes("尚未设置登录密码") || error.includes("尚未注册"));

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

        <div className="login-mode-tabs" role="tablist" aria-label="登录与注册切换">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={`login-mode-tab${mode === "login" ? " is-active" : ""}`}
            onClick={() => switchMode("login")}
          >
            账户登录
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={`login-mode-tab${mode === "register" ? " is-active" : ""}`}
            onClick={() => switchMode("register")}
          >
            注册 / 首次设密
          </button>
        </div>

        {mode === "reset" ? (
          <div className="login-submode-bar">
            <span>通过邮箱验证码重置登录密码</span>
            <button
              type="button"
              className="text-link-btn"
              onClick={() => switchMode("login")}
            >
              返回密码登录
            </button>
          </div>
        ) : null}

        {hintedEmail ? (
          <div className="login-hint-banner">
            本邮件直达链接对应账户：<strong>{hintedEmail}</strong>
          </div>
        ) : null}

        {mode === "login" ? (
          <form className="stack login-form" onSubmit={submitLogin}>
            <label>
              <span className="field-label">账户邮箱</span>
              <input
                type="email"
                name="email"
                autoComplete="username"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (error) {
                    setError("");
                  }
                }}
              />
            </label>
            {suggestedEmail ? (
              <div className="notice-banner is-error">
                <div>
                  检测到邮箱后缀可能拼写有误，是否应为 <strong>{suggestedEmail}</strong>？
                </div>
                <button
                  type="button"
                  className="banner-action-btn"
                  onClick={() => {
                    setEmail(suggestedEmail);
                    setError("");
                  }}
                >
                  一键修正为 {suggestedEmail} →
                </button>
              </div>
            ) : null}
            <label>
              <div className="field-label-row">
                <span className="field-label">登录密码</span>
                <button
                  type="button"
                  className="text-link-btn"
                  onClick={() => switchMode("reset")}
                >
                  忘记密码？
                </button>
              </div>
              <div className="password-input-wrap">
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  autoComplete="current-password"
                  required
                  placeholder="请输入登录密码"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "隐藏密码" : "显示密码"}
                >
                  {showPassword ? "隐藏" : "显示"}
                </button>
              </div>
            </label>

            {error ? (
              <div className="notice-banner is-error">
                <div>{error}</div>
                {canGuideToRegister ? (
                  <button
                    type="button"
                    className="banner-action-btn"
                    onClick={() => switchMode("register")}
                  >
                    前往「注册 / 首次设密」验证邮箱并设置密码 →
                  </button>
                ) : null}
              </div>
            ) : null}

            <button className="primary-button login-submit-btn" type="submit" disabled={pending}>
              {pending ? (
                <>
                  <span className="loading-spinner" />
                  <span>正在登录工作台…</span>
                </>
              ) : (
                <span>登录工作台</span>
              )}
            </button>

            <p className="login-footer-copy muted">
              原有免密账户首次登录或新用户？{" "}
              <button
                type="button"
                className="text-link-btn"
                onClick={() => switchMode("register")}
              >
                立即验证邮箱设密 / 注册
              </button>
            </p>
          </form>
        ) : (
          <form className="stack login-form" onSubmit={submitRegisterOrReset}>
            {mode === "register" ? (
              <p className="small-copy" style={{ margin: 0 }}>
                新邮箱将自动创建账户；原有免密账户验证邮箱后将直接绑定新密码（自动保留原有角色权限与收藏数据）。
              </p>
            ) : null}
            <label>
              <span className="field-label">电子邮箱</span>
              <input
                type="email"
                name="email"
                autoComplete="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (error) {
                    setError("");
                  }
                }}
              />
            </label>

            {suggestedEmail ? (
              <div className="notice-banner is-error">
                <div>
                  检测到邮箱后缀可能拼写有误，是否应为 <strong>{suggestedEmail}</strong>？
                </div>
                <button
                  type="button"
                  className="banner-action-btn"
                  onClick={() => {
                    setEmail(suggestedEmail);
                    setError("");
                  }}
                >
                  一键修正为 {suggestedEmail} →
                </button>
              </div>
            ) : null}

            <label>
              <span className="field-label">邮箱验证码</span>
              <div className="otp-input-row">
                <input
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  maxLength={8}
                  placeholder="6 位数字验证码"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
                <button
                  type="button"
                  className="ghost-button otp-send-btn"
                  disabled={otpSending || activeCooldown > 0 || !email.trim()}
                  onClick={() => void handleSendOtp()}
                >
                  {otpSending
                    ? "发送中…"
                    : activeCooldown > 0
                      ? `${activeCooldown}s 后重发`
                      : isSameIssuedEmail
                        ? "重新获取"
                        : "获取验证码"}
                </button>
              </div>
            </label>

            {issued && isSameIssuedEmail ? (
              <div className="notice-banner is-success login-otp-notice">
                <div>
                  验证码已由 <strong>ai2science@agent.qq.com</strong> 发送至{" "}
                  <strong>{issued.email}</strong>，请在{" "}
                  {Math.max(Math.ceil(issued.expires_in / 60), 1)} 分钟内完成验证。
                </div>
                <div className="small-copy" style={{ marginTop: "0.25rem", opacity: 0.9 }}>
                  若 1 分钟内未收到，请检查邮箱「垃圾箱 / 广告邮件」或核对上方邮箱地址拼写。
                </div>
                {issued.dev_code ? (
                  <div className="dev-code-hint">
                    开发模式验证码：<strong>{issued.dev_code}</strong>
                  </div>
                ) : null}
              </div>
            ) : null}

            {mode === "register" ? (
              <label>
                <span className="field-label">显示姓名（可选）</span>
                <input
                  type="text"
                  name="name"
                  autoComplete="name"
                  placeholder="例如：杨森（留空默认取邮箱前缀）"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
            ) : null}

            <label>
              <span className="field-label">
                {mode === "reset" ? "设置新密码" : "设置登录密码"}
              </span>
              <div className="password-input-wrap">
                <input
                  type={showPassword ? "text" : "password"}
                  name="new_password"
                  autoComplete="new-password"
                  required
                  minLength={6}
                  placeholder="至少 6 位字符"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "隐藏密码" : "显示密码"}
                >
                  {showPassword ? "隐藏" : "显示"}
                </button>
              </div>
            </label>

            <label>
              <span className="field-label">
                {mode === "reset" ? "确认新密码" : "确认登录密码"}
              </span>
              <input
                type={showPassword ? "text" : "password"}
                name="confirm_password"
                autoComplete="new-password"
                required
                minLength={6}
                placeholder="请再次输入密码"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
            </label>

            {error ? <div className="notice-banner is-error">{error}</div> : null}

            <button className="primary-button login-submit-btn" type="submit" disabled={pending}>
              {pending ? (
                <>
                  <span className="loading-spinner" />
                  <span>{mode === "reset" ? "正在重置密码…" : "正在完成注册…"}</span>
                </>
              ) : (
                <span>{mode === "reset" ? "重置密码并登录" : "验证邮箱并完成注册"}</span>
              )}
            </button>

            <p className="login-footer-copy muted">
              已有账户密码？{" "}
              <button
                type="button"
                className="text-link-btn"
                onClick={() => switchMode("login")}
              >
                返回直接登录
              </button>
            </p>
          </form>
        )}
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
