import { test, expect } from '@playwright/test';

const event = (type: string, data: unknown) => `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
const final = {answer: 'Verified final response', status: 'INSUFFICIENT_DATA', metadata: {}};

for (const lang of ['en', 'ar']) {
  for (const failure of ['eof', 'malformed', 'server-error']) {
    test(`Incomplete output is discarded and retry restores a final answer (${lang}, ${failure})`, async ({page}) => {
      let attempt = 0;
      await page.route('**/api/v1/query/stream', route => {
        attempt++;
        const body = attempt > 1 ? event('done', final) :
          event('started', {request_id: 'interrupted-fixture'}) + event('token', {text: 'Uncommitted partial claim'}) +
          (failure === 'eof' ? '' : failure === 'malformed' ? 'event: done\ndata: {"answer":\n\n' :
            event('error', {message: 'Unavailable', code: 'AUDIT_STORAGE_FAILED'}));
        return route.fulfill({status: 200, contentType: 'text/event-stream', body});
      });
      await page.goto(`/chat?lang=${lang}`);
      await page.locator('#prompt').fill('Explain this contract');
      await page.locator('#send').click();
      await expect(page.locator('.error-bubble')).toHaveCount(1);
      await expect(page.locator('#messages')).not.toContainText('Uncommitted partial claim');
      await expect(page.locator('#send')).toBeEnabled();
      await page.locator('.error-bubble button').click();
      await expect(page.locator('#messages .message.assistant')).toContainText(final.answer);
      await page.reload();
      await expect(page.locator('#messages')).toContainText(final.answer);
      await expect(page.locator('#messages')).not.toContainText('Uncommitted partial claim');
    });
  }
}

test('Final payload is canonical even when tokens differ, with fragmented Arabic CRLF parsing', async ({page}) => {
  await page.route('**/api/v1/query/stream', route => route.fulfill({status: 200, contentType: 'text/event-stream',
    body: event('token', {text: 'Provisional draft'}) + event('done', final)}));
  await page.goto('/chat?lang=en');
  await page.locator('#prompt').fill('Explain');
  await page.locator('#send').click();
  await expect(page.locator('#messages .message.assistant')).toContainText(final.answer);
  await expect(page.locator('#messages')).not.toContainText('Provisional draft');
  await page.reload();
  await expect(page.locator('#messages')).toContainText(final.answer);
  const parsed = await page.evaluate(async () => {
    const bytes = new TextEncoder().encode('event: done\r\ndata: {"answer":"إجابة موثقة","status":"INSUFFICIENT_DATA"}\r\n\r\n');
    const stream = new ReadableStream({start(controller) { for (const b of bytes) controller.enqueue(new Uint8Array([b])); controller.close(); }});
    return await new Promise(resolve => {
      let answer = '', errors = 0;
      (window as any).processSseStream(stream.getReader(), {onDone: (data: any) => answer = data.answer,
        onStreamError: () => errors++, onComplete: () => resolve({answer, errors})});
    });
  });
  expect(parsed).toEqual({answer: 'إجابة موثقة', errors: 0});
});
