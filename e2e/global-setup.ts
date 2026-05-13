import { test asSetup, expect } from "@playwright/test";

const BASE_URL = process.env.MUSHIR_API_URL || "http://127.0.0.1:8000";

testSetup("global setup — verify API health", async ({ request }) => {
  const res = await request.get(`${BASE_URL}/health`);
  if (!res.ok()) {
    throw new Error(`API not reachable at ${BASE_URL}/health (${res.status()}). Start the server first.`);
  }
});