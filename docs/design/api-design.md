# AI 热点信息每日汇总 API 接口文档

版本：v0.1

日期：2026-09-02

阶段：系统设计

关联文档：

- [系统架构设计](system-architecture.md)
- [数据库设计](database-design.md)
- [安全设计](security-design.md)

## 1. API 设计原则

- API base path：`/api/v1`。
- 请求和响应使用 JSON。
- 认证使用 HttpOnly Cookie Session。
- 后端根据 session 识别当前用户，不信任前端传入的用户 ID。
- 管理接口统一放在 `/admin` 下，并强制 `admin` 角色。
- 列表接口统一支持分页。
- 普通用户不能调用任何 source 创建、外部实时检索或任务触发接口。
- HTTP router 只做协议适配，不直接操作 ORM model；写操作进入 application use case，核心规则由 domain 层维护。

## 2. 通用响应格式

成功响应：

```json
{
  "data": {},
  "meta": {}
}
```

错误响应：

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "当前用户无权访问该资源",
    "details": {}
  }
}
```

分页响应：

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 128
  }
}
```

## 3. 通用错误码

| HTTP | code | 说明 |
| --- | --- | --- |
| 400 | `BAD_REQUEST` | 请求参数错误 |
| 401 | `UNAUTHORIZED` | 未登录或 session 失效 |
| 403 | `FORBIDDEN` | 权限不足 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `CONFLICT` | 唯一约束或状态冲突 |
| 422 | `VALIDATION_ERROR` | 字段校验失败 |
| 429 | `RATE_LIMITED` | 请求过于频繁 |
| 500 | `INTERNAL_ERROR` | 服务端异常 |
| 502 | `UPSTREAM_ERROR` | 外部 source 或 LLM provider 异常 |

## 4. 认证接口

### 4.1 登录

`POST /api/v1/auth/login`

请求：

```json
{
  "login": "admin@example.com",
  "password": "password"
}
```

响应：

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin",
      "status": "active"
    }
  }
}
```

说明：

- 成功后设置 HttpOnly session cookie。
- 被禁用用户返回 `403 FORBIDDEN`。
- 系统不提供公开注册接口。

### 4.2 退出登录

`POST /api/v1/auth/logout`

说明：

- 撤销当前 session。
- 清除浏览器 cookie。

### 4.3 当前用户

`GET /api/v1/auth/me`

响应：

```json
{
  "data": {
    "id": "uuid",
    "username": "user",
    "email": "user@example.com",
    "role": "user",
    "status": "active"
  }
}
```

## 5. Digest 接口

### 5.1 今日简报

`GET /api/v1/digests/today`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `view` | string | 否 | `system` 或 `following`，默认 `system` |
| `category` | string | 否 | 分类 code |
| `source_type` | string | 否 | 来源类型 |

响应：

```json
{
  "data": {
    "date": "2026-09-02",
    "version": 1,
    "status": "published",
    "title": "2026-09-02 AI 热点简报",
    "overview_zh": "今日 AI 热点集中在...",
    "stats": {
      "topic_count": 8,
      "item_count": 24,
      "source_count": 48
    },
    "topics": [],
    "items": []
  }
}
```

说明：

- `view=following` 时后端根据当前用户规则计算个性化结果。
- 无 digest 时返回 `data: null`，前端展示空状态。

### 5.2 历史简报

`GET /api/v1/digests/{date}`

路径参数：

- `date`：格式 `YYYY-MM-DD`。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `version` | integer | 否 | 指定版本，不传则取最新 published version |
| `view` | string | 否 | `system` 或 `following` |
| `category` | string | 否 | 分类筛选 |
| `source_type` | string | 否 | 来源类型筛选 |
| `keyword` | string | 否 | 当前 digest 内关键词筛选 |

说明：

- 历史简报只查询当天 digest 快照。
- 不返回未入选 digest 的全量内容。

## 6. 信息库与详情接口

### 6.1 信息库搜索

`GET /api/v1/items`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 站内关键词 |
| `source_id` | uuid | 否 | 来源 ID |
| `source_type` | string | 否 | 来源类型 |
| `category` | string | 否 | 分类 |
| `status` | string | 否 | 处理状态 |
| `published_from` | date | 否 | 发布时间起 |
| `published_to` | date | 否 | 发布时间止 |
| `sort` | string | 否 | `score`, `published_at`, `collected_at` |
| `order` | string | 否 | `asc`, `desc` |
| `page` | integer | 否 | 默认 1 |
| `page_size` | integer | 否 | 默认 20，最大 100 |

响应 item 摘要字段：

```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Example title",
      "source": {
        "id": "uuid",
        "name": "GitHub",
        "type": "github"
      },
      "category": "open_source",
      "tags": ["agent", "rag"],
      "status": "summarized",
      "score": 86.5,
      "published_at": "2026-09-02T09:12:00Z",
      "summary_zh": "中文摘要预览",
      "importance_zh": "为什么重要"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 128
  }
}
```

约束：

- 该接口只搜索已采集入库内容。
- 不触发外部实时检索。

### 6.2 条目详情

`GET /api/v1/items/{item_id}`

响应：

```json
{
  "data": {
    "id": "uuid",
    "title": "Example title",
    "url": "https://example.com/post",
    "canonical_url": "https://example.com/post",
    "source": {
      "id": "uuid",
      "name": "OpenAI Blog",
      "type": "rss"
    },
    "category": "model_company",
    "tags": ["model"],
    "score": 88.2,
    "score_breakdown": {
      "source_weight": 20,
      "freshness": 25,
      "community": 30,
      "keyword": 13.2
    },
    "summary_zh": "中文摘要",
    "importance_zh": "为什么重要",
    "summary_original": "Original summary",
    "content_snippet": "Original snippet",
    "status": "summarized",
    "published_at": "2026-09-02T09:12:00Z",
    "collected_at": "2026-09-02T09:20:00Z",
    "topic": {
      "id": "uuid",
      "title": "专题标题"
    },
    "related_items": []
  }
}
```

### 6.3 Topic 详情

`GET /api/v1/topics/{topic_id}`

说明：

- 该接口只服务 digest 卡片和详情抽屉。
- MVP 不提供独立热点专题页面。

## 7. 我的关注接口

### 7.1 获取我的关注配置

`GET /api/v1/me/preferences`

响应：

```json
{
  "data": {
    "follow_keywords": ["Agent", "RAG"],
    "exclude_keywords": ["招聘", "课程"],
    "follow_categories": ["model_company", "open_source"],
    "follow_source_types": ["rss", "github", "arxiv"],
    "disabled_source_types": ["product_hunt"],
    "blocked_source_ids": [],
    "blocked_domains": ["example.com"]
  }
}
```

### 7.2 更新我的关注配置

`PUT /api/v1/me/preferences`

请求：

```json
{
  "follow_keywords": ["Agent", "RAG"],
  "exclude_keywords": ["招聘", "课程"],
  "follow_categories": ["model_company", "open_source"],
  "follow_source_types": ["rss", "github", "arxiv"],
  "disabled_source_types": ["product_hunt"],
  "blocked_source_ids": [],
  "blocked_domains": ["example.com"]
}
```

说明：

- 只更新当前用户。
- 不影响全局 digest。
- 不允许提交外部 URL source。

### 7.3 保存搜索

`POST /api/v1/me/saved-searches`

请求：

```json
{
  "name": "RAG 技术动态",
  "query": {
    "keyword": "RAG",
    "source_types": ["github", "arxiv"],
    "time_range": "7d",
    "sort": "score"
  },
  "apply_as_filter": true,
  "apply_as_boost": true
}
```

说明：

- `query` 只能包含站内搜索字段。
- 如包含外部 URL、外部搜索 endpoint 或抓取配置，返回 `422 VALIDATION_ERROR`。

### 7.4 保存搜索列表

`GET /api/v1/me/saved-searches`

### 7.5 更新保存搜索

`PATCH /api/v1/me/saved-searches/{saved_search_id}`

### 7.6 删除保存搜索

`DELETE /api/v1/me/saved-searches/{saved_search_id}`

### 7.7 提交反馈

`POST /api/v1/me/feedback`

请求：

```json
{
  "target_type": "item",
  "target_id": "uuid",
  "action": "more_like"
}
```

动作：

- `more_like`
- `less_like`
- `block_source`

说明：

- `block_source` 会写入反馈记录，并同步更新当前用户屏蔽来源配置。

## 8. 管理员用户接口

### 8.1 用户列表

`GET /api/v1/admin/users`

查询参数：

- `role`
- `status`
- `keyword`
- `page`
- `page_size`

### 8.2 创建用户

`POST /api/v1/admin/users`

请求：

```json
{
  "username": "user01",
  "email": "user01@example.com",
  "display_name": "User 01",
  "password": "initial-password",
  "role": "user",
  "status": "active"
}
```

说明：

- 只有管理员可调用。
- 密码服务端哈希后存储。
- 不存在公开注册接口。

### 8.3 更新用户

`PATCH /api/v1/admin/users/{user_id}`

可更新字段：

- `display_name`
- `role`
- `status`

### 8.4 重置密码

`POST /api/v1/admin/users/{user_id}/reset-password`

请求：

```json
{
  "new_password": "new-password"
}
```

## 9. 管理员来源接口

### 9.1 来源列表

`GET /api/v1/admin/sources`

查询参数：

- `type`
- `status`
- `keyword`
- `page`
- `page_size`

### 9.2 创建来源

`POST /api/v1/admin/sources`

请求：

```json
{
  "name": "OpenAI Blog",
  "type": "rss",
  "url": "https://openai.com/news/rss.xml",
  "query_config": {},
  "credential_ref": null,
  "weight": 90,
  "language": "en",
  "status": "enabled"
}
```

说明：

- 只有管理员可调用。
- URL 必须经过 SSRF 防护校验。
- 普通用户不能创建 source。

### 9.3 更新来源

`PATCH /api/v1/admin/sources/{source_id}`

### 9.4 手动抓取单个来源

`POST /api/v1/admin/sources/{source_id}/collect`

响应：

```json
{
  "data": {
    "job_run_id": "uuid",
    "status": "pending"
  }
}
```

### 9.5 Source Token 列表

`GET /api/v1/admin/source-credentials`

说明：

- 仅管理员可访问。
- 响应只返回 token 掩码、状态和最近测试结果。

### 9.6 创建 Source Token

`POST /api/v1/admin/source-credentials`

请求：

```json
{
  "name": "GitHub Token",
  "source_type": "github",
  "secret": "ghp_***"
}
```

说明：

- `secret` 后端加密保存。
- 响应不返回明文。

### 9.7 更新 Source Token

`PATCH /api/v1/admin/source-credentials/{credential_id}`

### 9.8 测试 Source Token

`POST /api/v1/admin/source-credentials/{credential_id}/test`

## 10. 管理员任务接口

### 10.1 任务列表

`GET /api/v1/admin/jobs`

查询参数：

- `job_type`
- `status`
- `source_id`
- `date_from`
- `date_to`
- `page`
- `page_size`

### 10.2 任务详情

`GET /api/v1/admin/jobs/{job_run_id}`

### 10.3 重跑任务

`POST /api/v1/admin/jobs/{job_run_id}/retry`

### 10.4 触发全量采集

`POST /api/v1/admin/jobs/collect`

请求：

```json
{
  "source_types": ["rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"],
  "since": "2026-09-01T00:00:00Z"
}
```

### 10.5 生成 Digest

`POST /api/v1/admin/jobs/generate-digest`

请求：

```json
{
  "digest_date": "2026-09-02"
}
```

说明：

- 生成新版本 digest。
- 不覆盖旧版本历史快照。

### 10.6 获取调度配置

`GET /api/v1/admin/scheduler/configs`

响应示例：

```json
{
  "data": [
    {
      "id": "uuid",
      "job_type": "generate_digest",
      "name": "每日 Digest 生成",
      "cron_expression": "0 8 * * *",
      "timezone": "Asia/Shanghai",
      "enabled": true
    }
  ]
}
```

### 10.7 更新调度配置

`PATCH /api/v1/admin/scheduler/configs/{config_id}`

请求：

```json
{
  "cron_expression": "0 8 * * *",
  "timezone": "Asia/Shanghai",
  "enabled": true
}
```

说明：

- Digest 默认北京时间每天 08:00 生成。
- 修改调度配置只影响后续任务，不修改历史 digest。

## 11. 管理员 LLM Provider 接口

### 11.1 Provider 列表

`GET /api/v1/admin/llm/providers`

### 11.2 创建 Provider

`POST /api/v1/admin/llm/providers`

请求：

```json
{
  "name": "DeepSeek",
  "type": "openai_compatible",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "api_key": "sk-***",
  "timeout_seconds": 60,
  "retry_count": 2,
  "enabled": true,
  "is_default": false
}
```

响应不返回 `api_key` 明文，只返回 `api_key_masked`。

### 11.3 更新 Provider

`PATCH /api/v1/admin/llm/providers/{provider_id}`

### 11.4 测试 Provider

`POST /api/v1/admin/llm/providers/{provider_id}/test`

### 11.5 设置默认 Provider

`POST /api/v1/admin/llm/providers/{provider_id}/set-default`

## 12. 健康检查接口

### 12.1 存活检查

`GET /api/v1/healthz`

### 12.2 就绪检查

`GET /api/v1/readyz`

检查项：

- 数据库连接。
- Redis 连接。
- 必要配置是否存在。

## 13. 权限矩阵

| 接口组 | 未登录 | 普通用户 | 管理员 |
| --- | --- | --- | --- |
| `/auth/login` | 可访问 | 可访问 | 可访问 |
| `/auth/logout`, `/auth/me` | 不可访问 | 可访问 | 可访问 |
| `/digests`, `/items`, `/topics` | 不可访问 | 可访问 | 可访问 |
| `/me/preferences` | 不可访问 | 仅本人 | 仅本人 |
| `/me/saved-searches` | 不可访问 | 仅本人 | 仅本人 |
| `/me/feedback` | 不可访问 | 仅本人 | 仅本人 |
| `/admin/users` | 不可访问 | 不可访问 | 可访问 |
| `/admin/sources` | 不可访问 | 不可访问 | 可访问 |
| `/admin/jobs` | 不可访问 | 不可访问 | 可访问 |
| `/admin/scheduler` | 不可访问 | 不可访问 | 可访问 |
| `/admin/llm` | 不可访问 | 不可访问 | 可访问 |

## 14. 后续可扩展接口

以下接口不进入 MVP：

- 邮件订阅和推送接口。
- RSS 输出接口。
- Telegram、飞书、企业微信推送接口。
- 面向第三方系统的公开 API token。
- 普通用户自定义外部 URL source。
- 普通用户外部实时搜索。
