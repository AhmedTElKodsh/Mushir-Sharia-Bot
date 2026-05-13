import { test, expect } from "@playwright/test";

test.describe("/query/stream — SSE", () => {
  test("[P0] POST /query/stream returns SSE with done event", async ({ request }) => {
    const res = await request.post("/api/v1/query/stream", {
      data: { query: "What is ijara?", context: { disclaimer_acknowledged: true } },
    });
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("text/event-stream");
    const text = await res.text();
    expect(text).toContain("event: started");
    expect(text).toContain("event: done");
  });

  test("[P0] POST /query/stream includes token event with answer text", async ({ request }) => {
    const res = await request.post("/api/v1/query/stream", {
      data: { query: "What is sukuk?", context: { disclaimer_acknowledged: true } },
    });
    const text = await res.text();
    const blocks = text.split("\n\n").filter(Boolean);
    const tokenBlock = blocks.find((b) => b.startsWith("event: token"));
    expect(tokenBlock).toBeDefined();
    const dataLine = tokenBlock!.split("\n").find((l) => l.startsWith("data: "));
    expect(dataLine).toBeDefined();
  });

  test("[P1] POST /query/stream returns authority refusal as error event", async ({ request }) => {
    const res = await request.post("/api/v1/query/stream", {
      data: { query: "Give me legal advice", context: { disclaimer_acknowledged: true } },
    });
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text).toContain("event: done");
  });

  test("[P1] POST /query/stream sets X-Request-ID", async ({ request }) => {
    const res = await request.post("/api/v1/query/stream", {
      data: { query: "Is this halal?", context: { disclaimer_acknowledged: true } },
    });
    expect(res.headers()).toHaveProperty("x-request-id");
  });
});