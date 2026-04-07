# Bio Literature Config

本目录是 `bio-literature-digest-web` 的实例目录，专门放可变路径、真实配置和运行数据。

- `paths.env`: 实例目录布局定义，脚本优先从这里解析路径
- `env/producer/`: 供 `bio-literature-digest` 读取的邮箱、翻译和样式本地配置
- `env/web/backend.env.local`: web 后端本地开发配置
- `env/web/deploy.env.local`: web 本机进程和 Tunnel 部署配置
- `data/web/bio_digest_web.db`: 网页主数据库
- `data/web/access-traces/`: 用户进入站点后的访问追踪文件
- `data/web/review-tables/`: 收藏修改延迟汇总后的审查表输出
- `runtime/web/`: 本地 pid 与日志
- `tunnel/web/`: Cloudflare Tunnel 本地配置与凭据

真实密码、邮箱地址、SMTP、API key、Tunnel 凭据、访问记录和审查导出都放这里。
公开仓库不要提交这些真实文件，只提交 `*.example*` 模板。

当前推荐的本地文件：

- `env/producer/.env.local`
- `env/producer/email_config.local.yaml`
- `env/producer/email_style.local.yaml`
- `env/producer/translation_google_basic_v2.local.yaml`
- `env/producer/translation_tencent_tmt.local.yaml`
- `env/web/backend.env.local`
- `env/web/deploy.env.local`
- `tunnel/web/config.yml`
- `tunnel/web/*.json`

说明：

- `paths.env` 是唯一需要维护的实例路径入口，后续即使移动目录，也只改这一处
- `env/web/backend.env.local` 对应直接运行后端的本地开发配置，默认前端是 `http://127.0.0.1:8601`
- `env/web/deploy.env.local` 供 `start-amt-web.sh` 和邮件链接生成使用
- `data/web/` 与 `runtime/web/` 都是运行期目录，不应该进入 GitHub
