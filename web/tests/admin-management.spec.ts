import { expect, test, type Page } from "@playwright/test";

const adminUser = {
  id: "admin-1",
  username: "admin",
  email: "admin@example.com",
  display_name: "系统管理员",
  role: "admin",
  status: "active"
};

const providers = [
  {
    id: "provider-1",
    name: "Primary OpenAI",
    type: "openai_compatible",
    base_url: "https://api.openai.com/v1",
    model: "gpt-5.2",
    api_key_masked: "sk-...9x2",
    timeout_seconds: 60,
    retry_count: 2,
    enabled: true,
    is_default: true,
    last_test_at: null,
    last_test_status: "success",
    last_test_error: null,
    created_at: "2026-09-01T08:00:00+08:00",
    updated_at: "2026-09-10T08:00:00+08:00"
  },
  {
    id: "provider-2",
    name: "Backup Gateway",
    type: "openai_compatible",
    base_url: "https://gateway.example.com/v1",
    model: "qwen-max",
    api_key_masked: null,
    timeout_seconds: 90,
    retry_count: 3,
    enabled: false,
    is_default: false,
    last_test_at: null,
    last_test_status: null,
    last_test_error: null,
    created_at: "2026-09-02T08:00:00+08:00",
    updated_at: "2026-09-09T08:00:00+08:00"
  }
];

const users = [
  { ...adminUser, last_login_at: "2026-09-11T09:30:00+08:00" },
  { id: "user-2", username: "editor", email: "editor@example.com", display_name: "内容编辑", role: "user", status: "active", last_login_at: "2026-09-10T17:00:00+08:00" },
  { id: "user-3", username: "reader", email: null, display_name: "只读用户", role: "user", status: "disabled", last_login_at: null }
];

const schedulerConfigs = [
  { id: "schedule-1", job_type: "daily_pipeline", name: "每日 AI 简报", cron_expression: "0 8 * * *", timezone: "Asia/Shanghai", enabled: true, params: {}, created_by: null, updated_by: null, created_at: "2026-09-01T08:00:00+08:00", updated_at: "2026-09-10T08:00:00+08:00" },
  { id: "schedule-2", job_type: "collect", name: "午间增量采集", cron_expression: "0 12 * * 1-5", timezone: "Asia/Shanghai", enabled: false, params: {}, created_by: null, updated_by: null, created_at: "2026-09-01T08:00:00+08:00", updated_at: "2026-09-02T08:00:00+08:00" }
];

const jobs = [
  { id: "job-running-0001", job_type: "collect", trigger_type: "manual", status: "running", source_id: null, parent_job_run_id: null, created_by: "admin-1", params: {}, total_count: 120, success_count: 72, duplicate_count: 48, failure_count: 0, error_message: null, error_detail: null, started_at: "2026-09-11T09:50:00+08:00", ended_at: null, created_at: "2026-09-11T09:50:00+08:00" },
  { id: "job-success-0002", job_type: "summarize", trigger_type: "scheduled", status: "success", source_id: null, parent_job_run_id: null, created_by: null, params: {}, total_count: 30, success_count: 30, duplicate_count: 0, failure_count: 0, error_message: null, error_detail: null, started_at: "2026-09-11T08:04:00+08:00", ended_at: "2026-09-11T08:06:10+08:00", created_at: "2026-09-11T08:04:00+08:00" },
  { id: "job-failed-0003", job_type: "normalize", trigger_type: "manual", status: "failed", source_id: null, parent_job_run_id: null, created_by: "admin-1", params: {}, total_count: 12, success_count: 9, duplicate_count: 0, failure_count: 3, error_message: "3 条内容缺少可解析的正文，任务已停止。", error_detail: null, started_at: "2026-09-10T18:00:00+08:00", ended_at: "2026-09-10T18:00:24+08:00", created_at: "2026-09-10T18:00:00+08:00" }
];

const sources = [
  { id: "source-1", name: "OpenAI Blog", type: "rss", status: "enabled", url: "https://openai.com/blog/rss.xml", query_config: { limit: 30 }, credential_id: null, credential_env_key: null, weight: 90, language: "en", last_fetched_at: "2026-09-11T08:00:00+08:00", last_success_at: "2026-09-11T08:00:00+08:00", last_error: null, created_at: "2026-09-01T08:00:00+08:00", updated_at: "2026-09-11T08:00:00+08:00" },
  { id: "source-2", name: "GitHub Trending", type: "github", status: "disabled", url: "https://github.com/trending", query_config: { query: "AI agent", limit: 20 }, credential_id: "credential-1", credential_env_key: null, weight: 75, language: "en", last_fetched_at: null, last_success_at: null, last_error: null, created_at: "2026-09-01T08:00:00+08:00", updated_at: "2026-09-10T08:00:00+08:00" }
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, json: { data: adminUser } }));
  await page.route("**/api/v1/favorites/folders", (route) => route.fulfill({ status: 200, json: { data: { folders: [], total: 0, root_count: 0, categories: [], source_types: [] } } }));
  await page.route("**/api/v1/admin/llm-providers**", (route) => route.fulfill({ status: 200, json: { data: providers } }));
  await page.route("**/api/v1/admin/users**", (route) => route.fulfill({ status: 200, json: { data: users } }));
  await page.route("**/api/v1/admin/scheduler/configs**", (route) => route.fulfill({ status: 200, json: { data: schedulerConfigs } }));
  await page.route("**/api/v1/admin/jobs?**", (route) => route.fulfill({ status: 200, json: { data: jobs, meta: { page: 1, page_size: 20, total: 3 } } }));
  await page.route("**/api/v1/admin/sources**", (route) => route.fulfill({ status: 200, json: { data: sources } }));
  await page.route("**/api/v1/admin/source-credentials**", (route) => route.fulfill({ status: 200, json: { data: [{ id: "credential-1", name: "GitHub Token", source_type: "github", secret_masked: "ghp_...31f", status: "active", last_test_at: null, last_test_status: "success", last_test_error: null, created_at: "2026-09-01T08:00:00+08:00", updated_at: "2026-09-10T08:00:00+08:00" }] } }));
});

test("admin management surfaces share one visual system and working drawers", async ({ page }, testInfo) => {
  await page.goto("/admin/sources");
  await expect(page.getByRole("heading", { name: "来源管理" })).toBeVisible();
  await expect(page.getByRole("button", { name: "打开信息库智能助手" })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "主工作区快捷导航" })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("source-reference.png"), fullPage: true });
  await expectNoPageOverflow(page);

  await page.goto("/admin/llm");
  await expect(page.getByRole("heading", { name: "LLM 设置" })).toBeVisible();
  await expect(page.getByRole("table").getByText("Primary OpenAI")).toBeVisible();
  await page.getByRole("button", { name: "新增 Provider" }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "新增 Provider" })).toBeVisible();
  await page.getByRole("button", { name: "关闭" }).click();
  await page.screenshot({ path: testInfo.outputPath("llm-management.png"), fullPage: true });
  await expectNoPageOverflow(page);

  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "用户管理" })).toBeVisible();
  await page.getByPlaceholder("搜索用户名、显示名或邮箱").fill("只读");
  await expect(page.getByText("只读用户")).toBeVisible();
  await expect(page.getByText("内容编辑")).toHaveCount(0);
  await page.getByPlaceholder("搜索用户名、显示名或邮箱").fill("");
  await page.getByRole("button", { name: "重置 reader 的密码" }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "重置密码" })).toBeVisible();
  await page.getByRole("button", { name: "关闭" }).click();
  await page.locator(".managementTableWrap").evaluate((element) => {
    element.scrollLeft = 0;
  });
  await page.screenshot({ path: testInfo.outputPath("user-management.png"), fullPage: true });
  await expectNoPageOverflow(page);

  await page.goto("/admin/scheduler");
  await expect(page.getByRole("heading", { name: "调度配置" })).toBeVisible();
  await page.getByRole("button", { name: "编辑 每日 AI 简报" }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "编辑调度" })).toBeVisible();
  await page.getByRole("button", { name: "保存配置" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("scheduler-management.png"), fullPage: true });
  await expectNoPageOverflow(page);

  await page.goto("/admin/jobs");
  await expect(page.getByRole("heading", { name: "任务日志" })).toBeVisible();
  await expect(page.getByText("简报流水线")).toBeVisible();
  await expect(page.getByText("拉取 120 条", { exact: true })).toBeVisible();
  await expect(page.getByText("新增 72 · 重复 48 · 失败 0", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "单步任务" }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "执行单步任务" })).toBeVisible();
  await page.getByRole("button", { name: "关闭" }).click();
  await page.screenshot({ path: testInfo.outputPath("job-management.png"), fullPage: true });
  await expectNoPageOverflow(page);
});

async function expectNoPageOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
}
