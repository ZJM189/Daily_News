# 运维手册

## 服务组成

- `postgres`：主数据库，保存用户、来源、条目、专题、简报、任务记录、关注偏好。
- `redis`：任务状态和后续异步队列基础设施。
- `api`：FastAPI HTTP API。
- `worker`：后台任务执行入口。
- `scheduler`：定时调度入口，默认每天北京时间 08:00 触发完整处理链路。
- `web`：Next.js Web 看板。
- `caddy`：公网反向代理和 HTTPS 证书。

## 日常检查

```bash
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 scheduler
docker compose logs --tail=100 worker
docker compose logs --tail=100 caddy
curl -f http://127.0.0.1:8181/api/v1/healthz
```

生产环境建议使用公网域名检查：

```bash
curl -f https://news.example.com/api/v1/healthz
```

## 常用操作

重启单个服务：

```bash
docker compose restart api
docker compose restart web
docker compose restart scheduler
```

查看任务日志：

```bash
docker compose logs -f worker
docker compose logs -f scheduler
```

手动验证完整处理链路：

- 登录管理员后台 `/admin/jobs`。
- 点击“执行完整链路”。
- 观察 `collect → normalize → rank → dedupe → summarize → generate_digest` 任务状态是否依次变为成功。

进入 API 容器：

```bash
docker compose exec api bash
```

执行迁移：

```bash
docker compose exec api alembic upgrade head
```

创建管理员：

```bash
docker compose exec api daily-news create-admin
```

## 备份

备份 PostgreSQL：

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U daily_news -d daily_news -Fc > backups/daily_news_$(date +%Y%m%d_%H%M%S).dump
```

备份上传对象存储或异地服务器，不要只保存在当前机器。

## 恢复

先停止写入服务：

```bash
docker compose stop api worker scheduler web
```

恢复数据库：

```bash
docker compose exec -T postgres pg_restore -U daily_news -d daily_news --clean --if-exists < backups/daily_news_YYYYMMDD_HHMMSS.dump
```

恢复后启动服务：

```bash
docker compose up -d api worker scheduler web caddy
docker compose exec api alembic upgrade head
```

## 证书与域名

生产环境使用 `infra/caddy/Caddyfile.production`。Caddy 会通过 Let’s Encrypt 自动申请和续期证书。

如果证书申请失败，优先检查：

- `APP_DOMAIN` 是否为真实域名。
- 域名 A 记录是否指向当前服务器公网 IP。
- 云安全组和系统防火墙是否放行 80 和 443。
- `docker compose logs --tail=200 caddy` 中的 ACME 错误。

## 生产安全基线

- `APP_ENV=production`。
- `SESSION_COOKIE_SECURE=true`。
- `SESSION_SECRET`、`CSRF_SECRET` 使用高强度随机值。
- `ENCRYPTION_KEY` 使用 Fernet key，不能使用模板默认值。
- 不开放公开注册，只允许管理员创建用户。
- 数据源凭据和 LLM Key 通过后台加密保存或通过环境变量注入。
- 不把 PostgreSQL、Redis 端口暴露到公网。
- 定期备份 PostgreSQL，并做恢复演练。

## 故障排查

登录失败：

- 检查用户是否被管理员禁用。
- 检查浏览器是否能写入 HttpOnly cookie。
- 生产 HTTPS 下确认 `SESSION_COOKIE_SECURE=true`。

页面能打开但 API 失败：

- 检查 Caddy `/api/v1/*` 是否反向代理到 `api:8000`。
- 检查 `NEXT_PUBLIC_API_BASE_URL=/api/v1`。
- 查看 `docker compose logs --tail=100 api`。

没有新内容：

- 检查 `/admin/scheduler` 是否启用。
- 检查 `docker compose logs --tail=200 scheduler`，确认已加载启用配置并创建 scheduled pipeline jobs。
- 检查 `/admin/jobs` 中最近任务状态。
- 检查来源是否启用、Token 是否有效、外部平台是否限流。

中文摘要为空：

- 检查 `/admin/llm` 是否有默认 Provider。
- 检查 LLM API Key、Base URL、Model 是否正确。
- 查看摘要任务日志。
