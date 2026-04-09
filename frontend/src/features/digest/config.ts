export const DIGEST_INITIAL_GROUP_COUNT = 3;
export const DIGEST_TOAST_DURATION_MS = 2600;

export const DIGEST_FLAGSHIP_JOURNAL_ORDER = ["Cell", "Nature", "Science"] as const;

export const DIGEST_JOURNAL_MARKER_OVERRIDES: Record<string, string> = {
  cell: "CEL",
  nature: "NAT",
  science: "SCI",
  "new england journal of medicine": "NEJM",
};

export const DIGEST_LAST_ROUTE_STORAGE_KEY = "bio-literature-digest.last-route";
export const DIGEST_PAGE_STATE_STORAGE_KEY = "bio-literature-digest.digest-page-state";
export const DIGEST_PAGE_CACHE_STORAGE_KEY = "bio-literature-digest.digest-page-cache";
