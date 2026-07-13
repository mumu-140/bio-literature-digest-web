import { Dispatch, SetStateAction, useEffect } from "react";
import {
  PaperItem,
  PaperLibraryGroup,
  PaperLibraryOverview,
  fetchPaperLibraryOverview,
} from "../../dataClient";
import {
  persistDigestPageCache,
  persistDigestPageState,
} from "./browserState";
import { DIGEST_INITIAL_GROUP_COUNT } from "./config";
import {
  PaperFilters,
  arePaperFiltersEqual,
  buildLoadedGroupMap,
  buildPaperFiltersFromSearchParams,
  getPaperSelectionKey,
  hasDigestSearchParams,
  pickActiveRailDate,
  pickActiveRailDateFromScroll,
  sanitizeExpandedPublishDates,
} from "./digestUtils";

type SetState<T> = Dispatch<SetStateAction<T>>;
type MutableValue<T> = { current: T };
type GroupSummary = PaperLibraryOverview["groups"][number];

export function useSearchFilterSync(
  searchParams: URLSearchParams,
  setFilters: SetState<PaperFilters>,
) {
  useEffect(() => {
    if (!hasDigestSearchParams(searchParams)) {
      return;
    }
    const nextFilters = buildPaperFiltersFromSearchParams(searchParams);
    setFilters((current) => (arePaperFiltersEqual(current, nextFilters) ? current : nextFilters));
  }, [searchParams, setFilters]);
}

export function useFilterUrlSync(
  filters: PaperFilters,
  setSearchParams: (params: URLSearchParams, options: { replace: boolean }) => void,
) {
  useEffect(() => {
    const next = new URLSearchParams();
    if (filters.query.trim()) next.set("q", filters.query.trim());
    if (filters.publishDate) next.set("publish_date", filters.publishDate);
    if (filters.category) next.set("category", filters.category);
    if (filters.tag) next.set("tag", filters.tag);
    if (filters.sort !== "publish_date_desc") next.set("sort", filters.sort);
    setSearchParams(next, { replace: true });
  }, [filters, setSearchParams]);
}

type OverviewLoaderOptions = {
  appliedFilters: PaperFilters;
  filterSignature: string;
  requestVersion: number;
  overview: PaperLibraryOverview | null;
  lastLoadedSignatureRef: MutableValue<string>;
  restoreScrollYRef: MutableValue<number>;
  shouldRestoreScrollRef: MutableValue<boolean>;
  setOverview: SetState<PaperLibraryOverview | null>;
  setLoadedGroups: SetState<Record<string, PaperLibraryGroup>>;
  setExpandedPublishDates: SetState<string[]>;
  setActiveRailDate: SetState<string>;
  setLoadingOverview: SetState<boolean>;
  setRefreshingOverview: SetState<boolean>;
};

async function loadOverview(options: OverviewLoaderOptions, isIgnored: () => boolean) {
  const { appliedFilters } = options;
  try {
    const response = await fetchPaperLibraryOverview({
      q: appliedFilters.query,
      publish_date: appliedFilters.publishDate,
      category: appliedFilters.category,
      tag: appliedFilters.tag,
      sort: appliedFilters.sort,
      initial_group_count: DIGEST_INITIAL_GROUP_COUNT,
    });
    if (isIgnored()) return;
    options.setOverview(response);
    options.setLoadedGroups(buildLoadedGroupMap(response.loaded_groups));
    options.setExpandedPublishDates((current) =>
      sanitizeExpandedPublishDates(
        appliedFilters.publishDate
          ? [appliedFilters.publishDate]
          : current.length
            ? current
            : response.loaded_groups.map((group) => group.publish_date),
        response.groups,
      ),
    );
    options.setActiveRailDate((current) => pickActiveRailDate(current, appliedFilters.publishDate, response.groups));
    options.lastLoadedSignatureRef.current = options.filterSignature;
    options.shouldRestoreScrollRef.current = true;
  } catch {
    if (!isIgnored()) options.setOverview((current) => current);
  } finally {
    if (!isIgnored()) {
      options.setLoadingOverview(false);
      options.setRefreshingOverview(false);
    }
  }
}

export function useOverviewLoader(options: OverviewLoaderOptions) {
  const { appliedFilters, filterSignature, requestVersion } = options;
  useEffect(() => {
    let ignore = false;
    if (options.lastLoadedSignatureRef.current !== filterSignature) {
      options.restoreScrollYRef.current = 0;
    }
    options.overview ? options.setRefreshingOverview(true) : options.setLoadingOverview(true);
    void loadOverview(options, () => ignore);
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
}

export function useSelectionCleanup(
  loadedPapers: PaperItem[],
  setSelectedKeys: SetState<string[]>,
) {
  useEffect(() => {
    const validKeys = new Set(loadedPapers.map(getPaperSelectionKey));
    setSelectedKeys((current) => {
      const next = current.filter((key) => validKeys.has(key));
      return next.length === current.length && next.every((key, index) => key === current[index]) ? current : next;
    });
  }, [loadedPapers, setSelectedKeys]);
}

type PersistenceOptions = {
  filters: PaperFilters;
  activeRailDate: string;
  expandedPublishDates: string[];
  overview: PaperLibraryOverview | null;
  groupSummaries: GroupSummary[];
  loadedGroups: Record<string, PaperLibraryGroup>;
};

export function useDigestSnapshotPersistence(options: PersistenceOptions) {
  const { filters, activeRailDate, expandedPublishDates, overview, groupSummaries, loadedGroups } = options;

  useEffect(() => {
    persistDigestPageState({ filters, activeRailDate, expandedPublishDates, scrollY: window.scrollY });
  }, [filters, activeRailDate, expandedPublishDates]);

  useEffect(() => {
    if (!overview) return;
    persistDigestPageCache({
      overview,
      loadedGroups: groupSummaries
        .map((group) => loadedGroups[group.publish_date])
        .filter((group): group is PaperLibraryGroup => Boolean(group)),
    });
  }, [groupSummaries, loadedGroups, overview]);
}

export function useDigestScrollPersistence(
  filters: PaperFilters,
  activeRailDate: string,
  expandedPublishDates: string[],
) {
  useEffect(() => {
    let timer = 0;
    const persistCurrentScroll = () => {
      persistDigestPageState({ filters, activeRailDate, expandedPublishDates, scrollY: window.scrollY });
    };
    const schedulePersist = () => {
      if (timer) return;
      timer = window.setTimeout(() => {
        timer = 0;
        persistCurrentScroll();
      }, 120);
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") persistCurrentScroll();
    };

    window.addEventListener("scroll", schedulePersist, { passive: true });
    window.addEventListener("pagehide", persistCurrentScroll);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      if (timer) window.clearTimeout(timer);
      persistCurrentScroll();
      window.removeEventListener("scroll", schedulePersist);
      window.removeEventListener("pagehide", persistCurrentScroll);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [filters, activeRailDate, expandedPublishDates]);
}

type ViewportOptions = {
  overview: PaperLibraryOverview | null;
  loadedGroups: Record<string, PaperLibraryGroup>;
  groupSummaries: GroupSummary[];
  restoreScrollYRef: MutableValue<number>;
  shouldRestoreScrollRef: MutableValue<boolean>;
  setActiveRailDate: SetState<string>;
};

export function useDigestViewportTracking(options: ViewportOptions) {
  const { overview, loadedGroups, groupSummaries, restoreScrollYRef, shouldRestoreScrollRef, setActiveRailDate } = options;

  useEffect(() => {
    if (!overview || !shouldRestoreScrollRef.current) return;
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: restoreScrollYRef.current, left: 0, behavior: "auto" });
    });
    shouldRestoreScrollRef.current = false;
  }, [loadedGroups, overview, restoreScrollYRef, shouldRestoreScrollRef]);

  useEffect(() => {
    if (!groupSummaries.length) return;
    let frame = 0;
    const updateActiveDate = () => {
      frame = 0;
      const nextActive = pickActiveRailDateFromScroll(groupSummaries);
      if (nextActive) setActiveRailDate((current) => (current === nextActive ? current : nextActive));
    };
    const scheduleUpdate = () => {
      if (!frame) frame = window.requestAnimationFrame(updateActiveDate);
    };

    scheduleUpdate();
    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", scheduleUpdate);
      window.removeEventListener("resize", scheduleUpdate);
    };
  }, [groupSummaries, setActiveRailDate]);
}

export function useToastTimeout<T>(
  toast: T | null,
  setToast: SetState<T | null>,
  durationMs: number,
) {
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), durationMs);
    return () => window.clearTimeout(timer);
  }, [durationMs, setToast, toast]);
}
