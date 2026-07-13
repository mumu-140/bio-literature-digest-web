import { FavoriteItem, PaperItem } from "../../dataClient";
import { formatReviewDecision } from "./WorkbenchUi";

export function exportSelectedPapers(items: PaperItem[], kind: "metadata" | "doi-list") {
  if (kind === "doi-list") {
    const content = Array.from(new Set(items.map((item) => item.doi).filter(Boolean))).join("\n");
    downloadFile(`selected-papers-doi-${Date.now()}.txt`, `${content}${content ? "\n" : ""}`, "text/plain;charset=utf-8");
    return;
  }

  const columns = [
    ["digest_date", "digest_date"],
    ["id", "id"],
    ["canonical_key", "canonical_key"],
    ["doi", "doi"],
    ["journal", "journal"],
    ["publish_date", "publish_date"],
    ["category", "category"],
    ["interest_level", "interest_level"],
    ["interest_tag", "interest_tag"],
    ["title_en", "title_en"],
    ["title_zh", "title_zh"],
    ["summary_zh", "summary_zh"],
    ["abstract", "abstract"],
    ["article_url", "article_url"],
    ["tags", "tags"],
  ] as const;

  const rows = items.map((item) =>
    columns.map(([key]) => {
      if (key === "tags") {
        return item.tags.join(" | ");
      }
      return String(item[key as keyof PaperItem] ?? "");
    }),
  );
  downloadFile(`selected-papers-metadata-${Date.now()}.csv`, buildCsv(columns.map(([, label]) => label), rows), "text/csv;charset=utf-8");
}

export function exportSelectedFavorites(items: FavoriteItem[], kind: "metadata" | "doi-list") {
  if (kind === "doi-list") {
    const content = Array.from(new Set(items.map((item) => item.doi).filter(Boolean))).join("\n");
    downloadFile(`selected-favorites-doi-${Date.now()}.txt`, `${content}${content ? "\n" : ""}`, "text/plain;charset=utf-8");
    return;
  }

  const headers = [
    "favorite_id",
    "paper_id",
    "canonical_key",
    "digest_date",
    "favorited_at",
    "doi",
    "journal",
    "publish_date",
    "category",
    "interest_level",
    "interest_tag",
    "manual_interest_level",
    "manual_interest_tag",
    "final_status",
    "manual_group",
    "manual_notes",
    "manual_updated_at",
    "title_en",
    "title_zh",
    "article_url",
  ];
  const rows = items.map((item) => [
    item.id,
    item.paper_id,
    item.canonical_key,
    item.digest_date || "",
    item.favorited_at,
    item.doi,
    item.journal,
    item.publish_date,
    item.category,
    item.interest_level,
    item.interest_tag,
    item.review_interest_level,
    item.review_interest_tag,
    formatReviewDecision(item.review_final_decision),
    item.review_final_category,
    item.reviewer_notes,
    item.review_updated_at || "",
    item.title_en,
    item.title_zh,
    item.article_url,
  ]);
  downloadFile(`selected-favorites-metadata-${Date.now()}.csv`, buildCsv(headers, rows), "text/csv;charset=utf-8");
}

function buildCsv(headers: string[], rows: Array<Array<string | number>>) {
  return [headers, ...rows]
    .map((row) =>
      row
        .map((value) => `"${String(value ?? "").replace(/"/g, "\"\"")}"`)
        .join(","),
    )
    .join("\n");
}

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
