# Bio Literature Config

本目录是 `bio-literature-digest-web` 的本地敏感配置和运行期数据目录。

- `producer/`: 供 `bio-literature-digest` 读取的邮箱、翻译和样式模板示例
- `web/backend.env.local`: web 后端本地开发配置
- `web/deploy.env.local`: web 本机进程和 Tunnel 部署配置
- `web/cloudflare-tunnel/`: Cloudflare Tunnel 本地配置与凭据
- `web/access-traces/`: 用户进入站点后的访问追踪文件
- `web/review-tables/`: 收藏修改延迟汇总后的审查表输出

真实密码、邮箱地址、SMTP、API key、Tunnel 凭据、访问记录和审查导出都放这里。
公开仓库不要提交这些真实文件，只提交 `*.example*` 模板。

当前推荐的本地文件：

- `producer/.env.local`
- `producer/email_config.local.yaml`
- `producer/email_style.local.yaml`
- `producer/translation_google_basic_v2.local.yaml`
- `producer/translation_tencent_tmt.local.yaml`
- `web/backend.env.local`
- `web/deploy.env.local`
- `web/cloudflare-tunnel/config.yml`
- `web/cloudflare-tunnel/*.json`

说明：

- `web/backend.env.local` 对应直接运行后端的本地开发配置，默认前端是 `http://127.0.0.1:8601`
- `web/deploy.env.local` 供 `start-amt-web.sh` 和邮件链接生成使用
- `web/access-traces/` 与 `web/review-tables/` 都是运行期目录，不应该进入 GitHub
