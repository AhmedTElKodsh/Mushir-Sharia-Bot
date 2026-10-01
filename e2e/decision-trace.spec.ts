import { test, expect } from "@playwright/test";

for (const lang of ["en", "ar"]) {
  test(`Structured explanation is collapsed, localized and restored (${lang})`, async ({ page }) => {
    const fact = '<img src=x onerror="window.injected=1">';
    const trace = {
      understood_as: {lane: "described_operation", language: lang, mechanism: "unknown"},
      known: [{slot: "financing_party", status: "user_reported", value: fact},
              {slot: "seller", status: "observed", value: "Fixture seller"}],
      missing: [{slot: "additional_fees", status: "unknown"},
                {slot: "cash_price", status: "conflicting"}],
      question_asked: "Who provides the plan?",
      sources: [],
      decided_by: {gate: "clarification", reason_code: "financing_party_unknown"},
      would_decide: [{condition: "financing_party", state: "user_reported"}],
    };
    await page.route("**/api/v1/query/stream", async route => {
      const evidence = {status: "clarification_required", source_age_status: "unknown", sources: []};
      const answer = "Who provides the plan?";
      const events = [
        ["started", {request_id: "trace-fixture"}],
        ["retrieval", {evidence}],
        ["token", {text: answer}],
        ["done", {answer, status: "CLARIFICATION_NEEDED", clarification_question: answer,
                  metadata: {decision_trace: trace, evidence}}],
      ];
      await route.fulfill({status: 200, contentType: "text/event-stream",
        body: events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join("")});
    });
    await page.goto(`/chat?lang=${lang}`);
    await page.locator("#prompt").fill("I bought an iPhone on instalments");
    await page.locator("#send").click();
    const panel = page.locator("details.decision-trace").last();
    await expect(panel).toHaveCount(1);
    await expect(panel).toHaveAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    await expect(panel.locator("summary")).toContainText(lang === "ar" ? "كيف تحددت" : "How this response");
    expect(await panel.evaluate(node => (node as HTMLDetailsElement).open)).toBe(false);
    await panel.locator("summary").focus();
    await page.keyboard.press("Enter");
    expect(await panel.evaluate(node => (node as HTMLDetailsElement).open)).toBe(true);
    await expect(panel).toContainText(lang === "ar" ? "معاملة موصوفة" : "A described transaction");
    await expect(panel).toContainText(fact);
    const labels = lang === "ar" ? ["✓", "ذكرتَ ذلك", "مرصود في مصدر", "?", "غير معروف", "✗", "معلومات متعارضة",
      "الرموز تبين توافر المعلومات ولا تعني استيفاء قاعدة شرعية."] :
      ["✓", "You reported", "Observed in source", "?", "Unknown", "✗", "Conflicting information",
       "Symbols show information availability, not whether a rule is satisfied."];
    for (const text of labels) await expect(panel).toContainText(text);
    await expect(panel.locator("ul").last()).toContainText(lang === "ar" ? "جهة التمويل" : "Financing party");
    expect(await page.evaluate(() => (window as any).injected || 0)).toBe(0);
    await expect(page.locator("#messages img")).toHaveCount(0);
    const smaller = await panel.evaluate(node => {
      const answer = node.nextElementSibling as HTMLElement;
      return {panel: parseFloat(getComputedStyle(node).fontSize), answer: parseFloat(getComputedStyle(answer).fontSize),
        italic: getComputedStyle(node).fontStyle};
    });
    expect(smaller.panel).toBeLessThan(smaller.answer);
    expect(smaller.italic).toBe("italic");
    await page.reload();
    await expect(page.locator("details.decision-trace")).toHaveCount(1);
    await page.locator("details.decision-trace summary").click();
    for (const text of labels) await expect(page.locator("details.decision-trace")).toContainText(text);
  });
}

test("Older restored answer without a trace remains readable", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(String(error)));
  await page.goto("/chat?lang=en");
  await page.evaluate(() => {
    (window as any).restoreMessages([{role: "assistant", content: "Older answer", status: "INSUFFICIENT_DATA"}]);
  });
  await expect(page.locator("#messages .message.assistant")).toContainText("Older answer");
  await expect(page.locator("details.decision-trace")).toHaveCount(0);
  expect(errors).toEqual([]);
});

for (const theme of ["light", "dark"]) {
  test(`Long Arabic explanation fits a small screen (${theme})`, async ({ page }) => {
    await page.setViewportSize({width: 390, height: 844});
    await page.goto("/chat?lang=ar");
    if (theme === "dark") await page.locator("#theme-toggle").click();
    await page.evaluate(() => {
      (window as any).restoreMessages([{role: "assistant", content: "أحتاج إلى مستندات المعاملة.",
        status: "INSUFFICIENT_DATA", decision_trace: {
          understood_as: {lane: "described_operation", language: "ar", mechanism: "unknown"},
          known: [{slot: "financing_party", status: "user_reported", value: "جهة تمويل تحتاج إلى تحقق من مستندات المعاملة ".repeat(12)}],
          missing: [{slot: "late_payment_clause", status: "unknown"}], sources: [],
          decided_by: {gate: "material_fact", reason_code: "material_evidence_incomplete"},
          would_decide: [{condition: "late_payment_clause", state: "unknown"}]
        }}]);
    });
    const panel = page.locator("details.decision-trace");
    await panel.locator("summary").click();
    await expect(panel).toContainText("بند التأخر في السداد");
    const measured = await panel.evaluate(node => {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      const lum = (color: string) => {
        const parts = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(x => {
          x /= 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
        });
        return parts[0] * 0.2126 + parts[1] * 0.7152 + parts[2] * 0.0722;
      };
      const colors = [lum(style.color), lum(style.backgroundColor)].sort((a,b) => a-b);
      return {left: rect.left, right: rect.right, overflow: node.scrollWidth - node.clientWidth,
        contrast: (colors[1] + 0.05) / (colors[0] + 0.05)};
    });
    expect(measured.left).toBeGreaterThanOrEqual(0);
    expect(measured.right).toBeLessThanOrEqual(391);
    expect(measured.overflow).toBeLessThanOrEqual(1);
    expect(measured.contrast).toBeGreaterThanOrEqual(4.5);
  });
}
