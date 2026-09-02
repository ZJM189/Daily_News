# Daily News

AI 热点信息每日汇总 Web 看板项目。

当前阶段：系统设计。

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

## 阶段进度

- 已完成：项目调研、需求分析、产品设计。
- 当前进行：系统设计，包括系统架构、数据库设计、API 接口设计和安全设计。
- 下一阶段：开发阶段，包括工程骨架、数据库迁移、后端 API、前端页面和后台任务。

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
2. 启动基础服务和应用：`docker compose up --build`
3. 访问 Web：`http://localhost`
4. 访问 API 健康检查：`http://localhost/api/v1/healthz`

首个管理员账号后续通过后端命令 `daily-news create-admin` 创建。
