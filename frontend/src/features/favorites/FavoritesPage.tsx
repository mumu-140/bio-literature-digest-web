import { useEffect, useState } from "react";

import {
  AuthUser,
  FavoriteItem,
  FavoriteReviewDraft,
  FavoriteReviewOptions,
  fetchFavoriteReviewOptions,
  listFavorites,
  saveFavoriteReview as saveFavoriteReviewRequest,
} from "../../dataClient";
import { importIntoEndNote, importIntoZotero } from "../../referenceImport";
import { FavoriteReviewEditor, FavoriteReviewSummary } from "./FavoriteReviewComponents";
import { exportSelectedFavorites } from "../shared/paperExport";
import {
  EmptyState,
  formatReviewDecision,
  InterestBadge,
  MetricTile,
  useAdminUsers,
  UserSelect,
} from "../shared/WorkbenchUi";

export function FavoritesPage({ user }: { user: AuthUser }) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [targetUserId, setTargetUserId] = useState(String(user.id));
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
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

  const allSelected = favorites.length > 0 && favorites.every((favorite) => selectedIds.includes(favorite.id));

  function toggleFavoriteSelection(favorite: FavoriteItem) {
    setSelectedIds((current) => (current.includes(favorite.id) ? current.filter((id) => id !== favorite.id) : [...current, favorite.id]));
  }

  function toggleFavoriteBatch(items: FavoriteItem[]) {
    const ids = items.map((item) => item.id);
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
  }

  function exportFavorites(kind: "metadata" | "doi-list") {
    const selected = favorites.filter((favorite) => selectedIds.includes(favorite.id));
    if (!selected.length) {
      return;
    }
    exportSelectedFavorites(selected, kind);
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  function startEdit(favorite: FavoriteItem) {
    if (
      !reviewOptions.interest_levels.length &&
      !reviewOptions.interest_tags.length &&
      !reviewOptions.review_final_decisions.length &&
      !reviewOptions.review_final_categories.length
    ) {
      void loadReviewOptions();
    }
    setEditingPaperId(favorite.paper_id);
    setDraft({
      review_interest_level: favorite.review_interest_level || favorite.interest_level,
      review_interest_tag: favorite.review_interest_tag || favorite.interest_tag,
      review_final_decision: favorite.review_final_decision || "",
      review_final_category: favorite.review_final_category || favorite.category,
      reviewer_notes: favorite.reviewer_notes || "",
    });
    setSaveMessage("");
    setSaveError("");
  }

  function cancelEdit() {
    setEditingPaperId(null);
    setSaveError("");
  }

  function updateDraft<K extends keyof FavoriteReviewDraft>(key: K, value: FavoriteReviewDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function saveFavoriteReview(favorite: FavoriteItem) {
    setSavingPaperId(favorite.paper_id);
    setSaveMessage("");
    setSaveError("");
    try {
      const updated = await saveFavoriteReviewRequest(
        favorite.paper_id,
        draft,
        user.role === "admin" ? targetUserId : undefined,
      );
      setFavorites((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setEditingPaperId(null);
      setSaveMessage("已保存，修改会保留在当前工作台数据中，并用于后续人工导出。");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSavingPaperId(null);
    }
  }

  const activeTarget = user.role === "admin" ? adminUsers.find((item) => String(item.id) === targetUserId) : null;
  const targetLabel = activeTarget ? activeTarget.name : user.name;

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">个人收藏</p>
          <h2>收藏与人工备注</h2>
        </div>
        {user.role === "admin" ? (
          <UserSelect users={adminUsers} value={targetUserId} onChange={setTargetUserId} placeholder="选择查看账户" />
        ) : null}
      </div>
      <div className="stats-strip">
        <MetricTile label="收藏数" value={String(favorites.length)} />
        <MetricTile label="查看账户" value={targetLabel} />
      </div>
      {reviewOptionsError ? <div className="notice-banner is-error">{reviewOptionsError}</div> : null}
      {saveMessage ? <div className="notice-banner is-success">{saveMessage}</div> : null}
      {saveError ? <div className="notice-banner is-error">{saveError}</div> : null}
      <div className="selection-toolbar">
        <label className="check-row">
          <input type="checkbox" checked={allSelected} onChange={() => toggleFavoriteBatch(favorites)} />
          <span>全选收藏结果</span>
        </label>
        <div className="actions">
          <span className="selection-copy">已选 {selectedIds.length} 篇</span>
          <button className="ghost-button" onClick={clearSelection} disabled={!selectedIds.length}>清空选择</button>
          <button className="primary-button" onClick={() => importSelectedFavoriteReferences("zotero")} disabled={!selectedIds.length}>导入 Zotero</button>
          <button className="ghost-button" onClick={() => importSelectedFavoriteReferences("endnote")} disabled={!selectedIds.length}>导入 EndNote</button>
          <button className="ghost-button" onClick={() => exportFavorites("metadata")} disabled={!selectedIds.length}>导出选中元数据</button>
          <button className="ghost-button" onClick={() => exportFavorites("doi-list")} disabled={!selectedIds.length}>导出选中 DOI</button>
        </div>
      </div>
      <div className="table-shell">
        {favorites.length === 0 ? <EmptyState title="当前没有收藏记录" description="收藏后的论文会沉淀在这里，适合继续做二次筛选和导出。" /> : null}
        <div className="mobile-only">
          <div className="mobile-stack">
            {favorites.map((favorite) => (
              <article className="mobile-card" key={favorite.id}>
                <div className="mobile-card-head">
                  <label className="check-row card-check">
                    <input
                      type="checkbox"
                      aria-label={`选择收藏：${favorite.title_en}`}
                      checked={selectedIds.includes(favorite.id)}
                      onChange={() => toggleFavoriteSelection(favorite)}
                    />
                  </label>
                  <div>
                    <p className="eyebrow">{favorite.journal}</p>
                    <strong>{favorite.favorited_at}</strong>
                  </div>
                  <InterestBadge level={favorite.interest_level} />
                </div>
                <h3 className="title-strong title-strong-en">{favorite.title_en}</h3>
                <p className="mobile-summary title-strong title-strong-zh">{favorite.title_zh}</p>
                <div className="mobile-meta-grid">
                  <div>
                    <span className="meta-label">分类</span>
                    <strong>{favorite.category}</strong>
                  </div>
                  <div>
                    <span className="meta-label">标签</span>
                    <strong>{favorite.interest_tag}</strong>
                  </div>
                </div>
                <FavoriteReviewSummary favorite={favorite} />
                {editingPaperId === favorite.paper_id ? (
                  <FavoriteReviewEditor
                    draft={draft}
                    options={reviewOptions}
                    disabled={savingPaperId === favorite.paper_id}
                    onChange={updateDraft}
                    onCancel={cancelEdit}
                    onSave={() => void saveFavoriteReview(favorite)}
                  />
                ) : null}
                <div className="mobile-card-actions">
                  <button className="ghost-button" onClick={() => startEdit(favorite)}>修改</button>
                  <a className="table-link link-button" href={favorite.article_url} target="_blank" rel="noreferrer">Open</a>
                </div>
              </article>
            ))}
          </div>
        </div>
        <div className="desktop-only">
          <table>
            <thead>
              <tr>
                <th><input type="checkbox" aria-label="全选当前收藏" checked={allSelected} onChange={() => toggleFavoriteBatch(favorites)} /></th>
                <th>收藏时间</th>
                <th>期刊</th>
                <th>标题</th>
                <th>当前调整</th>
                <th>链接</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {favorites.map((favorite) => (
                <tr key={favorite.id}>
                  <td><input type="checkbox" aria-label={`选择收藏：${favorite.title_en}`} checked={selectedIds.includes(favorite.id)} onChange={() => toggleFavoriteSelection(favorite)} /></td>
                  <td>{favorite.favorited_at}</td>
                  <td>{favorite.journal}</td>
                  <td>
                    <div className="table-title table-title-en">{favorite.title_en}</div>
                    <div className="table-title table-title-zh">{favorite.title_zh}</div>
                  </td>
                  <td>
                    <FavoriteReviewSummary favorite={favorite} />
                    {editingPaperId === favorite.paper_id ? (
                      <FavoriteReviewEditor
                        draft={draft}
                        options={reviewOptions}
                        disabled={savingPaperId === favorite.paper_id}
                        onChange={updateDraft}
                        onCancel={cancelEdit}
                        onSave={() => void saveFavoriteReview(favorite)}
                      />
                    ) : null}
                  </td>
                  <td><a href={favorite.article_url} target="_blank" rel="noreferrer">Open</a></td>
                  <td>
                    <button className="ghost-button" onClick={() => startEdit(favorite)}>修改</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
