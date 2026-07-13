import { AuthUser, DigestSortKey } from "../../dataClient";
import { MetricTile, UserSelect } from "../shared/WorkbenchUi";
import { DigestController } from "./useDigestLibrary";

type ControlsProps = {
  user: AuthUser;
  digest: DigestController;
};

export function DigestControls(props: ControlsProps) {
  return (
    <>
      <DigestHeader digest={props.digest} />
      <DigestMetrics digest={props.digest} />
      <AdminPushControls {...props} />
      <FilterControls digest={props.digest} />
      <SelectionControls digest={props.digest} />
      {props.digest.exportMessage ? <p className="success-text">{props.digest.exportMessage}</p> : null}
      {props.digest.loadingOverview ? <div className="small-copy">正在按发布日期加载文献目录…</div> : null}
      {props.digest.refreshingOverview ? <div className="small-copy">正在更新筛选结果…</div> : null}
    </>
  );
}

function DigestHeader({ digest }: { digest: DigestController }) {
  return (
    <div className="card-header">
      <div>
        <p className="eyebrow">本地导入池</p>
        <h2>发布日期文献</h2>
      </div>
      <div className="actions">
        <button className="ghost-button" onClick={digest.refreshOverview}>刷新本地目录</button>
        <button className="ghost-button" onClick={digest.clearFilters}>清空筛选</button>
      </div>
    </div>
  );
}

function DigestMetrics({ digest }: { digest: DigestController }) {
  const dateCount = digest.publishDateOptions.length;
  return (
    <div className="stats-strip">
      <MetricTile label="发布日期" value={dateCount ? String(dateCount) + " 天" : "0 天"} />
      <MetricTile label="筛选结果" value={String(digest.overview?.total_papers || 0)} />
      <MetricTile label="已选条目" value={String(digest.selectedKeys.length)} />
    </div>
  );
}

function AdminPushControls({ user, digest }: ControlsProps) {
  if (user.role !== "admin") {
    return null;
  }
  return (
    <div className="push-bar">
      <UserSelect
        users={digest.adminUsers}
        value={digest.pushTargetUserId}
        onChange={digest.setPushTargetUserId}
        placeholder="选择接收账户"
      />
      <input
        aria-label="推送备注"
        name="push_note"
        placeholder="推送备注"
        value={digest.pushNote}
        onChange={(event) => digest.setPushNote(event.target.value)}
      />
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={digest.sendPushEmail}
          onChange={(event) => digest.setSendPushEmail(event.target.checked)}
        />
        邮件提醒
      </label>
      {digest.pushMessage ? <span className="success-text">{digest.pushMessage}</span> : null}
    </div>
  );
}

function FilterControls({ digest }: { digest: DigestController }) {
  return (
    <div className="filter-row filter-grid-wide">
      <input
        aria-label="搜索文献"
        name="paper_search"
        placeholder="搜索标题、摘要、期刊、标签"
        value={digest.filters.query}
        onChange={(event) => digest.setFilters((current) => ({ ...current, query: event.target.value }))}
      />
      <select
        aria-label="发布日期"
        name="publish_date"
        value={digest.filters.publishDate}
        onChange={(event) => digest.setFilters((current) => ({ ...current, publishDate: event.target.value }))}
      >
        <option value="">全部发布日期</option>
        {digest.publishDateOptions.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      <select
        aria-label="分类"
        name="category"
        value={digest.filters.category}
        onChange={(event) => digest.setFilters((current) => ({ ...current, category: event.target.value }))}
      >
        <option value="">全部分类</option>
        {digest.categoryOptions.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      <select
        aria-label="标签"
        name="tag"
        value={digest.filters.tag}
        onChange={(event) => digest.setFilters((current) => ({ ...current, tag: event.target.value }))}
      >
        <option value="">全部标签</option>
        {digest.tagOptions.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      <select
        aria-label="排序方式"
        name="sort"
        value={digest.filters.sort}
        onChange={(event) => digest.setFilters((current) => ({ ...current, sort: event.target.value as DigestSortKey }))}
      >
        <option value="publish_date_desc">发布日期：从新到旧</option>
        <option value="publish_date_asc">发布日期：从旧到新</option>
      </select>
    </div>
  );
}

function SelectionControls({ digest }: { digest: DigestController }) {
  const hasSelection = digest.selectedKeys.length > 0;
  return (
    <div className="selection-toolbar">
      <label className="check-row">
        <input
          name="select_loaded_papers"
          type="checkbox"
          checked={digest.allVisibleSelected}
          onChange={() => digest.togglePaperBatch(digest.visibleLoadedPapers)}
        />
        <span>全选当前已加载</span>
      </label>
      <div className="actions">
        <span className="selection-copy">已选 {digest.selectedKeys.length} 篇</span>
        <button className="ghost-button" onClick={digest.clearSelection} disabled={!hasSelection}>清空选择</button>
        <button className="primary-button" onClick={() => digest.importSelectedReferences("zotero")} disabled={!hasSelection}>导入 Zotero</button>
        <button className="ghost-button" onClick={() => digest.importSelectedReferences("endnote")} disabled={!hasSelection}>导入 EndNote</button>
        <button className="ghost-button" onClick={() => digest.runSelectedExport("metadata")} disabled={!hasSelection}>导出选中元数据</button>
        <button className="ghost-button" onClick={() => digest.runSelectedExport("doi-list")} disabled={!hasSelection}>导出选中 DOI</button>
      </div>
    </div>
  );
}
