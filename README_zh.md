# Bio Literature Digest Web 中文说明

这是 `bio-literature-digest` 的网页消费端 / 工作台。

- `bio-literature-digest` 仍然是唯一的文献内容生产端。
- producer SQLite 和 producer archives 只是只读输入源。
- 网页端 UI 只读取本项目自己的本地运行数据面。
- 当前产品面聚焦于文献阅读、收藏、推送、导出，以及低频人工备注。

不再把 analytics 作为支持中的产品功能。

## 目录

- `backend/`: FastAPI、导入器、本地运行数据模型、测试
- `frontend/`: React + Vite 前端
- `deploy/cloudflare-tunnel/`: 唯一的 Tunnel 模板目录
- `docs/`: 架构与部署说明
- `bio-literature-config/`: 本地实例目录
- `bio-literature-config/env/`: 真实 env 与 producer 本地配置
- `bio-literature-config/data/`: 本地数据库、访问记录、审查表导出
- `bio-literature-config/runtime/`: pid 与日志
- `bio-literature-config/tunnel/`: 真实 Tunnel 配置与凭据

## 当前支持的运行模型

1. producer 完成一次运行并写入 producer SQLite
2. web 在启动时检查最新可用运行并导入本地数据库
3. 管理员也可以手动检查、导入、重导入
4. archives / 导出产物只用于校验或兜底，不阻塞基于 SQLite 的导入
5. 前端读取的始终是 web 本地数据库，不直接读 producer DB

## 快速开始

后端：

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 18002
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 18001
```

本机托管流程：

```bash
./start.sh
./stop.sh
```

`start.sh` 会读取 `bio-literature-config/env/web/deploy.env.local`，拉起后端、前端 dev server，以及可选的 Cloudflare Tunnel。

## 与 producer 的边界

网页端只依赖这些只读输入：

- producer SQLite
- producer archives
- producer 用户配置
- producer 规则文件与导出模板

网页端不会重写 producer 的抓取、分类、翻译、归档流程。

## 人工备注导出

人工备注导出只读取网页端本地运行数据面，再调用 producer 导出格式器输出 `daily_review_schema`。

命名规则：

- 有 producer UID 时：`<uid>-data.xlsx`
- 没有 UID 时：`webuser-<id>-data.xlsx`
- 聚合表：`aggregate-data.xlsx`

保留同 stem 的 `.csv` 和 `.html` sidecar。

命令：

```bash
cd backend
. .venv/bin/activate
python export_favorite_review_tables.py
```

## Tunnel

只保留一个 canonical 模板：

```bash
cp deploy/cloudflare-tunnel/config.yml.example \
  bio-literature-config/tunnel/web/config.yml
```

真实的 `bio-literature-config/tunnel/web/config.yml` 和凭据 JSON 都不要提交。

## 验证

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
