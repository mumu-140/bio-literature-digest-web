# Bio Literature Config

本目录是 `bio-literature-digest-web` 的实例目录，专门放真实配置和运行数据。

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

- `env/web/backend.env.local` 对应直接运行后端的本地开发配置，前端来源由 `FRONTEND_ORIGIN` 指定
- `env/web/backend.env.local` 里的 `PRODUCER_ROOT` 可显式指定只读归档来源
- `env/web/deploy.env.local` 供 `start.sh` 和邮件链接生成使用，也控制是否自动拉起补采集 worker 与 tunnel
- `data/web/` 与 `runtime/web/` 都是运行期目录，不应该进入 GitHub
- 旧副本里如果还有 `paths.env`，现在已经只是兼容遗留物，脚本不再依赖它
