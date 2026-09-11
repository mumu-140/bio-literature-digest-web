# Web Agent Guide — 消费端专用守则与入口

> **适用范围**：本文件专门适用于前端与 Web 工作台 `bio-literature-digest-web`。
> 单独在本工程工作时，请首先阅读本手册；全局架构、数据所有权及运维规范请参见父级总控文档：
> - 🌐 **总控全局地图**：[`../AGENTS.md`](../AGENTS.md)
> - 📐 **系统架构与数据所有权**：[`../ARCHITECTURE.md`](../ARCHITECTURE.md)
> - ⚡ **性能与全链路缓存规范**：[`../docs/operations/PERFORMANCE.md`](../docs/operations/PERFORMANCE.md)
> - 🛡️ **安全与数据保护守则**：[`../docs/operations/SAFETY.md`](../docs/operations/SAFETY.md)
> - 🚀 **vps219 验证与部署手册**：[`../docs/operations/DEPLOYMENT.md`](../docs/operations/DEPLOYMENT.md)

---

## 一、 核心定位与职责

本工程是整个系统的 **Consumer（下游消费端）与 User Workspace（用户学术工作台）**。
核心职责涵盖：
1. **只读增量镜像同步**：从上游 Producer 只读导入日度归档与文献元数据；
2. **毫秒级学术检索**：基于 SQLite WAL + FTS5 构建本地全文检索引擎；
3. **沉浸式学术阅读器**：提供文献分类过滤、旗舰期刊高亮、DOI 一键复制、Zotero 导出与引用；
4. **用户工作台状态管理**：独立维护用户的收藏（Favorites）、已读标记（Read State）、人工批注（Annotations）与推送订阅；
5. **非破坏性人工修订**：提供对机翻标题与摘要的人工修正能力（作为前端覆盖层展示，不回写 Producer 原值）；
6. **生态集成**：支持多选批量推送到外部知识库，以及接入 DeerFlow SSO 权限认证。

---

## 二、 日常维护不变量 (Invariants)

任何日常缺陷修复、功能优化或样式调整，必须严格捍卫以下不变量：

1. **【全局第一红线】绝对禁止在本地构建与安装**：
   - 本机（Mac）绝不运行 `npm install`、`npm run build`、`npx tsc`、`vite build` 等依赖安装与编译命令；
   - 本地仅负责代码编辑与 Git 提交；所有测试、类型检查、构建打包与部署在远端 `vps219` 执行。
2. **对 Producer 生产端严格只读**：
   - 严禁向 Producer 数据库发起 `INSERT`、`UPDATE`、`DELETE` 或反向同步调用；
   - 生产端目录（`../bio-literature-digest/`）在 Web 端看来完全为**只读数据源**。
3. **Imported 镜像数据与 Web-owned 用户数据严格物理隔离**：
   - 同步流水线（`sync_archives.py`）仅允许刷新只读镜像表；
   - 同步动作**绝对不得冲刷、覆盖或重置任何 Web 用户的收藏、已读状态、人工批注与偏好设置**。
4. **人工修订覆盖层模型 (Display Overlay)**：
   - 遵循 `Producer 原值 → Web 镜像 + Web 人工修订 → 前端展示值` 原则；
   - 用户修订以独立表存储，仅作为前端展示层的补丁，绝不篡改原数据源。
5. **全链路性能与缓存标准**：
   - 恪守 [`PERFORMANCE.md`](../docs/operations/PERFORMANCE.md) 规约：必须走 `digestCacheService`（已读历史日期 0ms 秒开）与 `useDigestPrefetch`（空闲预取）；
   - 收藏状态变化必须原子同步更新内存缓存；
   - 静态资源配置永久 CDN 缓存；业务 API 响应配置严格为 `Cache-Control: private`，绝不外泄导致多用户串号。
6. **数据与索引完整性**：
   - 保持 FTS5 全文索引与文献表的数据强一致性；
   - **绝对禁止将“重建数据库”或“清空表”作为常规 Bug 修复手段**。

---

## 三、 修改前检查清单 (Pre-flight Checklist)

在对前端或后端代码发起修改前，必须自查：

- [ ] **数据所有权判断**：本次改动涉及的数据属于只读 Imported 镜像，还是 Web-owned 用户状态？
- [ ] **同步幂等性**：若修改同步逻辑，确认重复同步同一批次数据不会新增重复记录，且能安全重试；
- [ ] **缓存维度自审**：若修改数据获取逻辑，确认 Cache Key 是否包含完整维度，是否会导致缓存击穿或多组件重复并发？
- [ ] **数据库变更预案**：涉及 SQLite 字段变动前，遵循 [`SAFETY.md`](../docs/operations/SAFETY.md) 先创建带时间戳的快照并原地验证可读性。

---

## 四、 提交流程与远端 vps219 门禁

### 1. 本地精细提交与推送
```bash
git status --short
git add <改动文件>
git commit -m "feat(web): <清晰的提交信息>"
# 注意：Web 当前核心生产分支为 codex/deerflow-library-sso
git push origin codex/deerflow-library-sso
```

### 2. 远端 vps219 门禁校验与平滑重启
SSH 登录生产主机，执行三道质量门禁验证：
```bash
ssh vps219
cd /root/software/bio-literature-digest-web
export PATH=/root/software/node-v24.18.0-linux-x64/bin:$PATH

# 快进拉取
git pull --ff-only origin codex/deerflow-library-sso

# 质量门禁（必须三项全绿通过）
npm test
npx tsc --noEmit
npm run build

# 门禁通过后平滑重启
./start.sh
```

### 3. 线上健康双 200 验证
```bash
# 1. 公网反代入口
curl -fsS -o /dev/null -w '%{http_code}\n' https://accept.yangsen666.cloud
# 2. 内部环回接口
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8602/healthz
```

### 4. VPS 知识库台账同步
服务部署后，若涉及版本或配置变更，同步更新 [`/Users/mumu/workspace/VPS/servers/vps219.md`](file:///Users/mumu/workspace/VPS/servers/vps219.md) 与 `inventory.json`。
