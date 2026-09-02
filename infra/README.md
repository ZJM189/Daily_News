# Infrastructure

基础设施目录。

- `caddy/`：本地和单台云服务器反向代理配置。

生产环境需要把 `APP_DOMAIN` 设置为真实域名，并启用 Caddy 自动 HTTPS。当前 Caddyfile 默认关闭自动 HTTPS，方便本地开发。
