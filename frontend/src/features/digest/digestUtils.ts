import { DigestSortKey, PaperItem, PaperLibraryGroup } from "../../dataClient";
import {
  DIGEST_FLAGSHIP_JOURNAL_ORDER,
  DIGEST_JOURNAL_MARKER_OVERRIDES,
} from "./config";

export type PaperFilters = {
  query: string;
  publishDate: string;
  category: string;
  tag: string;
  sort: DigestSortKey;
};

export function getPaperSelectionKey(item: PaperItem) {
  return String(item.id);
}

export function hasDigestSearchParams(searchParams: URLSearchParams) {
  return ["q", "publish_date", "date", "category", "tag", "sort"].some((key) => Boolean(searchParams.get(key)));
}

export function buildPaperFiltersFromSearchParams(searchParams: URLSearchParams): PaperFilters {
  const sort = searchParams.get("sort");
  return {
    query: searchParams.get("q") || "",
    publishDate: searchParams.get("publish_date") || searchParams.get("date") || "",
    category: searchParams.get("category") || "",
    tag: searchParams.get("tag") || "",
    sort: sort === "publish_date_asc" ? "publish_date_asc" : "publish_date_desc",
  };
}

export function arePaperFiltersEqual(left: PaperFilters, right: PaperFilters) {
  return (
    left.query === right.query &&
    left.publishDate === right.publishDate &&
    left.category === right.category &&
    left.tag === right.tag &&
    left.sort === right.sort
  );
}

export function getPaperFiltersSignature(filters: PaperFilters) {
  return JSON.stringify(filters);
}

export function buildLoadedGroupMap(groups: PaperLibraryGroup[]) {
  return groups.reduce<Record<string, PaperLibraryGroup>>((current, group) => {
    current[group.publish_date] = group;
    return current;
  }, {});
}

export function collectLoadedPapers(loadedGroups: Record<string, PaperLibraryGroup>, orderedGroups: Array<{ publish_date: string }>) {
  return orderedGroups.flatMap((group) => loadedGroups[group.publish_date]?.items || []);
}

export function collectVisibleLoadedPapers(
  loadedGroups: Record<string, PaperLibraryGroup>,
  expandedPublishDates: string[],
  orderedGroups: Array<{ publish_date: string }>,
) {
  const expandedSet = new Set(expandedPublishDates);
  return orderedGroups.flatMap((group) => (expandedSet.has(group.publish_date) ? loadedGroups[group.publish_date]?.items || [] : []));
}

export function sanitizeExpandedPublishDates(
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

export function ensurePublishDateExpanded(
  expandedPublishDates: string[],
  publishDate: string,
  orderedGroups: Array<{ publish_date: string }>,
) {
  return sanitizeExpandedPublishDates([publishDate], orderedGroups);
}

export function pickActiveRailDate(current: string, requestedPublishDate: string, orderedGroups: Array<{ publish_date: string }>) {
  if (requestedPublishDate && orderedGroups.some((group) => group.publish_date === requestedPublishDate)) {
    return requestedPublishDate;
  }
  if (current && orderedGroups.some((group) => group.publish_date === current)) {
    return current;
  }
  return orderedGroups[0]?.publish_date || "";
}

export function pickActiveRailDateFromScroll(orderedGroups: Array<{ publish_date: string }>) {
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

export function updateFavoriteStateInGroups(
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

export function formatJournalMarker(journal: string) {
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

export function compactPaperTags(tags: string[]) {
  const visibleTags = tags.slice(0, 3);
  if (!visibleTags.length) {
    return [];
  }
  if (tags.length <= 3) {
    return visibleTags;
  }
  return [...visibleTags, `+${tags.length - 3}`];
}

export function getPaperDisplayTags(paper: Pick<PaperItem, "tags" | "interest_tag" | "category">) {
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

export function normalizeJournalName(journal: string) {
  return String(journal || "").trim().toLowerCase();
}

export function isFlagshipJournal(journal: string) {
  return DIGEST_FLAGSHIP_JOURNAL_ORDER.map((value) => value.toLowerCase()).includes(normalizeJournalName(journal));
}
