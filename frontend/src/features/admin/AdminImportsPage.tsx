import { useEffect, useState } from "react";

import {
  checkImportRuns,
  fetchImportRuns,
  importRun,
  ImportResult,
  ImportRun,
  reimportRun,
} from "../../dataClient";
import { EmptyState, MetricTile } from "../shared/WorkbenchUi";

function formatImportSummary(results: ImportResult[], prefix: string) {
  const imported = results.reduce((sum, result) => sum + result.imported_memberships, 0);
  return results.length
    ? `${prefix}：${results.length} 个运行，${imported} 条成员记录。`
    : `${prefix}：没有需要处理的运行。`;
}

export function AdminImportsPage() {
  const [runs, setRuns] = useState<ImportRun[]>([]);
  const [busyRunId, setBusyRunId] = useState("");
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    setRuns(await fetchImportRuns());
  }

  useEffect(() => {
    void load();
  }, []);

  async function runCheck() {
    setChecking(true);
    setMessage("");
    try {
      const results = await checkImportRuns();
      setMessage(formatImportSummary(results, "已完成最新运行检查"));
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "检查失败");
    } finally {
      setChecking(false);
    }
  }

  async function handleImport(runId: string, force: boolean) {
    setBusyRunId(runId);
    setMessage("");
    try {
      const result = force ? await reimportRun(runId) : await importRun(runId);
      setMessage(formatImportSummary([result], force ? "已执行重导入" : "已执行导入"));
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导入失败");
    } finally {
      setBusyRunId("");
    }
  }

  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <p className="eyebrow">Producer Import</p>
            <h2>导入与重导入</h2>
          </div>
          <div className="actions">
            <button className="ghost-button" onClick={() => void load()}>刷新列表</button>
            <button className="primary-button" onClick={() => void runCheck()} disabled={checking}>
              {checking ? "检查中…" : "检查最新运行"}
            </button>
          </div>
        </div>
        <div className="stats-strip">
          <MetricTile label="可导入日期" value={String(runs.length)} />
          <MetricTile label="已对齐" value={String(runs.filter((run) => run.is_current).length)} />
          <MetricTile label="待导入" value={String(runs.filter((run) => !run.is_current).length)} />
        </div>
        {message ? <div className="notice-banner is-success">{message}</div> : null}
        <div className="table-shell">
          {runs.length === 0 ? <EmptyState title="当前没有可导入运行" description="请确认 producer SQLite 已生成可用运行记录。" /> : null}
          <div className="desktop-only">
            <table>
              <thead>
                <tr>
                  <th>日期</th>
                  <th>运行</th>
                  <th>记录数</th>
                  <th>归档校验</th>
                  <th>本地状态</th>
                  <th>动作</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={`${run.digest_date}-${run.run_id}`}>
                    <td>{run.digest_date}</td>
                    <td>{run.run_id}<div className="small-copy">{run.updated_at_utc}</div></td>
                    <td>{run.record_count}</td>
                    <td>{run.validation_status}</td>
                    <td>{run.is_current ? "已同步" : `当前 ${run.current_local_run_id || "未导入"}`}</td>
                    <td>
                      <button className="table-link" onClick={() => void handleImport(run.run_id, false)} disabled={busyRunId === run.run_id}>
                        {busyRunId === run.run_id ? "处理中…" : "导入"}
                      </button>
                      <button className="table-link" onClick={() => void handleImport(run.run_id, true)} disabled={busyRunId === run.run_id}>
                        重导入
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-only">
            <div className="mobile-stack">
              {runs.map((run) => (
                <article className="mobile-card" key={`${run.digest_date}-${run.run_id}`}>
                  <div className="mobile-card-head">
                    <div>
                      <p className="eyebrow">{run.digest_date}</p>
                      <strong>{run.run_id}</strong>
                    </div>
                    <span className={`status-pill ${run.is_current ? "is-live" : "is-idle"}`}>{run.is_current ? "已同步" : "待处理"}</span>
                  </div>
                  <p className="small-copy">记录数：{run.record_count}</p>
                  <p className="small-copy">归档校验：{run.validation_status}</p>
                  <p className="small-copy">本地运行：{run.current_local_run_id || "未导入"}</p>
                  <div className="mobile-card-actions">
                    <button className="table-link" onClick={() => void handleImport(run.run_id, false)} disabled={busyRunId === run.run_id}>导入</button>
                    <button className="table-link" onClick={() => void handleImport(run.run_id, true)} disabled={busyRunId === run.run_id}>重导入</button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
