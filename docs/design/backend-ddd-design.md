# AI 热点信息每日汇总后端 DDD 设计文档

版本：v0.1

日期：2026-09-02

阶段：系统设计

关联文档：

- [系统架构设计](system-architecture.md)
- [数据库设计](database-design.md)
- [API 接口设计](api-design.md)
- [安全设计](security-design.md)

## 1. 设计结论

后端采用 DDD 风格的分层单体架构。

首期不拆微服务，也不在顶层按 bounded context 拆包。原因是系统仍处于 0 到 1 阶段，领域边界需要在开发中验证；直接把每个业务域拆成顶层模块，会让目录数量过多、早期开发成本偏高。后端代码先采用 `domain / application / infrastructure / interfaces` 大分层，业务域作为各层内部的子包逐步沉淀。

## 2. 分层架构

```text
interfaces/http-tasks-scheduler
          |
          v
application/use-cases
          |
          v
domain/entities-value-objects-domain-services-ports
          ^
          |
infrastructure/repositories-collectors-llm-redis
          |
          v
external systems/PostgreSQL-Redis-source-APIs-LLM
```

依赖规则：

- `domain` 不依赖 FastAPI、SQLAlchemy、Redis、外部 API SDK。
- `application` 编排 use case，依赖 domain 抽象和 repository/port 接口。
- `infrastructure` 实现数据库仓储、外部 collector、LLM provider、Redis lock 等技术细节。
- `interfaces` 暴露 HTTP API、后台任务入口和 scheduler 入口。
- 跨业务域协作通过 application service 或 domain event 完成，不直接绕过用例访问内部模型。

说明：

- 上图表达源码依赖方向；运行时由依赖注入把 infrastructure 实现装配给 application use case。
- 外部系统只允许被 infrastructure adapter 访问。

## 3. 业务域边界

以下业务域先作为设计边界存在，首期代码不在顶层拆目录；实现时根据需要放入对应 DDD 层内，例如 `domain/identity`、`application/digests`、`infrastructure/sources`、`interfaces/http/admin`。

| 业务域 | 职责 | 主要对象 |
| --- | --- | --- |
| Identity & Access | 登录、会话、用户、角色权限 | User、AuthSession |
| Source Management | 全局 source 配置、启停、抓取配置 | Source |
| Ingestion | 多来源采集、raw item 入库 | RawItem、Collector |
| Content Intelligence | 标准化 item、去重、topic 聚合、评分、摘要 | Item、Topic、Score、Summary |
| Digest Publishing | 每日 digest 生成、版本、发布和历史快照 | Digest、DigestItem |
| Personalization | 我的关注、保存搜索、反馈、user score | UserPreference、SavedSearch、UserFeedback |
| Library Chat | 信息库聊天会话、消息历史、意图门控和自然语言查询编排 | LibraryChatThread、LibraryChatMessage、LibraryChatIntent |
| LLM Operations | provider 配置、prompt 版本、调用记录 | LLMProvider、PromptVersion、LLMCallLog |
| Job Operations | 后台任务状态、重跑、错误追踪 | JobRun |

## 4. 聚合设计

### 4.1 Identity & Access

聚合根：

- `User`
- `AuthSession`

领域规则：

- 用户只能由管理员创建。
- `disabled` 用户不能登录。
- 密码永不以明文进入领域对象持久化。
- 普通用户不能获得管理员权限能力。

### 4.2 Source Management

聚合根：

- `Source`

领域规则：

- 普通用户不能创建 source。
- 禁用 source 不参与定时采集。
- token 缺失时 source 可以存在，但状态应为 `missing_token` 或不可采集。
- source URL 必须经过安全校验后才能启用。

### 4.3 Ingestion

聚合根：

- `RawItem`

领域服务：

- `CollectorRegistry`
- `RawItemNormalizer`

领域规则：

- 同一 source 的同一 external id 不重复入库。
- 同一 source 的同一 raw hash 不重复入库。
- 单个 source 失败不影响其他 source。

### 4.4 Content Intelligence

聚合根：

- `Item`
- `Topic`

值对象：

- `CanonicalUrl`
- `Score`
- `ScoreBreakdown`
- `Category`
- `Tag`
- `Summary`

领域服务：

- `DeduplicationService`
- `TopicAggregationService`
- `ScoringService`
- `SummarizationService`

当前 Worker 中的 `TopicAggregationJobExecutor` 负责应用层编排，
领域规则由确定性专题聚合函数实现，基础设施层负责 `Topic` 和 `TopicItem` 持久化。
`SummarizeJobExecutor` 负责 item 级中文摘要编排，LLM Provider 的协议适配和密钥解密只放在基础设施层。

领域规则：

- 去重优先级为 source external id、canonical URL、URL、标题归一化 hash。
- 全局 score 不受用户偏好影响。
- 摘要失败时 item 状态必须明确标记，不伪装成成功摘要。
- 自然语言信息库查询只能通过已校验的筛选 DTO 访问 repository，不能让 LLM 直接生成 SQL 或外部请求。

### 4.5 Digest Publishing

聚合根：

- `Digest`

领域规则：

- digest 按日期和版本保存。
- 同一天重新生成 digest 必须创建新版本，不覆盖历史快照。
- published digest 可以被查询，failed digest 不作为默认展示。

当前 `GenerateDigestJobExecutor` 负责按日期窗口选择高分 topic，生成 `Digest` 和 `DigestItem` 快照。

### 4.6 Personalization

聚合根：

- `UserPreference`
- `SavedSearch`
- `UserFeedback`

领域服务：

- `UserScoringService`
- `PreferenceRuleEvaluator`

领域规则：

- 用户偏好只影响当前用户视图。
- 关注关键词软加权。
- 关注分类作为默认筛选并轻量加权。
- 关注来源类型作为默认筛选。
- 排除关键词、关闭来源类型、屏蔽来源硬过滤。
- 保存搜索只能保存站内搜索条件，不允许外部 URL 或实时外部检索配置。

### 4.7 Library Chat

聚合根：

- `LibraryChatThread`
- `LibraryChatMessage`

应用服务：

- `ContentLibraryChatService`
- `LibraryChatIntentClassifier`
- `LibrarySearchAgent`

领域规则：

- 聊天会话和消息按 `user_id` 隔离。
- 范围外问题固定拒答，不调用 DeepAgents 和数据库检索。
- 范围内问题只允许 DeepAgents 调用 `search_library_database` 只读工具。
- 助手消息保存查询模式、意图、结果 ID、结果预览和跳转信息库 URL。

### 4.8 LLM Operations

聚合根：

- `LLMProvider`
- `PromptVersion`
- `LLMCallLog`

领域规则：

- 摘要业务只依赖 provider port。
- provider key 不从接口返回明文。
- LLM 输出必须经过 schema 校验。
- provider 调用失败必须记录调用日志。

### 4.9 Job Operations

聚合根：

- `JobRun`

领域规则：

- 手动重跑创建新的 job run，不覆盖原记录。
- job 状态变更必须记录开始和结束时间。
- 任务错误摘要可展示，错误详情不泄露密钥。

## 5. 后端目录结构

```text
api/
├── app/
│   ├── main.py
│   ├── domain/                     # Entity、ValueObject、Aggregate、领域服务、领域事件
│   ├── application/                # Use Case、Command、Query、事务编排
│   ├── infrastructure/             # ORM、Repository 实现、外部 API adapter、Redis、加密
│   └── interfaces/                 # FastAPI router、HTTP schema、CLI、Worker、Scheduler
│       ├── http/
│       │   ├── health.py
│       │   └── routes.py
│       ├── cli.py
│       ├── scheduler.py
│       └── worker.py
└── alembic/
```

当前仓库只放已经需要的基础文件，不提前创建空业务目录。

后续业务代码按需在各层内部增加子包，例如：

```text
domain/identity
domain/sources
domain/contents
domain/digests
application/identity
application/sources
application/content_library
infrastructure/llm
infrastructure/content_library
interfaces/http/admin
```

## 6. 每层职责

### 6.1 Domain

包含：

- Entity。
- Value Object。
- Aggregate Root。
- Domain Service。
- Domain Event。
- Repository Interface。
- 领域异常。

不包含：

- FastAPI router。
- SQLAlchemy session。
- HTTP request/response。
- Redis client。
- 外部 API SDK。

### 6.2 Application

包含：

- Use Case。
- Command / Query DTO。
- Application Service。
- UnitOfWork 接口。
- 权限前置校验调用。
- 事务边界。

示例：

- `CreateUserUseCase`
- `LoginUseCase`
- `CollectSourceUseCase`
- `GenerateDigestUseCase`
- `SearchItemsQuery`
- `ContentLibraryChatService`
- `UpdateUserPreferenceUseCase`

### 6.3 Infrastructure

包含：

- SQLAlchemy ORM model。
- Repository 实现。
- Alembic migration。
- Redis lock 和 cache。
- 外部 source collector 实现。
- OpenAI-compatible LLM provider 实现。
- DeepAgents 查询 Agent 和信息库聊天意图分类器实现。
- 加密、哈希、密钥读取。

### 6.4 Interfaces

包含：

- FastAPI router。
- HTTP request schema。
- HTTP response schema。
- 当前用户依赖。
- 管理员权限依赖。
- 后台任务入口。
- scheduler handler。

## 7. Repository 与 Unit Of Work

Repository 接口定义在 domain 或 application 边界内，具体实现放在 infrastructure。

示例：

```text
ContentItemRepository
  - get_by_id(item_id)
  - find_by_canonical_url(canonical_url)
  - search(query)
  - save(item)

DigestRepository
  - get_latest_published(date)
  - next_version(date)
  - save(digest)
```

UnitOfWork 负责事务边界：

```text
with uow:
    item = item_repo.get_by_id(id)
    item.mark_summarized(summary)
    item_repo.save(item)
    uow.commit()
```

## 8. CQRS 使用边界

MVP 不引入独立读库，但在 application 层区分 command 和 query：

- Command：创建用户、更新 source、触发采集、生成 digest、更新我的关注。
- Query：今日简报、历史简报、信息库搜索、详情、信息库聊天历史、任务列表。

复杂列表查询可以使用 read model 或查询服务直接面向数据库优化，但不能把写入规则绕过领域聚合。

## 9. Domain Event

首期 domain event 先采用进程内事件，必要时记录到数据库。

候选事件：

- `SourceCollectRequested`
- `RawItemCollected`
- `ItemNormalized`
- `ItemScored`
- `ItemSummarizationFailed`
- `DigestGenerated`
- `DigestPublished`
- `UserFeedbackSubmitted`
- `SourceBlockedByUser`

事件使用原则：

- 事件用于解耦上下文之间的后续动作。
- 事件处理失败必须记录 job run 或应用日志。
- 不在事件中传递敏感密钥。

## 10. API 与 DDD 的关系

- HTTP router 不直接操作 ORM model。
- Router 将请求转换为 command/query。
- Application use case 返回 DTO。
- Response schema 由 interfaces 层负责组装。
- 管理员权限在 interfaces 层校验，关键业务规则在 domain 层再次约束。

## 11. 数据库与 DDD 的关系

- 数据库表服务于持久化，不等同于领域模型。
- SQLAlchemy ORM model 放在 infrastructure 层。
- Domain entity 不继承 ORM model。
- 聚合内规则由 domain 方法维护。
- 跨聚合查询可以使用 query service，但跨聚合写入必须经过 use case 编排。

## 12. 测试策略

- Domain 层：纯单元测试，不依赖数据库和网络。
- Application 层：使用 fake repository 和 fake provider 测 use case。
- Infrastructure 层：使用测试数据库测 repository、collector、provider adapter。
- Interfaces 层：使用 FastAPI test client 测 API、认证和权限。

优先测试的领域规则：

- 管理员创建用户。
- 禁用用户不能登录。
- 普通用户不能创建 source。
- 保存搜索不能包含外部 URL。
- 摘要失败不能标记为成功。
- digest 重新生成必须创建新版本。
- 我的关注硬过滤和软加权只影响当前用户。
