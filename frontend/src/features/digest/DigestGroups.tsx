import { AuthUser, PaperLibraryOverview } from "../../dataClient";
import { EmptyState, formatDigestDate } from "../shared/WorkbenchUi";
import { PaperTable } from "./PaperTable";
import { DigestController } from "./useDigestLibrary";

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
    <aside className="date-rail desktop-only">
      {digest.groupSummaries.map((group) => (
        <button
          className={"date-rail-item" + (group.publish_date === digest.activeRailDate ? " is-active" : "")}
          key={group.publish_date}
          onClick={() => void digest.scrollToDate(group.publish_date)}
        >
          <span className="date-rail-marker"><span /></span>
          <span className="date-rail-label">{formatDigestDate(group.publish_date)}</span>
        </button>
      ))}
    </aside>
  );
}

function DigestSections(props: GroupsProps) {
  const { digest } = props;
  return (
    <div className="digest-sections">
      <MobileDateStrip digest={digest} />
      {digest.groupSummaries.length === 0 ? (
        <EmptyState title="当前没有符合条件的文献" description="调整搜索、发布日期、分类或标签筛选后再试。" />
      ) : null}
      {digest.groupSummaries.map((group) => (
        <DigestDaySection key={group.publish_date} group={group} {...props} />
      ))}
    </div>
  );
}

function MobileDateStrip({ digest }: { digest: DigestController }) {
  return (
    <div className="mobile-day-strip mobile-only">
      {digest.groupSummaries.map((group) => (
        <button
          className={"date-chip" + (group.publish_date === digest.activeRailDate ? " is-active" : "")}
          key={group.publish_date}
          onClick={() => void digest.scrollToDate(group.publish_date)}
        >
          {formatDigestDate(group.publish_date)}
        </button>
      ))}
    </div>
  );
}

function DigestDaySection({ user, digest, group }: GroupsProps & { group: GroupSummary }) {
  const isExpanded = digest.expandedPublishDates.includes(group.publish_date);
  const groupData = digest.loadedGroups[group.publish_date];
  const isLoading = digest.loadingGroupDates.includes(group.publish_date);

  return (
    <section className="day-section subpanel" id={"digest-day-" + group.publish_date}>
      <div className="day-section-header">
        <div>
          <p className="eyebrow">发布日期</p>
          <h3>{formatDigestDate(group.publish_date)}</h3>
        </div>
        <div className="day-section-meta">
          <span className="status-pill is-idle">{group.paper_count} 篇</span>
          <button className="ghost-button day-section-toggle" onClick={() => void digest.togglePublishDateGroup(group.publish_date)}>
            {isExpanded ? "收起" : "展开"}
          </button>
        </div>
      </div>
      {isExpanded ? <ExpandedGroup user={user} digest={digest} group={group} isLoading={isLoading} groupData={groupData} /> : null}
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
    return <div className="small-copy">正在加载该发布日期的文献…</div>;
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
        <div className="actions">
          <button
            className="ghost-button"
            onClick={() => void digest.loadMoreGroup(group.publish_date)}
            disabled={isLoading}
          >
            {isLoading ? "加载中…" : "加载更多（剩余 " + String(groupData.paper_count - groupData.items.length) + "）"}
          </button>
        </div>
      ) : null}
    </>
  );
}
