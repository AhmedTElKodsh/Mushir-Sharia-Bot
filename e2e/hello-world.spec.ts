import { test, expect } from "@playwright/test";

test.describe("/health endpoint", () => {
  test("[P0] GET /health returns 200 with status ok", async ({ request }) => {
    const res = await request.get("/health");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({ status: "healthy" });
    expect(body).toHaveProperty("timestamp");
    expect(body).toHaveProperty("version");
  });

  test("[P0] GET /health is unauthenticated", async ({ request }) => {
    const res = await request.get("/health");
    expect(res.status()).toBe(200);
  });
});

test.describe("/ready endpoint", () => {
  test("[P0] GET /ready returns readiness level", async ({ request }) => {
    const res = await request.get("/ready");
    expect([200, 503]).toContain(res.status());
    const body = await res.json();
    expect(body).toHaveProperty("status");
    expect(body).toHaveProperty("readiness_level");
    expect(body).toHaveProperty("checks");
  });

  test("[P1] GET /ready checks includes infrastructure state", async ({ request }) => {
    const res = await request.get("/ready");
    const body = await res.json();
    expect(body.checks).toHaveProperty("retrieval_configured");
    expect(body.checks).toHaveProperty("provider_configured");
    expect(body.checks).toHaveProperty("auth_configured");
  });
});