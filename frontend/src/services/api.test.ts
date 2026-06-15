import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchStats, triggerSync } from './api';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

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

describe('apiFetch cold-start retry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('retries a GET after a network error, then succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(jsonResponse({ total_listens: 1 }));
    vi.stubGlobal('fetch', fetchMock);

    const promise = fetchStats();
    await vi.advanceTimersByTimeAsync(1000);
    const result = await promise;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ total_listens: 1 });
  });

  it('retries a GET that returns 503, then succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'cold' }, 503))
      .mockResolvedValueOnce(jsonResponse({ total_listens: 5 }));
    vi.stubGlobal('fetch', fetchMock);

    const promise = fetchStats();
    await vi.advanceTimersByTimeAsync(1000);
    const result = await promise;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ total_listens: 5 });
  });

  it('gives up after exhausting retries and rejects', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('down'));
    vi.stubGlobal('fetch', fetchMock);

    const promise = fetchStats();
    const assertion = expect(promise).rejects.toThrow('down');
    await vi.advanceTimersByTimeAsync(1000);
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;

    // Initial attempt + RETRY_ATTEMPTS (2) = 3 total.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('does not retry a non-GET request', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('down'));
    vi.stubGlobal('fetch', fetchMock);

    await expect(triggerSync(false)).rejects.toThrow();

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
