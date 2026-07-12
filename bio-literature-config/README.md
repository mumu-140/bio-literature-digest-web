# Bio Literature Config

本目录是 `bio-literature-digest-web` 的本地实例目录，只放真实配置和运行数据。

## 目录边界

- `env/producer/`: producer 读取的本地配置，例如用户配置、邮件配置、翻译配置
- `env/web/backend.env.local`: 后端本地开发配置
- `env/web/deploy.env.local`: `start.sh` 使用的本机部署配置
- `data/web/bio_digest_web.db`: 网页端本地运行数据库
- `data/web/access-traces/`: 访问记录
- `data/web/review-tables/`: 人工备注导出结果
- `runtime/web/`: pid 与日志
- `tunnel/web/`: 真实 Cloudflare Tunnel 配置与凭据

## 约束

- 真实密码、邮箱、SMTP、API key、Tunnel 凭据、访问记录和导出文件都放这里
- 公共仓库不要提交这些真实文件
- 只提交 `*.example` 模板

## 推荐本地文件

- `env/producer/users.local.yaml`
- `env/producer/email_config.local.yaml`
- `env/producer/email_style.local.yaml`
- `env/producer/translation_google_basic_v2.local.yaml`
- `env/producer/translation_tencent_tmt.local.yaml`
- `env/web/backend.env.local`
- `env/web/deploy.env.local`
- `tunnel/web/config.yml`
- `tunnel/web/*.json`

## 说明

- `env/web/backend.env.local` 用于直接运行后端
- `env/web/deploy.env.local` 供 `start.sh` 使用，也控制是否自动拉起 Tunnel
- `data/web/` 与 `runtime/web/` 都是运行期目录，不应该进入 GitHub
- producer SQLite / archives / 用户配置是只读输入源，不属于 web 端运行数据面
