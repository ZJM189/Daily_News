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
    "id": "uuid",
    "digest_date": "2026-09-02",
    "version": 1,
    "status": "published",
    "title": "2026-09-02 AI 热点简报",
    "overview_zh": "今日 AI 热点集中在...",
    "stats": {
      "topic_count": 8,
      "item_count": 24,
      "source_count": 48
    },
    "items": [
      {
        "id": "uuid",
        "item_type": "topic",
        "rank": 1,
        "score_snapshot": 85.5,
        "title_snapshot": "OpenAI 发布新模型",
        "summary_snapshot_zh": "中文摘要",
        "importance_snapshot_zh": "重要性说明",
        "category_snapshot": "model_company",
        "source_snapshot": {
          "source_count": 2,
          "primary_item_id": "uuid",
          "primary_source_type": "rss",
          "primary_source_name": "OpenAI News",
          "primary_url": "https://example.com/news",
          "canonical_url": "https://example.com/news"
        }
      }
    ]
  }
}
```

说明：

- `view=following` 时后端根据当前用户规则计算个性化结果。
- 无 digest 时返回 `data: null`，前端展示空状态。
- 当前实现返回最新 published 版本及 `digest_items` 快照；个性化过滤后续在该接口上扩展。

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
- 当前实现支持按 `version` 查询，不传则返回当天最新 published 版本。

## 6. 信息库与详情接口

### 6.1 信息库搜索

`GET /api/v1/library/items`

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
| `min_score` | number | 否 | 最低热度分，0-100 |
| `has_summary` | boolean | 否 | 是否已有中文摘要 |
| `sort` | string | 否 | `latest`, `score`, `collected` |
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

### 6.2 信息库数据概览

`GET /api/v1/library/analytics`

查询参数与信息库搜索保持同一口径，额外支持：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `window_days` | integer | 否 | 统计窗口，`7` 最近 7 天，`30` 最近 30 天，`0` 表示全部；默认 30 |

响应：

```json
{
  "data": {
    "totals": {
      "item_count": 248,
      "summarized_count": 120,
      "summary_rate": 48.4,
      "source_count": 8,
      "average_score": 68.4
    },
    "trend": [
      { "date": "2026-09-01", "count": 42 },
      { "date": "2026-09-02", "count": 51 }
    ],
    "source_types": [
      { "key": "github", "label": "GitHub", "value": 86 },
      { "key": "arxiv", "label": "arXiv", "value": 64 }
    ],
    "sources": [
      { "key": "uuid", "label": "GitHub AI Trending", "value": 32 }
    ],
    "categories": [
      { "key": "open_source", "label": "开源项目", "value": 92 }
    ],
    "score_buckets": [
      { "key": "0_40", "label": "0-40", "min_score": null, "max_score": 40, "value": 12 },
      { "key": "40_60", "label": "40-60", "min_score": 40, "max_score": 60, "value": 44 },
      { "key": "60_80", "label": "60-80", "min_score": 60, "max_score": 80, "value": 130 },
      { "key": "80_plus", "label": "80+", "min_score": 80, "max_score": null, "value": 62 }
    ]
  }
}
```

约束：

- 图表维度使用动态数组返回，前端不写死具体来源名称。
- 该接口不触发外部实时抓取，只统计已入库内容。

### 6.3 条目详情

`GET /api/v1/library/items/{item_id}`

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

### 6.4 Topic 详情

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

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `type` | string | 否 | `rss`、`hacker_news`、`github`、`arxiv`、`product_hunt`、`hugging_face` |
| `status` | string | 否 | `enabled`、`disabled`、`missing_token`、`error` |
| `keyword` | string | 否 | 按名称或 URL 模糊搜索 |
| `page` | integer | 否 | 默认 1 |
| `page_size` | integer | 否 | 默认 20，最大 100 |

### 9.2 创建来源

`POST /api/v1/admin/sources`

请求：

```json
{
  "name": "OpenAI Blog",
  "type": "rss",
  "url": "https://openai.com/news/rss.xml",
  "query_config": {},
  "credential_id": null,
  "credential_env_key": null,
  "weight": 90,
  "language": "en",
  "status": "enabled"
}
```

说明：

- 只有管理员可调用。
- 普通用户不能创建 source。
- 首期已实现配置落库；URL SSRF 防护在 collector 实际请求外部 URL 前执行。

### 9.3 更新来源

`PATCH /api/v1/admin/sources/{source_id}`

说明：

- 支持更新 `name`、`status`、`url`、`query_config`、`credential_id`、`credential_env_key`、`weight`、`language`。
- `credential_id`、`credential_env_key`、`url`、`language` 传 `null` 表示清空。

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

状态：待实现，进入任务管理与 collector 阶段后落地。

### 9.5 Source Token 列表

`GET /api/v1/admin/source-credentials`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source_type` | string | 否 | 来源类型 |
| `status` | string | 否 | `active`、`disabled`、`missing`、`error` |
| `keyword` | string | 否 | 按名称模糊搜索 |
| `page` | integer | 否 | 默认 1 |
| `page_size` | integer | 否 | 默认 20，最大 100 |

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
  "secret": "ghp_***",
  "status": "active"
}
```

说明：

- `secret` 后端加密保存。
- 响应不返回明文。

### 9.7 更新 Source Token

`PATCH /api/v1/admin/source-credentials/{credential_id}`

说明：

- 支持更新 `name`、`secret`、`status`。
- `secret` 传入后会覆盖原密钥；响应仍只返回 `secret_masked`。

### 9.8 测试 Source Token

`POST /api/v1/admin/source-credentials/{credential_id}/test`

状态：待实现，进入各 source connector 阶段后落地。

## 10. 管理员任务接口

### 10.1 任务列表

`GET /api/v1/admin/jobs`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `job_type` | string | 否 | `collect`、`normalize`、`dedupe`、`rank`、`summarize`、`generate_digest`、`publish_digest` |
| `status` | string | 否 | `pending`、`running`、`success`、`failed`、`partial_success`、`cancelled` |
| `source_id` | uuid | 否 | 来源 ID |
| `created_from` | datetime | 否 | 创建时间起 |
| `created_to` | datetime | 否 | 创建时间止 |
| `page` | integer | 否 | 默认 1 |
| `page_size` | integer | 否 | 默认 20，最大 100 |

响应字段：

```json
{
  "data": [
    {
      "id": "uuid",
      "job_type": "collect",
      "trigger_type": "manual",
      "status": "pending",
      "source_id": null,
      "parent_job_run_id": null,
      "created_by": "uuid",
      "params": {},
      "total_count": 0,
      "success_count": 0,
      "failure_count": 0,
      "error_message": null,
      "error_detail": null,
      "started_at": null,
      "ended_at": null,
      "created_at": "2026-09-02T08:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 10.2 任务详情

`GET /api/v1/admin/jobs/{job_run_id}`

### 10.3 重跑任务

`POST /api/v1/admin/jobs/{job_run_id}/retry`

说明：

- 当前实现会创建一条新的 `pending` job，`trigger_type=retry`。
- 新 job 的 `parent_job_run_id` 指向原任务。
- `collect` 类型 retry 已可由 worker 消费执行；其他任务类型的执行逻辑待后续阶段实现。

### 10.4 触发全量采集

`POST /api/v1/admin/jobs/collect`

请求：

```json
{
  "source_types": ["rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"],
  "source_id": null,
  "since": "2026-09-01T00:00:00Z"
}
```

说明：

- 当前实现会创建一条 `job_type=collect`、`trigger_type=manual`、`status=pending` 的任务记录。
- `source_types` 为空数组表示 worker 按所有启用 source 处理。
- `source_id` 可用于指定单个 source。
- RSS collector 已实现，执行后写入 `raw_items`。
- GitHub、Hacker News、arXiv、Product Hunt、Hugging Face collector 待实现。
- 单个 source 失败不会中断整个 collect job，会写入任务错误信息和 source 最近错误。

### 10.5 触发完整每日链路

`POST /api/v1/admin/jobs/daily-pipeline`

请求：

```json
{
  "source_types": [],
  "digest_date": "2026-09-02",
  "exclude_recent_digest_days": 3,
  "normalize_limit": 5000,
  "rank_limit": 5000,
  "topic_limit": 1000,
  "summarize_limit": 100,
  "min_score": 60
}
```

说明：

- 当前实现会按顺序创建 6 条 `manual`、`pending` 任务：`collect`、`normalize`、`rank`、`dedupe`、`summarize`、`generate_digest`。
- `source_types` 为空数组表示采集所有启用 source。
- `digest_date` 不传时使用服务端默认时区当天日期。
- worker 会按固定优先级领取任务，适合管理员在 `/admin/jobs` 手动验证完整处理链路。
- 该接口只创建任务，不在 HTTP 请求内同步执行采集、LLM 摘要或简报生成。

### 10.6 生成 Digest

`POST /api/v1/admin/jobs/generate-digest`

请求：

```json
{
  "digest_date": "2026-09-02",
  "exclude_recent_digest_days": 3
}
```

说明：

- 当前实现会创建一条 `job_type=generate_digest`、`trigger_type=manual`、`status=pending` 的任务记录。
- worker 会按 `digest_date` 和 `timezone` 计算当天 `collected_at` 窗口，默认时区为 `Asia/Shanghai`。
- `exclude_recent_digest_days` 默认 3，用于排除最近几天已经进入过简报的 topic，避免连续重复上榜。
- 同一天重复触发生成任务时，也会沿用该排重规则。
- 当前生成逻辑从当天窗口内的高分 `topics` 生成 `digests` 和 `digest_items` 快照。
- 生成结果直接发布为 `published` 状态。
- 同一天重复生成会创建新版本，不覆盖旧版本历史快照。
- `digest_items` 当前以 `topic` 为快照目标，记录标题、分数、来源规则分类、摘要、重要性说明、来源数、主来源名称和原文链接。

### 10.7 触发 RawItem 标准化

`POST /api/v1/admin/jobs/normalize`

请求：

```json
{
  "source_id": null,
  "limit": 5000
}
```

说明：

- 当前实现会创建一条 `job_type=normalize`、`trigger_type=manual`、`status=pending` 的任务记录。
- worker 会读取 `status=collected` 的 `raw_items`，生成 `items`。
- 默认批量大小为 5000，避免单次只处理到早期同源数据。
- 标准化会写入 `normalized_title`、`title_hash`、`summary_original`、`content_snippet`、来源规则分类和 `status=normalized`。
- 已存在的重复条目不重复写入 `items`，对应 `raw_items` 标记为 `deduped`。
- 评分、专题聚合和中文摘要仍由后续 rank/topic/summarize 阶段处理。

### 10.8 触发 Item 评分

`POST /api/v1/admin/jobs/rank`

请求：

```json
{
  "source_id": null,
  "limit": 500
}
```

说明：

- 当前实现会创建一条 `job_type=rank`、`trigger_type=manual`、`status=pending` 的任务记录。
- worker 会读取 `status=normalized` 的 `items`，计算 `score` 和 `score_breakdown`。
- 评分口径为启发式规则：来源权重、新鲜度、AI 关键词命中、内容完整度。
- 执行成功后 item 状态更新为 `ranked`。
- 该分数是全局分数，不受用户“我的关注”影响；用户关注的软加权在个性化视图阶段另算。

### 10.9 触发专题聚合

`POST /api/v1/admin/jobs/dedupe`

请求：

```json
{
  "source_id": null,
  "limit": 1000
}
```

说明：

- 当前 `dedupe` 任务表示专题聚合，不是删除原始信息。
- worker 只读取 `status=ranked` 的 `items`。
- 聚合使用确定性候选键：规范化标题、去停用词后的关键词组合、规范化 canonical URL。
- 任一候选键相同的条目归入同一 `topic`，并在 `topic_items` 中建立关联。
- 专题主条目取全局分数最高的条目；专题分数叠加条目数量和来源多样性奖励。
- 重复执行会更新已有专题并幂等更新关联，不删除 `items` 或历史 digest。
- 首期不使用向量模型或语义聚类，后续可在不改变专题接口的前提下替换聚合策略。

### 10.10 触发中文摘要

`POST /api/v1/admin/jobs/summarize`

请求：

```json
{
  "source_id": null,
  "limit": 100,
  "min_score": 60
}
```

说明：

- 当前实现会创建一条 `job_type=summarize`、`trigger_type=manual`、`status=pending` 的任务记录。
- worker 会读取 `status=ranked`、`summary_zh is null` 且 `score >= min_score` 的高分条目。
- 摘要使用后台配置的默认启用 OpenAI-compatible LLM Provider。
- LLM 必须返回 JSON：`summary_zh`、`importance_zh`、`tags`、`confidence`。
- 成功后写入 `items.summary_zh`、`importance_zh`、`tags`、`summary_confidence`、`llm_provider_id`、`llm_model`、`prompt_version`，并将 item 状态置为 `summarized`。
- `items.category` 不由 LLM 判断；分类来自 source/source URL/source name 的规则映射。
- 每次调用都会写入 `llm_call_logs`，记录成功、失败或 schema error。
- 没有默认启用 Provider 时，任务失败且不修改任何 item。

### 10.11 获取调度配置

`GET /api/v1/admin/scheduler/configs`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `job_type` | string | 否 | 任务类型 |
| `enabled` | boolean | 否 | 是否启用 |
| `page` | integer | 否 | 默认 1 |
| `page_size` | integer | 否 | 默认 20，最大 100 |

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

### 10.12 更新调度配置

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

- Digest 处理链路默认北京时间每天 08:00 触发。
- 修改调度配置只影响后续任务，不修改历史 digest。
- `cron_expression` 使用 5 段 crontab 格式，例如 `0 8 * * *`。
- `timezone` 使用 IANA 时区，例如 `Asia/Shanghai`。
- scheduler 进程启动时加载启用的调度配置，并按配置创建 APScheduler Cron 任务。
- 调度时间到达后创建 `scheduled` 状态的完整 pipeline jobs：`collect`、`normalize`、`rank`、`dedupe`、`summarize`、`generate_digest`，由 worker 负责按顺序实际执行。
- scheduler 每 60 秒刷新一次配置，因此管理员修改启停状态、Cron 或时区后无需重启容器。

### 10.13 初始化默认调度配置和默认来源

命令：

```bash
daily-news init-scheduler-configs
daily-news seed-default-sources
```

说明：

- 两个命令都是幂等命令，不覆盖已有配置。
- 用于空库或老环境补齐默认每日处理链路调度配置。
- `seed-default-sources` 首期写入默认 RSS source。

### 10.14 单次执行 Worker

命令：

```bash
daily-news worker-once
```

说明：

- 优先从最早的 `pending collect` job 领取一条执行。
- 没有 `collect` 任务时，领取最早的 `pending normalize` job 执行。
- 没有 `normalize` 任务时，领取最早的 `pending rank` job 执行。
- 没有 `rank` 任务时，领取最早的 `pending dedupe` job 执行。
- 没有 `dedupe` 任务时，领取最早的 `pending summarize` job 执行。
- `collect` 执行 RSS collector 并写入 `raw_items`。
- `normalize` 将 `raw_items` 标准化写入 `items`。
- `rank` 为 `items` 写入全局 `score` 和 `score_breakdown`。
- `dedupe` 根据确定性候选键聚合 `topics` 和 `topic_items`。
- `summarize` 调用默认 LLM Provider 写入中文摘要和重要性说明。
- 正常生产环境使用 `worker` 服务循环执行。

## 11. 管理员 LLM Provider 接口

### 11.1 Provider 列表

`GET /api/v1/admin/llm-providers`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `enabled` | boolean | 否 | 是否启用 |
| `keyword` | string | 否 | 按名称模糊搜索 |
| `page` | integer | 否 | 默认 1 |
| `page_size` | integer | 否 | 默认 20，最大 100 |

### 11.2 创建 Provider

`POST /api/v1/admin/llm-providers`

请求：

```json
{
  "name": "DeepSeek",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "api_key": "sk-***",
  "timeout_seconds": 60,
  "retry_count": 2,
  "enabled": true,
  "is_default": false
}
```

说明：

- 首期只支持 OpenAI-compatible 协议，后端写入 `type=openai_compatible`。
- 响应不返回 `api_key` 明文，只返回 `api_key_masked`。
- `is_default=true` 时会自动取消其他 provider 的默认状态。

### 11.3 更新 Provider

`PATCH /api/v1/admin/llm-providers/{provider_id}`

说明：

- 支持更新 `name`、`base_url`、`model`、`api_key`、`timeout_seconds`、`retry_count`、`enabled`、`is_default`。
- `api_key` 传 `null` 表示清空密钥；不传表示保持原密钥。

### 11.4 测试 Provider

`POST /api/v1/admin/llm-providers/{provider_id}/test`

状态：待实现，进入 LLM adapter 阶段后落地。

### 11.5 设置默认 Provider

`POST /api/v1/admin/llm-providers/{provider_id}/set-default`

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
