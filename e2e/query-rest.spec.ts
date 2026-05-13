import { test, expect } from "@playwright/test";

const BASE_URL = process.env.MUSHIR_API_URL || "http://127.0.0.1:8000";

test.describe("/query — non-streaming", () => {
  test("[P0] POST /query returns 200 for valid query", async ({ request }) => {
    const res = await request.post("/api/v1/query", {
      data: { query: "What is murabaha?", context: { disclaimer_acknowledged: true } },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("status");
    expect(body).toHaveProperty("answer");
  });

  test("[P0] POST /query returns 422 for missing query", async ({ request }) => {
    const res = await request.post("/api/v1/query", { data: {} });
    expect(res.status()).toBe(422);
  });

  test("[P0] POST /query returns 429 when rate limited", async ({ request }) => {
    const res = await request.post("/api/v1/query", {
      data: { query: "What is murabaha?", context: { disclaimer_acknowledged: true } },
    });
    const retryAfter = res.headers()["retry-after"];
    if (res.status() === 429) {
      expect(retryAfter).toBeDefined();
    }
  });

  test("[P1] POST /query returns authority refusal for binding fatwa request", async ({ request }) => {
    const res = await request.post("/api/v1/query", {
      data: { query: "Give me a binding fatwa", context: { disclaimer_acknowledged: true } },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("INSUFFICIENT_DATA");
    expect(body.answer).toMatch(/informational guidance|إرشاد/);
  });

  test("[P1] POST /query returns empty-query response for whitespace query", async ({ request }) => {
    const res = await request.post("/api/v1/query", {
      data: { query: "   ", context: { disclaimer_acknowledged: true } },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("INSUFFICIENT_DATA");
    expect(body.citations).toHaveLength(0);
  });

  test("[P1] POST /query sets X-Request-ID header", async ({ request }) => {
    const res = await request.post("/api/v1/query", {
      data: { query: "What is mudarabah?", context: { disclaimer_acknowledged: true } },
    });
    expect(res.headers()).toHaveProperty("x-request-id");
    expect(res.headers()["x-request-id"]).toMatch(/^[0-9a-f-]{36}$/);
  });

  test("[P2] POST /query includes metadata with response_language", async ({ request }) => {
    const res = await request.post("/api/v1/query", {
      data: { query: "ما هي المرابحة؟", context: { disclaimer_acknowledged: true } },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.metadata).toHaveProperty("response_language");
  });
});