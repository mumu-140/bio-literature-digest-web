export type AuthUser = {
  id: number;
  email: string;
  name: string;
  role: "admin" | "member";
  is_active: boolean;
};

export type PaperItem = {
  id: number;
  canonical_key: string;
  digest_date: string;
  doi: string;
  journal: string;
  publish_date: string;
  publish_date_day: string;
  category: string;
  interest_level: string;
  interest_score: number;
  interest_tag: string;
  title_en: string;
  title_zh: string;
  summary_zh: string;
  abstract: string;
  article_url: string;
  publication_stage: string;
  tags: string[];
  is_favorited: boolean;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type DigestSortKey = "publish_date_desc" | "publish_date_asc";

export type PaperLibraryGroupSummary = {
  publish_date: string;
  paper_count: number;
};

export type PaperLibraryGroup = {
  publish_date: string;
  paper_count: number;
  items: PaperItem[];
};

export type PaperLibraryOverview = {
  total_papers: number;
  available_publish_dates: string[];
  available_categories: string[];
  available_tags: string[];
  groups: PaperLibraryGroupSummary[];
  loaded_groups: PaperLibraryGroup[];
  sort: DigestSortKey;
};

export type FavoriteItem = {
  id: number;
  user_id: number;
  paper_id: number;
  canonical_key: string;
  digest_date?: string | null;
  doi: string;
  journal: string;
  publish_date: string;
  category: string;
  interest_level: string;
  interest_tag: string;
  title_en: string;
  title_zh: string;
  article_url: string;
  favorited_at: string;
  review_interest_level: string;
  review_interest_tag: string;
  review_final_decision: string;
  review_final_category: string;
  reviewer_notes: string;
  review_updated_at?: string | null;
};

export type FavoriteReviewOptions = {
  interest_levels: string[];
  interest_tags: string[];
  review_final_decisions: string[];
  review_final_categories: string[];
};

export type FavoriteReviewDraft = {
  review_interest_level: string;
  review_interest_tag: string;
  review_final_decision: string;
  review_final_category: string;
  reviewer_notes: string;
};

export type UserItem = {
  id: number;
  email: string;
  name: string;
  role: "admin" | "member";
  user_group: "internal" | "outsider";
  owner_admin_user_id?: number | null;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
};

export type ExportJob = {
  id: number;
  kind: string;
  status: string;
  output_name: string;
  content_type: string;
  created_at: string;
  finished_at?: string | null;
  download_url: string;
};

export type PaperPushItem = {
  id: number;
  paper_id: number;
  canonical_key: string;
  recipient_user_id: number;
  sent_by_user_id: number;
  note: string;
  is_read: boolean;
  pushed_at: string;
  read_at?: string | null;
  title_en: string;
  title_zh: string;
  journal: string;
  publish_date: string;
  article_url: string;
  sender_name: string;
  recipient_name: string;
};

export type ImportRun = {
  digest_date: string;
  run_id: string;
  updated_at_utc: string;
  status: string;
  email_status: string;
  work_dir: string;
  validation_status: string;
  validation_payload: Record<string, unknown>;
  record_count: number;
  is_current: boolean;
  current_local_run_id: string;
  current_local_updated_at_utc: string;
};

export type ImportResult = {
  digest_date: string;
  source_run_id: string;
  source_updated_at_utc: string;
  result_status: string;
  imported_items: number;
  imported_memberships: number;
  skipped_missing_key_count: number;
  duplicate_membership_count: number;
  conflict_count: number;
  validation_status: string;
  summary: Record<string, unknown>;
};

const apiBase = "";

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

function browserLanguage(): string {
  if (typeof navigator === "undefined") {
    return "";
  }
  return navigator.language || "";
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const timezone = browserTimezone();
  const language = browserLanguage();
  const response = await fetch(`${apiBase}${path}`, {
    credentials: "include",
    headers: {
      "content-type": "application/json",
      ...(timezone ? { "x-browser-timezone": timezone } : {}),
      ...(language ? { "x-browser-language": language } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(extractErrorMessage(payload));
  }
  return payload as T;
}

function extractErrorMessage(payload: unknown): string {
  if (typeof payload === "string") {
    return payload;
  }
  if (!payload || typeof payload !== "object") {
    return "Request failed";
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const collected = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return item.msg;
        }
        return "";
      })
      .filter(Boolean);
    if (collected.length) {
      return collected.join("；");
    }
  }
  try {
    return JSON.stringify(payload);
  } catch {
    return "Request failed";
  }
}

export async function fetchAuthUser() {
  return request<AuthUser>("/api/auth/me");
}

export async function login(form: { email: string; name: string }) {
  return request<{ user: AuthUser }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(form),
  });
}

export async function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export async function fetchAdminUsers() {
  return request<UserItem[]>("/api/admin/users");
}

export async function fetchPaperLibraryOverview(params: {
  q?: string;
  publish_date?: string;
  category?: string;
  tag?: string;
  sort?: DigestSortKey;
  initial_group_count?: number;
}) {
  const query = buildQueryString({
    q: params.q || "",
    publish_date: params.publish_date || "",
    category: params.category || "",
    tag: params.tag || "",
    sort: params.sort || "publish_date_desc",
    initial_group_count: params.initial_group_count ? String(params.initial_group_count) : "",
  });
  return request<PaperLibraryOverview>(`/api/papers/library${query}`);
}

export async function fetchPaperLibraryGroup(
  publishDate: string,
  params: {
    q?: string;
    category?: string;
    tag?: string;
    sort?: DigestSortKey;
  },
) {
  const query = buildQueryString({
    q: params.q || "",
    category: params.category || "",
    tag: params.tag || "",
    sort: params.sort || "publish_date_desc",
  });
  return request<PaperLibraryGroup>(`/api/papers/library/groups/${encodeURIComponent(publishDate)}${query}`);
}

export async function toggleFavorite(paperId: number, isFavorited: boolean) {
  if (isFavorited) {
    return request(`/api/favorites/${paperId}`, { method: "DELETE" });
  }
  return request("/api/favorites", {
    method: "POST",
    body: JSON.stringify({ paper_id: paperId }),
  });
}

export async function listFavorites(targetUserId?: string) {
  const query = targetUserId ? `?user_id=${targetUserId}` : "";
  return request<FavoriteItem[]>(`/api/favorites${query}`);
}

export async function fetchFavoriteReviewOptions() {
  return request<FavoriteReviewOptions>("/api/favorites/review-options");
}

export async function saveFavoriteReview(paperId: number, draft: FavoriteReviewDraft, targetUserId?: string) {
  const query = targetUserId ? `?user_id=${targetUserId}` : "";
  return request<FavoriteItem>(`/api/favorites/${paperId}${query}`, {
    method: "PATCH",
    body: JSON.stringify(draft),
  });
}

export async function listPushes(targetUserId?: string) {
  const suffix = targetUserId ? `?user_id=${targetUserId}` : "";
  return request<PaperPushItem[]>(`/api/pushes${suffix}`);
}

export async function updatePush(pushId: number, isRead: boolean) {
  return request<PaperPushItem>(`/api/pushes/${pushId}`, {
    method: "PATCH",
    body: JSON.stringify({ is_read: isRead }),
  });
}

export async function createPush(payload: { paper_id: number; recipient_user_id: number; note: string }) {
  return request<PaperPushItem>("/api/admin/pushes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function exportCustomTable(userId: number, columns: Array<{ source: string; label: string }>) {
  return request<ExportJob>("/api/exports/custom-table", {
    method: "POST",
    body: JSON.stringify({ columns, user_id: userId }),
  });
}

export async function fetchImportRuns() {
  return request<ImportRun[]>("/api/admin/imports/runs");
}

export async function checkImportRuns() {
  return request<ImportResult[]>("/api/admin/imports/check", { method: "POST" });
}

export async function importRun(runId: string) {
  return request<ImportResult>(`/api/admin/imports/runs/${encodeURIComponent(runId)}/import`, {
    method: "POST",
  });
}

export async function reimportRun(runId: string) {
  return request<ImportResult>(`/api/admin/imports/runs/${encodeURIComponent(runId)}/reimport`, {
    method: "POST",
  });
}

function buildQueryString(params: Record<string, string>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value.trim()) {
      query.set(key, value);
    }
  }
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}
