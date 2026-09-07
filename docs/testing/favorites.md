# 收藏功能测试

## 后端

常规测试：在 `api` 中执行 `.venv/bin/pytest -q`。PostgreSQL 集成测试默认跳过，需先准备独立数据库并迁移：

```bash
export DATABASE_URL='postgresql+psycopg://user:password@localhost/daily_news_favorites_test'
export FAVORITES_TEST_DATABASE_URL="$DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/pytest -q
```

集成测试通过事务回滚隔离，覆盖根目录、重复收藏、目录 CRUD、移动、删除保留内容、跨用户访问、批量状态、搜索排序分页、参数校验及数据库唯一/归属约束。迁移回退验证只在独立空测试库中执行。

## 浏览器 E2E

使用独立数据库，库名必须以 `_test` 结尾。测试 API 不启动采集器或调度器，只准备两名测试用户和示例条目：

```bash
# api 目录，沿用上面的测试数据库变量
export E2E_PASSWORD='choose-a-test-only-password'
PYTHONPATH=. .venv/bin/python tests/serve_favorites_e2e.py
```

测试 API 监听 `127.0.0.1:8100`。另一个终端运行前端：

```bash
# web 目录
API_INTERNAL_BASE_URL=http://127.0.0.1:8100 npm run dev -- --hostname 127.0.0.1 --port 3100
```

运行浏览器测试：

```bash
# web 目录，E2E_PASSWORD 必须与测试 API 相同
npx playwright install chromium
E2E_PASSWORD='choose-a-test-only-password' npm run test:e2e
```

每次完整重跑前重启测试 API，以重置测试用户收藏。测试分别使用桌面和 Pixel 7 视口，覆盖登录、根目录收藏与撤销、列表/详情状态同步、目录创建重命名删除、移动、关注流收藏、内联建目录、模拟保存失败和重试、搜索、取消收藏及刷新持久化。截图、失败跟踪保存在 `web/test-results/`，不提交 Git。
