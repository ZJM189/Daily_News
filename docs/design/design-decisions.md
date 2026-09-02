# 系统设计决策记录

版本：v0.1

日期：2026-09-02

阶段：系统设计

## 1. 已确认决策

| 序号 | 决策项 | 结论 | 影响 |
| --- | --- | --- | --- |
| 1 | 生产部署形态 | 单台云服务器部署 | MVP 使用 Docker Compose，不直接上 Kubernetes |
| 2 | HTTPS 与反向代理 | 外公网部署必须使用 HTTPS 反向代理 | 推荐 Caddy 或 Nginx 终止 TLS，并转发 Web/API |
| 3 | 外部 API token 维护方式 | 允许管理员在后台录入 | 后端加密保存，前端只展示掩码和配置状态 |
| 4 | Digest 调度时间 | 默认北京时间每天 08:00 | 调度配置可由管理员修改 |
| 5 | Digest 调度时区 | `Asia/Shanghai` | Scheduler 使用明确时区，避免服务器时区差异 |
| 6 | 首个管理员账号 | 使用一次性 `create-admin` 初始化命令 | 不使用固定默认账号，不把初始密码长期留在环境变量 |
| 7 | 首批默认 source | 每类预置 1-3 个最小可用配置 | 通过 seed 脚本导入，管理员后台可继续调整 |
| 8 | 数据保留周期 | raw/log 保留 180 天，核心 item/digest 长期保留 | 通过清理任务控制数据库增长 |
| 9 | 数据库备份周期 | 每日备份一次，默认保留 14 天 | 部署上线阶段落备份脚本和恢复说明 |

## 2. 需要解释的设计点

### 2.1 首个管理员账号是什么意思

因为系统不开放公开注册，并且后续用户只能由管理员创建，所以系统首次部署时会遇到“还没有管理员可以登录”的问题。

因此需要一个 bootstrap 机制创建第一个管理员账号。

确认方案：

- 提供一次性初始化命令，例如 `create-admin`。
- 初始化命令读取管理员邮箱、用户名和密码。
- 创建成功后，后续用户全部通过后台“用户管理”创建。
- 生产环境不使用固定默认账号和默认密码。

## 3. 首批默认 Source 清单是什么意思

“首批默认 Source 清单”不是指系统支持哪些类型，而是指系统初始化后默认预置哪些具体来源、关键词或查询规则。

示例：

| 类型 | 示例配置 | 说明 |
| --- | --- | --- |
| RSS | OpenAI Blog、Anthropic News、Google AI Blog、DeepMind Blog、Meta AI Blog | 以官方博客和高可信来源为主 |
| Hacker News | 查询关键词 `AI`、`LLM`、`agents`、`RAG`、`Claude`、`OpenAI` | 追踪社区讨论热度 |
| GitHub | 查询 topic/keyword：`ai`、`llm`、`agent`、`rag`，并限制 stars、更新时间 | 发现开源项目和工具 |
| arXiv | 分类 `cs.AI`、`cs.CL`、`cs.LG`，关键词 `large language model`、`agent`、`multimodal` | 追踪论文研究 |
| Product Hunt | 主题 `AI`、`Developer Tools`、`Productivity` | 追踪 AI 产品发布 |
| Hugging Face | 模型、数据集、Spaces 的 trending 或关键词查询 | 追踪模型和应用生态 |

已确认开发默认值：

- 每类 source 先预置 1-3 个最小可用配置。
- API token 缺失的 source 保留但状态显示 `missing_token`。
- 默认清单通过 seed 脚本导入，不写死在数据库 migration 中。

## 4. 首批默认 Source Seed

| 类型 | 默认配置 | 初始状态 | 说明 |
| --- | --- | --- | --- |
| RSS | OpenAI Blog | enabled | 官方模型与产品动态 |
| RSS | Anthropic News | enabled | 官方模型与产品动态 |
| RSS | Google AI Blog | enabled | 官方研究与产品动态 |
| Hacker News | `AI OR LLM OR agents OR RAG` | enabled | 社区讨论热点 |
| GitHub | `ai OR llm OR agent OR rag`, stars >= 100, updated <= 30d | missing_token | 开源项目和工具趋势 |
| arXiv | `cs.AI`, `cs.CL`, `cs.LG` | enabled | AI、NLP、机器学习论文 |
| Product Hunt | `AI`, `Developer Tools` | missing_token | AI 产品发布 |
| Hugging Face | trending models, datasets, spaces | missing_token | 模型、数据集和 Spaces 趋势 |

## 5. 当前无阻塞项

当前系统设计已可进入开发阶段。后续如果需要更精细的 source 名单、保留周期或备份策略，可以作为配置迭代，不阻塞 MVP 开发。
