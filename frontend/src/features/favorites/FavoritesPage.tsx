import { useEffect, useMemo, useState } from "react";

import {
  AuthUser,
  FavoriteItem,
  FavoriteReviewDraft,
  FavoriteReviewOptions,
  fetchFavoriteReviewOptions,
  listFavorites,
  saveFavoriteReview as saveFavoriteReviewRequest,
  toggleFavorite,
} from "../../dataClient";
import { importIntoEndNote, importIntoZotero } from "../../referenceImport";
import { FavoriteReviewEditor, FavoriteReviewSummary } from "./FavoriteReviewComponents";
import { exportSelectedFavorites } from "../shared/paperExport";
import {
  AuthorList,
  CopyDoiButton,
  EmptyState,
  formatDigestDate,
  InterestBadge,
  MetricTile,
  normalizeDoi,
  buildDoiUrl,
  useAdminUsers,
  UserSelect,
} from "../shared/WorkbenchUi";
import { buildDeerFlowDiscussionUrl } from "../digest/deerflowDiscussion";
import {
  IconArrowDownTray,
  IconChatBubble,
  IconExternalLink,
  IconSearch,
  IconStar,
  IconXMark,
} from "../shared/Icons";

export function FavoritesPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [decisionFilter, setDecisionFilter] = useState("");
  const [interestFilter, setInterestFilter] = useState("");

  const [reviewOptions, setReviewOptions] = useState<FavoriteReviewOptions>({
    interest_levels: [],
    interest_tags: [],
    review_final_decisions: [],
    review_final_categories: [],
  });
  const [editingPaperId, setEditingPaperId] = useState<number | null>(null);
  const [draft, setDraft] = useState<FavoriteReviewDraft>({
    review_interest_level: "",
    review_interest_tag: "",
    review_final_decision: "",
    review_final_category: "",
    reviewer_notes: "",
  });
  const [reviewOptionsError, setReviewOptionsError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const [savingPaperId, setSavingPaperId] = useState<number | null>(null);
  const [pendingUnfavIds, setPendingUnfavIds] = useState<Set<number>>(new Set());

  async function loadReviewOptions() {
    try {
      const next = await fetchFavoriteReviewOptions();
      setReviewOptions(next);
      setReviewOptionsError("");
    } catch (error) {
      setReviewOptionsError(error instanceof Error ? error.message : "人工备注选项加载失败");
    }
  }

  async function load() {
    const next = await listFavorites(user.role === "admin" ? targetUserId : undefined);
    setFavorites(next);
    setSelectedIds((current) => current.filter((id) => next.some((favorite) => favorite.id === id)));
  }

  useEffect(() => {
    void load();
    setEditingPaperId(null);
    setSaveMessage("");
    setSaveError("");
  }, [targetUserId]);

  useEffect(() => {
    void loadReviewOptions();
  }, []);

  useEffect(() => {
    if (user.role === "admin" && adminUsers.length && !targetUserId) {
      setTargetUserId(String(adminUsers[0].id));
    }
  }, [adminUsers, targetUserId, user.role]);

  // Client-side filtering
  const filteredFavorites = useMemo(() => {
    return favorites.filter((item) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchTitleEn = item.title_en?.toLowerCase().includes(q);
        const matchTitleZh = item.title_zh?.toLowerCase().includes(q);
        const matchJournal = item.journal?.toLowerCase().includes(q);
        const matchAuthors = item.authors?.some((a) => a.toLowerCase().includes(q));
        const matchNotes = item.reviewer_notes?.toLowerCase().includes(q);
        const matchDoi = item.doi?.toLowerCase().includes(q);
        if (!matchTitleEn && !matchTitleZh && !matchJournal && !matchAuthors && !matchNotes && !matchDoi) {
          return false;
        }
      }
      if (decisionFilter) {
        if (decisionFilter === "none") {
          if (item.review_final_decision) return false;
        } else if (item.review_final_decision !== decisionFilter) {
          return false;
        }
      }
      if (interestFilter) {
        const effLevel = item.review_interest_level || item.interest_level;
        if (effLevel !== interestFilter) return false;
      }
      return true;
    });
  }, [favorites, searchQuery, decisionFilter, interestFilter]);

  const allFilteredSelected =
    filteredFavorites.length > 0 &&
    filteredFavorites.every((favorite) => selectedIds.includes(favorite.id));

  function toggleFavoriteSelection(favorite: FavoriteItem) {
    setSelectedIds((current) =>
      current.includes(favorite.id)
        ? current.filter((id) => id !== favorite.id)
        : [...current, favorite.id],
    );
  }

  function toggleFilteredBatch() {
    const ids = filteredFavorites.map((item) => item.id);
    setSelectedIds((current) => {
      const currentSet = new Set(current);
      const shouldSelect = ids.some((id) => !currentSet.has(id));
      for (const id of ids) {
        if (shouldSelect) {
          currentSet.add(id);
        } else {
          currentSet.delete(id);
        }
      }
      return Array.from(currentSet);
    });
  }

  function importSelectedFavoriteReferences(target: "zotero" | "endnote") {
    const selected = favorites.filter((favorite) => selectedIds.includes(favorite.id));
    if (target === "zotero") {
      importIntoZotero(selected);
    } else {
      importIntoEndNote(selected);
    }
    setSaveMessage(`已导出 ${selected.length} 篇文献到 ${target === "zotero" ? "Zotero" : "EndNote"}。`);
  }

  function exportFavoritesFile(kind: "metadata" | "doi-list") {
    const selected = favorites.filter((favorite) => selectedIds.includes(favorite.id));
    if (!selected.length) return;
    exportSelectedFavorites(selected, kind);
    setSaveMessage(`已导出 ${selected.length} 条${kind === "metadata" ? "元数据" : " DOI"}。`);
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  function startReview(favorite: FavoriteItem) {
    setEditingPaperId(favorite.paper_id);
    setDraft({
      review_interest_level: favorite.review_interest_level || "",
      review_interest_tag: favorite.review_interest_tag || "",
      review_final_decision: favorite.review_final_decision || "",
      review_final_category: favorite.review_final_category || "",
      reviewer_notes: favorite.reviewer_notes || "",
    });
    setSaveMessage("");
    setSaveError("");
  }

  function cancelReview() {
    setEditingPaperId(null);
    setSaveError("");
  }

  async function saveReview(paperId: number) {
    setSavingPaperId(paperId);
    setSaveError("");
    setSaveMessage("");
    try {
      const updated = await saveFavoriteReviewRequest(
        paperId,
        draft,
        user.role === "admin" ? targetUserId : undefined,
      );
      setFavorites((current) =>
        current.map((item) => (item.paper_id === paperId ? { ...item, ...updated } : item)),
      );
      setEditingPaperId(null);
      setSaveMessage("人工评审与备注已保存。");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "保存备注失败");
    } finally {
      setSavingPaperId(null);
    }
  }

  async function handleRemoveFavorite(favorite: FavoriteItem) {
    if (pendingUnfavIds.has(favorite.paper_id)) return;
    setPendingUnfavIds((prev) => new Set(prev).add(favorite.paper_id));
    try {
      await toggleFavorite(favorite.paper_id, true);
      setFavorites((prev) => prev.filter((item) => item.id !== favorite.id));
      setSelectedIds((prev) => prev.filter((id) => id !== favorite.id));
      setSaveMessage(`已从收藏夹移出：《${favorite.title_en}》`);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "移除收藏失败");
    } finally {
      setPendingUnfavIds((prev) => {
        const next = new Set(prev);
        next.delete(favorite.paper_id);
        return next;
      });
    }
  }

  function discussSelected() {
    const selected = favorites.filter((favorite) => selectedIds.includes(favorite.id));
    if (!selected.length) return;
    try {
      const url = buildDeerFlowDiscussionUrl(selected.map((item) => item.canonical_key));
      window.open(url, "_blank", "noopener,noreferrer");
      setSaveMessage(`已将 ${selected.length} 篇文献提交给 DeerFlow 准备讨论。`);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "无法开启 DeerFlow 讨论");
    }
  }

  const reviewedCount = favorites.filter(
    (item) => item.review_final_decision || item.reviewer_notes,
  ).length;

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">个人知识库</p>
          <h2>收藏与人工备注</h2>
        </div>
        {user.role === "admin" ? (
          <UserSelect
            users={adminUsers}
            value={targetUserId}
            onChange={setTargetUserId}
            placeholder="选择查看账户"
          />
        ) : null}
      </div>

      <div className="stats-strip">
        <MetricTile label="收藏文献总数" value={String(favorites.length)} hint="当前账户所有收藏" />
        <MetricTile label="已人工评审" value={String(reviewedCount)} hint="带有结论或备注的条目" />
        <MetricTile label="已选条目" value={String(selectedIds.length)} hint="可批量导出或研讨" />
      </div>

      {/* Favorites filter row */}
      <div className="filter-row filter-grid-favorites">
        <div className="search-input-wrap">
          <IconSearch size={16} className="search-icon" />
          <input
            aria-label="搜索收藏文献"
            placeholder="在收藏中搜索标题、作者、期刊、备注…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {searchQuery ? (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => setSearchQuery("")}
              title="清除搜索"
              aria-label="清除搜索"
            >
              <IconXMark size={14} />
            </button>
          ) : null}
        </div>

        <select
          aria-label="按评审结论筛选"
          value={decisionFilter}
          onChange={(e) => setDecisionFilter(e.target.value)}
        >
          <option value="">全部评审结论</option>
          <option value="keep">已保留 (keep)</option>
          <option value="follow_up">继续跟进 (follow_up)</option>
          <option value="archive">已归档 (archive)</option>
          <option value="exclude">已排除 (exclude)</option>
          <option value="none">未指定结论</option>
        </select>

        <select
          aria-label="按兴趣强度筛选"
          value={interestFilter}
          onChange={(e) => setInterestFilter(e.target.value)}
        >
          <option value="">全部强度</option>
          <option value="非常感兴趣">非常感兴趣</option>
          <option value="感兴趣">感兴趣</option>
          <option value="一般">一般</option>
          <option value="非常一般">非常一般</option>
        </select>
      </div>

      {/* Batch toolbar */}
      <div className={`selection-toolbar${selectedIds.length > 0 ? " is-active" : ""}`}>
        <label className="check-row select-all-label">
          <input
            type="checkbox"
            checked={allFilteredSelected}
            onChange={toggleFilteredBatch}
          />
          <span>全选当前筛选 ({filteredFavorites.length})</span>
        </label>

        <div className="selection-actions-cluster">
          <span className="selection-count-badge">
            已选 <strong>{selectedIds.length}</strong> 篇
          </span>

          <button
            className="primary-button discuss-batch-btn"
            type="button"
            onClick={discussSelected}
            disabled={!selectedIds.length || selectedIds.length > 10}
            title={selectedIds.length > 10 ? "一次最多讨论 10 篇" : "在 DeerFlow 启动深度研讨"}
          >
            <IconChatBubble size={15} />
            <span>在 DeerFlow 讨论 {selectedIds.length > 0 ? `(${selectedIds.length}/10)` : ""}</span>
          </button>

          <button
            className="ghost-button"
            onClick={() => importSelectedFavoriteReferences("zotero")}
            disabled={!selectedIds.length}
            title="生成所选收藏文献的 RIS 导入文件"
          >
            <IconArrowDownTray size={14} />
            <span>Zotero</span>
          </button>

          <button
            className="ghost-button"
            onClick={() => importSelectedFavoriteReferences("endnote")}
            disabled={!selectedIds.length}
            title="生成所选收藏文献的 EndNote 导入文件"
          >
            <IconArrowDownTray size={14} />
            <span>EndNote</span>
          </button>

          <button
            className="ghost-button"
            onClick={() => exportFavoritesFile("metadata")}
            disabled={!selectedIds.length}
            title="导出所选收藏文献元数据"
          >
            <span>元数据</span>
          </button>

          <button
            className="ghost-button"
            onClick={() => exportFavoritesFile("doi-list")}
            disabled={!selectedIds.length}
            title="导出所选文献 DOI 列表"
          >
            <span>DOI 列表</span>
          </button>

          <button
            className="ghost-button clear-selection-btn"
            onClick={clearSelection}
            disabled={!selectedIds.length}
          >
            清空选择
          </button>
        </div>
      </div>

      {saveMessage ? <div className="notice-banner is-success">{saveMessage}</div> : null}
      {saveError ? <div className="notice-banner is-error">{saveError}</div> : null}
      {reviewOptionsError ? (
        <div className="notice-banner is-error">{reviewOptionsError}</div>
      ) : null}

      <div className="table-shell">
        {filteredFavorites.length === 0 ? (
          <EmptyState
            title={favorites.length === 0 ? "暂无收藏文献" : "没有匹配筛选条件的收藏条目"}
            description={
              favorites.length === 0
                ? "浏览“发布日期文献”时，点击星标收藏文献，即可沉淀在此处。"
                : "请尝试清除搜索关键词或调整评审结论筛选。"
            }
          />
        ) : null}

        {/* Mobile View */}
        <div className="mobile-only">
          <div className="mobile-stack">
            {filteredFavorites.map((favorite) => {
              const normalizedDoi = normalizeDoi(favorite.doi);
              const isSelected = selectedIds.includes(favorite.id);
              const isEditing = editingPaperId === favorite.paper_id;
              const isUnfaving = pendingUnfavIds.has(favorite.paper_id);

              return (
                <article
                  className={`mobile-card paper-card favorite-card${isSelected ? " is-selected" : ""}`}
                  key={favorite.id}
                >
                  <div className="mobile-card-rail" aria-hidden="true">
                    <span />
                  </div>
                  <div className="mobile-card-body">
                    <div className="mobile-card-head mobile-paper-head">
                      <label className="check-row card-check">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleFavoriteSelection(favorite)}
                        />
                      </label>
                      <div className="mobile-paper-copy">
                        <h3 className="title-strong title-strong-en">
                          <a
                            href={favorite.article_url}
                            target="_blank"
                            rel="noreferrer"
                            className="paper-title-link"
                          >
                            {favorite.title_en}
                            <IconExternalLink size={12} className="title-jump-icon" />
                          </a>
                        </h3>
                        {favorite.title_zh ? (
                          <p className="mobile-summary title-strong title-strong-zh">
                            {favorite.title_zh}
                          </p>
                        ) : null}
                      </div>
                    </div>

                    <div className="mobile-paper-meta-row">
                      <InterestBadge
                        level={favorite.review_interest_level || favorite.interest_level}
                      />
                      <span className="mobile-journal-name">{favorite.journal}</span>
                      <span className="muted mobile-date">
                        {formatDigestDate(favorite.publish_date)}
                      </span>
                    </div>

                    {favorite.authors && favorite.authors.length ? (
                      <div className="paper-authors-row">
                        <AuthorList authors={favorite.authors} maxVisible={3} />
                      </div>
                    ) : null}

                    {normalizedDoi ? (
                      <div className="mobile-doi-row">
                        <span className="doi-pill">
                          <span className="doi-label">DOI</span>
                          <a
                            href={buildDoiUrl(normalizedDoi)}
                            target="_blank"
                            rel="noreferrer"
                            className="doi-link-compact"
                          >
                            {normalizedDoi}
                          </a>
                        </span>
                        <CopyDoiButton doi={normalizedDoi} />
                      </div>
                    ) : null}

                    {/* Review Block */}
                    <div className="favorite-review-container">
                      {isEditing ? (
                        <FavoriteReviewEditor
                          draft={draft}
                          options={reviewOptions}
                          disabled={savingPaperId === favorite.paper_id}
                          onChange={(key, val) => setDraft((prev) => ({ ...prev, [key]: val }))}
                          onCancel={cancelReview}
                          onSave={() => void saveReview(favorite.paper_id)}
                        />
                      ) : (
                        <FavoriteReviewSummary favorite={favorite} />
                      )}
                    </div>

                    <div className="mobile-card-actions paper-card-actions">
                      <button
                        className="table-link"
                        onClick={() =>
                          isEditing ? cancelReview() : startReview(favorite)
                        }
                      >
                        {isEditing ? "关闭评审" : "编辑备注"}
                      </button>
                      <button
                        className="table-link action-favorite-btn is-favorited"
                        onClick={() => void handleRemoveFavorite(favorite)}
                        disabled={isUnfaving}
                        title="移出收藏"
                      >
                        <IconStar size={14} filled={true} />
                        <span>{isUnfaving ? "…" : "取消收藏"}</span>
                      </button>
                      <a
                        className="table-link link-button"
                        href={favorite.article_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <IconExternalLink size={13} />
                        <span>Open</span>
                      </a>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        {/* Desktop View */}
        <div className="desktop-only">
          <table>
            <thead>
              <tr>
                <th className="select-col">
                  <input
                    type="checkbox"
                    checked={allFilteredSelected}
                    onChange={toggleFilteredBatch}
                  />
                </th>
                <th className="action-col">操作</th>
                <th className="journal-col">期刊 / 日期</th>
                <th className="score-col">强度</th>
                <th className="title-col">文献与作者</th>
                <th className="review-col">人工评审与备注</th>
              </tr>
            </thead>
            <tbody>
              {filteredFavorites.map((favorite) => {
                const normalizedDoi = normalizeDoi(favorite.doi);
                const isSelected = selectedIds.includes(favorite.id);
                const isEditing = editingPaperId === favorite.paper_id;
                const isUnfaving = pendingUnfavIds.has(favorite.paper_id);

                return (
                  <tr key={favorite.id} className={`paper-row${isSelected ? " is-selected" : ""}`}>
                    <td className="select-col">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleFavoriteSelection(favorite)}
                      />
                    </td>
                    <td className="action-col">
                      <div className="paper-actions-stack">
                        <button
                          className="table-link"
                          onClick={() =>
                            isEditing ? cancelReview() : startReview(favorite)
                          }
                        >
                          {isEditing ? "关闭" : "评审"}
                        </button>
                        <button
                          className="table-link action-favorite-btn is-favorited"
                          onClick={() => void handleRemoveFavorite(favorite)}
                          disabled={isUnfaving}
                          title="移出收藏"
                        >
                          <IconStar size={13} filled={true} />
                          <span>{isUnfaving ? "…" : "已收藏"}</span>
                        </button>
                      </div>
                    </td>
                    <td className="journal-col">
                      <div className="journal-cell">
                        <span className="journal-badge" title={favorite.journal}>
                          {favorite.journal}
                        </span>
                        <span className="muted journal-date">
                          {formatDigestDate(favorite.publish_date)}
                        </span>
                      </div>
                    </td>
                    <td className="score-col">
                      <InterestBadge
                        level={favorite.review_interest_level || favorite.interest_level}
                      />
                    </td>
                    <td className="title-col">
                      <div className="paper-title-block">
                        <a
                          className="table-title table-title-en paper-title-link"
                          href={favorite.article_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <span>{favorite.title_en}</span>
                          <IconExternalLink size={12} className="title-jump-icon" />
                        </a>
                      </div>

                      {favorite.title_zh ? (
                        <div className="table-title table-title-zh">{favorite.title_zh}</div>
                      ) : null}

                      {favorite.authors && favorite.authors.length ? (
                        <div className="paper-authors-row">
                          <AuthorList authors={favorite.authors} maxVisible={3} />
                        </div>
                      ) : null}

                      {normalizedDoi ? (
                        <div className="paper-doi-row">
                          <span className="doi-pill">
                            <span className="doi-label">DOI</span>
                            <a
                              className="doi-link-compact"
                              href={buildDoiUrl(normalizedDoi)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {normalizedDoi}
                            </a>
                          </span>
                          <CopyDoiButton doi={normalizedDoi} />
                        </div>
                      ) : null}
                    </td>
                    <td className="review-col">
                      {isEditing ? (
                        <FavoriteReviewEditor
                          draft={draft}
                          options={reviewOptions}
                          disabled={savingPaperId === favorite.paper_id}
                          onChange={(key, val) =>
                            setDraft((prev) => ({ ...prev, [key]: val }))
                          }
                          onCancel={cancelReview}
                          onSave={() => void saveReview(favorite.paper_id)}
                        />
                      ) : (
                        <FavoriteReviewSummary favorite={favorite} />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
