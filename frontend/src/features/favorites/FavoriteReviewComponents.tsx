import { FavoriteItem, FavoriteReviewDraft, FavoriteReviewOptions } from "../../dataClient";
import { formatReviewDecision, InterestBadge } from "../shared/WorkbenchUi";

export function FavoriteReviewSummary({ favorite }: { favorite: FavoriteItem }) {
  const effectiveInterestLevel = favorite.review_interest_level || favorite.interest_level;
  const effectiveInterestTag = favorite.review_interest_tag || favorite.interest_tag;
  const effectiveGroup = favorite.review_final_category || favorite.category;
  const effectiveDecision = formatReviewDecision(favorite.review_final_decision);

  return (
    <div className="favorite-review-summary">
      <div className="tag-list">
        <InterestBadge level={effectiveInterestLevel} />
        {effectiveInterestTag ? <span>{effectiveInterestTag}</span> : null}
        {effectiveGroup ? <span>{effectiveGroup}</span> : null}
        {effectiveDecision ? <span>{effectiveDecision}</span> : null}
      </div>
      <div className="small-copy">
        {favorite.reviewer_notes ? favorite.reviewer_notes : "尚未添加人工备注。"}
      </div>
      {favorite.review_updated_at ? (
        <div className="small-copy">最近修改：{favorite.review_updated_at}</div>
      ) : (
        <div className="small-copy">保存后会保留在当前工作台数据中，并用于后续导出。</div>
      )}
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
  return (
    <div className="favorite-review-editor">
      <div className="inline-form">
        <label>
          <span>标签强度</span>
          <select value={draft.review_interest_level} onChange={(event) => onChange("review_interest_level", event.target.value)}>
            <option value="">沿用当前</option>
            {options.interest_levels.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label>
          <span>兴趣标签</span>
          <select value={draft.review_interest_tag} onChange={(event) => onChange("review_interest_tag", event.target.value)}>
            <option value="">沿用当前</option>
            {options.interest_tags.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label>
          <span>处理结果</span>
          <select value={draft.review_final_decision} onChange={(event) => onChange("review_final_decision", event.target.value)}>
            <option value="">暂不指定</option>
            {options.review_final_decisions.map((option) => (
              <option key={option} value={option}>{formatReviewDecision(option)}</option>
            ))}
          </select>
        </label>
        <label>
          <span>分组</span>
          <select value={draft.review_final_category} onChange={(event) => onChange("review_final_category", event.target.value)}>
            <option value="">沿用当前</option>
            {options.review_final_categories.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
      </div>
      <label>
        <span>备注</span>
        <textarea
          rows={4}
          value={draft.reviewer_notes}
          onChange={(event) => onChange("reviewer_notes", event.target.value)}
          placeholder="这里写人工判断、补充标签或后续处理意见。"
        />
      </label>
      <div className="favorite-review-actions">
        <button className="ghost-button" onClick={onCancel} disabled={disabled}>取消</button>
        <button className="primary-button" onClick={onSave} disabled={disabled}>{disabled ? "保存中…" : "保存修改"}</button>
      </div>
    </div>
  );
}
