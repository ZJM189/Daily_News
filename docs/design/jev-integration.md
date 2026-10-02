# Jev 决策模型集成说明

版本：v1.0

日期：2026-10-01

## 1. 集成目标

Daily News 保留现有 OpenAI-compatible 模型作为文本生成模型，新增 TypeSafe Jev 作为结构化决策模型。

职责边界：

| 能力 | 负责组件 |
| --- | --- |
| 采集、标准化、时间和来源规则 | Daily News 规则代码 |
| 意图分类、AI 相关性、质量、重要性、提示词注入判断 | Jev |
| 中文摘要、专题标题、专题摘要、自然语言回答 | OpenAI-compatible LLM / GLM |

Jev 不直接生成日报文字，也不替换 DeepAgents 的查询 Agent。

## 2. 代码结构

```text
api/app/application/decision/
├── dtos.py       # provider-neutral decision DTO
├── ports.py      # StructuredDecisionClient port
├── item.py       # 新闻决策问题和结果解析
└── scoring.py    # 规则分与 Jev 分的组合策略

api/app/infrastructure/typesafe_jev/
├── client.py     # TypeSafe HTTP Adapter、响应归一化、重试
└── factory.py    # 配置到客户端的 Factory
```

使用的设计模式：

- Port/Adapter：应用层只依赖 `StructuredDecisionClient`，不依赖 TypeSafe SDK 或 HTTP。
- Factory：`create_jev_client()` 集中处理配置、启用开关和 Key 缺失。
- Strategy/Composite：`score_item()` 保持纯规则策略，`compose_item_score()` 组合可选 Jev 策略。
- Fallback：Jev 不可用时，排名回退规则分，信息库意图分类回退现有 OpenAI-compatible 分类器。

## 3. 处理流程

### 3.1 新闻排名

```text
normalized item
  -> score_item()               # 确定性规则分
  -> ItemDecisionService        # Jev Choice/Score/Noul
  -> compose_item_score()       # 综合分
  -> items.score_breakdown      # 保存可解释明细
```

综合分默认公式：

```text
jev_score =
  ai_relevance * 40
  + importance * 0.35
  + quality * 0.25

final_score =
  rule_score * (1 - JEV_SCORE_WEIGHT)
  + jev_score * JEV_SCORE_WEIGHT
```

默认 `JEV_SCORE_WEIGHT=0.3`。提示词注入概率达到 `0.5` 时，条目最终分数置为 `0`，避免进入摘要和日报。

为控制外部请求量，单次排名只对规则分最高的 `JEV_ITEM_LIMIT` 条内容调用 Jev，其余内容直接使用规则分。

### 3.2 信息库意图

当前顺序为：

```text
硬规则
  -> Jev 意图分类
  -> OpenAI-compatible fallback
  -> 保守拒绝
```

Jev 判断：

- 是否允许进入信息库；
- 用户意图；
- 是否存在提示词注入。

硬规则仍然优先，Jev 不能绕过代码中的代码请求、外部联网请求和提示词注入拦截。

## 4. 配置

`.env.example` 提供模板：

```dotenv
JEV_ENABLED=false
JEV_API_KEY=
JEV_BASE_URL=https://api.typesafe.ai
JEV_MODEL=jev-1.13.0
JEV_TIMEOUT_SECONDS=30
JEV_RETRY_COUNT=3
JEV_SCORE_WEIGHT=0.3
JEV_ITEM_LIMIT=200
JEV_INTENT_ENABLED=true
JEV_ITEM_DECISION_ENABLED=true
```

真实 Key 只能放在部署服务器的 `.env` 或 Secret Manager 中，不能写入代码、前端或文档。

## 5. 失败和重试

客户端对网络错误、超时、408、429、500、502、503、504 和 529 执行有限重试。

- 默认重试次数为 3；
- 优先使用 `Retry-After`；
- 没有该响应头时使用指数退避和随机抖动；
- Jev 最终失败时排名回退到规则分；
- 意图分类最终失败时回退到现有 OpenAI-compatible 分类器；
- 不把 Jev 失败标记为整个采集或排名任务失败。

## 6. 自测

本地测试：

```bash
api/.venv/bin/ruff check api/app api/tests
api/.venv/bin/pytest -q api/tests
```

真实接口探测：

```bash
PYTHONPATH=api api/.venv/bin/python -c \
  'from app.infrastructure.typesafe_jev.factory import create_jev_client
   from app.infrastructure.config import get_settings
   print(create_jev_client(get_settings()) is not None)'
```

真实接口测试只能在后端环境执行，Key 不应出现在命令参数、日志或测试输出中。

## 7. 后续演进

当前版本先复用 `items.score_breakdown` 保存决策明细，不增加迁移。

后续需要大规模重算、审计和模型对比时，再增加 `decision_evaluations` 表，保存：

```text
task
object_type
object_id
model
question_version
answers_json
confidence
latency_ms
status
error_message
created_at
```

