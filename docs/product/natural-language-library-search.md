# 自然语言信息库聊天助手需求

## 1. 需求背景

用户希望在网页端通过一个全局悬浮聊天入口，用自然语言描述想查的内容，系统自动转换为信息库检索条件，并以流式对话返回相关的已入库内容。该能力用于降低用户理解筛选器和组合条件的成本，不改变信息库“只查询站内已采集内容”的边界。

## 2. 产品目标

- 让用户在任意已登录页面快速发起信息库查询，并保留按用户隔离的聊天历史。
- 支持“最近几天关于 RAG 的论文”“80 分以上的 GitHub 项目”“OpenAI 相关产品发布”等自然语言表达。
- 将自然语言解释成可追溯、可编辑的信息库筛选条件。
- 结果优先在助手消息中展示高相关内容，并提供跳转到信息库继续筛选的入口。
- 不触发外部平台实时检索，不新增普通用户采集权限。

## 3. 首期范围

首期做“流式聊天 + 自然语言到站内检索条件”的信息库助手，不做通用聊天机器人。

包含：

- 全局悬浮聊天入口。
- 自然语言多轮输入。
- 查询意图预分类与固定拒答。
- DeepAgents 查询意图解析。
- 信息库站内检索。
- SSE 流式状态、回答文本和结果预览。
- 用户级会话与消息历史落库。
- 跳转信息库并回填筛选条件。
- 空状态、错误状态和权限控制。

不包含：

- 外部实时联网搜索。
- 自动新增 source 或修改采集规则。
- 基于结果生成长篇无引用问答回答。
- 跨用户或跨租户共享聊天历史。
- 向量数据库或全文 RAG 平台依赖。
- 语音输入。

## 4. 功能需求拆分

### 4.1 全局悬浮聊天入口

功能点：

- 登录后的所有普通页面展示悬浮按钮，默认位于右下角。
- 点击后展开悬浮聊天窗口。
- 展开后支持关闭、新建会话、切换最近会话和重新打开。
- 聊天运行时使用 `@assistant-ui/react` core primitives 管理消息、输入框、示例 prompt、自动滚动和复制操作；`@assistant-ui/react-ui` 仅复用 CSS 样式入口，避免其当前预制 React 组件与新版 core API 不兼容。
- 移动端悬浮框应转为底部抽屉或全宽浮层，避免遮挡主内容。
- 登录页、全屏弹窗和关键确认弹窗上不展示或自动收起悬浮框。

验收标准：

- 用户在今日简报、历史简报、信息库、我的关注、我的收藏页面都能打开悬浮聊天窗口。
- 悬浮框不遮挡页面主操作按钮和底部分页。
- 切换页面后悬浮框状态可重置为收起状态。

### 4.2 自然语言输入

功能点：

- 输入框支持 1-500 字中文或英文查询。
- 支持 Enter 提交，Shift+Enter 换行。
- 支持示例提示词，如“最近 7 天 Agent 相关论文”“分数 80 以上的开源项目”。
- 提交时显示流式状态，防止重复提交。
- 空输入、超长输入和明显无意义输入给出前端校验提示。

验收标准：

- 空输入不能发起请求。
- 提交中按钮禁用，完成后恢复。
- 输入内容不作为 HTML 渲染，避免 XSS。

### 4.3 查询意图预分类

功能点：

- 后端在调用 DeepAgents 前执行 `LibraryChatIntentClassifier`。
- 明确属于信息库查询、筛选、结果总结或上一轮结果追问时才进入检索 Agent。
- 代码编写、通用聊天、金融、天气、医疗、法律、外部实时搜索、提示词绕过和内容创作请求必须拒绝。
- 拒绝时不调用 DeepAgents，不执行数据库检索，只保存一条助手消息并返回固定话术：

```text
我只能查询已入库的 AI 信息、论文、开源项目和产业动态。你可以试试：“最近 7 天 RAG 论文”或“GitHub 上高分 Agent 项目”。
```

验收标准：

- “帮我写一个 Python 爬虫”返回固定拒答，不触发信息库查询。
- “Agent 代码怎么写”即使包含 Agent 关键词也返回固定拒答。
- “最近 7 天 RAG 论文”进入 DeepAgents 信息库查询流程。

### 4.4 查询意图解析

功能点：

- 将自然语言解析为信息库已有字段：
  - `keyword`
  - `search_terms`
  - `source_id`
  - `source_type`
  - `category`
  - `status`
  - `published_from`
  - `published_to`
  - `min_score`
  - `has_summary`
  - `sort`
  - `page_size`
- 解析结果以筛选 chips 展示，例如“关键词：RAG”“分类：研究论文”“最近 7 天”“分数 80+”。
- 用户可通过“在信息库查看全部”进入信息库页面继续调整筛选条件。
- 首期即使用后台配置的默认启用 LLM Provider，负责理解查询意图、提取结构化条件和扩展同义词。
- 解析置信度低时，保留原句作为 `keyword`，不强行推断过多条件。
- LLM 只能返回结构化查询意图，不能生成 SQL、直接返回查询结果、调用外部搜索或触发采集。

验收标准：

- “最近 7 天 RAG 论文”能解析出关键词、检索词、时间范围和研究论文分类。
- “GitHub 80 分以上项目”能解析出 GitHub 来源类型、最低分和开源项目倾向。
- 无法解析的自然语言仍能作为关键词查询。
- 解析结果必须展示给用户，不做不可解释的黑盒筛选。

### 4.4.1 LLM 解析约束

- 使用管理员配置的默认启用 OpenAI-compatible LLM Provider。
- 后端向 LLM 发送查询文本、当前日期和允许的字段/枚举说明，不发送不必要的用户敏感信息。
- LLM 必须返回 JSON，后端使用 schema 校验后才允许进入 repository 查询。
- 后端校验字段类型、日期范围、分数范围、来源 ID、分类、状态和排序枚举；非法字段直接丢弃或触发降级。
- `search_terms` 用于站内关键词匹配和同义词扩展，不能改变“只查询已入库内容”的边界。
- 记录 provider、model、耗时、解析模式和置信度，不记录 API key。
- 默认 Provider 不可用、超时、返回非法 JSON 或 schema 校验失败时，使用原句作为关键词执行站内检索，并返回 `mode=fallback`。

LLM 解析结果建议固定为以下 JSON 结构，字段值只能使用后端维护的枚举和范围：

```json
{
  "keyword": "RAG",
  "search_terms": ["RAG", "retrieval augmented generation"],
  "source_id": null,
  "source_type": null,
  "category": "research_paper",
  "status": null,
  "published_from": "2026-09-01T00:00:00+08:00",
  "published_to": "2026-09-08T23:59:59+08:00",
  "min_score": null,
  "has_summary": null,
  "sort": "latest",
  "page_size": 10,
  "explanation": "查询最近 7 天与 RAG 相关的研究论文",
  "confidence": 0.92
}
```

后端不得把模型输出直接拼接为 SQL；应将校验后的对象传给现有信息库 repository。`source_id`、`source_type`、`category`、`status` 和 `sort` 使用白名单，`confidence` 限制在 `0-1`，`page_size` 限制在 `1-20`。

### 4.4.2 Agent 与数据库工具

后端使用 DeepAgents 构建受限的 `LibrarySearchAgent`，不是让 Agent 直接操作数据库：

```text
前端自然语言
  -> FastAPI /library/chat/threads/{thread_id}/messages/stream
  -> LibraryChatIntentClassifier
  -> DeepAgents LibrarySearchAgent
  -> search_library_database 只读工具
  -> ContentLibraryService
  -> ContentLibraryRepository
  -> PostgreSQL items/sources
```

`search_library_database` 是 Agent 唯一的业务工具，负责接收已校验的筛选字段并返回条目预览。Agent 不拥有文件系统、命令执行、子 Agent、外部搜索和采集工具权限。工具内部仍使用参数化 SQLAlchemy 查询，因此模型无法越过权限边界。

查询执行顺序：

1. 前端在当前会话中提交 `content`。
2. 后端保存用户消息，并读取最近消息作为意图上下文。
3. `LibraryChatIntentClassifier` 判断是否允许进入信息库查询。
4. 允许时后端读取默认启用的 LLM Provider，创建 DeepAgents Agent。
5. Agent 理解自然语言，并调用 `search_library_database`。
6. 工具将条件转换为 `LibrarySearchQuery`，由 repository 查询已入库数据。
7. 后端校验 Agent 的结构化输出，保存助手消息和结果 metadata，并用 SSE 推送文本与结果卡片。
8. Agent 或 Provider 失败时，后端使用原句关键词检索并返回 `mode=fallback`。

### 4.5 信息库检索执行

功能点：

- 查询只调用站内信息库能力，不访问外部搜索引擎。
- 默认返回最多 10 条预览结果。
- 排序默认使用相关性近似策略：关键词命中 + score + 发布时间；如果解析出“最新”“高分”，则使用对应排序。
- 支持复用现有 `GET /api/v1/library/items` 查询字段；也可新增自然语言检索包装接口。
- 查询失败时展示错误提示和重试按钮。

验收标准：

- 检索结果只来自 `items` 表中已入库内容。
- 普通用户不能通过自然语言绕过权限触发采集、管理 source 或访问管理员接口。
- 无匹配结果时明确提示“仅搜索已入库内容”。

### 4.6 结果预览

功能点：

- 聊天助手消息内展示结果卡片列表。
- 每条结果展示标题、来源、分数和发布时间。
- 支持打开原文。
- 提供“在信息库查看全部结果”入口，并携带解析后的筛选条件。

验收标准：

- 点击“查看全部”后进入 `/library`，并回填等价筛选条件。
- 结果列表和信息库同一条目的标题、来源、分类、分数保持一致。

### 4.7 查询历史

首期会话和消息历史落库，按登录用户隔离。

功能点：

- 展开悬浮聊天窗口时加载最近会话列表。
- 进入会话后按时间顺序展示用户消息、助手消息、拒答消息和结果 metadata。
- 新建会话时创建 `library_chat_threads` 记录。
- 每次发送消息创建 `library_chat_messages` 用户记录，助手响应完成后创建助手记录。
- 用户可以在历史会话条目中删除自己的会话，删除时通过确认弹窗防误触；消息记录随会话级联删除。

验收标准：

- 刷新浏览器后历史仍可恢复。
- 查询历史不跨用户共享。
- 用户只能删除自己的历史会话，不能删除其他用户会话。

### 4.8 权限与安全

功能点：

- 未登录用户不可使用悬浮聊天窗口。
- 普通用户和管理员查询结果口径一致，除非未来显式增加管理员专属字段。
- 对输入做长度限制、转义和日志脱敏。
- 自然语言里出现 URL、外部搜索、抓取、添加来源等意图时，系统应返回固定拒答，不调用 DeepAgents。
- 后端接口应使用当前认证依赖和统一错误格式。

验收标准：

- 未登录访问接口返回 401。
- 普通用户输入“去 GitHub 实时搜最新项目”不会触发外部请求。
- 恶意脚本输入不会在页面执行。

### 4.9 可观测性

功能点：

- 记录自然语言检索次数、成功/失败次数、无结果次数。
- 记录解析后的字段，不记录敏感 token、cookie 或密码。
- 记录接口耗时，便于观察性能。

验收标准：

- 管理员能从日志中判断自然语言检索是否异常升高。
- 查询失败能定位是解析失败、信息库查询失败还是认证失败。

## 5. 推荐接口设计

### 5.1 兼容自然语言检索接口

`POST /api/v1/library/natural-language-search`

请求：

```json
{
  "query": "最近 7 天 RAG 相关论文",
  "page_size": 10
}
```

响应：

```json
{
  "mode": "llm",
  "explanation": "查询最近 7 天与 RAG 相关的研究论文",
  "interpreted_query": {
    "keyword": "RAG",
    "search_terms": ["RAG", "retrieval augmented generation"],
    "category": "research_paper",
    "source_type": null,
    "source_id": null,
    "status": null,
    "published_from": "2026-09-01T00:00:00+08:00",
    "published_to": "2026-09-08T23:59:59+08:00",
    "min_score": null,
    "has_summary": null,
    "sort": "latest",
    "page_size": 10
  },
  "chips": [
    { "key": "keyword", "label": "关键词：RAG" },
    { "key": "category", "label": "分类：研究论文" }
  ],
  "data": [],
  "meta": {
    "total": 0,
    "page": 1,
    "page_size": 10
  },
  "llm": {
    "provider": "Default Provider",
    "model": "configured-model",
    "confidence": 0.92
  },
  "library_url": "/library?keyword=RAG&category=research_paper&sort=latest"
}
```

接口约束：

- `query` 必填，1-200 字。
- `page_size` 默认 10，最大 20。
- 默认使用后台配置的默认启用 LLM Provider 解析查询。
- LLM 输出必须经过 JSON schema、枚举白名单和权限校验，前端不得直接信任模型输出。
- `mode` 取值为 `llm` 或 `fallback`；`fallback` 表示 LLM 不可用或输出无效，系统使用原句关键词查询。
- 只查询站内已采集内容。
- 不触发外部实时采集。
- 解析失败不返回 500，应降级为关键词检索。

### 5.2 流式聊天接口

#### 5.2.1 会话列表

`GET /api/v1/library/chat/threads?limit=20`

响应：

```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "title": "最近 7 天 RAG 论文",
      "created_at": "2026-09-08T10:00:00+08:00",
      "updated_at": "2026-09-08T10:02:00+08:00"
    }
  ]
}
```

#### 5.2.2 创建会话

`POST /api/v1/library/chat/threads`

请求：

```json
{ "title": "新的智能查询" }
```

#### 5.2.3 消息历史

`GET /api/v1/library/chat/threads/{thread_id}/messages`

响应：

```json
{
  "data": [
    {
      "id": "uuid",
      "thread_id": "uuid",
      "user_id": "uuid",
      "role": "assistant",
      "content": "查询 RAG 论文。共找到 12 条，先展示 6 条。",
      "metadata": {
        "mode": "llm",
        "item_ids": ["uuid"],
        "items": [],
        "library_url": "/library?keyword=RAG&sort=latest"
      },
      "created_at": "2026-09-08T10:02:00+08:00"
    }
  ]
}
```

#### 5.2.4 删除会话

`DELETE /api/v1/library/chat/threads/{thread_id}`

响应：

```json
{
  "data": { "ok": true }
}
```

接口约束：

- 只能删除当前登录用户自己的会话。
- 会话不存在或不属于当前用户时返回 404。
- 删除会话后，`library_chat_messages` 通过外键级联删除。

#### 5.2.5 流式发送消息

`POST /api/v1/library/chat/threads/{thread_id}/messages/stream`

请求：

```json
{ "content": "最近 7 天 RAG 相关论文" }
```

响应为 `text/event-stream`，事件类型：

```text
event: status
data: {"message":"正在判断查询范围","message_id":"uuid"}

event: delta
data: {"message_id":"uuid","text":"查询 RAG 论文。"}

event: results
data: {"message_id":"uuid","items":[],"meta":{"page":1,"page_size":6,"total":0},"library_url":"/library?keyword=RAG&sort=latest","mode":"llm","chips":[],"llm":{"provider":"Default","model":"model","confidence":0.9}}

event: rejected
data: {"message":"我只能查询已入库的 AI 信息、论文、开源项目和产业动态。你可以试试：“最近 7 天 RAG 论文”或“GitHub 上高分 Agent 项目”。","message_id":"uuid","intent":"coding"}

event: error
data: {"message":"信息库查询暂时不可用，请稍后重试。","message_id":"uuid"}

event: done
data: {"message_id":"uuid"}
```

约束：

- `content` 必填，1-500 字。
- `rejected` 表示固定拒答，不调用 DeepAgents 和信息库查询。
- `results` 中的 `items` 来自已入库数据库查询结果。
- SSE 请求使用当前登录态 cookie，未登录返回 401。

## 6. 示例查询映射

| 用户输入 | 解析结果 |
| --- | --- |
| 最近 7 天 Agent 论文 | `keyword=Agent`，`category=research_paper`，`published_from=最近7天` |
| OpenAI 相关新闻 | `keyword=OpenAI`，`sort=latest` |
| GitHub 上 80 分以上的项目 | `source_type=github`，`category=open_source`，`min_score=80` |
| 没有中文摘要的模型公司内容 | `category=model_company`，`has_summary=false` |
| 最近产品发布 | `category=product_launch`，`sort=latest` |

## 7. 非功能需求

- 首屏悬浮聊天框资源不应明显增加页面加载时间。
- 前端不得引入与当前 `@assistant-ui/react` 版本不兼容的预制组件；升级 assistant-ui 时必须同时跑 `npm run build` 和自然语言聊天 E2E。
- 聊天流式接口首个 `status` 事件 P95 目标小于 1 秒；完整自然语言检索目标小于 4 秒，其中 LLM 解析阶段目标不超过 3 秒；超时必须降级为关键词检索。
- 悬浮聊天框应支持键盘访问和屏幕阅读器标签。
- 移动端宽度小于 768px 时不得产生横向滚动。
- 与现有信息库查询结果口径和跳转筛选参数保持一致。

## 8. 分期建议

第一期：

- 固定拒答的 `LibraryChatIntentClassifier` 前置意图门控。
- 默认 LLM Provider + DeepAgents 智能意图理解 + 现有信息库查询。
- 结构化输出 schema 校验、白名单校验和 `fallback` 降级。
- 全局悬浮聊天框。
- SSE 状态、文本和结果预览流式返回。
- 用户级会话与消息历史落库。
- 历史会话删除。
- 跳转信息库回填筛选。

第二期：

- 支持更丰富的同义词、时间表达和多条件组合。
- 优化历史会话重命名、搜索和归档。

第三期：

- 引入语义检索或向量索引。
- 支持基于检索结果的引用式回答，但仍需明确引用来源。
