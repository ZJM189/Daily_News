import { expect, test } from "@playwright/test";

test("private favorites, folders, recovery and responsive layout", async ({
  page
}, testInfo) => {
  test.skip(
    !process.env.E2E_PASSWORD,
    "Use the isolated E2E API and E2E_PASSWORD"
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page
    .getByLabel("账号或邮箱")
    .fill(`favorites-e2e-${testInfo.project.name}`);
  await page
    .getByLabel("密码", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/today$/);
  await page.goto("/library");
  const row = page.locator(".libraryFavoriteRow").first();
  await expect(
    row.getByRole("button", { name: "收藏", exact: true })
  ).toBeEnabled();
  await row.getByRole("button", { name: "收藏", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("已收藏至根目录");
  await expect(
    page
      .locator(".detailPanel")
      .getByRole("button", { name: "已收藏至根目录，管理收藏" })
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "撤销", exact: true }).click();
  await expect(
    row.getByRole("button", { name: "收藏", exact: true })
  ).toBeEnabled();
  await row.getByRole("button", { name: "收藏", exact: true }).click();
  await expect(
    row.getByRole("button", { name: "已收藏至根目录，管理收藏" })
  ).toBeVisible();

  await page.goto("/favorites");
  await expect(page.locator(".favoriteEntry")).toHaveCount(1);
  await page.getByRole("button", { name: "新建目录", exact: true }).click();
  await page.getByRole("dialog").getByLabel("目录名称").fill("Agent 资料");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "保存", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .locator(".favoriteEntry")
    .getByRole("button", { name: /移动或取消收藏/ })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("radio", { name: "Agent 资料" })
    .check();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "保存位置" })
    .click();
  await expect(page.locator(".favoriteEntryFooter")).toContainText(
    "Agent 资料"
  );

  const chooseFolder = async (name: string) => {
    if (testInfo.project.name === "mobile")
      await page.getByLabel("当前目录").selectOption({ label: `${name} (1)` });
    else
      await page
        .locator(".favoritesFolderNav")
        .getByRole("button", { name: new RegExp(name) })
        .first()
        .click();
  };
  await chooseFolder("Agent 资料");
  await page
    .locator(".favoritesListHeading")
    .getByRole("button", { name: "管理目录：Agent 资料" })
    .click();
  await page
    .locator(".favoritesListHeading")
    .getByRole("button", { name: "重命名" })
    .click();
  const longName = "Agent 工程资料与开源实现对比".repeat(4);
  await page.getByRole("dialog").getByLabel("目录名称").fill(longName);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "保存", exact: true })
    .click();
  await expect(page.locator(".favoritesListHeading h2")).toHaveText(longName);
  await page.screenshot({
    path: testInfo.outputPath("favorites.png"),
    fullPage: true
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth
    )
  ).toBeTruthy();

  await page
    .locator(".favoriteEntry")
    .getByRole("button", { name: /查看详情/ })
    .click();
  await expect(page.getByRole("dialog", { name: "内容详情" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("detail.png") });
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "关闭", exact: true })
    .click();

  await page
    .locator(".favoritesListHeading")
    .getByRole("button", { name: `管理目录：${longName}` })
    .click();
  await page
    .locator(".favoritesListHeading")
    .getByRole("button", { name: "删除目录", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("1 条收藏将移至根目录");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "删除并移至根目录" })
    .click();
  await expect(page.locator(".favoritesListHeading h2")).toHaveText("根目录");
  await expect(page.locator(".favoriteEntry")).toHaveCount(1);

  await page.goto("/following");
  const feedFavoriteButton = page
    .locator('.followingItem button.favoriteIconButton[aria-label="收藏"]')
    .first();
  await expect(feedFavoriteButton).toBeEnabled();
  await feedFavoriteButton.click();
  await expect(page.getByRole("status")).toContainText("已收藏至根目录");
  await page.goto("/favorites");
  await expect(page.locator(".favoriteEntry")).toHaveCount(2);

  await page.getByRole("button", { name: "新建目录", exact: true }).click();
  await page.getByRole("dialog").getByLabel("目录名称").fill("阅读清单");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "保存", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto("/library");
  const unsavedLibraryButton = page
    .locator('.libraryFavoriteRow > button.favoriteIconButton[aria-label="收藏"]')
    .first();
  await expect(unsavedLibraryButton).toBeEnabled();
  await unsavedLibraryButton.click();
  await expect(page.getByRole("dialog", { name: "收藏到" })).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "新建目录", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("目录名称", { exact: true })
    .fill("论文");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "创建", exact: true })
    .click();
  await expect(
    page.getByRole("dialog").getByRole("radio", { name: "论文" })
  ).toBeChecked();
  await page.screenshot({ path: testInfo.outputPath("folder-picker.png") });
  await page.route("**/api/v1/favorites/items/*", async (route) => {
    if (route.request().method() === "PUT")
      await route.fulfill({ status: 503, json: { detail: "保存失败测试" } });
    else await route.continue();
  });
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "确认收藏" })
    .click();
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveText(
    "保存失败测试"
  );
  await expect(
    page.getByRole("dialog").getByRole("radio", { name: "论文" })
  ).toBeChecked();
  await page.unroute("**/api/v1/favorites/items/*");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "确认收藏" })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto("/favorites");
  await expect(page.locator(".favoriteEntry")).toHaveCount(3);
  await page.getByLabel("搜索", { exact: true }).fill("no-result-for-test");
  await page.getByRole("button", { name: "检索", exact: true }).click();
  await expect(page.getByText("无匹配内容", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "清除筛选" }).click();
  await expect(page.locator(".favoriteEntry")).toHaveCount(3);
  await page
    .locator(".favoriteEntry")
    .first()
    .getByRole("button", { name: /移动或取消收藏/ })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "取消收藏", exact: true })
    .click();
  await expect(page.locator(".favoriteEntry")).toHaveCount(2);
  await page.reload();
  await expect(page.locator(".favoriteEntry")).toHaveCount(2);
  expect(errors).toEqual([]);
});
