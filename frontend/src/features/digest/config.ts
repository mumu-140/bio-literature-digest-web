export const DIGEST_INITIAL_GROUP_COUNT = 1;
export const DIGEST_TOAST_DURATION_MS = 2600;

export const DIGEST_FLAGSHIP_JOURNAL_ORDER = ["Cell", "Nature", "Science"] as const;

export const CELL_PRESS_ADDITIONAL_JOURNALS = [
  "current biology",
  "molecular plant",
  "plant communications",
  "developmental cell",
  "trends in plant science",
] as const;

export function isPreprintJournal(name: string): boolean {
  const lower = (name || "").trim().toLowerCase();
  return (
    lower.includes("biorxiv") ||
    lower.includes("medrxiv") ||
    lower.includes("arxiv") ||
    lower.includes("chemrxiv") ||
    lower.includes("preprint")
  );
}

export function isCnsJournal(name: string): boolean {
  const lower = (name || "").trim().toLowerCase();
  if (isPreprintJournal(lower)) return false;
  if (
    lower.startsWith("cell") ||
    lower.startsWith("nature") ||
    lower.startsWith("science")
  ) {
    return true;
  }
  return CELL_PRESS_ADDITIONAL_JOURNALS.some((j) => lower === j);
}

export const DIGEST_JOURNAL_MARKER_OVERRIDES: Record<string, string> = {
  cell: "CEL",
  nature: "NAT",
  science: "SCI",
  "new england journal of medicine": "NEJM",
};

export const DIGEST_LAST_ROUTE_STORAGE_KEY = "bio-literature-digest.last-route";
export const DIGEST_PAGE_STATE_STORAGE_KEY = "bio-literature-digest.digest-page-state-v3";
export const DIGEST_PAGE_CACHE_STORAGE_KEY = "bio-literature-digest.digest-page-cache-v3";
