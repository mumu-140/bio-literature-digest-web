import { AuthUser, PaperLibraryOverview } from "../../dataClient";
import { EmptyState, formatDigestDate } from "../shared/WorkbenchUi";
import { PaperTable } from "./PaperTable";
import { DigestController } from "./useDigestLibrary";
import { IconCalendar, IconChevronDown, IconChevronUp } from "../shared/Icons";

type GroupsProps = {
  user: AuthUser;
  digest: DigestController;
};

type GroupSummary = PaperLibraryOverview["groups"][number];

export function DigestGroups(props: GroupsProps) {
  return (
    <div className="digest-layout">
      <DateRail digest={props.digest} />
      <DigestSections {...props} />
    </div>
  );
}

function DateRail({ digest }: { digest: DigestController }) {
  return (
    <aside className="date-rail desktop-only" aria-label="发布日期导航">
      <div className="date-rail-title">
        <IconCalendar size={13} />
        <span>日期时间线</span>
      </div>
      <div className="date-rail-scroll">
        {digest.groupSummaries.map((group) => {
          const isActive = group.publish_date === digest.activeRailDate;
          return (
            <button
              className={"date-rail-item" + (isActive ? " is-active" : "")}
              key={group.publish_date}
              onClick={() => void digest.scrollToDate(group.publish_date)}
              title={`${group.publish_date}（共 ${group.paper_count} 篇）`}
            >
              <span className="date-rail-marker">
                <span />
              </span>
              <div className="date-rail-info">
                <span className="date-rail-label">{formatDigestDate(group.publish_date)}</span>
                <span className="date-rail-count">{group.paper_count}</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function DigestSections(props: GroupsProps) {
  const { digest } = props;
  const allDates = digest.groupSummaries.map((g) => g.publish_date);
  const allExpanded =
    allDates.length > 0 &&
    allDates.every((date) => digest.expandedPublishDates.includes(date));

  function handleToggleAllDays() {
    if (allExpanded) {
      // Collapse all
      for (const date of digest.expandedPublishDates) {
        digest.togglePublishDateGroup(date);
      }
    } else {
      // Expand all available
      for (const group of digest.groupSummaries) {
        if (!digest.expandedPublishDates.includes(group.publish_date)) {
          digest.togglePublishDateGroup(group.publish_date);
        }
      }
    }
  }

  return (
    <div className="digest-sections">
      <MobileDateStrip digest={digest} />

      {digest.groupSummaries.length > 0 ? (
        <div className="sections-quickbar">
          <span className="sections-count-hint">
            共收录 <strong>{digest.groupSummaries.length}</strong> 个发布日
          </span>
          <button
            type="button"
            className="ghost-button toggle-all-days-btn"
            onClick={handleToggleAllDays}
          >
            {allExpanded ? "收起所有日期" : "展开所有日期"}
          </button>
        </div>
      ) : null}

      {digest.groupSummaries.length === 0 ? (
        <EmptyState
          title="当前没有符合条件的文献"
          description="调整搜索词、发布日期、分类或标签筛选条件后再试。"
          action={
            <button className="primary-button" onClick={digest.clearFilters}>
              清空所有筛选条件
            </button>
          }
        />
      ) : null}

      {digest.groupSummaries.map((group) => (
        <DigestDaySection key={group.publish_date} group={group} {...props} />
      ))}
    </div>
  );
}

function MobileDateStrip({ digest }: { digest: DigestController }) {
  return (
    <div className="mobile-day-strip mobile-only" aria-label="移动端快速选日">
      {digest.groupSummaries.map((group) => {
        const isActive = group.publish_date === digest.activeRailDate;
        return (
          <button
            className={"date-chip" + (isActive ? " is-active" : "")}
            key={group.publish_date}
            onClick={() => void digest.scrollToDate(group.publish_date)}
          >
            <span>{formatDigestDate(group.publish_date)}</span>
            <span className="date-chip-count">{group.paper_count}</span>
          </button>
        );
      })}
    </div>
  );
}

function DigestDaySection({
  user,
  digest,
  group,
}: GroupsProps & { group: GroupSummary }) {
  const isExpanded = digest.expandedPublishDates.includes(group.publish_date);
  const groupData = digest.loadedGroups[group.publish_date];
  const isLoading = digest.loadingGroupDates.includes(group.publish_date);

  const dayPapers = groupData?.items || [];
  const dayHasPapers = dayPapers.length > 0;
  const dayAllSelected =
    dayHasPapers &&
    dayPapers.every((p) => digest.selectedKeySet.has(String(p.id)));

  function handleToggleDaySelection() {
    if (!dayHasPapers) return;
    digest.togglePaperBatch(dayPapers);
  }

  return (
    <section className="day-section subpanel" id={"digest-day-" + group.publish_date}>
      <div className="day-section-header">
        <div className="day-section-title-wrap">
          <p className="eyebrow">发布日期</p>
          <div className="day-section-title-row">
            <h3>{formatDigestDate(group.publish_date)}</h3>
            <span className="status-pill is-idle day-count-pill">{group.paper_count} 篇</span>
          </div>
        </div>

        <div className="day-section-meta">
          {isExpanded && dayHasPapers ? (
            <button
              type="button"
              className="table-link select-day-batch-btn"
              onClick={handleToggleDaySelection}
              title={dayAllSelected ? "取消全选本日" : "快速勾选本日已加载的所有文献"}
            >
              {dayAllSelected ? "取消本日全选" : "全选本日"}
            </button>
          ) : null}

          <button
            className="ghost-button day-section-toggle"
            onClick={() => void digest.togglePublishDateGroup(group.publish_date)}
            aria-expanded={isExpanded}
          >
            <span>{isExpanded ? "收起" : "展开"}</span>
            {isExpanded ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
          </button>
        </div>
      </div>

      {isExpanded ? (
        <ExpandedGroup
          user={user}
          digest={digest}
          group={group}
          isLoading={isLoading}
          groupData={groupData}
        />
      ) : null}
    </section>
  );
}

function ExpandedGroup({
  user,
  digest,
  group,
  isLoading,
  groupData,
}: GroupsProps & {
  group: GroupSummary;
  isLoading: boolean;
  groupData: DigestController["loadedGroups"][string] | undefined;
}) {
  if (isLoading && !groupData) {
    return (
      <div className="group-loading-state">
        <span className="loading-spinner" />
        <span>正在加载该发布日期的文献条目…</span>
      </div>
    );
  }

  return (
    <>
      <PaperTable
        papers={groupData?.items || []}
        selectedKeys={digest.selectedKeySet}
        pendingFavoriteIds={digest.pendingFavoriteIdSet}
        onToggleSelect={digest.togglePaperSelection}
        onToggleSelectAll={digest.togglePaperBatch}
        onFavorite={digest.toggleFavorite}
        onDiscuss={digest.discussPaper}
        onPush={user.role === "admin" ? digest.pushPaper : undefined}
        pushingPaperId={digest.pushingPaperId}
        pushPending={digest.isPushPending}
      />
      {groupData?.has_more ? (
        <div className="actions load-more-actions">
          <button
            className="ghost-button load-more-btn"
            onClick={() => void digest.loadMoreGroup(group.publish_date)}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner" />
                <span>正在获取文献…</span>
              </>
            ) : (
              <span>
                加载更多本篇文献（剩余 {groupData.paper_count - groupData.items.length} 篇）
              </span>
            )}
          </button>
        </div>
      ) : null}
    </>
  );
}
