# Daily News

AI 热点信息每日汇总 Web 看板项目。

当前阶段：MVP 开发与生产化补齐。

## 文档

- [AI 热点信息每日汇总项目调研](docs/ai-daily-news-research.md)
- [AI 热点信息每日汇总项目需求分析](docs/requirements-analysis.md)
- [需求说明书](docs/requirements/requirements-specification.md)
- [业务流程图](docs/requirements/business-flow.md)
- [低保真原型图](docs/requirements/prototype.md)
- [需求评审记录](docs/requirements/requirements-review-record.md)
- [产品需求文档 PRD](docs/product/prd.md)
- [产品原型](docs/product/product-prototype.md)
- [页面流程](docs/product/page-flow.md)
- [系统设计文档目录](docs/design/README.md)
- [系统架构设计文档](docs/design/system-architecture.md)
- [后端 DDD 设计文档](docs/design/backend-ddd-design.md)
- [系统设计决策记录](docs/design/design-decisions.md)
- [数据库设计文档](docs/design/database-design.md)
- [API 接口文档](docs/design/api-design.md)
- [安全设计文档](docs/design/security-design.md)
- [部署文档](docs/deployment.md)
- [运维手册](docs/operations.md)

## 阶段进度

- 已完成：项目调研、需求分析、产品设计、系统设计、MVP 工程骨架、核心后端 API、Web 看板基础页面。
- 当前进行：生产化补齐，包括部署、运维、备份、安全配置和上线检查。
- 下一阶段：生产安全增强、前端管理能力完善、个性化推荐增强、真实数据采集验证。

## 初步方向

本项目计划建设一个面向外公网部署的多用户 AI 情报聚合与每日简报平台，核心能力包括：

- 多来源采集：RSS、Hacker News、GitHub、arXiv、Product Hunt、Hugging Face 等。
- 信息处理：去重、分类、热度评分、中文摘要。
- 多厂商 LLM：通过统一 provider 接口兼容不同模型服务。
- 前端工作台：登录、今日简报、历史简报、信息库、我的关注、详情抽屉、任务日志、用户管理。
- 个性化规则：关注关键词采用软加权，关注分类作为默认筛选并轻量加权，关注来源类型作为默认筛选，排除关键词、关闭来源类型和屏蔽来源采用硬过滤。
- 账号管理：不开放公开注册，用户只能由管理员创建。
- 用户边界：普通用户不能添加外部 URL 信息源，也不能发起任意外部平台实时检索。
- 部署形态：单台云服务器，通过 HTTPS 反向代理对外提供 Web 和 API。
- 管理配置：外部 API token 允许管理员后台录入，后端加密保存。
- 调度配置：Digest 默认北京时间每天 08:00 自动生成，时间可配置。
- 内容发布：每日 digest 自动发布到 Web 看板。
- 后续扩展：Email、RSS、Telegram、飞书、企业微信等推送渠道。

## 建议技术栈

- 后端：FastAPI
- 后端架构：DDD 风格模块化单体
- 前端：Next.js
- 数据库：PostgreSQL
- 缓存/任务状态：Redis
- 调度：APScheduler 起步，后续可升级到 Celery 或 Dramatiq

## 工程结构

```text
daily_news/
├── api/      # FastAPI 后端，DDD 模块化单体
├── web/      # Next.js App Router 前端
├── infra/    # Caddy 等基础设施配置
└── docs/     # 调研、需求、产品和系统设计文档
```

## 本地启动

1. 复制环境变量模板：`cp .env.example .env`
2. 构建并启动服务：`docker compose up --build -d`
3. 执行迁移：`docker compose exec api alembic upgrade head`
4. 创建管理员：`docker compose exec api daily-news create-admin`
5. 访问 Web：`http://localhost`
6. 访问 API 健康检查：`http://localhost/api/v1/healthz`

核心页面：

- `/login`：登录。
- `/today`：今日简报。
- `/history`：历史简报。
- `/library`：信息库，全量条目检索和筛选。
- `/following`：我的关注，基于关注关键词、分类、来源和反馈生成个性化信息流。
- `/admin/users`：管理员用户管理。
- `/admin/sources`：来源和凭据管理。
- `/admin/llm`：LLM Provider 管理。
- `/admin/jobs`：任务日志和手动触发。
- `/admin/scheduler`：调度配置。

## 生产部署

单台云服务器部署见 [部署文档](docs/deployment.md)。生产环境核心配置：

```dotenv
APP_ENV=production
APP_DOMAIN=news.example.com
APP_EXTERNAL_URL=https://news.example.com
CADDYFILE_PATH=./infra/caddy/Caddyfile.production
CADDY_ACME_EMAIL=admin@example.com
SESSION_COOKIE_SECURE=true
NEXT_PUBLIC_API_BASE_URL=/api/v1
```

生产环境不要使用 `.env.example` 中的默认密码和密钥。`POSTGRES_PASSWORD`、`SESSION_SECRET`、`CSRF_SECRET`、`ENCRYPTION_KEY` 必须替换为强随机值。

## 运维

日常运维、日志检查、备份恢复、证书排障见 [运维手册](docs/operations.md)。

常用命令：

```bash
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 worker
docker compose logs --tail=100 scheduler
curl -f http://127.0.0.1/api/v1/healthz
```

备份数据库：

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U daily_news -d daily_news -Fc > backups/daily_news_$(date +%Y%m%d_%H%M%S).dump
```

如果直接暴露 Next.js 开发服务器给外网预览，可在启动前设置 `NEXT_ALLOWED_DEV_ORIGINS=你的域名或服务器IP`，避免 Next.js 16 拦截开发态 HMR 请求。生产环境应通过 Caddy 对外暴露，不直接暴露 `web:3000` 或 `api:8000`。
