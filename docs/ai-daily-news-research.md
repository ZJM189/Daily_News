# AI 热点信息每日汇总项目调研

调研日期：2026-08-31

## 1. 调研目标

本次调研围绕“AI 热点信息每日汇总”的前后端项目展开，重点回答以下问题：

- 市面上类似产品通常如何组织信息、摘要和分发？
- GitHub 上是否已有类似开源项目可以参考？
- 一个可落地的前后端产品应包含哪些核心模块？
- 初版 MVP 应该优先做哪些能力，避免变成只跑脚本的日报项目？

## 2. 初步结论

类似项目已经不少，但大多数偏向“脚本 + 定时任务 + Markdown/邮件/IM 推送”。真正适合作为完整前后端产品的机会在于：

- 可视化 Dashboard，而不是只生成日报文件。
- 可追溯来源，支持查看原文、来源、发布时间、抓取时间和摘要依据。
- 智能去重与聚类，把多来源报道的同一事件合并成一个 topic。
- 热度评分与排序，结合来源权重、GitHub stars、HN points、Product Hunt votes、论文引用/讨论热度等信号。
- 用户偏好订阅，比如方向、关键词、排除词、语言、推送时间和推送渠道。
- 历史趋势分析，比如某个模型、公司、框架、论文方向在过去 7 天/30 天的热度变化。

因此，建议项目定位不要只是“AI 新闻总结器”，而应是“AI 情报聚合与每日简报平台”。

## 3. 产品和内容形态调研

### 3.1 Newsletter 类产品

#### TLDR AI

官网：https://tldr.tech/ai/

特点：

- 面向工程师、开发者和技术从业者。
- 每日短简报，强调快速浏览。
- 内容包括 AI 新闻、论文、工具和产品发布。
- 主要价值是节省筛选时间，而不是深度研究。

可借鉴点：

- 信息块要短，适合扫读。
- 每条内容都应该有标题、摘要、原文链接和一句“为什么重要”。
- 分类清晰，避免把新闻、论文、工具和融资消息混在一起。

#### The Rundown AI

官网：https://www.therundown.ai/

特点：

- 面向更广泛的 AI 使用者和业务人群。
- 强调可读性和“为什么这件事重要”。
- 语气更接近大众化 AI 新闻简报。

可借鉴点：

- 摘要不应只是复述新闻，而应告诉用户影响是什么。
- 可以增加“适合谁关注”的标签，比如开发者、产品经理、创业者、研究者。

#### Skimless

官网：https://www.skimless.com/

特点：

- 聚合多个 newsletter、博客、YouTube、changelog 等来源。
- 强调去重和个性化。
- 更接近“对已有信息源做二次聚合”的产品。

可借鉴点：

- 用户真正痛点不只是“没有信息”，而是“信息太多且重复”。
- 去重、个性化和来源透明度是差异化关键。

## 4. GitHub 开源项目调研

### 4.1 YeeKal/ai-daily

仓库：https://github.com/YeeKal/ai-daily

定位：

- 中文 AI 信号筛选与日报项目。
- 支持 RSS、GitHub Trending、Hacker News 等来源。
- 支持飞书、Discord 等推送渠道。

可借鉴点：

- 多源采集。
- LLM 评分。
- 跨日去重。
- 早报/晚报机制。
- 中文摘要和推送。

风险或不足：

- 更偏自动化脚本和推送，不一定有完整产品化后台。
- 如果要做前后端平台，需要补充用户系统、Dashboard、信源管理和历史查询。

### 4.2 duanyytop/agents-radar

仓库：https://github.com/duanyytop/agents-radar

定位：

- 面向 AI Agents 领域的自动雷达。
- GitHub Actions 定时运行。
- 输出 GitHub Pages、RSS、MCP 等形态。

数据源覆盖：

- GitHub。
- Hacker News。
- Product Hunt。
- arXiv。
- Hugging Face。
- Dev.to。
- Lobste.rs。
- OpenAI、Anthropic 等官方站点或 sitemap。

可借鉴点：

- 数据源设计很完整。
- 中英双语输出。
- 静态页面和 RSS 分发成本低。
- 可以作为“采集与内容生成 pipeline”的参考。

风险或不足：

- 更偏垂直主题雷达，不是通用用户可配置平台。
- 管理后台、用户偏好和多租户能力不足。

### 4.3 pursky7468/ai-news-radar

仓库：https://github.com/pursky7468/ai-news-radar

定位：

- 更接近完整前后端项目。
- 技术栈包括 FastAPI、Next.js、APScheduler、Postgres/SQLite。
- 提供 Dashboard、搜索、收藏等产品功能。

可借鉴点：

- 后端 API + 前端 Dashboard 的项目形态符合本项目方向。
- 有定时抓取、数据库存储和前端检索能力。
- 可参考模块边界：采集器、调度器、数据库、API、前端页面。

风险或不足：

- 需要进一步确认代码质量、测试覆盖和数据模型是否适合复用。
- 如果直接参考，需要避免结构过重。

### 4.4 fanyang-888/personal-ai-intelligence-tool

仓库：https://github.com/fanyang-888/personal-ai-intelligence-tool

定位：

- 个人 AI 情报系统。
- Next.js + FastAPI + Postgres。
- 更强调全栈产品化。

可借鉴点：

- 多阶段流水线。
- 聚类和跨日去重。
- 双语输出。
- 邮件简报。
- 适合参考完整产品架构。

风险或不足：

- 项目复杂度可能较高。
- 初版 MVP 不应完整照搬其 pipeline，应该先实现最小闭环。

### 4.5 datawhalechina/omni-info-radar

仓库：https://github.com/datawhalechina/omni-info-radar

定位：

- 泛主题信息雷达。
- 覆盖 GitHub、公众号、论文、产品、安全资讯等。

可借鉴点：

- 频道化信息组织。
- 关注词和关键词配置。
- 多端推送。
- Web Beta 形态。

风险或不足：

- 泛主题会带来信息源和分类复杂度。
- 本项目建议先聚焦 AI 主题，再扩展泛技术/泛资讯。

### 4.6 AlexK020908/AI-News-Ranker

仓库：https://github.com/AlexK020908/AI-News-Ranker

定位：

- AI 新闻排序和摘要项目。
- 技术栈包含 Next.js、Supabase、Claude、Redis 等。

可借鉴点：

- 多源 story panel。
- topic cluster。
- ranking。
- Supabase schema。
- Redis 缓存。

风险或不足：

- 需要评估数据源、授权和成本控制。
- 适合参考“排序和聚类”部分，不一定适合作为整体骨架。

### 4.7 Alionkissadeer/ai-daily-news

仓库：https://github.com/Alionkissadeer/ai-daily-news

定位：

- RSS + X 信息源。
- 支持微信、Telegram、Markdown 输出。
- 支持播客音频形态。

可借鉴点：

- 多渠道分发。
- 音频 digest 是差异化方向。
- 适合后续作为增强功能，而不是初版核心。

风险或不足：

- X 数据源稳定性、授权和成本需要特别关注。
- 音频生成会增加成本和处理链路。

### 4.8 frankzch/ai-news-skill

仓库：https://github.com/frankzch/ai-news-skill

定位：

- Agent Skill 形态的 AI 新闻聚合能力。
- 覆盖 AI 新闻、社交热点、KOL、视频、GitHub Trending 等。

可借鉴点：

- 信源覆盖广。
- 可以作为来源清单参考。
- 适合后续扩展到 Agent 工具调用或 MCP 服务。

风险或不足：

- Skill 形态不等于完整 Web 产品。
- 可作为能力模块参考，不适合直接当做前后端项目模板。

## 5. 推荐数据源

优先使用稳定 API 和 RSS，初版不建议大量依赖非结构化网页爬虫。

### 5.1 官方博客和 RSS

建议来源：

- OpenAI。
- Anthropic。
- Google DeepMind。
- Microsoft AI。
- Meta AI。
- Hugging Face。
- LangChain。
- Vercel AI。
- Perplexity。
- Mistral AI。
- Stability AI。

用途：

- 获取官方产品发布、模型更新、研究进展和平台变更。

实现建议：

- 建立 `sources` 表，保存源名称、类型、URL、语言、权重、是否启用。
- RSS 解析结果进入统一 `items` 表。
- 官方来源权重应高于二次转载站点。

### 5.2 GitHub

建议来源：

- GitHub Search API。
- GitHub Trending 页面。
- 指定 topic，如 `llm`、`ai-agent`、`rag`、`machine-learning`、`generative-ai`。

用途：

- 捕捉开源项目趋势。
- 发现新框架、Agent 工具、RAG 工具、模型部署工具。

建议字段：

- repo name。
- description。
- stars。
- stars today。
- forks。
- language。
- topics。
- pushed_at。
- created_at。
- README 摘要。

注意事项：

- GitHub Trending 没有正式稳定 API，页面解析可能变动。
- Search API 有 rate limit，需要缓存和增量抓取。

### 5.3 Hacker News

建议来源：

- Hacker News Algolia API：https://hn.algolia.com/api

用途：

- 捕捉技术社区讨论热度。
- 通过 points、comments、created_at 排序。

建议查询：

- `AI`。
- `LLM`。
- `OpenAI`。
- `Anthropic`。
- `agents`。
- `RAG`。
- `model release`。

注意事项：

- HN 对工程和创业内容敏感，但不是所有 AI 重要事件都会出现。
- points 和 comments 可以作为热度评分的一部分。

### 5.4 arXiv

建议来源：

- arXiv API：https://info.arxiv.org/help/api/

建议分类：

- `cs.AI`。
- `cs.CL`。
- `cs.LG`。
- `cs.CV`。
- `stat.ML`。

用途：

- 获取研究论文。
- 按关键词和分类筛选重要论文。

注意事项：

- 论文数量大，必须先筛选再摘要。
- 摘要时要标注“论文尚未经过社区验证”的不确定性。

### 5.5 Product Hunt

建议来源：

- Product Hunt API 2.0：https://api.producthunt.com/v2/docs

用途：

- 捕捉 AI 产品发布。
- votes、comments 可作为热度信号。

注意事项：

- 需要 token。
- 商业化使用需要关注官方条款。

### 5.6 Hugging Face

建议来源：

- Hugging Face Hub API：https://huggingface.co/docs/hub/api

用途：

- 捕捉模型、数据集和 Spaces 的发布趋势。
- 对模型类热点尤其重要。

建议字段：

- model id。
- task。
- likes。
- downloads。
- tags。
- pipeline_tag。
- lastModified。

注意事项：

- downloads 和 likes 可做热度信号，但不能完全代表质量。

### 5.7 正文抽取和网页解析

可选工具：

- Jina Reader：https://github.com/jina-ai/reader
- Firecrawl：https://github.com/firecrawl/firecrawl
- trafilatura：https://github.com/adbar/trafilatura

用途：

- 把网页正文转成更适合 LLM 处理的 Markdown 或结构化文本。

注意事项：

- 初版应优先使用 RSS/API 已提供的标题、摘要、链接和元数据。
- 对高价值条目再抓正文，控制成本和失败率。

## 6. 产品功能建议

### 6.1 首页日报

核心模块：

- 今日重点。
- 模型与大厂动态。
- 开源项目。
- 论文。
- 产品发布。
- 融资与行业。
- 社区讨论。

每条信息建议展示：

- 标题。
- 一句话摘要。
- 为什么重要。
- 来源。
- 发布时间。
- 热度分。
- 分类标签。
- 原文链接。

### 6.2 趋势 Dashboard

核心能力：

- 按时间查看热点趋势。
- 按分类筛选。
- 按来源筛选。
- 按关键词搜索。
- 查看某个 topic 的相关报道。

### 6.3 信源管理

核心能力：

- 新增 RSS/API source。
- 启用/禁用 source。
- 配置信源权重。
- 查看最近抓取状态。
- 查看失败日志。

### 6.4 用户偏好

核心能力：

- 关注关键词。
- 排除关键词。
- 关注分类。
- 语言偏好。
- 简报时间。
- 推送渠道。

初版可以先做单用户配置，后续再扩展多用户。

### 6.5 推送渠道

初版建议：

- Email。
- RSS feed。
- Markdown 导出。

后续扩展：

- Telegram。
- 飞书。
- 企业微信。
- Discord。
- Webhook。

## 7. 后端架构建议

推荐初版后端模块：

- `collectors`：不同来源的采集器。
- `normalizer`：统一字段结构。
- `deduplicator`：URL、标题相似度、embedding 聚类。
- `ranker`：热度评分。
- `summarizer`：摘要、分类、为什么重要。
- `scheduler`：定时任务。
- `api`：对前端暴露查询和管理接口。
- `delivery`：邮件、RSS、Webhook 推送。

推荐数据流：

1. 定时任务触发采集。
2. 采集器从 RSS/API 获取原始条目。
3. normalizer 标准化字段。
4. 写入数据库，保留 raw payload。
5. 去重和聚类。
6. 对高价值条目调用 LLM 生成摘要和分类。
7. 排序生成每日 digest。
8. 前端读取 digest 和 item API。
9. 推送渠道发送日报。

## 8. 前端架构建议

初版页面：

- `/`：今日日报。
- `/topics`：热点聚类列表。
- `/items`：原始条目列表。
- `/sources`：信源管理。
- `/settings`：偏好设置。
- `/history`：历史日报。

界面风格：

- 偏信息工作台，不做营销 landing page。
- 高密度但清晰，适合快速扫读。
- 分类、来源、时间、热度分应一眼可见。
- 避免大面积装饰，优先表格、列表、筛选器和详情抽屉。

关键交互：

- 点击条目打开详情抽屉。
- 在详情里展示原文链接、摘要、为什么重要、相关条目、原始来源。
- 支持收藏和标记不感兴趣。
- 支持按日期回看。

## 9. 技术栈建议

### 方案 A：FastAPI + Next.js + PostgreSQL

适合目标：

- 做完整前后端产品。
- 后续支持用户系统、搜索、任务调度、推送和管理后台。

建议组合：

- 后端：FastAPI。
- 前端：Next.js。
- 数据库：PostgreSQL。
- ORM：SQLAlchemy 或 SQLModel。
- 任务调度：APScheduler、Celery 或 Dramatiq。
- 缓存：Redis。
- 搜索：Postgres full-text search，后续可换 Meilisearch。
- 部署：Docker Compose。

优点：

- 工程边界清晰。
- Python 适合采集、摘要、LLM、NLP、网页解析。
- Next.js 适合做 Dashboard。

缺点：

- 初始工程量比纯脚本大。
- 需要设计 API 和数据模型。

### 方案 B：Next.js 全栈 + Supabase

适合目标：

- 快速做在线 Demo。
- 降低后端部署复杂度。

建议组合：

- Next.js App Router。
- Supabase Postgres。
- Supabase Auth。
- Vercel Cron。
- Edge/API Routes。

优点：

- 启动快。
- 登录、数据库和部署体验好。

缺点：

- Python 生态的数据处理和爬取能力不如方案 A 方便。
- 长任务、复杂采集和调度可能受平台限制。

### 推荐

如果目标是认真做一个“可持续维护的 AI 情报平台”，推荐方案 A：

- `FastAPI` 负责采集、处理、摘要和 API。
- `Next.js` 负责信息工作台。
- `PostgreSQL` 作为主存储。
- `Redis` 用于缓存、任务状态和限流。

初版可以先不用 Celery，使用 APScheduler 或简单 cron 跑定时任务。等采集源和任务量变大后，再升级到 Celery/Dramatiq。

## 10. 数据模型草案

### sources

- `id`
- `name`
- `type`: rss, github, hn, arxiv, product_hunt, huggingface, custom
- `url`
- `language`
- `weight`
- `enabled`
- `last_fetched_at`
- `last_error`
- `created_at`
- `updated_at`

### raw_items

- `id`
- `source_id`
- `external_id`
- `url`
- `title`
- `author`
- `published_at`
- `fetched_at`
- `raw_payload`
- `content_hash`

### items

- `id`
- `raw_item_id`
- `canonical_url`
- `title`
- `summary`
- `why_it_matters`
- `category`
- `language`
- `score`
- `sentiment`
- `confidence`
- `created_at`
- `updated_at`

### topics

- `id`
- `title`
- `summary`
- `category`
- `score`
- `first_seen_at`
- `last_seen_at`

### topic_items

- `topic_id`
- `item_id`
- `relation_score`

### digests

- `id`
- `date`
- `title`
- `summary`
- `language`
- `status`
- `created_at`

### digest_items

- `digest_id`
- `item_id`
- `position`
- `section`

### user_preferences

- `id`
- `user_id`
- `include_keywords`
- `exclude_keywords`
- `categories`
- `language`
- `delivery_channels`
- `delivery_time`

## 11. 热度评分草案

评分可以先用规则，不必一开始训练模型。

示例：

```text
score =
  source_weight * 0.30 +
  freshness_score * 0.20 +
  social_signal_score * 0.20 +
  keyword_relevance_score * 0.15 +
  novelty_score * 0.10 +
  llm_importance_score * 0.05
```

其中：

- `source_weight`：官方源、权威媒体、重要社区的基础权重。
- `freshness_score`：发布时间越近越高。
- `social_signal_score`：HN points/comments、GitHub stars today、Product Hunt votes 等。
- `keyword_relevance_score`：是否命中用户关注关键词。
- `novelty_score`：是否是新事件，而不是重复报道。
- `llm_importance_score`：LLM 对影响力的辅助判断。

## 12. MVP 范围建议

### MVP 必做

- RSS 采集。
- Hacker News 采集。
- GitHub repo 趋势采集。
- PostgreSQL/SQLite 入库。
- URL/hash 去重。
- LLM 中文摘要。
- 今日日报页面。
- 条目详情页或详情抽屉。
- 信源配置文件或简单管理页。
- 手动触发采集。
- 每日定时任务。

### MVP 可延后

- 多用户系统。
- 复杂权限。
- Product Hunt API。
- Hugging Face 深度集成。
- embedding 聚类。
- 邮件以外的多渠道推送。
- 音频日报。
- MCP 服务。
- 移动端 App。

## 13. 初步里程碑

### M1：采集闭环

目标：

- 跑通 RSS、HN、GitHub 三类来源。
- 原始数据可以入库。
- 可以手动触发采集。

产出：

- 后端项目结构。
- 数据库 schema。
- 采集器接口。
- 初始 source 配置。

### M2：摘要和排序

目标：

- 对条目进行去重、分类、摘要和评分。
- 生成当天 digest。

产出：

- 摘要任务。
- 分类字段。
- 排序规则。
- digest API。

### M3：前端 Dashboard

目标：

- 用户可以查看今日日报、历史日报和原始条目。
- 支持筛选、搜索和查看详情。

产出：

- Next.js 前端。
- 今日日报页。
- 条目列表页。
- 信源管理页。

### M4：推送和配置

目标：

- 支持每日自动推送。
- 支持用户或系统级偏好配置。

产出：

- Email/RSS 输出。
- 偏好设置。
- 调度和失败日志。

## 14. 风险和注意事项

- 信息源授权：Product Hunt、X、部分媒体网站需要注意 API 条款和商业使用限制。
- 抓取稳定性：网页结构会变化，应优先使用 RSS/API。
- LLM 成本：不应对所有原始条目都调用 LLM，应该先用规则筛选。
- 摘要可靠性：需要保留原文链接和原始摘要，避免用户无法追溯。
- 重复内容：AI 新闻重复转载严重，去重和聚类是关键能力。
- 语言处理：中英文来源都要支持，摘要可统一输出中文。
- 定时任务可靠性：需要记录抓取状态、失败原因和重试次数。
- 冷启动：初期信源质量比数量更重要，应先配置 30-50 个高质量来源，而不是盲目扩到几百个。

## 15. 推荐下一步

建议下一步把本调研转成一份项目 PRD，明确：

- 产品定位。
- 用户画像。
- MVP 页面和接口范围。
- 数据源清单。
- 数据模型。
- 技术选型。
- 2-4 周实现计划。

之后再进入工程初始化：后端 FastAPI、前端 Next.js、数据库 schema、Docker Compose 和第一批采集器。
