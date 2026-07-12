import { PaperLibraryGroup, PaperLibraryOverview } from "../../dataClient";
import {
  DIGEST_LAST_ROUTE_STORAGE_KEY,
  DIGEST_PAGE_CACHE_STORAGE_KEY,
  DIGEST_PAGE_STATE_STORAGE_KEY,
} from "./config";

export type DigestSortKey = "publish_date_desc" | "publish_date_asc";

export type DigestPageFilters = {
  query: string;
  publishDate: string;
  category: string;
  tag: string;
  sort: DigestSortKey;
};

export type DigestPageState = {
  filters: DigestPageFilters;
  activeRailDate: string;
  expandedPublishDates: string[];
  scrollY: number;
};

export type DigestPageCache = {
  overview: PaperLibraryOverview | null;
  loadedGroups: PaperLibraryGroup[];
};

let rememberedRoute = "";
let digestPageState: DigestPageState | null = null;
let digestPageCache: DigestPageCache | null = null;

export function sanitizeRememberedRoute(route: string | null | undefined): string {
  const candidate = typeof route === "string" ? route.trim() : "";
  if (!candidate || candidate === "/" || !candidate.startsWith("/")) {
    return "";
  }
  if (candidate.startsWith("/login")) {
    return "";
  }
  return candidate;
}

export function restoreRememberedRoute(): string {
  if (rememberedRoute) {
    return rememberedRoute;
  }
  const restored = sanitizeRememberedRoute(readStorage<string>(DIGEST_LAST_ROUTE_STORAGE_KEY));
  rememberedRoute = restored;
  return rememberedRoute;
}

export function rememberRoute(nextRoute: string) {
  const sanitizedRoute = sanitizeRememberedRoute(nextRoute);
  if (!sanitizedRoute) {
    return;
  }
  rememberedRoute = sanitizedRoute;
  writeStorage(DIGEST_LAST_ROUTE_STORAGE_KEY, sanitizedRoute);
}

export function restoreDigestPageState(): DigestPageState | null {
  if (digestPageState) {
    return digestPageState;
  }
  digestPageState = readStorage<DigestPageState>(DIGEST_PAGE_STATE_STORAGE_KEY);
  return digestPageState;
}

export function persistDigestPageState(nextState: DigestPageState) {
  digestPageState = nextState;
  writeStorage(DIGEST_PAGE_STATE_STORAGE_KEY, nextState);
}

export function restoreDigestPageCache(): DigestPageCache | null {
  if (digestPageCache) {
    return digestPageCache;
  }
  digestPageCache = readStorage<DigestPageCache>(DIGEST_PAGE_CACHE_STORAGE_KEY);
  return digestPageCache;
}

export function persistDigestPageCache(nextCache: DigestPageCache) {
  digestPageCache = nextCache;
  writeStorage(DIGEST_PAGE_CACHE_STORAGE_KEY, nextCache);
}

function readStorage<T>(key: string): T | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeStorage<T>(key: string, value: T) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    return;
  }
}
