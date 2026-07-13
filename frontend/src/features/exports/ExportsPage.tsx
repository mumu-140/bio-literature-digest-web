import { useState } from "react";

import { AuthUser, ExportJob, exportCustomTable } from "../../dataClient";

export function ExportsPage({ user }: { user: AuthUser }) {
  const [mappings, setMappings] = useState([
    { source: "journal", label: "期刊" },
    { source: "title_en", label: "英文标题" },
    { source: "doi", label: "DOI" },
  ]);
  const [job, setJob] = useState<ExportJob | null>(null);

  async function exportCustom() {
    setJob(await exportCustomTable(user.id, mappings));
  }

  function updateMapping(index: number, field: "source" | "label", value: string) {
    setMappings((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)));
  }

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">导出中心</p>
          <h2>自定义表格列名</h2>
        </div>
      </div>
      <div className="mapping-grid">
        {mappings.map((mapping, index) => (
          <div className="mapping-row" key={`${mapping.source}-${index}`}>
            <input value={mapping.source} onChange={(event) => updateMapping(index, "source", event.target.value)} />
            <input value={mapping.label} onChange={(event) => updateMapping(index, "label", event.target.value)} />
          </div>
        ))}
      </div>
      <div className="actions">
        <button className="ghost-button" onClick={() => setMappings((current) => [...current, { source: "", label: "" }])}>新增列</button>
        <button className="primary-button" onClick={() => void exportCustom()}>生成自定义导出</button>
      </div>
      {job ? (
        <p className="success-text">
          已生成 {job.output_name}：
          <a href={job.download_url}>下载</a>
        </p>
      ) : null}
    </section>
  );
}
