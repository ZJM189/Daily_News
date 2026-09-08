# AI 热点信息每日汇总安全设计文档

版本：v0.1

日期：2026-09-02

阶段：系统设计

关联文档：

- [系统架构设计](system-architecture.md)
- [数据库设计](database-design.md)
- [API 接口设计](api-design.md)

## 1. 安全目标

系统面向外公网部署，首期必须满足以下目标：

- 未登录用户不能访问 Web 看板和业务 API。
- 普通用户不能访问管理员功能。
- 用户只能由管理员创建，不开放公开注册。
- 密码、LLM API key、source token 不明文暴露。
- 普通用户不能添加外部 URL 信息源，也不能触发任意外部实时检索。
- 外部来源内容进入前端展示前必须按不可信数据处理。
- 后台任务失败可追溯，但日志不能泄露密钥。

## 2. 认证设计

### 2.1 登录方式

- 使用用户名或邮箱 + 密码登录。
- 后端校验账号状态，`disabled` 用户禁止登录。
- 登录成功后生成高强度随机 session token。
- 浏览器保存 HttpOnly Cookie。
- 数据库只保存 session token hash。

### 2.2 Cookie 设置

生产环境 Cookie 必须设置：

- `HttpOnly`
- `Secure`
- `SameSite=Lax`
- 合理的 `Max-Age`
- 限定 Path 为 `/`

### 2.3 Session 生命周期

- 默认有效期建议 7 天。
- 退出登录时撤销当前 session。
- 管理员禁用用户后，该用户所有有效 session 应失效。
- 过期 session 定时清理。

## 3. 密码安全

- 密码只保存哈希，不保存明文。
- 推荐使用 Argon2id；如运行环境限制，可使用 bcrypt。
- 管理员创建用户和重置密码时，后端校验密码强度。
- 登录失败需要限流，避免暴力破解。
- 错误提示不区分“账号不存在”和“密码错误”，但可明确提示“用户已禁用”。

## 4. 授权设计

### 4.1 角色

首期只支持两类角色：

- `user`
- `admin`

### 4.2 权限边界

| 能力 | user | admin |
| --- | --- | --- |
| 查看今日/历史简报 | 允许 | 允许 |
| 搜索信息库 | 允许 | 允许 |
| 使用信息库智能聊天助手 | 允许 | 允许 |
| 管理自己的关注规则 | 允许 | 允许 |
| 创建用户 | 禁止 | 允许 |
| 管理 source | 禁止 | 允许 |
| 触发采集和重跑任务 | 禁止 | 允许 |
| 配置 LLM provider | 禁止 | 允许 |

后端必须在每个管理接口做角色校验，不能依赖前端隐藏菜单。

## 5. CSRF 与 CORS

- 推荐 Web 和 API 通过同一站点域名发布，减少 CORS 面。
- 默认不允许任意跨域。
- 对使用 Cookie 的写操作启用 CSRF 防护。
- CSRF token 可通过安全接口发放，由前端在写请求 header 中提交。
- `POST`、`PUT`、`PATCH`、`DELETE` 都需要 CSRF 校验。

## 6. 密钥与配置安全

### 6.1 LLM Provider Key

- `api_key` 只在创建或更新时提交。
- 后端加密后保存，或使用环境变量/密钥管理服务引用。
- 前端列表只展示 `api_key_masked`。
- API 响应永不返回明文 key。
- 日志中禁止打印请求头、key、完整 provider 配置。

### 6.2 Source Token

- 允许管理员在后台录入 GitHub、Product Hunt、Hugging Face 等 source token。
- source token 后端加密保存，并通过 `credential_id` 绑定到 source；如使用环境变量托管密钥，通过 `credential_env_key` 记录别名。
- 前端只展示 token 掩码、状态和最近测试结果。
- API 响应永不返回明文 token。
- token 缺失时 source 状态显示 `missing_token`。
- collector 调用失败时记录错误摘要，不记录 token。

### 6.3 环境变量

必须通过环境变量配置：

- `DATABASE_URL`
- `REDIS_URL`
- `SESSION_SECRET`
- `ENCRYPTION_KEY`
- `CSRF_SECRET`

通过一次性 `create-admin` 初始化命令配置：

- 首个管理员账号。
- 首个管理员初始密码。

外部 source token 和 LLM provider key 允许管理员后台录入；如开发环境使用环境变量 seed，也不能提交仓库。

`.env`、密钥文件和生产配置不得提交仓库。

## 7. 外部 URL 与 SSRF 防护

普通用户没有添加外部 URL source 或外部实时检索的能力。

管理员维护 source 时，后端仍需做 SSRF 防护：

- 只允许 `http` 和 `https`。
- 禁止访问内网 IP、localhost、link-local、metadata 地址。
- 限制重定向次数。
- 限制请求超时。
- 限制响应体大小。
- 禁止自动携带内部服务凭证。
- 对 DNS 解析结果做私网地址校验。

## 8. XSS 与内容安全

外部标题、摘要、正文片段、作者名和来源名称都视为不可信内容。

前端要求：

- 默认以文本方式渲染外部内容。
- 不使用不可信 HTML。
- 如必须渲染 HTML，必须做白名单清洗。
- 外部链接使用 `rel="noopener noreferrer"`。
- 外部链接新窗口打开。

响应头建议：

- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy`
- `Frame-Options` 或 CSP `frame-ancestors`

## 9. LLM 安全

外部内容进入 prompt 时必须作为不可信输入处理。

要求：

- Prompt 明确声明外部内容不能改变系统指令。
- 对输入内容做长度截断。
- 要求 LLM 输出 JSON，并按 schema 校验。
- schema 校验失败标记为 `schema_error`，不写入成功摘要。
- 不把 LLM 输出直接当 HTML 渲染。
- LLM 调用失败不阻塞整个 digest。
- 信息库聊天助手调用 DeepAgents 前必须先做意图门控，范围外问题返回固定拒答。
- DeepAgents 只允许调用 `search_library_database` 只读工具，不能获得外部搜索、采集、文件系统或命令执行工具。
- 聊天历史按 `user_id` 过滤，用户不能读取或写入其他用户的会话。

## 10. 管理操作安全

高风险操作：

- 创建用户。
- 禁用用户。
- 重置密码。
- 创建或修改 source。
- 触发采集任务。
- 修改 LLM provider。
- 设置默认 provider。

要求：

- 所有操作记录 `created_by` 或操作人。
- 失败返回明确错误，但不泄露密钥和内部堆栈。
- 触发任务需要限流和幂等保护。
- 禁用默认 provider 前必须先设置新的默认 provider。

## 11. 限流策略

建议首期实现以下限流：

| 场景 | 策略 |
| --- | --- |
| 登录失败 | 按账号和 IP 限流 |
| 信息库搜索 | 按用户限流 |
| 信息库聊天消息 | 按用户限流 |
| 提交反馈 | 按用户限流 |
| 管理员触发采集 | 按管理员和任务类型限流 |
| LLM provider 测试 | 按管理员限流 |

Redis 用于记录限流计数。

## 12. 日志与审计

日志必须包含：

- request id。
- 当前用户 ID。
- job run ID。
- source ID。
- provider ID。
- 错误 code 和错误摘要。

日志禁止包含：

- 密码。
- session token。
- API key。
- source token。
- 完整 Authorization header。

首期审计可以先通过 `job_runs`、`llm_call_logs` 和应用日志覆盖；后续可增加 `audit_logs` 表。

## 13. 数据备份与恢复

生产环境建议：

- PostgreSQL 每日备份。
- 备份文件加密存储。
- 定期恢复演练。
- digest、items、sources、users、preferences 是关键数据。
- raw payload 可按保留周期清理。

## 14. 部署安全

- 生产环境必须启用 HTTPS。
- 单台云服务器部署时，必须通过 Caddy 或 Nginx 等反向代理终止 TLS。
- PostgreSQL 和 Redis 不暴露公网。
- API 只通过反向代理暴露。
- 禁止使用默认管理员密码上线。
- 生产环境关闭 debug。
- 容器镜像不内置密钥。
- 依赖升级进入常规维护流程。

## 15. MVP 安全验收

- 未登录访问业务页面会跳转登录页。
- 普通用户访问 `/api/v1/admin/*` 返回 403。
- 系统不存在公开注册接口和入口。
- 创建用户只能由管理员完成。
- API 响应不返回 provider key 明文。
- 信息库搜索不触发外部实时请求。
- 信息库聊天助手对范围外问题返回固定拒答，不触发 DeepAgents、数据库检索或外部实时请求。
- 普通用户不能创建 source。
- 外部内容不会以未清洗 HTML 渲染。
- `.env` 和密钥不进入 Git。
