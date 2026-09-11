import {
  DigestSortKey,
  PaperLibraryGroup,
  PaperLibraryOverview,
  fetchPaperLibraryGroup,
  fetchPaperLibraryOverview,
} from "../../../dataClient";
import { LRUCache } from "./lruCache";
import {
  GroupCacheParams,
  LoadGroupOptions,
  LoadOverviewOptions,
  OverviewCacheParams,
} from "./types";

// Cache up to 100 date groups in memory
const GROUP_CACHE_MAX = 100;
// Date group TTL: 15 minutes
const GROUP_CACHE_TTL_MS = 15 * 60 * 1000;

// Cache up to 30 overview queries in memory
const OVERVIEW_CACHE_MAX = 30;
// Overview TTL: 5 minutes
const OVERVIEW_CACHE_TTL_MS = 5 * 60 * 1000;

class DigestCacheService {
  private groupCache = new LRUCache<string, PaperLibraryGroup>({
    maxSize: GROUP_CACHE_MAX,
    ttlMs: GROUP_CACHE_TTL_MS,
  });

  private overviewCache = new LRUCache<string, PaperLibraryOverview>({
    maxSize: OVERVIEW_CACHE_MAX,
    ttlMs: OVERVIEW_CACHE_TTL_MS,
  });

  private inFlightGroupRequests = new Map<string, Promise<PaperLibraryGroup>>();
  private inFlightOverviewRequests = new Map<string, Promise<PaperLibraryOverview>>();

  buildGroupKey(params: GroupCacheParams): string {
    const q = (params.q || "").trim().toLowerCase();
    const category = (params.category || "").trim();
    const tag = (params.tag || "").trim();
    const sort = params.sort || "publish_date_desc";
    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    return `${params.publishDate}::${q}::${category}::${tag}::${sort}::p${page}_s${pageSize}`;
  }

  buildOverviewKey(params: OverviewCacheParams): string {
    const q = (params.q || "").trim().toLowerCase();
    const publishDate = (params.publish_date || "").trim();
    const category = (params.category || "").trim();
    const tag = (params.tag || "").trim();
    const sort = params.sort || "publish_date_desc";
    const initialCount = params.initial_group_count || 1;
    return `ov::${q}::${publishDate}::${category}::${tag}::${sort}::c${initialCount}`;
  }

  getCachedGroup(params: GroupCacheParams): PaperLibraryGroup | undefined {
    const key = this.buildGroupKey(params);
    return this.groupCache.get(key);
  }

  setCachedGroup(params: GroupCacheParams, group: PaperLibraryGroup): void {
    const key = this.buildGroupKey(params);
    this.groupCache.set(key, group);
  }

  getCachedOverview(params: OverviewCacheParams): PaperLibraryOverview | undefined {
    const key = this.buildOverviewKey(params);
    return this.overviewCache.get(key);
  }

  setCachedOverview(params: OverviewCacheParams, overview: PaperLibraryOverview): void {
    const key = this.buildOverviewKey(params);
    this.overviewCache.set(key, overview);
  }

  seedGroupsFromOverview(
    groups: PaperLibraryGroup[],
    baseFilters: { q?: string; category?: string; tag?: string; sort?: DigestSortKey },
  ): void {
    for (const group of groups) {
      const key = this.buildGroupKey({
        publishDate: group.publish_date,
        q: baseFilters.q,
        category: baseFilters.category,
        tag: baseFilters.tag,
        sort: baseFilters.sort,
        page: group.page,
        page_size: group.page_size,
      });
      this.groupCache.set(key, group);
    }
  }

  async loadGroup(
    params: GroupCacheParams,
    options: LoadGroupOptions = {},
  ): Promise<PaperLibraryGroup> {
    const key = this.buildGroupKey(params);

    if (!options.forceRefresh) {
      const cached = this.groupCache.get(key);
      if (cached) {
        return cached;
      }
    }

    const inFlight = this.inFlightGroupRequests.get(key);
    if (inFlight) {
      return inFlight;
    }

    const requestPromise = (async () => {
      try {
        const group = await fetchPaperLibraryGroup(params.publishDate, {
          q: params.q,
          category: params.category,
          tag: params.tag,
          sort: params.sort,
          page: params.page,
          page_size: params.page_size,
        });
        this.groupCache.set(key, group);
        return group;
      } finally {
        this.inFlightGroupRequests.delete(key);
      }
    })();

    this.inFlightGroupRequests.set(key, requestPromise);
    return requestPromise;
  }

  async prefetchGroup(params: GroupCacheParams): Promise<PaperLibraryGroup | null> {
    const key = this.buildGroupKey(params);
    if (this.groupCache.has(key)) {
      return this.groupCache.get(key) || null;
    }
    try {
      return await this.loadGroup(params);
    } catch {
      return null;
    }
  }

  async loadOverview(
    params: OverviewCacheParams,
    options: LoadOverviewOptions = {},
  ): Promise<PaperLibraryOverview> {
    const key = this.buildOverviewKey(params);

    if (!options.forceRefresh) {
      const cached = this.overviewCache.get(key);
      if (cached) {
        return cached;
      }
    }

    const inFlight = this.inFlightOverviewRequests.get(key);
    if (inFlight) {
      return inFlight;
    }

    const requestPromise = (async () => {
      try {
        const overview = await fetchPaperLibraryOverview(params);
        this.overviewCache.set(key, overview);
        if (overview.loaded_groups?.length) {
          this.seedGroupsFromOverview(overview.loaded_groups, params);
        }
        return overview;
      } finally {
        this.inFlightOverviewRequests.delete(key);
      }
    })();

    this.inFlightOverviewRequests.set(key, requestPromise);
    return requestPromise;
  }

  updatePaperFavoriteState(paperId: number, isFavorited: boolean): void {
    // Synchronize across cached groups
    for (const [, group] of this.groupCache.entries()) {
      let changed = false;
      const updatedItems = group.items.map((item) => {
        if (item.id === paperId) {
          changed = true;
          return { ...item, is_favorited: isFavorited };
        }
        return item;
      });
      if (changed) {
        group.items = updatedItems;
      }
    }

    // Synchronize across cached overviews
    for (const [, overview] of this.overviewCache.entries()) {
      if (overview.loaded_groups) {
        for (const group of overview.loaded_groups) {
          let changed = false;
          const updatedItems = group.items.map((item) => {
            if (item.id === paperId) {
              changed = true;
              return { ...item, is_favorited: isFavorited };
            }
            return item;
          });
          if (changed) {
            group.items = updatedItems;
          }
        }
      }
    }
  }

  clear(): void {
    this.groupCache.clear();
    this.overviewCache.clear();
    this.inFlightGroupRequests.clear();
    this.inFlightOverviewRequests.clear();
  }
}

export const digestCache = new DigestCacheService();
