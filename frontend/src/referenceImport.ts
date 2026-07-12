export type ReferenceImportItem = {
  id: number;
  doi: string;
  journal: string;
  publish_date: string;
  title_en: string;
  title_zh: string;
  article_url: string;
  authors: string[];
  abstract?: string;
  summary_zh?: string;
  tags?: string[];
};

export function importIntoZotero(items: ReferenceImportItem[]) {
  if (!items.length) return;
  downloadReferenceFile(
    `zotero-import-${Date.now()}.ris`,
    buildRis(items),
    "application/x-research-info-systems;charset=utf-8",
  );
}

export function buildRis(items: ReferenceImportItem[]) {
  return items.map(buildRisRecord).join("\r\n");
}

function buildRisRecord(item: ReferenceImportItem) {
  const lines = ["TY  - JOUR", `TI  - ${risValue(item.title_en || item.title_zh)}`];
  if (item.title_zh && item.title_zh !== item.title_en) lines.push(`N1  - 中文标题：${risValue(item.title_zh)}`);
  for (const author of item.authors || []) {
    if (author.trim()) lines.push(`AU  - ${risValue(author)}`);
  }
  if (item.journal) lines.push(`T2  - ${risValue(item.journal)}`);
  if (item.publish_date) lines.push(`DA  - ${risValue(item.publish_date.slice(0, 10))}`);
  if (item.doi) lines.push(`DO  - ${risValue(item.doi)}`);
  if (item.article_url) lines.push(`UR  - ${risValue(item.article_url)}`);
  const abstract = item.abstract || item.summary_zh || "";
  if (abstract) lines.push(`AB  - ${risValue(abstract)}`);
  for (const tag of item.tags || []) {
    if (tag.trim()) lines.push(`KW  - ${risValue(tag)}`);
  }
  lines.push("ER  - ", "");
  return lines.join("\r\n");
}

function risValue(value: string) {
  return String(value || "").replace(/[\r\n]+/g, " ").trim();
}

function downloadReferenceFile(filename: string, content: string, type: string) {
  const blob = new Blob(["\ufeff", content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
