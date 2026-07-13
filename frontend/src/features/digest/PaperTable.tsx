import { PaperItem } from "../../dataClient";
import {
  buildDoiUrl,
  EmptyState,
  formatDigestDate,
  InterestBadge,
  normalizeDoi,
} from "../shared/WorkbenchUi";
import {
  compactPaperTags,
  formatJournalMarker,
  getPaperDisplayTags,
  getPaperSelectionKey,
  isFlagshipJournal,
} from "./digestUtils";

type PaperTableProps = {
  papers: PaperItem[];
  selectedKeys: Set<string>;
  pendingFavoriteIds: Set<number>;
  onToggleSelect: (item: PaperItem) => void;
  onToggleSelectAll: (items: PaperItem[]) => void;
  onFavorite: (item: PaperItem) => void;
  onPush?: (item: PaperItem) => void;
  pushingPaperId?: number | null;
  pushPending?: boolean;
};

export function PaperTable(props: PaperTableProps) {
  return (
    <div className="table-shell">
      {props.papers.length === 0 ? (
        <EmptyState title="当前没有可展示的文献" description="调整筛选条件后再刷新，或等待新的 digest 导入。" />
      ) : null}
      <MobilePaperList {...props} />
      <DesktopPaperTable {...props} />
    </div>
  );
}

function MobilePaperList(props: PaperTableProps) {
  return (
    <div className="mobile-only">
      <div className="mobile-stack">
        {props.papers.map((paper) => <MobilePaperCard key={paper.id} paper={paper} {...props} />)}
      </div>
    </div>
  );
}

function MobilePaperCard({ paper, ...props }: PaperTableProps & { paper: PaperItem }) {
  const compactTags = compactPaperTags(getPaperDisplayTags(paper));
  const pending = props.pendingFavoriteIds.has(paper.id);
  return (
    <article className="mobile-card paper-card">
      <div className="mobile-card-rail" aria-hidden="true"><span /></div>
      <div className="mobile-card-body">
        <div className="mobile-card-head mobile-paper-head">
          <label className="check-row card-check">
            <input
              type="checkbox"
              aria-label={"选择文献：" + paper.title_en}
              checked={props.selectedKeys.has(getPaperSelectionKey(paper))}
              onChange={() => props.onToggleSelect(paper)}
            />
          </label>
          <div className="mobile-paper-copy">
            <h3 className="title-strong title-strong-en">{paper.title_en}</h3>
            <p className="mobile-summary title-strong title-strong-zh">{paper.title_zh}</p>
          </div>
          <span className={"journal-marker" + (isFlagshipJournal(paper.journal) ? " is-flagship" : "")} title={paper.journal}>
            {formatJournalMarker(paper.journal)}
          </span>
        </div>
        <div className="mobile-paper-meta"><InterestBadge level={paper.interest_level} /></div>
        <p className="small-copy mobile-paper-blurb">{paper.summary_zh}</p>
        {compactTags.length ? (
          <div className="tag-list tag-list-compact">
            {compactTags.map((tag) => <span key={String(paper.id) + "-" + tag}>{tag}</span>)}
          </div>
        ) : null}
        <div className="mobile-card-actions paper-card-actions">
          <button className="table-link" onClick={() => props.onFavorite(paper)} disabled={pending}>
            {pending ? "处理中…" : paper.is_favorited ? "取消收藏" : "加入收藏"}
          </button>
          {props.onPush ? (
            <button className="table-link" onClick={() => props.onPush?.(paper)} disabled={props.pushPending}>
              {props.pushingPaperId === paper.id ? "推送中…" : "推送"}
            </button>
          ) : null}
          <a className="table-link link-button" href={paper.article_url} target="_blank" rel="noreferrer">Open</a>
        </div>
      </div>
    </article>
  );
}

function DesktopPaperTable(props: PaperTableProps) {
  const allSelected = props.papers.length > 0 && props.papers.every((paper) =>
    props.selectedKeys.has(getPaperSelectionKey(paper)),
  );
  return (
    <div className="desktop-only">
      <table className="paper-table">
        <thead>
          <tr>
            <th><input type="checkbox" aria-label="全选当前表格文献" checked={allSelected} onChange={() => props.onToggleSelectAll(props.papers)} /></th>
            <th className="action-col">操作</th>
            <th className="journal-col">期刊</th>
            <th className="score-col">评分</th>
            <th className="title-col">标题</th>
            <th className="zh-col">中文</th>
            <th className="tags-col">标签</th>
          </tr>
        </thead>
        <tbody>
          {props.papers.map((paper) => <DesktopPaperRow key={paper.id} paper={paper} {...props} />)}
        </tbody>
      </table>
    </div>
  );
}

function DesktopPaperRow({ paper, ...props }: PaperTableProps & { paper: PaperItem }) {
  const normalizedDoi = normalizeDoi(paper.doi);
  const displayTags = getPaperDisplayTags(paper);
  const pending = props.pendingFavoriteIds.has(paper.id);
  return (
    <tr>
      <td>
        <input
          type="checkbox"
          aria-label={"选择文献：" + paper.title_en}
          checked={props.selectedKeys.has(getPaperSelectionKey(paper))}
          onChange={() => props.onToggleSelect(paper)}
        />
      </td>
      <td className="action-col">
        <div className="paper-actions-stack">
          <button className="table-link" onClick={() => props.onFavorite(paper)} disabled={pending}>
            {pending ? "处理中…" : paper.is_favorited ? "取消" : "收藏"}
          </button>
          {props.onPush ? (
            <button className="table-link" onClick={() => props.onPush?.(paper)} disabled={props.pushPending}>
              {props.pushingPaperId === paper.id ? "推送中…" : "推送"}
            </button>
          ) : null}
        </div>
      </td>
      <td className="journal-col">{paper.journal}<br /><span className="muted">{formatDigestDate(paper.publish_date_day)}</span></td>
      <td className="score-col"><InterestBadge level={paper.interest_level} /></td>
      <td className="title-col">
        <a className="table-title table-title-en paper-title-link" href={paper.article_url} target="_blank" rel="noreferrer">
          {paper.title_en}<span className="title-jump" aria-hidden="true">↗</span>
        </a>
        <div className="small-copy table-subcopy">
          doi：
          {normalizedDoi ? (
            <a className="doi-link" href={buildDoiUrl(normalizedDoi)} target="_blank" rel="noreferrer">[{normalizedDoi}]</a>
          ) : <span className="muted">[暂无]</span>}
        </div>
        <div className="small-copy table-subcopy">{paper.summary_zh}</div>
      </td>
      <td className="zh-col"><div className="table-title table-title-zh">{paper.title_zh}</div></td>
      <td className="tags-col">
        <div className="paper-tags-inline">
          {displayTags.length
            ? displayTags.map((tag) => <span key={String(paper.id) + "-" + tag}>{tag}</span>)
            : <span className="muted">-</span>}
        </div>
      </td>
    </tr>
  );
}
