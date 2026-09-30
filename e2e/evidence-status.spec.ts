import { test, expect } from "@playwright/test";

for (const lang of ["en", "ar"]) {
  test(`Evidence labels and unknown capture dates persist (${lang})`, async ({ page }) => {
    await page.route("**/api/v1/query/stream", async route => {
      const evidence = {status: "insufficient_evidence", source_age_status: "unknown", sources: []};
      const answer = "The agreement is needed.";
      const events = [
        ["started", {request_id: "fixture"}],
        ["retrieval", {evidence}],
        ["token", {text: answer}],
        ["done", {answer, status: "INSUFFICIENT_DATA", metadata: {evidence}}],
      ];
      await route.fulfill({status: 200, contentType: "text/event-stream", body: events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join("")});
    });
    await page.goto(`/chat?lang=${lang}`);
    await page.locator("#prompt").fill("What is murabaha?");
    await page.locator("#send").click();
    const label = page.locator(".evidence-summary").last();
    await expect(label).toContainText(lang === "ar" ? "أدلة غير كافية" : "Insufficient evidence");
    await expect(label).toContainText(lang === "ar" ? "غير معروف" : "unknown");
    await expect(page.locator("#messages")).not.toContainText(/confidence|درجة الثقة|0\.99|99%/);
    await page.reload();
    await expect(page.locator(".evidence-summary").last()).toContainText(lang === "ar" ? "غير معروف" : "unknown");
    await page.screenshot({path: `test-results/evidence-status-${lang}.png`, fullPage: true});
  });
}

test("Historical citation metadata does not imply no sources", async ({ page }) => {
  await page.goto("/chat?lang=en");
  await page.evaluate(() => {
    (window as any).restoreMessages([{role: "assistant", content: "An older cited excerpt.",
      status: "INSUFFICIENT_DATA", citations: [{standard: "SS-08", excerpt: "Fixture source."}]}]);
  });
  await expect(page.locator(".evidence-summary").last()).toContainText("Evidence status unavailable");
  await expect(page.locator(".evidence-summary").last()).not.toContainText("No sources");
});

test("Known capture date displays elapsed days", async ({ page }) => {
  await page.goto("/chat?lang=en");
  await page.evaluate(() => {
    (window as any).restoreMessages([{role: "assistant", content: "A dated excerpt.",
      evidence: {status: "sources_available", sources: [{document_id: "SS-08", captured_at: "2026-01-01T00:00:00Z"}]}}]);
  });
  await expect(page.locator(".evidence-summary").last()).toContainText("2026-01-01T00:00:00Z");
  await expect(page.locator(".evidence-summary").last()).toContainText(/age: \d+ days/);
});
