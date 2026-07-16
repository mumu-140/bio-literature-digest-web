import { useDeferredValue, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AuthUser,
  PaperItem,
  PaperLibraryGroup,
  PaperLibraryOverview,
  fetchPaperLibraryGroup,
  toggleFavorite as toggleFavoriteRequest,
} from "../../dataClient";
import { importIntoEndNote, importIntoZotero } from "../../referenceImport";
import { exportSelectedPapers } from "../shared/paperExport";
import {
  restoreDigestPageCache,
  restoreDigestPageState,
} from "./browserState";
import {
  DIGEST_TOAST_DURATION_MS,
} from "./config";
import {
  useDigestScrollPersistence,
  useDigestSnapshotPersistence,
  useDigestViewportTracking,
  useFilterUrlSync,
  useOverviewLoader,
  useSearchFilterSync,
  useSelectionCleanup,
  useToastTimeout,
} from "./digestEffects";
import { useDigestPush } from "./useDigestPush";
import {
  PaperFilters,
  arePaperFiltersEqual,
  buildLoadedGroupMap,
  buildPaperFiltersFromSearchParams,
  collectLoadedPapers,
  collectVisibleLoadedPapers,
  ensurePublishDateExpanded,
  getPaperFiltersSignature,
  getPaperSelectionKey,
  hasDigestSearchParams,
  updateFavoriteStateInGroups,
} from "./digestUtils";
import { buildDeerFlowDiscussionUrl } from "./deerflowDiscussion";

export type ToastState = {
  kind: "success" | "error";
  message: string;
};

export function useDigestLibrary({ user }: { user: AuthUser }) {
  const [searchParams, setSearchParams] = useSearchParams();
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
  const digestPush = useDigestPush({ user, loadedPapers, selectedKeys });
  const visibleLoadedPapers = collectVisibleLoadedPapers(loadedGroups, expandedPublishDates, groupSummaries);
  const selectedKeySet = new Set(selectedKeys);
  const pendingFavoriteIdSet = new Set(pendingFavoriteIds);
  const allVisibleSelected = visibleLoadedPapers.length > 0 && visibleLoadedPapers.every((paper) => selectedKeySet.has(getPaperSelectionKey(paper)));

  useSearchFilterSync(searchParams, setFilters);
  useFilterUrlSync(filters, setSearchParams);
  useOverviewLoader({
    appliedFilters,
    filterSignature,
    requestVersion,
    overview,
    lastLoadedSignatureRef,
    restoreScrollYRef,
    shouldRestoreScrollRef,
    setOverview,
    setLoadedGroups,
    setExpandedPublishDates,
    setActiveRailDate,
    setLoadingOverview,
    setRefreshingOverview,
  });
  useSelectionCleanup(loadedPapers, setSelectedKeys);
  useDigestSnapshotPersistence({
    filters,
    activeRailDate,
    expandedPublishDates,
    overview,
    groupSummaries,
    loadedGroups,
  });
  useDigestScrollPersistence(filters, activeRailDate, expandedPublishDates);
  useDigestViewportTracking({
    overview,
    loadedGroups,
    groupSummaries,
    restoreScrollYRef,
    shouldRestoreScrollRef,
    setActiveRailDate,
  });
  useToastTimeout(favoriteToast, setFavoriteToast, DIGEST_TOAST_DURATION_MS);

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

  function importSelectedReferences(target: "zotero" | "endnote") {
    const selected = loadedPapers.filter((item) => selectedKeys.includes(getPaperSelectionKey(item)));
    if (target === "zotero") {
      importIntoZotero(selected);
    } else {
      importIntoEndNote(selected);
    }
    setExportMessage(`已生成 ${selected.length} 篇文献的 ${target === "zotero" ? "Zotero" : "EndNote"} 导入文件。`);
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

  function openDeerFlowDiscussion(papers: PaperItem[]) {
    try {
      const url = buildDeerFlowDiscussionUrl(papers.map((paper) => paper.canonical_key));
      const discussionWindow = window.open(url, "_blank", "noopener,noreferrer");
      if (!discussionWindow) {
        throw new Error("浏览器阻止了新标签页，请允许本站打开新标签页后重试。");
      }
      setExportMessage(`已将 ${papers.length} 篇文献交给 DeerFlow 准备讨论。`);
    } catch (error) {
      setExportMessage(error instanceof Error ? error.message : "无法打开 DeerFlow 讨论。");
    }
  }

  function discussSelectedPapers() {
    const selected = loadedPapers.filter((item) => selectedKeys.includes(getPaperSelectionKey(item)));
    openDeerFlowDiscussion(selected);
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

  return {
    ...digestPush,
    filters,
    setFilters,
    publishDateOptions,
    categoryOptions,
    tagOptions,
    overview,
    selectedKeys,
    allVisibleSelected,
    visibleLoadedPapers,
    exportMessage,
    loadingOverview,
    refreshingOverview,
    groupSummaries,
    activeRailDate,
    loadedGroups,
    loadingGroupDates,
    expandedPublishDates,
    selectedKeySet,
    pendingFavoriteIdSet,
    favoriteToast,
    setFavoriteToast,
    refreshOverview: () => setRequestVersion((current) => current + 1),
    clearFilters,
    togglePaperBatch,
    clearSelection,
    importSelectedReferences,
    runSelectedExport,
    discussPaper: (paper: PaperItem) => openDeerFlowDiscussion([paper]),
    discussSelectedPapers,
    scrollToDate,
    togglePublishDateGroup,
    togglePaperSelection,
    toggleFavorite,
    loadMoreGroup,
  };
}

export type DigestController = ReturnType<typeof useDigestLibrary>;
