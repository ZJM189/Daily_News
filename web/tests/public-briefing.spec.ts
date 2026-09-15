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

const previousDigest = {
  data: {
    ...todayDigest.data,
    id: "digest-public-previous-test",
    digest_date: "2026-09-08",
    title: "上一期 AI 情报简报",
    overview_zh: "这是用户选择日期后加载的上一期公开 AI 简报。"
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
  await page.route("**/api/v1/digests/public/2026-09-08", async (route) => {
    await route.fulfill({ status: 200, json: previousDigest });
  });
});

test("anonymous users can read public today digest without private widgets", async ({
  page
}, testInfo) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "今日 AI 情报简报" })).toBeVisible();
  await expect(page.getByText("今天的公开简报聚合了研究论文")).toBeVisible();
  const datePicker = page.getByLabel("选择简报日期");
  await expect(datePicker).toBeVisible();
  await page.locator(".publicDatePicker").click();
  await expect(datePicker).toBeFocused();
  await expect(datePicker).toHaveValue("2026-09-09");
  await expect(page.locator(".publicDatePickerLabel")).toHaveCSS(
    "font-size",
    testInfo.project.name === "mobile" ? "17px" : "18px"
  );
  await datePicker.fill("2026-09-08");
  await expect(page.getByRole("heading", { name: "上一期 AI 情报简报" })).toBeVisible();
  await expect(page.getByText("这是用户选择日期后加载的上一期公开 AI 简报。")).toBeVisible();
  await expect(datePicker).toHaveValue("2026-09-08");
  await expect(page.getByText("浏览专题", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "模型公司", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "全部", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "开源项目", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "社区动态", exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "多模态检索论文刷新长上下文评测" })).toBeVisible();
  const publicDigestNav = page.locator(".publicNav a");
  await expect(publicDigestNav).toHaveText("每日 AI 简报");
  await expect(publicDigestNav).toBeVisible();
  await expect(publicDigestNav).toHaveCSS("font-size", "22px");
  await expect(page.locator(".radarMark")).toHaveCSS("width", "34px");
  await expect(page.locator(".radarMark")).toHaveCSS("border-radius", "50%");
  await expect(page.locator(".radarMarkBlip")).toHaveCSS("animation-name", "publicNavRadarBlip");
  await expect
    .poll(() =>
      page.locator(".radarMark").evaluate((element) =>
        getComputedStyle(element, "::before").animationName
      )
    )
    .toBe("publicNavRadarSweep");
  await expect(
    page.getByRole("banner").getByRole("link", { name: "登录进入工作区" })
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "打开信息库智能助手" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "收藏", exact: true })).toHaveCount(0);
  await expect(page.locator(".publicRadar")).toHaveCount(0);
  await expect(page.getByText("分数 94.25")).toHaveCount(0);

  await page.goto("/today");

  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByRole("heading", { name: "今日 AI 情报简报" })).toBeVisible();
  await expect(page.getByLabel("本期简报概况")).toContainText("2 个专题");
  await expect(page.getByLabel("本期简报概况")).toContainText("3 个来源");

  const firstItem = page.locator("#public-digest-item-1");
  const firstTitle = firstItem.getByRole("heading", { name: "开源 Agent 框架加入可观测工具" });
  const firstSummary = firstItem.getByText("项目新增调用链和工具执行记录");
  await expect(firstTitle).toBeVisible();
  await expect(firstSummary).toBeVisible();
  await expect(
    page.locator(".publicRailStory").filter({ hasText: "多模态检索论文刷新长上下文评测" })
  ).toHaveCount(1);
  await expect(
    page.locator(".publicDigestItem").filter({ hasText: "多模态检索论文刷新长上下文评测" })
  ).toHaveCount(0);

  const index = page.getByRole("complementary", { name: "今日索引" });
  if (testInfo.project.name === "mobile") {
    await expect(index).toBeHidden();
    const titleBox = await firstTitle.boundingBox();
    const summaryBox = await firstSummary.boundingBox();
    const viewport = page.viewportSize();
    expect(titleBox && viewport && titleBox.y < viewport.height).toBeTruthy();
    expect(summaryBox && viewport && summaryBox.y + summaryBox.height <= viewport.height).toBeTruthy();
  } else {
    await expect(index).toBeVisible();
    await expect(index.getByRole("link")).toHaveCount(2);
  }

  await page.screenshot({
    path: testInfo.outputPath("public-briefing.png"),
    fullPage: true
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
  ).toBeTruthy();

  if (testInfo.project.name === "mobile") {
    await page.setViewportSize({ width: 320, height: 720 });
    await page.goto("/");
    const compactNavBox = await page.locator(".publicNav").boundingBox();
    const compactLoginBox = await page.getByRole("banner").getByRole("link", {
      name: "登录进入工作区"
    }).boundingBox();
    expect(
      compactNavBox && compactLoginBox && compactNavBox.x + compactNavBox.width < compactLoginBox.x
    ).toBeTruthy();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBeTruthy();
  }
});

test("anonymous private routes redirect to a responsive login form", async ({ page }, testInfo) => {
  await page.goto("/library");

  await expect(page).toHaveURL(/\/login\?next=%2Flibrary$/);
  await expect(page.getByRole("heading", { name: "登录工作区" })).toBeVisible();
  await expect(page.getByRole("link", { name: "每日 AI 简报" })).toBeVisible();
  const loginNameInput = page.getByPlaceholder("请输入账号或邮箱");
  const passwordInput = page.getByPlaceholder("请输入密码");
  const loginButton = page.getByRole("button", { name: "登录" });
  await expect(loginNameInput).toBeVisible();
  await expect(passwordInput).toBeVisible();
  await expect(loginButton).toBeVisible();
  await expect(loginButton).toBeDisabled();
  await expect(page.getByText("使用管理员创建的账号继续。", { exact: true })).toHaveCount(0);
  await expect(page.getByText("登录后将根据你的权限进入对应页面。", { exact: true })).toHaveCount(0);
  await expect(page.locator(".loginVisual, .loginVisualGrid")).toHaveCount(0);
  if (testInfo.project.name === "mobile") {
    const buttonBox = await loginButton.boundingBox();
    const viewport = page.viewportSize();
    expect(buttonBox && viewport && buttonBox.y + buttonBox.height <= viewport.height).toBeTruthy();
  }
  await page.screenshot({
    path: testInfo.outputPath("login-page.png"),
    fullPage: true
  });
  await loginNameInput.fill("reader@example.com");
  await passwordInput.fill("password");
  await expect(loginButton).toBeEnabled();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
  ).toBeTruthy();
});

test("authenticated users keep the responsive workspace navigation on today page", async ({
  page
}, testInfo) => {
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
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(() =>
      document.fonts.check('16px "Noto Sans SC Variable"', "中文字体")
    )
  ).toBeTruthy();

  const mobileNav = page.getByRole("navigation", { name: "主工作区快捷导航" });
  if (testInfo.project.name === "mobile") {
    await expect(mobileNav).toBeVisible();
    await expect(mobileNav.getByRole("link", { name: "今日" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    await expect(mobileNav.getByRole("link")).toHaveCount(5);

    const assistantBox = await page
      .getByRole("button", { name: "打开信息库智能助手" })
      .boundingBox();
    expect(assistantBox?.width).toBeLessThanOrEqual(50);
    expect(assistantBox?.height).toBeLessThanOrEqual(50);

    const mobileNavBox = await mobileNav.boundingBox();
    expect(assistantBox && mobileNavBox && assistantBox.y + assistantBox.height < mobileNavBox.y).toBeTruthy();

    const metricTops = await page.locator(".compactStats .metricCard").evaluateAll((cards) =>
      cards.map((card) => Math.round(card.getBoundingClientRect().top))
    );
    expect(new Set(metricTops).size).toBe(1);
  } else {
    await expect(mobileNav).toBeHidden();
    await page.getByRole("button", { name: "打开账号菜单" }).click();
    await expect(page.getByRole("menuitem", { name: "退出登录" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("menuitem", { name: "退出登录" })).toHaveCount(0);
  }
});
