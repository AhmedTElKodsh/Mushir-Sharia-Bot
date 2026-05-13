import { test, expect } from "@playwright/test";

test.describe("/compliance/disclaimer", () => {
  test("[P0] GET /compliance/disclaimer returns bilingual disclaimer", async ({ request }) => {
    const res = await request.get("/api/v1/compliance/disclaimer");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.version).toMatch(/l5-bilingual/);
    expect(body.text).toMatch(/informational guidance/);
    expect(body.translations).toHaveProperty("ar");
    expect(body.translations.ar).toMatch(/مشير/);
  });

  test("[P1] disclaimer requires acknowledgement", async ({ request }) => {
    const res = await request.get("/api/v1/compliance/disclaimer");
    const body = await res.json();
    expect(body.requires_acknowledgement).toBe(true);
    expect(body.supported_languages).toContain("en");
    expect(body.supported_languages).toContain("ar");
  });
});