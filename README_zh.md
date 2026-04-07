# Bio Literature Digest Web 中文说明

这是 `bio-literature-digest` 的网页端项目。  
它不负责抓取和翻译文献，只负责导入生产端生成的 `digest.csv`、`digest.html`、`digest.xlsx`、`run_metadata.json`，并提供账户、收藏、统计、导出和审查汇总能力。

## 快速开始

先安装依赖并复制本地配置模板。Cloudflare Tunnel 是可选的，如果你只是本机使用或局域网调试，可以先不配。

### 1. 后端依赖

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 2. 前端依赖

```bash
cd frontend
npm install
```

### 3. 准备配置

```bash
mkdir -p bio-literature-config/web
cp bio-literature-config/web/backend.env.local.example \
  bio-literature-config/web/backend.env.local
cp bio-literature-config/web/deploy.env.local.example \
  bio-literature-config/web/deploy.env.local
```

至少检查这些字段：

- `DATABASE_URL`
- `SESSION_SECRET`
- `INITIAL_ADMIN_EMAIL`
- `INITIAL_ADMIN_PASSWORD`
- `WEB_BASE_URL`

### 4. 本地启动

不走 Tunnel 时，直接分别启动后端和前端：

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8602
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 8601
```

然后访问：

- 前端：`http://127.0.0.1:8601`
- 后端健康检查：`http://127.0.0.1:8602/healthz`

如果你要用与生产更接近的本机进程方式：

```bash
./start-amt-web.sh
```

默认端口是：

- 前端：`127.0.0.1:8601`
- 后端：`127.0.0.1:8602`

项目启动脚本会拒绝 `8000-8200` 端口段。

## Tunnel 可选

Cloudflare Tunnel 不是必需项。

- 只想本地开发：不用配置 Tunnel
- 需要公网域名访问：再配置 Tunnel

Tunnel 配置模板在：

- `deploy/cloudflare-tunnel/config.yml.example`

真实本地配置位置是：

- `bio-literature-config/web/cloudflare-tunnel/config.yml`

启动命令：

```bash
./start-amt-tunnel.sh
```

公网域名以你自己的配置为准，例如：

- `https://app.example.com`

## 目录结构

- `backend/`: FastAPI、数据库模型、导入 CLI、测试
- `frontend/`: React + Vite 前端
- `deploy/`: 部署模板和 Tunnel 示例
- `docs/`: 架构和部署说明
- `bio-literature-config/`: 本地敏感配置、Tunnel 凭据、访问记录、审查表输出

其中：

- `bio-literature-config/web/backend.env.local` 是后端本地开发配置
- `bio-literature-config/web/deploy.env.local` 是本机部署配置
- `bio-literature-config/web/access-traces/` 是访问记录目录
- `bio-literature-config/web/review-tables/` 是收藏修改汇总后的审查表目录

## 与 `bio-literature-digest` 的联动

两者是“生产端 + 消费端”关系，不要混用职责。

### `bio-literature-digest` 负责

- 抓取文献
- 分类、翻译、整理
- 生成每日产物
- 发邮件

核心产物包括：

- `digest.csv`
- `digest.xlsx`
- `digest.html`
- `run_metadata.json`

### `bio-literature-digest-web` 负责

- 导入每日产物到数据库
- 提供网页账户体系
- 展示今日文献与历史文献
- 管理收藏、推送、统计、导出
- 输出审查汇总表

### 自动联动链路

1. `bio-literature-digest/scripts/run_digest.py` 生成每日产物  
2. `bio-literature-digest/scripts/run_production_digest.py` 归档产物  
3. 同一个生产脚本会调用 `bio-literature-digest-web/backend/import_digest_run.py` 导入 web 数据库  
4. `bio-literature-digest/scripts/send_email.py` 会读取 web 的 `SESSION_SECRET`，给每个收件人生成免密专属登录链接  
5. 用户从邮件进入网页端后，可继续收藏、修改标签和做个人操作

这意味着：

- 邮件内容和网页数据应来自同一批产物
- 如果生产脚本正常执行，邮件和网页日期应保持同步

## 常用命令

### 导入某一天归档

```bash
cd backend
. .venv/bin/activate
python import_digest_run.py --run-dir /path/to/daily-run
```

### 同步邮件收件人为 web 用户

```bash
cd backend
. .venv/bin/activate
python sync_email_accounts.py
```

### 导出收藏审查表

```bash
cd backend
. .venv/bin/activate
python export_favorite_review_tables.py
```

## GitHub 提交建议

真实运行项目建议保留为本地工作目录。

脱敏后的可公开副本建议单独复制后再上传。

公开副本已经去掉这些内容：

- 本地 `env` 配置
- Cloudflare 凭据 JSON
- 数据库文件
- `.venv`
- `node_modules`
- `dist`
- `.runtime`
- 访问记录
- 审查导出结果
