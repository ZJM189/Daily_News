import { expect, test } from "@playwright/test";

const todayDigest = {
  data: {
    id: "digest-public-test",
    digest_date: "2026-09-09",
    version: 3,
    status: "published",
    title: "今日 AI 情报简报",
    overview_zh:
      "今天的公开简报聚合了研究论文、开源项目和产品更新，适合未登录用户快速了解 AI 动态。",
    stats: {
      topic_count: 2,
      item_count: 2,
      source_count: 3
    },
    job_run_id: null,
    generated_at: "2026-09-09T08:10:00+08:00",
    published_at: "2026-09-09T08:30:00+08:00",
    created_at: "2026-09-09T08:10:00+08:00",
    items: [
      {
        id: "digest-item-1",
        item_id: "item-1",
        topic_id: "topic-1",
        item_type: "topic",
        rank: 1,
        score_snapshot: 94.25,
        title_snapshot: "开源 Agent 框架加入可观测工具",
        summary_snapshot_zh: "项目新增调用链和工具执行记录，便于排查智能查询链路。",
        importance_snapshot_zh: "这会提升企业把 Agent 接到私有信息库时的可控性。",
        category_snapshot: "open_source",
        source_snapshot: {
          primary_source_name: "GitHub",
          primary_url: "https://github.com/example/agent",
          source_count: 2
        },
        created_at: "2026-09-09T08:10:00+08:00"
      },
      {
        id: "digest-item-2",
        item_id: "item-2",
        topic_id: "topic-2",
        item_type: "topic",
        rank: 2,
        score_snapshot: 88.5,
        title_snapshot: "多模态检索论文刷新长上下文评测",
        summary_snapshot_zh: "论文对比了多种检索策略在长文档问答中的表现。",
        importance_snapshot_zh: "结果可用于优化信息库自然语言查询的召回策略。",
        category_snapshot: "research_paper",
        source_snapshot: {
          primary_source_type: "arxiv",
          primary_url: "https://arxiv.org/abs/2609.00001",
          source_count: 1
        },
        created_at: "2026-09-09T08:10:00+08:00"
      }
    ]
  }
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 401,
      json: { detail: "Not authenticated" }
    });
  });
  await page.route("**/api/v1/digests/today", async (route) => {
    await route.fulfill({ status: 200, json: todayDigest });
  });
});

test("anonymous users can read public today digest without private widgets", async ({
  page
}, testInfo) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "今日 AI 情报简报" })).toBeVisible();
  await expect(page.getByText("今天的公开简报聚合了研究论文")).toBeVisible();
  await expect(
    page.getByRole("banner").getByRole("link", { name: "登录进入工作区" })
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "打开信息库智能助手" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "收藏", exact: true })).toHaveCount(0);

  await page.goto("/today");

  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByRole("heading", { name: "今日 AI 情报简报" })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("public-briefing.png"),
    fullPage: true
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
  ).toBeTruthy();
});

test("anonymous private routes redirect to login with next path", async ({ page }) => {
  await page.goto("/library");

  await expect(page).toHaveURL(/\/login\?next=%2Flibrary$/);
  await expect(page.getByRole("heading", { name: "登录工作区" })).toBeVisible();
});

test("authenticated users keep the workspace shell on today page", async ({ page }) => {
  await page.unroute("**/api/v1/auth/me");
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          id: "user-1",
          username: "reader",
          email: "reader@example.com",
          display_name: "Reader",
          role: "user",
          status: "active"
        }
      }
    });
  });
  await page.route("**/api/v1/favorites/folders", async (route) => {
    await route.fulfill({
      status: 200,
      json: { data: { folders: [], total: 0, root_count: 0, categories: [], source_types: [] } }
    });
  });

  await page.goto("/today");

  await expect(page.getByRole("button", { name: "打开信息库智能助手" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "今日 AI 情报简报" })).toBeVisible();
  await expect(page.getByRole("link", { name: "登录进入工作区" })).toHaveCount(0);
});
