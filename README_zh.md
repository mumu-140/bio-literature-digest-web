# Bio Literature Digest Web 中文说明

这是 `bio-literature-digest` 的网页端项目。  
它不负责抓取和翻译文献；生产端会把文献同步到共享数据库，web 端直接读取共享库，并把收藏、导出等文献动作写回共享库。

当前认证模式为内部免密：仅需邮箱即可登录，不存在的邮箱会自动创建为 `member` 账户。

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
mkdir -p bio-literature-config/env/web
cp bio-literature-config/env/web/backend.env.local.example \
  bio-literature-config/env/web/backend.env.local
cp bio-literature-config/env/web/deploy.env.local.example \
  bio-literature-config/env/web/deploy.env.local
```

至少检查这些字段：

- `DATABASE_URL`
- `SESSION_SECRET`
- `INITIAL_ADMIN_EMAIL`
- `WEB_BASE_URL`

### 4. 本地启动

不走 Tunnel 时，直接分别启动后端和前端：

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 18002
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 18001
```

然后访问：

- 前端：`http://127.0.0.1:18001`
- 后端健康检查：`http://127.0.0.1:18002/healthz`

如果你要用与生产更接近的本机进程方式：

```bash
./start.sh
```

进程会使用 `bio-literature-config/env/web/deploy.env.local` 中的配置值，例如：

- 前端：`FRONTEND_HOST:FRONTEND_PORT`
- 后端：`BACKEND_HOST:BACKEND_PORT`

本地启动脚本会直接起 Vite dev server，并把 `/api` 代理到后端，所以本机访问不会再出现“已登录但没有数据”。

如果设置了 `RESERVED_PORT_RANGE`，启动脚本会拒绝落在该保留区间内的端口。
如果 `ENABLE_TUNNEL=true`，同一个启动脚本会一并拉起 Cloudflare Tunnel；默认值就是开启。

## Tunnel 可选

Cloudflare Tunnel 不是必需项。

- 只想本地开发：不用配置 Tunnel
- 需要公网域名访问：再配置 Tunnel

Tunnel 配置模板在：

- `deploy/cloudflare-tunnel/config.yml.example`

真实本地配置位置是：

- `bio-literature-config/tunnel/web/config.yml`

公网域名以你自己的配置为准，例如：

- `https://app.example.com`

## 目录结构

- `backend/`: FastAPI、数据库模型、测试
- `frontend/`: React + Vite 前端
- `deploy/`: 部署模板和 Tunnel 示例
- `docs/`: 架构和部署说明
- `bio-literature-config/`: 实例根目录
- `bio-literature-config/env/`: 本地真实配置与环境文件
- `bio-literature-config/data/`: 数据库、访问记录、审查表等运行数据
- `bio-literature-config/runtime/`: pid 与日志
- `bio-literature-config/tunnel/`: Tunnel 配置与凭据

其中：

- `bio-literature-config/env/web/backend.env.local` 是后端本地开发配置
- `bio-literature-config/env/web/deploy.env.local` 是本机部署配置
- `bio-literature-config/data/web/access-traces/` 是访问记录目录
- `bio-literature-config/data/web/review-tables/` 是收藏修改汇总后的审查表目录
- `bio-literature-config/data/web/bio_digest_web.db` 是网页主数据库

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

- 从共享数据库读取文献数据
- 提供网页账户体系
- 展示今日文献与历史文献
- 管理收藏、推送、统计、导出（文献相关动作写入共享数据库）
- 输出审查汇总表

### 自动联动链路

1. `bio-literature-digest/scripts/run_digest.py` 生成每日产物  
2. `bio-literature-digest/scripts/run_production_digest.py` 归档产物  
3. `run_digest.py` 在导出前执行共享数据库同步步骤  
4. 两端默认共享路径：`skills/bio-literature-digest/bio-literature-config/data/shared/bio_literature_shared.db`  
5. web API 从共享库读写文献数据，不再依赖 web 端扫描归档  
6. 用户从邮件进入网页端后，可继续收藏、修改标签和做个人操作

这意味着：

- 邮件内容和网页数据应来自同一批产物
- 如果生产脚本正常执行，邮件和网页日期应保持同步

## 常用命令

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

## Harness

统一验证入口：

```bash
python3 tools/run_harness.py
```

它会执行：

- `python3 tools/resolve_instance_path.py`
- `backend/.venv/bin/python -m unittest discover -s app/tests`
- `frontend/` 下的 `npm run build`
- `python3 tools/audit_open_source.py`

## Linux DO 声明

Linux DO 声明：本项目开源版本以 Linux 运维为默认基线（DO = Deployment Operator）。README 与示例配置中的域名、路径、账号均为占位示例，部署前必须替换为真实值。

## Harness

统一验证入口：

```bash
python3 tools/run_harness.py
```

它会执行：

- `python3 tools/resolve_instance_path.py`
- `backend/.venv/bin/python -m unittest discover -s app/tests`
- `frontend/` 下的 `npm run build`
- `python3 tools/audit_open_source.py`

---

## Acknowledgments
Special thanks to the **[Linux.do](https://linux.do/)** community for your support and feedback.
