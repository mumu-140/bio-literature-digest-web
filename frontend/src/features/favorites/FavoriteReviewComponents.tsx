import { FavoriteItem, FavoriteReviewDraft, FavoriteReviewOptions } from "../../dataClient";
import { formatReviewDecision, InterestBadge } from "../shared/WorkbenchUi";
import { IconCheck, IconXMark } from "../shared/Icons";

export function FavoriteReviewSummary({ favorite }: { favorite: FavoriteItem }) {
  const effectiveInterestLevel = favorite.review_interest_level || favorite.interest_level;
  const effectiveInterestTag = favorite.review_interest_tag || favorite.interest_tag;
  const effectiveGroup = favorite.review_final_category || favorite.category;
  const decisionKey = favorite.review_final_decision;
  const effectiveDecision = formatReviewDecision(decisionKey);

  let decisionTone = "is-idle";
  if (decisionKey === "keep") decisionTone = "is-live";
  else if (decisionKey === "follow_up") decisionTone = "is-warm";
  else if (decisionKey === "exclude" || decisionKey === "archive") decisionTone = "is-muted";

  return (
    <div className="favorite-review-summary">
      <div className="review-badges-row">
        <InterestBadge level={effectiveInterestLevel} />
        {effectiveInterestTag ? (
          <span className="review-tag-badge">{effectiveInterestTag}</span>
        ) : null}
        {effectiveGroup ? (
          <span className="review-group-badge">{effectiveGroup}</span>
        ) : null}
        {effectiveDecision ? (
          <span className={`status-pill ${decisionTone} review-decision-badge`}>
            {effectiveDecision}
          </span>
        ) : null}
      </div>

      <div className="review-notes-body">
        {favorite.reviewer_notes ? (
          <p className="reviewer-notes-text">{favorite.reviewer_notes}</p>
        ) : (
          <span className="muted small-copy">暂无人工评审备注</span>
        )}
      </div>

      {favorite.review_updated_at ? (
        <div className="muted review-timestamp">
          评审更新于：{favorite.review_updated_at}
        </div>
      ) : null}
    </div>
  );
}

export function FavoriteReviewEditor({
  draft,
  options,
  disabled,
  onChange,
  onCancel,
  onSave,
}: {
  draft: FavoriteReviewDraft;
  options: FavoriteReviewOptions;
  disabled: boolean;
  onChange: (key: keyof FavoriteReviewDraft, value: string) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  const quickDecisions = [
    { key: "keep", label: "保留" },
    { key: "follow_up", label: "继续跟进" },
    { key: "archive", label: "归档" },
    { key: "exclude", label: "排除" },
  ];

  return (
    <div className="favorite-review-editor">
      <div className="review-editor-head">
        <h4>编辑人工评审与备注</h4>
        <span className="muted small-copy">修改将保存在本地数据库中，可随文献导出</span>
      </div>

      <div className="review-quick-decisions">
        <span className="quick-decision-label">评审结论：</span>
        <div className="quick-decision-buttons">
          {quickDecisions.map((dec) => {
            const isSelected = draft.review_final_decision === dec.key;
            return (
              <button
                key={dec.key}
                type="button"
                className={`quick-decision-chip${isSelected ? " is-active" : ""}`}
                onClick={() =>
                  onChange("review_final_decision", isSelected ? "" : dec.key)
                }
              >
                {isSelected ? <IconCheck size={12} /> : null}
                <span>{dec.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="inline-form review-form-grid">
        <label>
          <span className="field-label">标签强度 (重写)</span>
          <select
            value={draft.review_interest_level}
            onChange={(event) => onChange("review_interest_level", event.target.value)}
          >
            <option value="">沿用当前强度</option>
            {options.interest_levels.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">兴趣标签</span>
          <select
            value={draft.review_interest_tag}
            onChange={(event) => onChange("review_interest_tag", event.target.value)}
          >
            <option value="">沿用当前标签</option>
            {options.interest_tags.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">业务分组</span>
          <select
            value={draft.review_final_category}
            onChange={(event) => onChange("review_final_category", event.target.value)}
          >
            <option value="">沿用当前分组</option>
            {options.review_final_categories.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="review-textarea-label">
        <span className="field-label">人工分析与后续处理意见</span>
        <textarea
          rows={3}
          value={draft.reviewer_notes}
          onChange={(event) => onChange("reviewer_notes", event.target.value)}
          placeholder="在此记录重点发现、实验价值、引用思考或团队跟进意见…"
        />
      </label>

      <div className="favorite-review-actions">
        <button className="ghost-button" onClick={onCancel} disabled={disabled}>
          <IconXMark size={14} />
          <span>取消</span>
        </button>
        <button className="primary-button" onClick={onSave} disabled={disabled}>
          <IconCheck size={14} />
          <span>{disabled ? "保存中…" : "保存评审"}</span>
        </button>
      </div>
    </div>
  );
}
