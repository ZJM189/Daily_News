# 部署文档

本文档面向单台云服务器外公网部署，默认使用 Docker Compose 编排 PostgreSQL、Redis、FastAPI、Worker、Scheduler、Next.js 和 Caddy。

## 服务器准备

- 一台 Linux 云服务器，建议 2C4G 起步。
- 已安装 Docker 和 Docker Compose。
- 域名 A 记录指向服务器公网 IP。
- 防火墙放行 `80/tcp`、`443/tcp`。
- 代码目录位于服务器，例如 `/opt/daily_news` 或 `/root/daily_news`。

## 环境变量

复制模板：

```bash
cp .env.example .env
```

生产环境至少修改：

```dotenv
APP_ENV=production
APP_DOMAIN=news.example.com
APP_EXTERNAL_URL=https://news.example.com
CADDYFILE_PATH=./infra/caddy/Caddyfile.production
CADDY_ACME_EMAIL=admin@example.com

POSTGRES_PASSWORD=replace-with-strong-password
DATABASE_URL=postgresql+psycopg://daily_news:replace-with-strong-password@postgres:5432/daily_news

SESSION_SECRET=replace-with-long-random-secret
CSRF_SECRET=replace-with-long-random-secret
ENCRYPTION_KEY=replace-with-fernet-key
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax

NEXT_PUBLIC_API_BASE_URL=/api/v1
DEFAULT_TIMEZONE=Asia/Shanghai
DIGEST_CRON=0 8 * * *
```

`ENCRYPTION_KEY` 用于加密后台录入的外部平台 Token 和 LLM API Key。建议使用 Fernet key：

```bash
docker compose run --rm api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 启动

构建并启动：

```bash
docker compose build
docker compose up -d
```

执行数据库迁移：

```bash
docker compose exec api alembic upgrade head
```

创建首个管理员：

```bash
docker compose exec api daily-news create-admin
```

访问：

- Web：`https://news.example.com`
- 健康检查：`https://news.example.com/api/v1/healthz`

## 初始化配置

登录管理员账号后，建议按顺序配置：

1. `/admin/llm`：录入 OpenAI-compatible LLM Provider，设置默认模型。
2. `/admin/sources`：录入 RSS、GitHub、arXiv、Hacker News、Product Hunt、Hugging Face 等来源。
3. `/admin/scheduler`：确认每日处理链路触发时间，默认北京时间每天 08:00。
4. `/admin/users`：由管理员创建普通用户。
5. `/admin/jobs`：点击“执行完整链路”，确认采集、标准化、评分、聚合、摘要和简报生成可用。

## 升级发布

```bash
git pull
docker compose build api web
docker compose up -d --force-recreate api worker scheduler web caddy
docker compose exec api alembic upgrade head
```

升级后检查：

```bash
docker compose ps
docker compose logs --tail=100 api
curl -f https://news.example.com/api/v1/healthz
```

## 回滚

如果新版本异常，先回退代码版本，再重建应用服务：

```bash
git checkout <previous-commit>
docker compose build api web
docker compose up -d --force-recreate api worker scheduler web caddy
```

涉及数据库迁移的版本回滚需要单独评估，不建议直接降级生产数据库。
