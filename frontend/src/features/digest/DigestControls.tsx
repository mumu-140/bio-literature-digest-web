import { useRef } from "react";
import { AuthUser, DigestSortKey } from "../../dataClient";
import { MetricTile, UserMultiSelect } from "../shared/WorkbenchUi";
import { DigestController } from "./useDigestLibrary";
import { MAX_DEERFLOW_DISCUSSION_PAPERS } from "./deerflowDiscussion";
import {
  IconArrowDownTray,
  IconChatBubble,
  IconFilter,
  IconSearch,
  IconXMark,
} from "../shared/Icons";

type ControlsProps = {
  user: AuthUser;
  digest: DigestController;
};

export function DigestControls(props: ControlsProps) {
  return (
    <>
      <DigestHeader digest={props.digest} />
      <DigestMetrics digest={props.digest} />
      <FilterControls digest={props.digest} />
      <ActiveFilterPills digest={props.digest} />
      <SelectionControls digest={props.digest} />
      <AdminPushControls {...props} />
      {props.digest.exportMessage ? (
        <div className="notice-banner is-success" role="status">
          {props.digest.exportMessage}
        </div>
      ) : null}
      {props.digest.loadingOverview ? (
        <div className="loading-bar">
          <span className="loading-spinner" />
          <span>正在按发布日期加载文献目录…</span>
        </div>
      ) : null}
      {props.digest.refreshingOverview ? (
        <div className="loading-bar">
          <span className="loading-spinner" />
          <span>正在更新筛选结果…</span>
        </div>
      ) : null}
    </>
  );
}

function DigestHeader({ digest }: { digest: DigestController }) {
  return (
    <div className="card-header">
      <div>
        <p className="eyebrow">本地文献仓库</p>
        <h2>发布日期文献库</h2>
      </div>
      <div className="actions">
        <button
          className="ghost-button"
          onClick={digest.refreshOverview}
          title="重新拉取本地最新文献索引"
        >
          刷新目录
        </button>
        <button
          className="ghost-button"
          onClick={digest.clearFilters}
          title="清空当前所有搜索与筛选条件"
        >
          重置筛选
        </button>
      </div>
    </div>
  );
}

function DigestMetrics({ digest }: { digest: DigestController }) {
  const dateCount = digest.publishDateOptions.length;
  const totalPapers = digest.overview?.total_papers || 0;
  const selectedCount = digest.selectedKeys.length;

  return (
    <div className="stats-strip">
      <MetricTile
        label="发布日期跨度"
        value={dateCount ? `${dateCount} 天` : "0 天"}
        hint="收录文献的发布日"
      />
      <MetricTile
        label="文献条目总数"
        value={totalPapers.toLocaleString()}
        hint="匹配筛选的文献篇数"
      />
      <MetricTile
        label="当前选中条目"
        value={String(selectedCount)}
        hint={selectedCount > 0 ? "可进行批量导出或讨论" : "勾选文献以批量操作"}
      />
    </div>
  );
}

function ActiveFilterPills({ digest }: { digest: DigestController }) {
  const { filters, setFilters } = digest;
  const hasQuery = Boolean(filters.query.trim());
  const hasDate = Boolean(filters.publishDate);
  const hasCategory = Boolean(filters.category);
  const hasTag = Boolean(filters.tag);

  if (!hasQuery && !hasDate && !hasCategory && !hasTag) {
    return null;
  }

  return (
    <div className="active-filters-bar">
      <span className="active-filters-label">
        <IconFilter size={13} />
        <span>当前筛选：</span>
      </span>
      <div className="active-filters-list">
        {hasQuery ? (
          <span className="filter-pill">
            <span className="filter-pill-text">搜索: &quot;{filters.query}&quot;</span>
            <button
              type="button"
              className="filter-pill-remove"
              onClick={() => setFilters((prev) => ({ ...prev, query: "" }))}
              title="清除搜索词"
              aria-label="清除搜索词"
            >
              <IconXMark size={12} />
            </button>
          </span>
        ) : null}

        {hasDate ? (
          <span className="filter-pill">
            <span className="filter-pill-text">日期: {filters.publishDate}</span>
            <button
              type="button"
              className="filter-pill-remove"
              onClick={() => setFilters((prev) => ({ ...prev, publishDate: "" }))}
              title="清除日期筛选"
              aria-label="清除日期筛选"
            >
              <IconXMark size={12} />
            </button>
          </span>
        ) : null}

        {hasCategory ? (
          <span className="filter-pill">
            <span className="filter-pill-text">分类: {filters.category}</span>
            <button
              type="button"
              className="filter-pill-remove"
              onClick={() => setFilters((prev) => ({ ...prev, category: "" }))}
              title="清除分类筛选"
              aria-label="清除分类筛选"
            >
              <IconXMark size={12} />
            </button>
          </span>
        ) : null}

        {hasTag ? (
          <span className="filter-pill">
            <span className="filter-pill-text">标签: {filters.tag}</span>
            <button
              type="button"
              className="filter-pill-remove"
              onClick={() => setFilters((prev) => ({ ...prev, tag: "" }))}
              title="清除标签筛选"
              aria-label="清除标签筛选"
            >
              <IconXMark size={12} />
            </button>
          </span>
        ) : null}

        <button
          type="button"
          className="clear-all-filters-btn"
          onClick={digest.clearFilters}
        >
          清空全部
        </button>
      </div>
    </div>
  );
}

function FilterControls({ digest }: { digest: DigestController }) {
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="filter-row filter-grid-wide">
      <div className="search-input-wrap">
        <IconSearch size={16} className="search-icon" />
        <input
          ref={searchInputRef}
          aria-label="搜索文献"
          name="paper_search"
          placeholder="搜索标题、摘要、期刊、标签… (按 / 聚焦)"
          value={digest.filters.query}
          onChange={(event) =>
            digest.setFilters((current) => ({ ...current, query: event.target.value }))
          }
          className="search-input"
        />
        {digest.filters.query ? (
          <button
            type="button"
            className="search-clear-btn"
            onClick={() => {
              digest.setFilters((current) => ({ ...current, query: "" }));
              searchInputRef.current?.focus();
            }}
            title="清空搜索内容"
            aria-label="清空搜索内容"
          >
            <IconXMark size={14} />
          </button>
        ) : null}
      </div>

      <select
        aria-label="发布日期"
        name="publish_date"
        value={digest.filters.publishDate}
        onChange={(event) =>
          digest.setFilters((current) => ({ ...current, publishDate: event.target.value }))
        }
      >
        <option value="">全部发布日期 ({digest.publishDateOptions.length}天)</option>
        {digest.publishDateOptions.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <select
        aria-label="分类"
        name="category"
        value={digest.filters.category}
        onChange={(event) =>
          digest.setFilters((current) => ({ ...current, category: event.target.value }))
        }
      >
        <option value="">全部分类 ({digest.categoryOptions.length})</option>
        {digest.categoryOptions.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <select
        aria-label="标签"
        name="tag"
        value={digest.filters.tag}
        onChange={(event) =>
          digest.setFilters((current) => ({ ...current, tag: event.target.value }))
        }
      >
        <option value="">全部标签 ({digest.tagOptions.length})</option>
        {digest.tagOptions.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <select
        aria-label="排序方式"
        name="sort"
        value={digest.filters.sort}
        onChange={(event) =>
          digest.setFilters((current) => ({
            ...current,
            sort: event.target.value as DigestSortKey,
          }))
        }
      >
        <option value="publish_date_desc">发布日期：从新到旧</option>
        <option value="publish_date_asc">发布日期：从旧到新</option>
      </select>
    </div>
  );
}

function SelectionControls({ digest }: { digest: DigestController }) {
  const selectedCount = digest.selectedKeys.length;
  const hasSelection = selectedCount > 0;
  const discussionOverLimit = selectedCount > MAX_DEERFLOW_DISCUSSION_PAPERS;

  return (
    <div className={`selection-toolbar${hasSelection ? " is-active" : ""}`}>
      <label className="check-row select-all-label">
        <input
          name="select_loaded_papers"
          type="checkbox"
          checked={digest.allVisibleSelected}
          onChange={() => digest.togglePaperBatch(digest.visibleLoadedPapers)}
        />
        <span>全选当前已加载 ({digest.visibleLoadedPapers.length})</span>
      </label>

      <div className="selection-actions-cluster">
        <span className="selection-count-badge">
          已选 <strong>{selectedCount}</strong> 篇
        </span>

        <button
          className="primary-button discuss-batch-btn"
          type="button"
          onClick={digest.discussSelectedPapers}
          disabled={!hasSelection || discussionOverLimit}
          title={
            discussionOverLimit
              ? `一次最多讨论 ${MAX_DEERFLOW_DISCUSSION_PAPERS} 篇`
              : "在 DeerFlow 启动针对选中文献的多篇研讨"
          }
        >
          <IconChatBubble size={15} />
          <span>在 DeerFlow 讨论 {hasSelection ? `(${selectedCount}/10)` : ""}</span>
        </button>

        <button
          className="ghost-button"
          onClick={() => digest.importSelectedReferences("zotero")}
          disabled={!hasSelection}
          title="生成所选文献的 RIS 导入文件"
        >
          <IconArrowDownTray size={14} />
          <span>Zotero</span>
        </button>

        <button
          className="ghost-button"
          onClick={() => digest.importSelectedReferences("endnote")}
          disabled={!hasSelection}
          title="生成所选文献的 EndNote 导入文件"
        >
          <IconArrowDownTray size={14} />
          <span>EndNote</span>
        </button>

        <button
          className="ghost-button"
          onClick={() => digest.runSelectedExport("metadata")}
          disabled={!hasSelection}
          title="导出所选文献的 JSON 元数据"
        >
          <span>元数据</span>
        </button>

        <button
          className="ghost-button"
          onClick={() => digest.runSelectedExport("doi-list")}
          disabled={!hasSelection}
          title="导出所选文献的 DOI 文本列表"
        >
          <span>DOI 列表</span>
        </button>

        <button
          className="ghost-button clear-selection-btn"
          onClick={digest.clearSelection}
          disabled={!hasSelection}
          title="取消选中所有条目"
        >
          清空已选
        </button>
      </div>

      {discussionOverLimit ? (
        <span className="error-text selection-error">
          ⚠️ 讨论最多选择 {MAX_DEERFLOW_DISCUSSION_PAPERS} 篇，当前已选 {selectedCount} 篇，请缩小选择范围。
        </span>
      ) : null}
    </div>
  );
}

function AdminPushControls({ user, digest }: ControlsProps) {
  if (user.role !== "admin") return null;

  return (
    <div className="push-bar">
      <div className="push-field">
        <span className="push-field-title">推送接收人</span>
        <UserMultiSelect
          users={digest.adminUsers}
          values={digest.pushTargetUserIds}
          onChange={digest.setPushTargetUserIds}
          placeholder="选择接收账户"
        />
      </div>

      <label className="push-field push-note-field">
        <span className="push-field-title">推送附言</span>
        <input
          aria-label="推送备注"
          name="push_note"
          placeholder="可选，添加阅读要点或备注"
          value={digest.pushNote}
          onChange={(event) => digest.setPushNote(event.target.value)}
        />
      </label>

      <label className="checkbox-label push-email-toggle">
        <input
          type="checkbox"
          checked={digest.sendPushEmail}
          onChange={(event) => digest.setSendPushEmail(event.target.checked)}
        />
        <span>邮件提醒</span>
      </label>

      <PushBatchCommand digest={digest} />
      <PushFeedback digest={digest} />
    </div>
  );
}

function PushBatchCommand({ digest }: { digest: DigestController }) {
  const paperCount = digest.selectedKeys.length;
  const recipientCount = digest.pushTargetUserIds.length;
  const overLimit = digest.pushCombinationCount > digest.maxPushCombinations;
  const disabled = !paperCount || !recipientCount || overLimit || digest.isPushPending;

  return (
    <div className="push-batch-command">
      <span className={overLimit ? "error-text" : "small-copy"}>
        {paperCount} 篇 × {recipientCount} 人 = {digest.pushCombinationCount} 条推送
      </span>
      <button
        className="primary-button"
        type="button"
        disabled={disabled}
        onClick={() => void digest.pushSelectedPapers()}
      >
        {digest.isBatchPushing ? "推送中…" : "推送选中"}
      </button>
    </div>
  );
}

function PushFeedback({ digest }: { digest: DigestController }) {
  if (!digest.pushFeedback) return null;

  return (
    <div
      className={"push-feedback is-" + digest.pushFeedback.kind}
      role="status"
      aria-live="polite"
    >
      {digest.pushFeedback.message}
    </div>
  );
}
