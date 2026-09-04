# Infrastructure

基础设施目录。

- `caddy/Caddyfile`：本地 HTTP 反向代理配置。
- `caddy/Caddyfile.production`：生产 HTTPS 反向代理配置。

本地默认使用 HTTP，生产环境设置：

```dotenv
APP_ENV=production
APP_DOMAIN=news.example.com
CADDYFILE_PATH=./infra/caddy/Caddyfile.production
CADDY_ACME_EMAIL=admin@example.com
```

更完整的部署、备份和运维说明见：

- [部署文档](../docs/deployment.md)
- [运维手册](../docs/operations.md)
