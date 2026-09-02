# AI 热点信息每日汇总系统业务流程图

版本：v0.2

日期：2026-09-01

关联文档：

- [需求说明书](requirements-specification.md)

## 1. 用户查看 Web 看板流程

```mermaid
flowchart TD
    A[用户打开 Web 站点] --> B{是否已登录}
    B -- 否 --> C[进入登录页]
    C --> D[输入账号密码]
    D --> E{认证是否成功}
    E -- 否 --> F[显示登录失败提示]
    F --> C
    E -- 是 --> G[进入今日简报页面]
    B -- 是 --> G
    G --> H{选择视图}
    H -- 系统精选 --> I[查看今日重点和分类摘要]
    H -- 我的关注 --> I2[查看个性化排序内容]
    I2 --> I
    I --> J{是否筛选或搜索}
    J -- 是 --> K[按分类/来源/关键词筛选]
    K --> I
    J -- 否 --> L{是否查看详情}
    L -- 是 --> M[打开详情抽屉]
    M --> N[查看摘要/为什么重要/原文链接/专题聚合/相关来源]
    N --> I
    L -- 否 --> O{是否提交反馈}
    O -- 是 --> P[记录多看类似/少看类似/屏蔽来源]
    P --> I
    O -- 否 --> Q[结束浏览]
```

## 2. 管理员维护信息源流程

```mermaid
flowchart TD
    A[管理员登录] --> B[进入来源管理页]
    B --> C{操作类型}
    C -- 新增 --> D[填写 source 名称/类型/URL/权重]
    C -- 编辑 --> E[修改 source 配置]
    C -- 启用/禁用 --> F[切换启用状态]
    D --> G[保存配置]
    E --> G
    F --> G
    G --> H{是否手动测试抓取}
    H -- 否 --> I[返回来源列表]
    H -- 是 --> J[触发单 source 抓取]
    J --> K{抓取是否成功}
    K -- 是 --> L[记录成功状态和最近抓取时间]
    K -- 否 --> M[记录失败状态和错误信息]
    L --> I
    M --> I
```

## 3. 系统自动生成每日 Digest 流程

```mermaid
flowchart TD
    A[定时任务触发] --> B[读取启用 source 列表]
    B --> C[并发或分批执行 collectors]
    C --> D[保存 raw payload]
    D --> E[标准化为统一 item]
    E --> F[URL/canonical URL/external id/hash 去重]
    F --> G[轻量 topic 聚合]
    G --> H[计算基础 score]
    H --> I[筛选高分候选条目]
    I --> J[调用默认 LLM provider]
    J --> K{摘要是否成功}
    K -- 是 --> L[保存中文摘要/分类/标签/为什么重要]
    K -- 否 --> M{是否有备用 provider}
    M -- 是 --> N[调用备用 provider]
    N --> K
    M -- 否 --> O[使用原始摘要兜底并标记失败]
    L --> P[生成每日 digest]
    O --> P
    P --> Q[自动发布到 Web 看板]
    Q --> R[记录 job run 状态]
```

## 4. 条目处理状态流

```mermaid
stateDiagram-v2
    [*] --> collected
    collected --> normalized
    normalized --> deduped
    deduped --> ranked
    ranked --> summarized: 高分候选
    ranked --> archived: 低分未入选
    summarized --> selected: 入选 digest
    summarized --> failed: 摘要失败且无兜底
    selected --> published
    failed --> retryable
    retryable --> summarized
```

## 5. 角色权限流程

```mermaid
flowchart TD
    A[请求进入系统] --> B{是否登录}
    B -- 否 --> C[拒绝访问并跳转登录页]
    B -- 是 --> D{访问资源类型}
    D -- 普通看板 --> E[允许 user/admin 访问]
    D -- 管理资源 --> F{是否 admin}
    F -- 是 --> G[允许访问管理功能]
    F -- 否 --> H[拒绝访问]
```

## 6. 管理员创建用户流程

```mermaid
flowchart TD
    A[管理员进入用户管理页] --> B[点击新增用户]
    B --> C[填写邮箱/用户名/初始密码/角色]
    C --> D{表单校验是否通过}
    D -- 否 --> E[展示校验错误]
    E --> C
    D -- 是 --> F[创建用户并加密保存密码]
    F --> G[用户出现在用户列表]
    G --> H[管理员将账号信息提供给用户]
    H --> I[用户使用账号登录 Web 看板]
```

## 7. 用户配置我的关注流程

```mermaid
flowchart TD
    A[用户进入我的关注页] --> B[配置关注关键词/关注分类/关注来源类型]
    B --> C[配置排除关键词/屏蔽来源]
    C --> D[查看保存搜索和反馈记录]
    D --> E[保存设置]
    E --> F[系统在当前用户视图中应用规则]
    F --> G[硬过滤排除词和屏蔽来源]
    F --> H[软加权关注词/分类/来源类型/反馈]
```

## 8. 用户站内搜索并保存流程

```mermaid
flowchart TD
    A[用户进入信息库] --> B[输入关键词并选择筛选条件]
    B --> C[系统检索已采集入库内容]
    C --> D{搜索结果是否有用}
    D -- 否 --> E[调整搜索条件]
    E --> B
    D -- 是 --> F[点击保存搜索]
    F --> G[填写规则名称]
    G --> H[保存为我的关注规则]
    H --> I[后续在我的关注视图中生效]
```

## 9. 管理员手动重跑流程

```mermaid
flowchart TD
    A[管理员进入任务页] --> B[选择失败任务或新任务]
    B --> C{任务类型}
    C -- 采集 --> D[触发 collect job]
    C -- 摘要 --> E[触发 summarize job]
    C -- Digest --> F[触发 digest generate job]
    D --> G[记录新的 job run]
    E --> G
    F --> G
    G --> H{执行成功}
    H -- 是 --> I[更新状态为 success]
    H -- 否 --> J[更新状态为 failed 并保存错误]
```
