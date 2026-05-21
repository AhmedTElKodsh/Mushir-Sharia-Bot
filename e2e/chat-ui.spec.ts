import { test, expect } from "@playwright/test";

test.describe("/chat UI — smoke", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat");
  });

  test("[P0] /chat page loads with heading", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Mushir Sharia");
  });

  test("[P0] /chat page has textarea for input", async ({ page }) => {
    await expect(page.locator("textarea#prompt")).toBeVisible();
  });

  test("[P0] /chat page has submit button", async ({ page }) => {
    await expect(page.locator("button#send")).toBeVisible();
    await expect(page.locator("button#send")).toBeEnabled();
  });

  test("[P0] /chat page has welcome guidance", async ({ page }) => {
    const welcome = page.locator("#messages .welcome-card").first();
    await expect(welcome).toBeVisible();
    await expect(welcome).toContainText("Ask a Sharia");
  });

  test("[P1] /chat accepts input in textarea", async ({ page }) => {
    await page.locator("textarea#prompt").fill("What is gharar?");
    await expect(page.locator("textarea#prompt")).toHaveValue("What is gharar?");
  });

  test("[P1] /chat submit remains available for acknowledged demo flow", async ({ page }) => {
    await expect(page.locator("button#send")).toBeEnabled();
  });

  test("[P1] /chat shows initial welcome card", async ({ page }) => {
    const initial = page.locator("#messages .welcome-card").first();
    await expect(initial).toBeVisible();
    await expect(initial).toContainText("AAOIFI-grounded assistant");
  });

  test("[P2] /chat submits query and shows user message", async ({ page }) => {
    await page.locator("textarea#prompt").fill("What is mudarabah?");
    await page.locator("button#send").click();
    const userMsg = page.locator("#messages .message.user").first();
    await expect(userMsg).toBeVisible();
    await expect(userMsg).toContainText("What is mudarabah?");
  });
});
