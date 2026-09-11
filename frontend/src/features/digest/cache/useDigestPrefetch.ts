import { useEffect, useRef } from "react";
import { PaperLibraryGroup, PaperLibraryOverview } from "../../../dataClient";
import { PaperFilters } from "../digestUtils";
import { digestCache } from "./digestCacheService";

type UseDigestPrefetchOptions = {
  activeRailDate: string;
  groupSummaries: PaperLibraryOverview["groups"];
  appliedFilters: PaperFilters;
  loadedGroups: Record<string, PaperLibraryGroup>;
};

/**
 * Hook to prefetch adjacent date groups in background when user is browsing a date.
 * Allows instant, 0ms transitions when scrolling or clicking timeline dates.
 */
export function useDigestPrefetch({
  activeRailDate,
  groupSummaries,
  appliedFilters,
  loadedGroups,
}: UseDigestPrefetchOptions) {
  const prefetchTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!activeRailDate || !groupSummaries.length) {
      return;
    }

    if (prefetchTimerRef.current !== null) {
      window.clearTimeout(prefetchTimerRef.current);
      prefetchTimerRef.current = null;
    }

    // Schedule prefetch on idle/low-priority timer
    prefetchTimerRef.current = window.setTimeout(() => {
      prefetchTimerRef.current = null;

      const currentIndex = groupSummaries.findIndex(
        (group) => group.publish_date === activeRailDate,
      );
      if (currentIndex === -1) {
        return;
      }

      // Identify candidate adjacent dates: next day (index + 1), previous day (index - 1), and index + 2
      const targetIndices = [currentIndex + 1, currentIndex - 1, currentIndex + 2];
      const targetDates = targetIndices
        .filter((idx) => idx >= 0 && idx < groupSummaries.length)
        .map((idx) => groupSummaries[idx].publish_date);

      for (const date of targetDates) {
        // Skip if already in loadedGroups state or already in LRU memory cache
        if (
          loadedGroups[date] ||
          digestCache.getCachedGroup({
            publishDate: date,
            q: appliedFilters.query,
            category: appliedFilters.category,
            tag: appliedFilters.tag,
            sort: appliedFilters.sort,
          })
        ) {
          continue;
        }

        // Prefetch in background silently
        void digestCache.prefetchGroup({
          publishDate: date,
          q: appliedFilters.query,
          category: appliedFilters.category,
          tag: appliedFilters.tag,
          sort: appliedFilters.sort,
        });
      }
    }, 350);

    return () => {
      if (prefetchTimerRef.current !== null) {
        window.clearTimeout(prefetchTimerRef.current);
        prefetchTimerRef.current = null;
      }
    };
  }, [activeRailDate, appliedFilters, groupSummaries, loadedGroups]);
}
