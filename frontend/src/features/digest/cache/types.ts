import { DigestSortKey, PaperLibraryGroup, PaperLibraryOverview } from "../../../dataClient";

export type CacheEntry<T> = {
  data: T;
  createdAt: number;
  lastAccessedAt: number;
};

export type LRUCacheOptions = {
  maxSize: number;
  ttlMs: number;
};

export type GroupCacheParams = {
  publishDate: string;
  q?: string;
  category?: string;
  tag?: string;
  sort?: DigestSortKey;
  page?: number;
  page_size?: number;
};

export type OverviewCacheParams = {
  q?: string;
  publish_date?: string;
  category?: string;
  tag?: string;
  sort?: DigestSortKey;
  initial_group_count?: number;
};

export type LoadGroupOptions = {
  forceRefresh?: boolean;
};

export type LoadOverviewOptions = {
  forceRefresh?: boolean;
};
