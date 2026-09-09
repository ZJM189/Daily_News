import { expect, test } from "@playwright/test";

test("library chat widget streams, rejects unrelated questions, and keeps history", async ({
  page
}, testInfo) => {
  test.skip(
    !process.env.E2E_PASSWORD,
    "Use the isolated E2E API and E2E_PASSWORD"
  );

  await page.goto("/login");
  await page
    .getByLabel("账号或邮箱")
    .fill(process.env.E2E_LOGIN || "demo_user");
  await page
    .getByLabel("密码", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/today$/);

  await page.getByRole("button", { name: "打开信息库智能助手" }).click();
  const chat = page.getByRole("dialog", { name: "信息库智能助手" });
  await expect(chat).toBeVisible();
  await expect(chat.getByRole("button", { name: "新建智能查询会话" })).toBeEnabled();
  await chat.getByRole("button", { name: "新建智能查询会话" }).click();
  await expect(chat.getByText("问我信息库里的内容")).toBeVisible();

  await chat.getByLabel("输入信息库查询问题").fill("帮我写一个 Python 爬虫");
  const rejectionRequest = page.waitForRequest(
    (request) =>
      request.url().includes("/api/v1/library/chat/threads/") &&
      request.url().includes("/messages/stream") &&
      request.method() === "POST"
  );
  await chat.getByRole("button", { name: "发送智能查询" }).click();
  await rejectionRequest;
  await expect(chat.getByText("我只能查询已入库的 AI 信息", { exact: false })).toBeVisible({
    timeout: 15_000
  });
  await expect(chat.getByRole("button", { name: "新建智能查询会话" })).toBeEnabled();

  await chat.getByRole("button", { name: "新建智能查询会话" }).click();
  await expect(chat.getByText("问我信息库里的内容")).toBeVisible();
  const libraryQuery = process.env.E2E_NATURAL_LANGUAGE_QUERY || "最近 7 天 RAG 论文";
  await chat.getByLabel("输入信息库查询问题").fill(libraryQuery);

  const searchRequest = page.waitForRequest(
    (request) =>
      request.url().includes("/api/v1/library/chat/threads/") &&
      request.url().includes("/messages/stream") &&
      request.method() === "POST"
  );
  await chat.getByRole("button", { name: "发送智能查询" }).click();
  await searchRequest;

  await expect(chat.getByText("智能解析", { exact: true })).toBeVisible({ timeout: 90_000 });
  await expect(chat.getByRole("button", { name: "在信息库查看全部" })).toBeVisible();
  await chat.getByRole("button", { name: "关闭信息库助手" }).click();
  await page.getByRole("button", { name: "打开信息库智能助手" }).click();
  await expect(
    chat.locator(".aui-user-message-root").filter({ hasText: libraryQuery }).first()
  ).toBeVisible();
  await page.once("dialog", async (dialog) => {
    expect(dialog.message()).toContain("删除后聊天记录无法恢复");
    await dialog.accept();
  });
  const deleteResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/library/chat/threads/") &&
      response.request().method() === "DELETE" &&
      response.ok()
  );
  await chat
    .locator(".libraryChatThreadItem")
    .filter({ hasText: libraryQuery })
    .first()
    .getByRole("button", { name: /删除会话/ })
    .click();
  await deleteResponse;
  await page.screenshot({ path: testInfo.outputPath("library-chat.png") });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth
    )
  ).toBeTruthy();
});
