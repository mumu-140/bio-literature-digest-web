import { FormEvent, ReactNode, useDeferredValue, useEffect, useRef, useState } from "react";
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
  ExportJob,
  FavoriteItem,
  FavoriteReviewDraft,
  FavoriteReviewOptions,
  ImportResult,
  ImportRun,
  DigestSortKey,
  PaperItem,
  PaperLibraryGroup,
  PaperLibraryOverview,
  PaperPushItem,
  UserItem,
  checkImportRuns,
  createPush,
  exportCustomTable,
  fetchAdminUsers,
  fetchAuthUser,
  fetchFavoriteReviewOptions,
  fetchImportRuns,
  fetchPaperLibraryGroup,
  fetchPaperLibraryOverview,
  importRun,
  listFavorites,
  listPushes,
  login,
  logout,
  reimportRun,
  request,
  saveFavoriteReview as saveFavoriteReviewRequest,
  toggleFavorite as toggleFavoriteRequest,
  updatePush,
} from "./dataClient";
import {
  rememberRoute,
  persistDigestPageCache,
  persistDigestPageState,
  restoreDigestPageCache,
  restoreDigestPageState,
  restoreRememberedRoute,
  sanitizeRememberedRoute,
} from "./features/digest/browserState";
import {
  DIGEST_FLAGSHIP_JOURNAL_ORDER,
  DIGEST_INITIAL_GROUP_COUNT,
  DIGEST_JOURNAL_MARKER_OVERRIDES,
  DIGEST_TOAST_DURATION_MS,
} from "./features/digest/config";

const APP_HOSTNAME = import.meta.env.VITE_APP_HOSTNAME || "localhost";

type PaperFilters = {
  query: string;
  publishDate: string;
  category: string;
  tag: string;
  sort: DigestSortKey;
};

type ToastState = {
  kind: "success" | "error";
  message: string;
};

const navItems = [
  { to: "/papers/published", label: "发布日期文献", shortLabel: "文献" },
  { to: "/pushes", label: "推送文献", shortLabel: "推送" },
  { to: "/favorites", label: "收藏文献", shortLabel: "收藏" },
  { to: "/exports", label: "批量导出", shortLabel: "导出" },
];

function useAdminUsers(enabled: boolean) {
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

function DigestPage({ user }: { user: AuthUser }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const adminUsers = useAdminUsers(user.role === "admin");
  const hasExplicitDigestParams = hasDigestSearchParams(searchParams);
  const storedDigestState = restoreDigestPageState();
  const initialFilters = hasExplicitDigestParams
    ? buildPaperFiltersFromSearchParams(searchParams)
    : storedDigestState?.filters ?? buildPaperFiltersFromSearchParams(searchParams);
  const canRestoreDigestSnapshot = Boolean(storedDigestState && arePaperFiltersEqual(storedDigestState.filters, initialFilters));
  const storedDigestCache = canRestoreDigestSnapshot ? restoreDigestPageCache() : null;
  const initialLoadedGroups = storedDigestCache?.loadedGroups || storedDigestCache?.overview?.loaded_groups || [];
  const [overview, setOverview] = useState<PaperLibraryOverview | null>(storedDigestCache?.overview ?? null);
  const [loadedGroups, setLoadedGroups] = useState<Record<string, PaperLibraryGroup>>(() => buildLoadedGroupMap(initialLoadedGroups));
  const [filters, setFilters] = useState<PaperFilters>(initialFilters);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [pushTargetUserId, setPushTargetUserId] = useState("");
  const [pushNote, setPushNote] = useState("");
  const [pushMessage, setPushMessage] = useState("");
  const [loadingOverview, setLoadingOverview] = useState(storedDigestCache?.overview ? false : true);
  const [refreshingOverview, setRefreshingOverview] = useState(false);
  const [loadingGroupDates, setLoadingGroupDates] = useState<string[]>([]);
  const [pendingFavoriteIds, setPendingFavoriteIds] = useState<number[]>([]);
  const [exportMessage, setExportMessage] = useState("");
  const [favoriteToast, setFavoriteToast] = useState<ToastState | null>(null);
  const [activeRailDate, setActiveRailDate] = useState(
    canRestoreDigestSnapshot ? storedDigestState?.activeRailDate || initialFilters.publishDate : initialFilters.publishDate,
  );
  const [expandedPublishDates, setExpandedPublishDates] = useState<string[]>(
    canRestoreDigestSnapshot ? storedDigestState?.expandedPublishDates || [] : [],
  );
  const [requestVersion, setRequestVersion] = useState(0);
  const deferredQuery = useDeferredValue(filters.query.trim());
  const lastLoadedSignatureRef = useRef(storedDigestCache?.overview ? getPaperFiltersSignature(initialFilters) : "");
  const restoreScrollYRef = useRef(canRestoreDigestSnapshot ? storedDigestState?.scrollY || 0 : 0);
  const shouldRestoreScrollRef = useRef(Boolean(canRestoreDigestSnapshot && storedDigestCache?.overview));

  const appliedFilters: PaperFilters = {
    ...filters,
    query: deferredQuery,
  };
  const filterSignature = getPaperFiltersSignature(appliedFilters);
  const groupSummaries = overview?.groups || [];
  const publishDateOptions = overview?.available_publish_dates || [];
  const categoryOptions = overview?.available_categories || [];
  const tagOptions = overview?.available_tags || [];
  const loadedPapers = collectLoadedPapers(loadedGroups, groupSummaries);
  const visibleLoadedPapers = collectVisibleLoadedPapers(loadedGroups, expandedPublishDates, groupSummaries);
  const selectedKeySet = new Set(selectedKeys);
  const pendingFavoriteIdSet = new Set(pendingFavoriteIds);
  const allVisibleSelected = visibleLoadedPapers.length > 0 && visibleLoadedPapers.every((paper) => selectedKeySet.has(getPaperSelectionKey(paper)));

  useEffect(() => {
    if (!hasDigestSearchParams(searchParams)) {
      return;
    }
    const nextFilters = buildPaperFiltersFromSearchParams(searchParams);
    setFilters((current) => (arePaperFiltersEqual(current, nextFilters) ? current : nextFilters));
  }, [searchParams]);

  useEffect(() => {
    if (user.role === "admin" && adminUsers.length && !pushTargetUserId) {
      setPushTargetUserId(String(adminUsers[0].id));
    }
  }, [adminUsers, pushTargetUserId, user.role]);

  useEffect(() => {
    const next = new URLSearchParams();
    if (filters.query.trim()) next.set("q", filters.query.trim());
    if (filters.publishDate) next.set("publish_date", filters.publishDate);
    if (filters.category) next.set("category", filters.category);
    if (filters.tag) next.set("tag", filters.tag);
    if (filters.sort !== "publish_date_desc") next.set("sort", filters.sort);
    setSearchParams(next, { replace: true });
  }, [filters, setSearchParams]);

  useEffect(() => {
    let ignore = false;
    if (lastLoadedSignatureRef.current !== filterSignature) {
      restoreScrollYRef.current = 0;
    }
    if (overview) {
      setRefreshingOverview(true);
    } else {
      setLoadingOverview(true);
    }

    fetchPaperLibraryOverview({
      q: appliedFilters.query,
      publish_date: appliedFilters.publishDate,
      category: appliedFilters.category,
      tag: appliedFilters.tag,
      sort: appliedFilters.sort,
      initial_group_count: DIGEST_INITIAL_GROUP_COUNT,
    })
      .then((response) => {
        if (ignore) {
          return;
        }
        setOverview(response);
        setLoadedGroups(buildLoadedGroupMap(response.loaded_groups));
        setExpandedPublishDates((current) =>
          sanitizeExpandedPublishDates(
            appliedFilters.publishDate
              ? [appliedFilters.publishDate]
              : current.length
                ? current
                : response.loaded_groups.map((group) => group.publish_date),
            response.groups,
          ),
        );
        setActiveRailDate((current) => pickActiveRailDate(current, appliedFilters.publishDate, response.groups));
        lastLoadedSignatureRef.current = filterSignature;
        shouldRestoreScrollRef.current = true;
      })
      .catch(() => {
        if (ignore) {
          return;
        }
        setOverview((current) => current);
      })
      .finally(() => {
        if (ignore) {
          return;
        }
        setLoadingOverview(false);
        setRefreshingOverview(false);
      });

    return () => {
      ignore = true;
    };
  }, [
    appliedFilters.category,
    appliedFilters.publishDate,
    appliedFilters.query,
    appliedFilters.sort,
    appliedFilters.tag,
    filterSignature,
    requestVersion,
  ]);

  useEffect(() => {
    const validKeys = new Set(loadedPapers.map(getPaperSelectionKey));
    setSelectedKeys((current) => {
      const next = current.filter((key) => validKeys.has(key));
      if (next.length === current.length && next.every((key, index) => key === current[index])) {
        return current;
      }
      return next;
    });
  }, [loadedPapers]);

  useEffect(() => {
    persistDigestPageState({
      filters,
      activeRailDate,
      expandedPublishDates,
      scrollY: window.scrollY,
    });
  }, [filters, activeRailDate, expandedPublishDates]);

  useEffect(() => {
    if (!overview) {
      return;
    }
    persistDigestPageCache({
      overview,
      loadedGroups: groupSummaries
        .map((group) => loadedGroups[group.publish_date])
        .filter((group): group is PaperLibraryGroup => Boolean(group)),
    });
  }, [groupSummaries, loadedGroups, overview]);

  useEffect(() => {
    let scrollPersistTimer = 0;
    const persistCurrentScroll = () => {
      persistDigestPageState({
        filters,
        activeRailDate,
        expandedPublishDates,
        scrollY: window.scrollY,
      });
    };
    const scheduleScrollPersist = () => {
      if (scrollPersistTimer) {
        return;
      }
      scrollPersistTimer = window.setTimeout(() => {
        scrollPersistTimer = 0;
        persistCurrentScroll();
      }, 120);
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        persistCurrentScroll();
      }
    };

    window.addEventListener("scroll", scheduleScrollPersist, { passive: true });
    window.addEventListener("pagehide", persistCurrentScroll);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      if (scrollPersistTimer) {
        window.clearTimeout(scrollPersistTimer);
      }
      persistCurrentScroll();
      window.removeEventListener("scroll", scheduleScrollPersist);
      window.removeEventListener("pagehide", persistCurrentScroll);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [filters, activeRailDate, expandedPublishDates]);

  useEffect(() => {
    if (!overview || !shouldRestoreScrollRef.current) {
      return;
    }
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: restoreScrollYRef.current, left: 0, behavior: "auto" });
    });
    shouldRestoreScrollRef.current = false;
  }, [loadedGroups, overview]);

  useEffect(() => {
    if (!groupSummaries.length) {
      return;
    }

    let frame = 0;
    const updateActiveDateFromScroll = () => {
      frame = 0;
      const nextActive = pickActiveRailDateFromScroll(groupSummaries);
      if (!nextActive) {
        return;
      }
      setActiveRailDate((current) => (current === nextActive ? current : nextActive));
    };

    const scheduleUpdate = () => {
      if (frame) {
        return;
      }
      frame = window.requestAnimationFrame(updateActiveDateFromScroll);
    };

    scheduleUpdate();
    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);

    return () => {
      if (frame) {
        window.cancelAnimationFrame(frame);
      }
      window.removeEventListener("scroll", scheduleUpdate);
      window.removeEventListener("resize", scheduleUpdate);
    };
  }, [groupSummaries]);

  useEffect(() => {
    if (!favoriteToast) {
      return;
    }
    const timer = window.setTimeout(() => setFavoriteToast(null), DIGEST_TOAST_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [favoriteToast]);

  async function toggleFavorite(item: PaperItem) {
    if (pendingFavoriteIdSet.has(item.id)) {
      return;
    }
    setPendingFavoriteIds((current) => [...current, item.id]);
    try {
      await toggleFavoriteRequest(item.id, item.is_favorited);
      setLoadedGroups((current) => updateFavoriteStateInGroups(current, item.id, !item.is_favorited));
      setFavoriteToast({
        kind: "success",
        message: item.is_favorited ? "已取消收藏" : "已加入收藏",
      });
    } catch (error) {
      setFavoriteToast({
        kind: "error",
        message: error instanceof Error ? error.message : "收藏状态保存失败",
      });
    } finally {
      setPendingFavoriteIds((current) => current.filter((value) => value !== item.id));
    }
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
    const selected = loadedPapers.filter((item) => selectedKeys.includes(getPaperSelectionKey(item)));
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
    await createPush({
      paper_id: item.id,
      recipient_user_id: Number(pushTargetUserId),
      note: pushNote,
    });
    setPushMessage(`已将《${item.title_en}》推送给账户 ${pushTargetUserId}。`);
  }

  async function ensureGroupLoaded(publishDate: string) {
    if (loadedGroups[publishDate]) {
      return;
    }
    setLoadingGroupDates((current) => (current.includes(publishDate) ? current : [...current, publishDate]));
    try {
      const group = await fetchPaperLibraryGroup(publishDate, {
        q: appliedFilters.query,
        category: appliedFilters.category,
        tag: appliedFilters.tag,
        sort: appliedFilters.sort,
      });
      setLoadedGroups((current) => ({ ...current, [publishDate]: group }));
    } finally {
      setLoadingGroupDates((current) => current.filter((value) => value !== publishDate));
    }
  }

  async function loadMoreGroup(publishDate: string) {
    const currentGroup = loadedGroups[publishDate];
    if (!currentGroup?.has_more || loadingGroupDates.includes(publishDate)) {
      return;
    }
    setLoadingGroupDates((current) => [...current, publishDate]);
    try {
      const nextGroup = await fetchPaperLibraryGroup(publishDate, {
        q: appliedFilters.query,
        category: appliedFilters.category,
        tag: appliedFilters.tag,
        sort: appliedFilters.sort,
        page: currentGroup.page + 1,
        page_size: currentGroup.page_size,
      });
      setLoadedGroups((current) => ({
        ...current,
        [publishDate]: {
          ...nextGroup,
          items: [...(current[publishDate]?.items || []), ...nextGroup.items],
        },
      }));
    } finally {
      setLoadingGroupDates((current) => current.filter((value) => value !== publishDate));
    }
  }

  async function scrollToDate(publishDate: string) {
    setActiveRailDate(publishDate);
    setExpandedPublishDates((current) => ensurePublishDateExpanded(current, publishDate, groupSummaries));
    await ensureGroupLoaded(publishDate);
    window.requestAnimationFrame(() => {
      document.getElementById(`digest-day-${publishDate}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  async function togglePublishDateGroup(publishDate: string) {
    const isExpanded = expandedPublishDates.includes(publishDate);
    if (isExpanded) {
      setExpandedPublishDates((current) => current.filter((value) => value !== publishDate));
      return;
    }
    setExpandedPublishDates((current) => ensurePublishDateExpanded(current, publishDate, groupSummaries));
    setActiveRailDate(publishDate);
    await ensureGroupLoaded(publishDate);
  }

  function clearFilters() {
    setFilters((current) => ({
      query: "",
      publishDate: "",
      category: "",
      tag: "",
      sort: current.sort,
    }));
  }

  function clearSelection() {
    setSelectedKeys([]);
  }

  return (
    <div className="content-stack">
      {favoriteToast ? <ToastBanner toast={favoriteToast} onClose={() => setFavoriteToast(null)} /> : null}
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">本地导入池</p>
            <h2>发布日期文献</h2>
          </div>
          <div className="actions">
            <button className="ghost-button" onClick={() => setRequestVersion((current) => current + 1)}>刷新本地目录</button>
            <button className="ghost-button" onClick={clearFilters}>清空筛选</button>
          </div>
        </div>
        <div className="stats-strip">
          <MetricTile label="发布日期" value={publishDateOptions.length ? `${publishDateOptions.length} 天` : "0 天"} />
          <MetricTile label="筛选结果" value={String(overview?.total_papers || 0)} />
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
            <input aria-label="推送备注" name="push_note" placeholder="推送备注" value={pushNote} onChange={(event) => setPushNote(event.target.value)} />
            {pushMessage ? <span className="success-text">{pushMessage}</span> : null}
          </div>
        ) : null}
        <div className="filter-row filter-grid-wide">
          <input
            aria-label="搜索文献"
            name="paper_search"
            placeholder="搜索标题、摘要、期刊、标签"
            value={filters.query}
            onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))}
          />
          <select aria-label="发布日期" name="publish_date" value={filters.publishDate} onChange={(event) => setFilters((current) => ({ ...current, publishDate: event.target.value }))}>
            <option value="">全部发布日期</option>
            {publishDateOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
          <select aria-label="分类" name="category" value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}>
            <option value="">全部分类</option>
            {categoryOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
          <select aria-label="标签" name="tag" value={filters.tag} onChange={(event) => setFilters((current) => ({ ...current, tag: event.target.value }))}>
            <option value="">全部标签</option>
            {tagOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
          <select aria-label="排序方式" name="sort" value={filters.sort} onChange={(event) => setFilters((current) => ({ ...current, sort: event.target.value as DigestSortKey }))}>
            <option value="publish_date_desc">发布日期：从新到旧</option>
            <option value="publish_date_asc">发布日期：从旧到新</option>
          </select>
        </div>
        <div className="selection-toolbar">
          <label className="check-row">
            <input name="select_loaded_papers" type="checkbox" checked={allVisibleSelected} onChange={() => togglePaperBatch(visibleLoadedPapers)} />
            <span>全选当前已加载</span>
          </label>
          <div className="actions">
            <span className="selection-copy">已选 {selectedKeys.length} 篇</span>
            <button className="ghost-button" onClick={clearSelection} disabled={!selectedKeys.length}>清空选择</button>
            <button className="ghost-button" onClick={() => runSelectedExport("metadata")} disabled={!selectedKeys.length}>导出选中元数据</button>
            <button className="ghost-button" onClick={() => runSelectedExport("doi-list")} disabled={!selectedKeys.length}>导出选中 DOI</button>
          </div>
        </div>
        {exportMessage ? <p className="success-text">{exportMessage}</p> : null}
        {loadingOverview ? <div className="small-copy">正在按发布日期加载文献目录…</div> : null}
        {refreshingOverview ? <div className="small-copy">正在更新筛选结果…</div> : null}
        <div className="digest-layout">
          <aside className="date-rail desktop-only">
            {groupSummaries.map((group) => (
                <button
                className={`date-rail-item${group.publish_date === activeRailDate ? " is-active" : ""}`}
                key={group.publish_date}
                onClick={() => void scrollToDate(group.publish_date)}
              >
                <span className="date-rail-marker"><span /></span>
                <span className="date-rail-label">{formatDigestDate(group.publish_date)}</span>
              </button>
            ))}
          </aside>
          <div className="digest-sections">
            <div className="mobile-day-strip mobile-only">
              {groupSummaries.map((group) => (
                <button
                  className={`date-chip${group.publish_date === activeRailDate ? " is-active" : ""}`}
                  key={group.publish_date}
                  onClick={() => void scrollToDate(group.publish_date)}
                >
                  {formatDigestDate(group.publish_date)}
                </button>
              ))}
            </div>
            {groupSummaries.length === 0 ? <EmptyState title="当前没有符合条件的文献" description="调整搜索、发布日期、分类或标签筛选后再试。" /> : null}
            {groupSummaries.map((group) => {
              const isExpanded = expandedPublishDates.includes(group.publish_date);
              const groupData = loadedGroups[group.publish_date];
              const isLoadingGroup = loadingGroupDates.includes(group.publish_date);
              return (
                <section className="day-section subpanel" key={group.publish_date} id={`digest-day-${group.publish_date}`}>
                  <div className="day-section-header">
                    <div>
                      <p className="eyebrow">发布日期</p>
                      <h3>{formatDigestDate(group.publish_date)}</h3>
                    </div>
                    <div className="day-section-meta">
                      <span className="status-pill is-idle">{group.paper_count} 篇</span>
                      <button className="ghost-button day-section-toggle" onClick={() => void togglePublishDateGroup(group.publish_date)}>
                        {isExpanded ? "收起" : "展开"}
                      </button>
                    </div>
                  </div>
                  {isExpanded ? (
                    isLoadingGroup && !groupData ? (
                      <div className="small-copy">正在加载该发布日期的文献…</div>
                    ) : (
                      <>
                        <PaperTable
                          papers={groupData?.items || []}
                          selectedKeys={selectedKeySet}
                          pendingFavoriteIds={pendingFavoriteIdSet}
                          onToggleSelect={togglePaperSelection}
                          onToggleSelectAll={togglePaperBatch}
                          onFavorite={toggleFavorite}
                          onPush={user.role === "admin" ? pushPaper : undefined}
                        />
                        {groupData?.has_more ? (
                          <div className="actions">
                            <button className="ghost-button" onClick={() => void loadMoreGroup(group.publish_date)} disabled={isLoadingGroup}>
                              {isLoadingGroup ? "加载中…" : `加载更多（剩余 ${groupData.paper_count - groupData.items.length}）`}
                            </button>
                          </div>
                        ) : null}
                      </>
                    )
                  ) : null}
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
  pendingFavoriteIds,
  onToggleSelect,
  onToggleSelectAll,
  onFavorite,
  onPush,
}: {
  papers: PaperItem[];
  selectedKeys: Set<string>;
  pendingFavoriteIds: Set<number>;
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
          {papers.map((paper) => {
            const displayTags = getPaperDisplayTags(paper);
            const compactTags = compactPaperTags(displayTags);
            return (
            <article className="mobile-card paper-card" key={paper.id}>
              <div className="mobile-card-rail" aria-hidden="true">
                <span />
              </div>
              <div className="mobile-card-body">
                <div className="mobile-card-head mobile-paper-head">
                  <label className="check-row card-check">
                    <input
                      type="checkbox"
                      aria-label={`选择文献：${paper.title_en}`}
                      checked={selectedKeys.has(getPaperSelectionKey(paper))}
                      onChange={() => onToggleSelect(paper)}
                    />
                  </label>
                  <div className="mobile-paper-copy">
                    <h3 className="title-strong title-strong-en">{paper.title_en}</h3>
                    <p className="mobile-summary title-strong title-strong-zh">{paper.title_zh}</p>
                  </div>
                  <span className={`journal-marker${isFlagshipJournal(paper.journal) ? " is-flagship" : ""}`} title={paper.journal}>
                    {formatJournalMarker(paper.journal)}
                  </span>
                </div>
                <div className="mobile-paper-meta">
                  <InterestBadge level={paper.interest_level} />
                </div>
                <p className="small-copy mobile-paper-blurb">{paper.summary_zh}</p>
                {compactTags.length ? (
                  <div className="tag-list tag-list-compact">
                    {compactTags.map((tag) => <span key={`${paper.id}-${tag}`}>{tag}</span>)}
                  </div>
                ) : null}
                <div className="mobile-card-actions paper-card-actions">
                  <button className="table-link" onClick={() => onFavorite(paper)} disabled={pendingFavoriteIds.has(paper.id)}>
                    {pendingFavoriteIds.has(paper.id) ? "处理中…" : paper.is_favorited ? "取消收藏" : "加入收藏"}
                  </button>
                  {onPush ? <button className="table-link" onClick={() => onPush(paper)}>推送</button> : null}
                  <a className="table-link link-button" href={paper.article_url} target="_blank" rel="noreferrer">Open</a>
                </div>
              </div>
            </article>
          );
          })}
        </div>
      </div>
      <div className="desktop-only">
        <table className="paper-table">
          <thead>
            <tr>
              <th><input type="checkbox" aria-label="全选当前表格文献" checked={allSelected} onChange={() => onToggleSelectAll(papers)} /></th>
              <th className="action-col">操作</th>
              <th className="journal-col">期刊</th>
              <th className="score-col">评分</th>
              <th className="title-col">标题</th>
              <th className="zh-col">中文</th>
              <th className="tags-col">标签</th>
            </tr>
          </thead>
          <tbody>
            {papers.map((paper) => {
              const normalizedDoi = normalizeDoi(paper.doi);
              const doiUrl = normalizedDoi ? buildDoiUrl(normalizedDoi) : "";
              const displayTags = getPaperDisplayTags(paper);
              return (
              <tr key={paper.id}>
                <td><input type="checkbox" aria-label={`选择文献：${paper.title_en}`} checked={selectedKeys.has(getPaperSelectionKey(paper))} onChange={() => onToggleSelect(paper)} /></td>
                <td className="action-col">
                  <div className="paper-actions-stack">
                    <button className="table-link" onClick={() => onFavorite(paper)} disabled={pendingFavoriteIds.has(paper.id)}>
                      {pendingFavoriteIds.has(paper.id) ? "处理中…" : paper.is_favorited ? "取消" : "收藏"}
                    </button>
                    {onPush ? <button className="table-link" onClick={() => onPush(paper)}>推送</button> : null}
                  </div>
                </td>
                <td className="journal-col">{paper.journal}<br /><span className="muted">{formatDigestDate(paper.publish_date_day)}</span></td>
                <td className="score-col"><InterestBadge level={paper.interest_level} /></td>
                <td className="title-col">
                  <a className="table-title table-title-en paper-title-link" href={paper.article_url} target="_blank" rel="noreferrer">
                    {paper.title_en}
                    <span className="title-jump" aria-hidden="true">↗</span>
                  </a>
                  <div className="small-copy table-subcopy">
                    doi：
                    {normalizedDoi ? (
                      <a className="doi-link" href={doiUrl} target="_blank" rel="noreferrer">
                        [{normalizedDoi}]
                      </a>
                    ) : (
                      <span className="muted">[暂无]</span>
                    )}
                  </div>
                  <div className="small-copy table-subcopy">{paper.summary_zh}</div>
                </td>
                <td className="zh-col"><div className="table-title table-title-zh">{paper.title_zh}</div></td>
                <td className="tags-col">
                  <div className="paper-tags-inline">
                    {displayTags.length ? displayTags.map((tag) => <span key={`${paper.id}-${tag}`}>{tag}</span>) : <span className="muted">-</span>}
                  </div>
                </td>
              </tr>
            );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ToastBanner({ toast, onClose }: { toast: ToastState; onClose: () => void }) {
  return (
    <div className={`top-toast is-${toast.kind}`} role="status" aria-live="polite">
      <span>{toast.message}</span>
      <button className="top-toast-close" onClick={onClose} aria-label="关闭提示">×</button>
    </div>
  );
}

function PushInboxPage({ user }: { user: AuthUser }) {
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
  const [reviewOptionsError, setReviewOptionsError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const [savingPaperId, setSavingPaperId] = useState<number | null>(null);

  async function loadReviewOptions() {
    try {
      const next = await fetchFavoriteReviewOptions();
      setReviewOptions(next);
      setReviewOptionsError("");
    } catch (error) {
      setReviewOptionsError(error instanceof Error ? error.message : "人工备注选项加载失败");
    }
  }

  async function load() {
    const next = await listFavorites(user.role === "admin" ? targetUserId : undefined);
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
    void loadReviewOptions();
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
    if (
      !reviewOptions.interest_levels.length &&
      !reviewOptions.interest_tags.length &&
      !reviewOptions.review_final_decisions.length &&
      !reviewOptions.review_final_categories.length
    ) {
      void loadReviewOptions();
    }
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
    setSavingPaperId(favorite.paper_id);
    setSaveMessage("");
    setSaveError("");
    try {
      const updated = await saveFavoriteReviewRequest(
        favorite.paper_id,
        draft,
        user.role === "admin" ? targetUserId : undefined,
      );
      setFavorites((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setEditingPaperId(null);
      setSaveMessage("已保存，修改会保留在当前工作台数据中，并用于后续人工导出。");
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
          <h2>收藏与人工备注</h2>
        </div>
        {user.role === "admin" ? (
          <UserSelect users={adminUsers} value={targetUserId} onChange={setTargetUserId} placeholder="选择查看账户" />
        ) : null}
      </div>
      <div className="stats-strip">
        <MetricTile label="收藏数" value={String(favorites.length)} />
        <MetricTile label="查看账户" value={targetLabel} />
      </div>
      {reviewOptionsError ? <div className="notice-banner is-error">{reviewOptionsError}</div> : null}
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
                    <input
                      type="checkbox"
                      aria-label={`选择收藏：${favorite.title_en}`}
                      checked={selectedIds.includes(favorite.id)}
                      onChange={() => toggleFavoriteSelection(favorite)}
                    />
                  </label>
                  <div>
                    <p className="eyebrow">{favorite.journal}</p>
                    <strong>{favorite.favorited_at}</strong>
                  </div>
                  <InterestBadge level={favorite.interest_level} />
                </div>
                <h3 className="title-strong title-strong-en">{favorite.title_en}</h3>
                <p className="mobile-summary title-strong title-strong-zh">{favorite.title_zh}</p>
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
                <th><input type="checkbox" aria-label="全选当前收藏" checked={allSelected} onChange={() => toggleFavoriteBatch(favorites)} /></th>
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
                  <td><input type="checkbox" aria-label={`选择收藏：${favorite.title_en}`} checked={selectedIds.includes(favorite.id)} onChange={() => toggleFavoriteSelection(favorite)} /></td>
                  <td>{favorite.favorited_at}</td>
                  <td>{favorite.journal}</td>
                  <td>
                    <div className="table-title table-title-en">{favorite.title_en}</div>
                    <div className="table-title table-title-zh">{favorite.title_zh}</div>
                  </td>
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
  const effectiveDecision = formatReviewDecision(favorite.review_final_decision);

  return (
    <div className="favorite-review-summary">
      <div className="tag-list">
        <InterestBadge level={effectiveInterestLevel} />
        {effectiveInterestTag ? <span>{effectiveInterestTag}</span> : null}
        {effectiveGroup ? <span>{effectiveGroup}</span> : null}
        {effectiveDecision ? <span>{effectiveDecision}</span> : null}
      </div>
      <div className="small-copy">
        {favorite.reviewer_notes ? favorite.reviewer_notes : "尚未添加人工备注。"}
      </div>
      {favorite.review_updated_at ? (
        <div className="small-copy">最近修改：{favorite.review_updated_at}</div>
      ) : (
        <div className="small-copy">保存后会保留在当前工作台数据中，并用于后续导出。</div>
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
          <span>处理结果</span>
          <select value={draft.review_final_decision} onChange={(event) => onChange("review_final_decision", event.target.value)}>
            <option value="">暂不指定</option>
            {options.review_final_decisions.map((option) => (
              <option key={option} value={option}>{formatReviewDecision(option)}</option>
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

function InterestBadge({ level }: { level: string }) {
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

function AdminUsersPage() {
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

function AdminImportsPage() {
  const [runs, setRuns] = useState<ImportRun[]>([]);
  const [busyRunId, setBusyRunId] = useState("");
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    setRuns(await fetchImportRuns());
  }

  useEffect(() => {
    void load();
  }, []);

  async function runCheck() {
    setChecking(true);
    setMessage("");
    try {
      const results = await checkImportRuns();
      setMessage(formatImportSummary(results, "已完成最新运行检查"));
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "检查失败");
    } finally {
      setChecking(false);
    }
  }

  async function handleImport(runId: string, force: boolean) {
    setBusyRunId(runId);
    setMessage("");
    try {
      const result = force ? await reimportRun(runId) : await importRun(runId);
      setMessage(formatImportSummary([result], force ? "已执行重导入" : "已执行导入"));
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导入失败");
    } finally {
      setBusyRunId("");
    }
  }

  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">Producer Import</p>
            <h2>导入与重导入</h2>
          </div>
          <div className="actions">
            <button className="ghost-button" onClick={() => void load()}>刷新列表</button>
            <button className="primary-button" onClick={() => void runCheck()} disabled={checking}>
              {checking ? "检查中…" : "检查最新运行"}
            </button>
          </div>
        </div>
        <div className="stats-strip">
          <MetricTile label="可导入日期" value={String(runs.length)} />
          <MetricTile label="已对齐" value={String(runs.filter((run) => run.is_current).length)} />
          <MetricTile label="待导入" value={String(runs.filter((run) => !run.is_current).length)} />
        </div>
        {message ? <div className="notice-banner is-success">{message}</div> : null}
        <div className="table-shell">
          {runs.length === 0 ? <EmptyState title="当前没有可导入运行" description="请确认 producer SQLite 已生成可用运行记录。" /> : null}
          <div className="desktop-only">
            <table>
              <thead>
                <tr>
                  <th>日期</th>
                  <th>运行</th>
                  <th>记录数</th>
                  <th>归档校验</th>
                  <th>本地状态</th>
                  <th>动作</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={`${run.digest_date}-${run.run_id}`}>
                    <td>{run.digest_date}</td>
                    <td>{run.run_id}<div className="small-copy">{run.updated_at_utc}</div></td>
                    <td>{run.record_count}</td>
                    <td>{run.validation_status}</td>
                    <td>{run.is_current ? "已同步" : `当前 ${run.current_local_run_id || "未导入"}`}</td>
                    <td>
                      <button className="table-link" onClick={() => void handleImport(run.run_id, false)} disabled={busyRunId === run.run_id}>
                        {busyRunId === run.run_id ? "处理中…" : "导入"}
                      </button>
                      <button className="table-link" onClick={() => void handleImport(run.run_id, true)} disabled={busyRunId === run.run_id}>
                        重导入
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-only">
            <div className="mobile-stack">
              {runs.map((run) => (
                <article className="mobile-card" key={`${run.digest_date}-${run.run_id}`}>
                  <div className="mobile-card-head">
                    <div>
                      <p className="eyebrow">{run.digest_date}</p>
                      <strong>{run.run_id}</strong>
                    </div>
                    <span className={`status-pill ${run.is_current ? "is-live" : "is-idle"}`}>{run.is_current ? "已同步" : "待处理"}</span>
                  </div>
                  <p className="small-copy">记录数：{run.record_count}</p>
                  <p className="small-copy">归档校验：{run.validation_status}</p>
                  <p className="small-copy">本地运行：{run.current_local_run_id || "未导入"}</p>
                  <div className="mobile-card-actions">
                    <button className="table-link" onClick={() => void handleImport(run.run_id, false)} disabled={busyRunId === run.run_id}>导入</button>
                    <button className="table-link" onClick={() => void handleImport(run.run_id, true)} disabled={busyRunId === run.run_id}>重导入</button>
                  </div>
                </article>
              ))}
            </div>
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
    setJob(await exportCustomTable(user.id, mappings));
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

function getPaperSelectionKey(item: PaperItem) {
  return String(item.id);
}

function hasDigestSearchParams(searchParams: URLSearchParams) {
  return ["q", "publish_date", "date", "category", "tag", "sort"].some((key) => Boolean(searchParams.get(key)));
}

function buildPaperFiltersFromSearchParams(searchParams: URLSearchParams): PaperFilters {
  const sort = searchParams.get("sort");
  return {
    query: searchParams.get("q") || "",
    publishDate: searchParams.get("publish_date") || searchParams.get("date") || "",
    category: searchParams.get("category") || "",
    tag: searchParams.get("tag") || "",
    sort: sort === "publish_date_asc" ? "publish_date_asc" : "publish_date_desc",
  };
}

function arePaperFiltersEqual(left: PaperFilters, right: PaperFilters) {
  return (
    left.query === right.query &&
    left.publishDate === right.publishDate &&
    left.category === right.category &&
    left.tag === right.tag &&
    left.sort === right.sort
  );
}

function getPaperFiltersSignature(filters: PaperFilters) {
  return JSON.stringify(filters);
}

function buildLoadedGroupMap(groups: PaperLibraryGroup[]) {
  return groups.reduce<Record<string, PaperLibraryGroup>>((current, group) => {
    current[group.publish_date] = group;
    return current;
  }, {});
}

function collectLoadedPapers(loadedGroups: Record<string, PaperLibraryGroup>, orderedGroups: Array<{ publish_date: string }>) {
  return orderedGroups.flatMap((group) => loadedGroups[group.publish_date]?.items || []);
}

function collectVisibleLoadedPapers(
  loadedGroups: Record<string, PaperLibraryGroup>,
  expandedPublishDates: string[],
  orderedGroups: Array<{ publish_date: string }>,
) {
  const expandedSet = new Set(expandedPublishDates);
  return orderedGroups.flatMap((group) => (expandedSet.has(group.publish_date) ? loadedGroups[group.publish_date]?.items || [] : []));
}

function sanitizeExpandedPublishDates(
  expandedPublishDates: string[],
  orderedGroups: Array<{ publish_date: string }>,
) {
  const validDates = new Set(orderedGroups.map((group) => group.publish_date));
  const sanitized = expandedPublishDates.filter((publishDate) => validDates.has(publishDate)).slice(-1);
  if (sanitized.length) {
    return sanitized;
  }
  return orderedGroups[0] ? [orderedGroups[0].publish_date] : [];
}

function ensurePublishDateExpanded(
  expandedPublishDates: string[],
  publishDate: string,
  orderedGroups: Array<{ publish_date: string }>,
) {
  return sanitizeExpandedPublishDates([publishDate], orderedGroups);
}

function pickActiveRailDate(current: string, requestedPublishDate: string, orderedGroups: Array<{ publish_date: string }>) {
  if (requestedPublishDate && orderedGroups.some((group) => group.publish_date === requestedPublishDate)) {
    return requestedPublishDate;
  }
  if (current && orderedGroups.some((group) => group.publish_date === current)) {
    return current;
  }
  return orderedGroups[0]?.publish_date || "";
}

function pickActiveRailDateFromScroll(orderedGroups: Array<{ publish_date: string }>) {
  if (!orderedGroups.length || typeof window === "undefined") {
    return "";
  }
  const anchorOffset = 180;
  let active = orderedGroups[0]?.publish_date || "";

  for (const group of orderedGroups) {
    const element = document.getElementById(`digest-day-${group.publish_date}`);
    if (!element) {
      continue;
    }
    const { top } = element.getBoundingClientRect();
    if (top <= anchorOffset) {
      active = group.publish_date;
      continue;
    }
    if (!active) {
      active = group.publish_date;
    }
    break;
  }

  return active;
}

function updateFavoriteStateInGroups(
  loadedGroups: Record<string, PaperLibraryGroup>,
  paperId: number,
  isFavorited: boolean,
) {
  const nextGroups: Record<string, PaperLibraryGroup> = {};
  for (const [publishDate, group] of Object.entries(loadedGroups)) {
    nextGroups[publishDate] = {
      ...group,
      items: group.items.map((paper) => (paper.id === paperId ? { ...paper, is_favorited: isFavorited } : paper)),
    };
  }
  return nextGroups;
}

function formatJournalMarker(journal: string) {
  const normalized = normalizeJournalName(journal);
  const override = DIGEST_JOURNAL_MARKER_OVERRIDES[normalized];
  if (override) {
    return override;
  }
  const compact = normalized.replace(/[^a-z0-9 ]/g, " ").trim();
  if (!compact) {
    return "JNL";
  }
  const words = compact.split(/\s+/).filter(Boolean);
  if (words.length > 1) {
    const acronym = words.map((word) => word[0]).join("").toUpperCase();
    if (acronym.length >= 2 && acronym.length <= 4) {
      return acronym;
    }
  }
  return words[0].slice(0, 4).toUpperCase();
}

function compactPaperTags(tags: string[]) {
  const visibleTags = tags.slice(0, 3);
  if (!visibleTags.length) {
    return [];
  }
  if (tags.length <= 3) {
    return visibleTags;
  }
  return [...visibleTags, `+${tags.length - 3}`];
}

function getPaperDisplayTags(paper: Pick<PaperItem, "tags" | "interest_tag" | "category">) {
  const direct = (paper.tags || []).map((tag) => String(tag || "").trim()).filter(Boolean);
  if (direct.length) {
    return Array.from(new Set(direct));
  }
  const fallbackInterest = String(paper.interest_tag || "")
    .split(/[,，|/;；、]/)
    .map((tag) => tag.trim())
    .filter(Boolean);
  if (fallbackInterest.length) {
    return Array.from(new Set(fallbackInterest));
  }
  const fallbackCategory = String(paper.category || "").trim();
  return fallbackCategory ? [fallbackCategory] : [];
}

function normalizeJournalName(journal: string) {
  return String(journal || "").trim().toLowerCase();
}

function isFlagshipJournal(journal: string) {
  return DIGEST_FLAGSHIP_JOURNAL_ORDER.map((value) => value.toLowerCase()).includes(normalizeJournalName(journal));
}

function formatReviewDecision(value: string) {
  if (value === "keep") return "保留";
  if (value === "review") return "稍后处理";
  if (value === "reject") return "不保留";
  return value;
}

function formatImportSummary(results: ImportResult[], prefix: string) {
  if (!results.length) {
    return `${prefix}，没有发现需要更新的运行。`;
  }
  return `${prefix}：${results
    .map((result) => `${result.digest_date} ${result.result_status}（条目 ${result.imported_items} / 成员 ${result.imported_memberships}）`)
    .join("；")}`;
}

function formatDigestDate(value: string) {
  if (!value || value === "unknown") {
    return "未知日期";
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" }).format(date);
}

function normalizeDoi(doi: string) {
  return String(doi || "")
    .trim()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//i, "")
    .replace(/\s+/g, "");
}

function buildDoiUrl(doi: string) {
  const normalized = normalizeDoi(doi);
  return normalized ? `https://doi.org/${encodeURI(normalized)}` : "";
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
    ["canonical_key", "canonical_key"],
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
    "canonical_key",
    "digest_date",
    "favorited_at",
    "doi",
    "journal",
    "publish_date",
    "category",
    "interest_level",
    "interest_tag",
    "manual_interest_level",
    "manual_interest_tag",
    "final_status",
    "manual_group",
    "manual_notes",
    "manual_updated_at",
    "title_en",
    "title_zh",
    "article_url",
  ];
  const rows = items.map((item) => [
    item.id,
    item.paper_id,
    item.canonical_key,
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
    formatReviewDecision(item.review_final_decision),
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
