import { request, type FullConfig } from "@playwright/test";

const BASE_URL = process.env.MUSHIR_API_URL || "http://127.0.0.1:8000";

export default async function globalSetup(config: FullConfig) {
  const baseURL = String(config.projects[0]?.use?.baseURL || BASE_URL);
  const context = await request.newContext({ baseURL });
  const res = await context.get("/health");
  if (!res.ok()) {
    await context.dispose();
    throw new Error(`API not reachable at ${baseURL}/health (${res.status()}). Start the server first.`);
  }
  await context.dispose();
}
