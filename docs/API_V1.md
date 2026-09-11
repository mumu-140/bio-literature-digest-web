# Bio Literature Digest REST API v1

## 定位

bio-literature-digest-web 是文献数据、报告任务和规则协作的唯一 API 边界。调用方不得读取、复制或挂载 Web 与 Producer 的 SQLite 数据库。

- Base URL: https://accept.yangsen666.cloud/api/v1
- OpenAPI: https://accept.yangsen666.cloud/docs
- 版本: v1

## 认证

服务调用使用 Bearer API Key：

    Authorization: Bearer <token>

服务端只在 api_clients 表保存加盐 SHA-256 哈希，不通过 API 返回原始密钥。

首期作用域：

| Scope | 能力 |
| --- | --- |
| literature:read | 检索和批量读取文献 |
| reports:write | 创建报告任务并上传产物 |
| rules:read | 读取规则和基线哈希 |
| rules:suggest | 提交规则建议 |
| audit:read | 读取服务账号审计事件 |

规则发布使用现有 Web 管理员会话，不接受服务 API Key。

## 通用响应

所有 /api/v1 响应包含：

- X-API-Version: v1
- X-Request-ID: UUID

调用方可以传入 X-Request-ID，否则服务端生成。

错误状态：

- 400：缺少 Idempotency-Key
- 401：缺少或无效认证
- 403：缺少作用域
- 404：资源不存在
- 409：幂等冲突或规则基线过期
- 422：请求字段校验失败

## 幂等

自动化写接口必须传：

    Idempotency-Key: <stable-key>

幂等键按 API 客户端、HTTP 方法和路径隔离。相同键与相同请求体重放时返回已保存结果和 HTTP 200；相同键对应不同请求体时返回 409。

## 版本信息

GET /

返回 api_version 和 service。

## 文献接口

### GET /literature

参数：

| 参数 | 说明 |
| --- | --- |
| q | 标题、摘要、中文摘要、期刊和 DOI 搜索 |
| category | 精确类别 |
| published_from | 起始日期，包含 |
| published_to | 结束日期，包含 |
| page | 页码，默认 1 |
| page_size | 每页数量，默认 50，最大 200 |

示例：

    curl -H "Authorization: Bearer $TOKEN"       "$BASE/literature?q=CRISPR&published_from=2026-01-01&page_size=20"

返回 total、page、page_size 和 items。文献字段包含 id、key、DOI、双语标题、作者、期刊、发布日期、类别、兴趣评分、摘要、链接、标签和更新时间。

### POST /literature/batch

按 canonical key 批量读取，最多 200 条，并保持请求顺序。

请求：

    {
      "keys": ["doi:10.1000/a", "doi:10.1000/b"]
    }

## 报告任务

报告任务只管理生命周期和产物，不在 Web 进程中运行大模型。后续 DeerFlow 创建任务、生成报告并回传产物。

### POST /report-tasks

需要 reports:write 和 Idempotency-Key。

请求：

    {
      "report_type": "weekly",
      "parameters": {
        "period": "2026-W27",
        "topic": "plant genomics"
      }
    }

report_type 只允许 weekly 或 monthly。初始状态为 queued。

### GET /report-tasks/{task_id}

返回任务状态及全部产物。

### POST /report-tasks/{task_id}/artifacts

请求：

    {
      "format": "markdown",
      "content": "# Weekly report",
      "metadata": {
        "paper_count": 25
      }
    }

format 允许 markdown 或 json，单个产物最大 2 MB。上传成功后任务状态变为 completed。

## 规则接口

### GET /rules

返回：

- path_name：仅文件名，不暴露服务器路径
- content：完整 YAML
- content_sha256：提交建议时使用的基线哈希

### POST /rule-suggestions

需要 rules:suggest 和 Idempotency-Key。

请求：

    {
      "baseline_sha256": "<sha256>",
      "proposed_content": "<完整 YAML>",
      "summary": "基于报告证据的修改说明"
    }

建议创建后为 pending。服务账号不能直接发布。

### POST /rule-suggestions/{suggestion_id}/publish

只接受 Web 管理员会话。发布过程：

1. 校验当前规则哈希与 baseline_sha256 一致。
2. 校验候选内容是 YAML mapping。
3. 在 Producer 的规则备份目录保存当前文件快照。
4. 通过同目录 staged 文件原子替换目标规则文件。
5. 写入 API 审计事件。

基线冲突返回 409，原文件保持不变。

## 审计接口

### GET /audit-events

需要 audit:read。默认返回 100 条，最大 500 条。

字段包括 request_id、action、entity_type、entity_key、outcome、detail 和 created_at。审计内容不记录 API Key 或 Authorization Header。

## 后续 DeerFlow 接入

建议环境变量：

    BIO_LITERATURE_API_BASE_URL=https://accept.yangsen666.cloud/api/v1
    BIO_LITERATURE_API_TOKEN=<service-token>

DeerFlow Skill 必须遵守：

1. 只通过 REST API 检索和批量读取文献。
2. 报告任务及产物上传使用稳定幂等键。
3. 提交规则建议前重新读取基线哈希。
4. 提交建议后停止，由管理员审核发布。
5. 不 SSH 到 vps219，不访问数据库和规则文件路径。

MCP 首期不启用。后续 MCP 只能作为 REST API 的薄适配层，不得建立第二条数据路径。
