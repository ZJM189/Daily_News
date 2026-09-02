# 系统设计文档

版本：v0.1

日期：2026-09-02

阶段：系统设计

本目录承接需求分析和产品设计，输出研发实现前需要确认的技术方案。

## 文档清单

- [系统架构设计文档](system-architecture.md)
- [后端 DDD 设计文档](backend-ddd-design.md)
- [系统设计决策记录](design-decisions.md)
- [数据库设计文档](database-design.md)
- [API 接口文档](api-design.md)
- [安全设计文档](security-design.md)

## 设计边界

- 本阶段定义技术选型、服务边界、数据结构、接口契约和安全策略。
- 本阶段不编写业务代码。
- 前端视觉细节和组件实现进入开发阶段处理。
- 部署脚本、CI/CD 和运维手册进入部署上线阶段细化。

## 关键约束

- 生产环境采用单台云服务器部署，外公网访问必须通过 HTTPS 反向代理。
- 外公网部署，必须前置认证、权限和密钥保护。
- 后端采用 DDD 风格的模块化单体架构，按 bounded context 和分层依赖组织代码。
- 首期即支持多用户，但只区分 `user` 和 `admin` 两类角色。
- 不开放公开注册，用户只能由管理员创建。
- 普通用户不能添加外部 URL 信息源，也不能触发任意外部实时检索。
- 首期数据源支持 RSS、Hacker News、GitHub、arXiv、Product Hunt、Hugging Face。
- 外部 API token 允许管理员在后台录入，后端加密保存，前端只展示掩码。
- Digest 默认北京时间每天 08:00 生成，调度时间可配置。
- 摘要输出为中文。
- LLM 通过统一 provider 抽象接入，首期优先支持 OpenAI-compatible API。
