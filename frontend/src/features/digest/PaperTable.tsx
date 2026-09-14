import { useState } from "react";
import { PaperItem } from "../../dataClient";
import {
  AuthorList,
  CopyDoiButton,
  EmptyState,
  formatDigestDate,
  InterestBadge,
  normalizeDoi,
  buildDoiUrl,
} from "../shared/WorkbenchUi";
import {
  compactPaperTags,
  formatJournalMarker,
  getPaperDisplayTags,
  getPaperSelectionKey,
  isFlagshipJournal,
} from "./digestUtils";
import {
  IconChatBubble,
  IconChevronDown,
  IconChevronUp,
  IconExternalLink,
  IconSend,
  IconStar,
} from "../shared/Icons";

type PaperTableProps = {
  papers: PaperItem[];
  selectedKeys: Set<string>;
  pendingFavoriteIds: Set<number>;
  onToggleSelect: (item: PaperItem) => void;
  onToggleSelectAll: (items: PaperItem[]) => void;
  onFavorite: (item: PaperItem) => void;
  onDiscuss: (item: PaperItem) => void;
  onPush?: (item: PaperItem) => void;
  pushingPaperId?: number | null;
  pushPending?: boolean;
};

export function PaperTable(props: PaperTableProps) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  function toggleExpand(id: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="table-shell">
      {props.papers.length === 0 ? (
        <EmptyState title="当前没有可展示的文献" description="调整筛选条件后再刷新，或等待新的 digest 导入。" />
      ) : null}
      <MobilePaperList {...props} expandedIds={expandedIds} onToggleExpand={toggleExpand} />
      <DesktopPaperTable {...props} expandedIds={expandedIds} onToggleExpand={toggleExpand} />
    </div>
  );
}

function MobilePaperList(
  props: PaperTableProps & {
    expandedIds: Set<number>;
    onToggleExpand: (id: number) => void;
  },
) {
  return (
    <div className="mobile-only">
      <div className="mobile-stack">
        {props.papers.map((paper) => (
          <MobilePaperCard key={paper.id} paper={paper} {...props} />
        ))}
      </div>
    </div>
  );
}

function MobilePaperCard({
  paper,
  expandedIds,
  onToggleExpand,
  ...props
}: PaperTableProps & {
  paper: PaperItem;
  expandedIds: Set<number>;
  onToggleExpand: (id: number) => void;
}) {
  const compactTags = compactPaperTags(getPaperDisplayTags(paper));
  const pending = props.pendingFavoriteIds.has(paper.id);
  const isSelected = props.selectedKeys.has(getPaperSelectionKey(paper));
  const normalizedDoi = normalizeDoi(paper.doi);
  const isExpanded = expandedIds.has(paper.id);
  const isFlagship = isFlagshipJournal(paper.journal);
  const fullSummary = paper.summary_zh || paper.abstract || "";
  const shouldTruncate = fullSummary.length > 110;

  return (
    <article className={`mobile-card paper-card${isSelected ? " is-selected" : ""}`}>
      <div className="mobile-card-rail" aria-hidden="true">
        <span />
      </div>
      <div className="mobile-card-body">
        <div className="mobile-card-head mobile-paper-head">
          <label className="check-row card-check">
            <input
              type="checkbox"
              aria-label={"选择文献：" + paper.title_en}
              checked={isSelected}
              onChange={() => props.onToggleSelect(paper)}
            />
          </label>
          <div className="mobile-paper-copy">
            <h3 className="title-strong title-strong-en">
              <a href={paper.article_url} target="_blank" rel="noreferrer" className="paper-title-link">
                {paper.title_en}
                <IconExternalLink size={12} className="title-jump-icon" />
              </a>
            </h3>
            {paper.title_zh ? (
              <p className="mobile-summary title-strong title-strong-zh">{paper.title_zh}</p>
            ) : null}
          </div>
          <span
            className={"journal-marker" + (isFlagship ? " is-flagship" : "")}
            title={paper.journal}
          >
            {formatJournalMarker(paper.journal)}
          </span>
        </div>

        <div className="mobile-paper-meta-row">
          <InterestBadge level={paper.interest_level} />
          <span className="mobile-journal-name">{paper.journal}</span>
          <span className="muted mobile-date">{formatDigestDate(paper.publish_date_day)}</span>
        </div>

        {paper.authors && paper.authors.length ? (
          <div className="paper-authors-row">
            <AuthorList authors={paper.authors} maxVisible={3} />
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

        {fullSummary ? (
          <div className="mobile-paper-summary-wrap">
            <p className={`small-copy mobile-paper-blurb${isExpanded ? " is-expanded" : ""}`}>
              {fullSummary}
            </p>
            {shouldTruncate ? (
              <button
                type="button"
                className="expand-summary-btn"
                onClick={() => onToggleExpand(paper.id)}
              >
                {isExpanded ? (
                  <><span>收起摘要</span><IconChevronUp size={12} /></>
                ) : (
                  <><span>展开摘要</span><IconChevronDown size={12} /></>
                )}
              </button>
            ) : null}
          </div>
        ) : null}

        {compactTags.length ? (
          <div className="tag-list tag-list-compact">
            {compactTags.map((tag) => (
              <span key={String(paper.id) + "-" + tag}>{tag}</span>
            ))}
          </div>
        ) : null}

        <div className="mobile-card-actions paper-card-actions">
          <button
            className={`table-link action-favorite-btn${paper.is_favorited ? " is-favorited" : ""}`}
            onClick={() => props.onFavorite(paper)}
            disabled={pending}
            title={paper.is_favorited ? "取消收藏" : "加入收藏"}
          >
            <IconStar size={14} filled={paper.is_favorited} />
            <span>{pending ? "处理中…" : paper.is_favorited ? "已收藏" : "收藏"}</span>
          </button>
          <button
            className="table-link action-discuss-btn"
            onClick={() => props.onDiscuss(paper)}
            title="在 DeerFlow 讨论本文献"
          >
            <IconChatBubble size={14} />
            <span>讨论</span>
          </button>
          {props.onPush ? (
            <button
              className="table-link action-push-btn"
              onClick={() => props.onPush?.(paper)}
              disabled={props.pushPending}
              title="推送到团队成员"
            >
              <IconSend size={14} />
              <span>{props.pushingPaperId === paper.id ? "推送中…" : "推送"}</span>
            </button>
          ) : null}
          <a
            className="table-link link-button"
            href={paper.article_url}
            target="_blank"
            rel="noreferrer"
            title="在新标签页中打开原文"
          >
            <IconExternalLink size={13} />
            <span>Open</span>
          </a>
        </div>
      </div>
    </article>
  );
}

function DesktopPaperTable(
  props: PaperTableProps & {
    expandedIds: Set<number>;
    onToggleExpand: (id: number) => void;
  },
) {
  const allSelected =
    props.papers.length > 0 &&
    props.papers.every((paper) => props.selectedKeys.has(getPaperSelectionKey(paper)));

  return (
    <div className="desktop-only paper-table-shell">
      <table className="paper-table">
        <thead>
          <tr>
            <th className="select-col">
              <input
                type="checkbox"
                aria-label="全选当前表格文献"
                checked={allSelected}
                onChange={() => props.onToggleSelectAll(props.papers)}
              />
            </th>
            <th className="action-col">操作</th>
            <th className="journal-col">期刊 / 日期</th>
            <th className="score-col">评分</th>
            <th className="title-col">文献与作者</th>
            <th className="zh-col">中文概述</th>
            <th className="tags-col">标签</th>
          </tr>
        </thead>
        <tbody>
          {props.papers.map((paper) => (
            <DesktopPaperRow key={paper.id} paper={paper} {...props} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DesktopPaperRow({
  paper,
  expandedIds,
  onToggleExpand,
  ...props
}: PaperTableProps & {
  paper: PaperItem;
  expandedIds: Set<number>;
  onToggleExpand: (id: number) => void;
}) {
  const normalizedDoi = normalizeDoi(paper.doi);
  const displayTags = getPaperDisplayTags(paper);
  const pending = props.pendingFavoriteIds.has(paper.id);
  const isSelected = props.selectedKeys.has(getPaperSelectionKey(paper));
  const isExpanded = expandedIds.has(paper.id);
  const isFlagship = isFlagshipJournal(paper.journal);
  const fullSummary = paper.summary_zh || paper.abstract || "";
  const shouldTruncate = fullSummary.length > 120;

  return (
    <tr className={`paper-row${isSelected ? " is-selected" : ""}`}>
      <td className="select-col">
        <input
          type="checkbox"
          aria-label={"选择文献：" + paper.title_en}
          checked={isSelected}
          onChange={() => props.onToggleSelect(paper)}
        />
      </td>
      <td className="action-col">
        <div className="paper-actions-stack">
          <button
            className={`table-link action-favorite-btn${paper.is_favorited ? " is-favorited" : ""}`}
            onClick={() => props.onFavorite(paper)}
            disabled={pending}
            title={paper.is_favorited ? "取消收藏" : "加入收藏"}
          >
            <IconStar size={13} filled={paper.is_favorited} />
            <span>{pending ? "…" : paper.is_favorited ? "已收藏" : "收藏"}</span>
          </button>
          <button
            className="table-link action-discuss-btn"
            onClick={() => props.onDiscuss(paper)}
            title="在 DeerFlow 启动深度讨论"
          >
            <IconChatBubble size={13} />
            <span>讨论</span>
          </button>
          {props.onPush ? (
            <button
              className="table-link action-push-btn"
              onClick={() => props.onPush?.(paper)}
              disabled={props.pushPending}
              title="推送到团队账户"
            >
              <IconSend size={13} />
              <span>{props.pushingPaperId === paper.id ? "…" : "推送"}</span>
            </button>
          ) : null}
        </div>
      </td>
      <td className="journal-col">
        <div className="journal-cell">
          <span
            className={"journal-badge" + (isFlagship ? " is-flagship" : "")}
            title={paper.journal}
          >
            {paper.journal}
          </span>
          <span className="muted journal-date">{formatDigestDate(paper.publish_date_day)}</span>
        </div>
      </td>
      <td className="score-col">
        <InterestBadge level={paper.interest_level} />
      </td>
      <td className="title-col">
        <div className="paper-title-block">
          <a
            className="table-title table-title-en paper-title-link"
            href={paper.article_url}
            target="_blank"
            rel="noreferrer"
            title="打开文章原文"
          >
            <span>{paper.title_en}</span>
            <IconExternalLink size={12} className="title-jump-icon" />
          </a>
        </div>

        {paper.authors && paper.authors.length ? (
          <div className="paper-authors-row">
            <AuthorList authors={paper.authors} maxVisible={3} />
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

        {displayTags.length ? (
          <div className="paper-tags-inline table-tags-inline">
            {displayTags.map((tag) => (
              <span key={String(paper.id) + "-inline-" + tag}>{tag}</span>
            ))}
          </div>
        ) : null}
      </td>
      <td className="zh-col">
        {paper.title_zh ? (
          <div className="table-title table-title-zh">{paper.title_zh}</div>
        ) : null}
        {fullSummary ? (
          <div className="summary-block">
            <div className={`small-copy table-subcopy${isExpanded ? " is-expanded" : ""}`}>
              {fullSummary}
            </div>
            {shouldTruncate ? (
              <button
                type="button"
                className="expand-summary-btn"
                onClick={() => onToggleExpand(paper.id)}
              >
                {isExpanded ? (
                  <><span>收起摘要</span><IconChevronUp size={11} /></>
                ) : (
                  <><span>展开摘要</span><IconChevronDown size={11} /></>
                )}
              </button>
            ) : null}
          </div>
        ) : (
          <span className="muted small-copy">暂无中文概述</span>
        )}
      </td>
      <td className="tags-col">
        <div className="paper-tags-inline">
          {displayTags.length ? (
            displayTags.map((tag) => (
              <span key={String(paper.id) + "-" + tag}>{tag}</span>
            ))
          ) : (
            <span className="muted">-</span>
          )}
        </div>
      </td>
    </tr>
  );
}
