import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { triggerSync } from './api';

describe('triggerSync', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('attaches the stored token as the X-Sync-Token header', async () => {
    localStorage.setItem('syncToken', 'my-secret');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'started', mode: 'normal' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await triggerSync(false);

    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe('POST');
    expect(options.headers['X-Sync-Token']).toBe('my-secret');
  });

  it('sends an empty header when no token is stored', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'started', mode: 'full' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await triggerSync(true);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/sync?mode=full');
    expect(options.headers['X-Sync-Token']).toBe('');
  });
});
