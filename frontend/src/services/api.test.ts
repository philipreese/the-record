import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchStats,
  triggerSync,
  deleteListen,
  submitListenCorrection,
  revertListenCorrection,
  submitTrackCorrection,
  revertTrackCorrection,
  fetchTrackListens,
  deleteTrackListens,
  fetchCoverArt,
  searchMusicBrainz,
  searchCoverArt,
} from './api';

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

    await triggerSync('normal');

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.method).toBe('POST');
    expect(req.headers.get('X-Sync-Token')).toBe('my-secret');
  });

  it('sends an empty header when no token is stored', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'started', mode: 'full' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await triggerSync('mirror');

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.url).toContain('/api/sync?mode=mirror');
    expect(req.headers.get('X-Sync-Token')).toBe('');
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
    await vi.advanceTimersByTimeAsync(2000);
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
    await vi.advanceTimersByTimeAsync(2000);
    const result = await promise;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ total_listens: 5 });
  });

  it('gives up after exhausting retries and rejects', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('down'));
    vi.stubGlobal('fetch', fetchMock);

    const promise = fetchStats();
    const assertion = expect(promise).rejects.toThrow('down');
    // 6 retries × 2000ms each = 12 000ms total delay
    await vi.advanceTimersByTimeAsync(13000);
    await assertion;

    // Initial attempt + RETRY_ATTEMPTS (6) = 7 total.
    expect(fetchMock).toHaveBeenCalledTimes(7);
  });

  it('does not retry a non-GET request', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('down'));
    vi.stubGlobal('fetch', fetchMock);

    await expect(triggerSync('normal')).rejects.toThrow();

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe('deleteListen', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends DELETE to the correct listen path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);

    await deleteListen(42);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/listens/42');
    expect(init.method).toBe('DELETE');
  });

  it('throws on non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 404 })));
    await expect(deleteListen(99)).rejects.toThrow();
  });
});

describe('submitListenCorrection', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('POSTs the correction payload to the listen path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 1,
        artist: 'Fixed Artist',
        title: 'Creep',
        unix_ts: 1000000,
        source: 'youtube_music',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await submitListenCorrection(1, { artist: 'Fixed Artist' });

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.method).toBe('POST');
    expect(req.url).toContain('/api/listens/1/correction');
    expect(result.artist).toBe('Fixed Artist');
  });
});

describe('revertListenCorrection', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('POSTs to the revert endpoint and returns the listen', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 1,
        artist: 'Original',
        title: 'Creep',
        unix_ts: 1000000,
        source: 'youtube_music',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await revertListenCorrection(1);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/listens/1/correction/revert');
    expect(init.method).toBe('POST');
    expect(result.artist).toBe('Original');
  });
});

describe('submitTrackCorrection', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('POSTs the track correction request body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 1,
        artist: 'Radiohead',
        title: 'Creep',
        unix_ts: 1000000,
        source: 'youtube_music',
        album: 'Pablo Honey',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await submitTrackCorrection({
      corrected_artist: 'Radiohead',
      corrected_title: 'Creep',
      corrections: { album: 'Pablo Honey' },
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/tracks/correction');
    expect(init.method).toBe('POST');
    const body = JSON.parse(init.body as string);
    expect(body.corrected_artist).toBe('Radiohead');
    expect(body.corrections.album).toBe('Pablo Honey');
    expect(result.album).toBe('Pablo Honey');
  });
});

describe('revertTrackCorrection', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('POSTs to the track correction revert endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 1,
        artist: 'Radiohead',
        title: 'Creep',
        unix_ts: 1000000,
        source: 'youtube_music',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await revertTrackCorrection({ corrected_artist: 'Radiohead', corrected_title: 'Creep' });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/tracks/correction/revert');
    expect(init.method).toBe('POST');
    const body = JSON.parse(init.body as string);
    expect(body.corrected_artist).toBe('Radiohead');
  });
});

describe('fetchTrackListens', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends GET with artist and title query params', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse([
        { id: 1, artist: 'Radiohead', title: 'Creep', unix_ts: 1000000, source: 'youtube_music' },
        { id: 2, artist: 'Radiohead', title: 'Creep', unix_ts: 999000, source: 'last_fm' },
      ]),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await fetchTrackListens('Radiohead', 'Creep');

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.method).toBe('GET');
    expect(req.url).toContain('/api/tracks/listens');
    expect(req.url).toContain('artist=Radiohead');
    expect(req.url).toContain('title=Creep');
    expect(result).toHaveLength(2);
    expect(result[0].artist).toBe('Radiohead');
  });
});

describe('deleteTrackListens', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends DELETE with artist and title query params', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);

    await deleteTrackListens('Radiohead', 'Creep');

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.method).toBe('DELETE');
    expect(req.url).toContain('/api/tracks/listens');
    expect(req.url).toContain('artist=Radiohead');
    expect(req.url).toContain('title=Creep');
  });

  it('throws when the server returns an error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Not found' }, 404)));
    await expect(deleteTrackListens('Nobody', 'Nothing')).rejects.toThrow();
  });
});

describe('fetchCoverArt', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns empty object immediately for empty input without fetching', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const result = await fetchCoverArt([]);
    expect(result).toEqual({});
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('POSTs entries and returns the art URL map', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ '1': 'https://example.com/art.jpg', '2': null }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await fetchCoverArt([
      { id: 1, artist: 'Radiohead', title: 'Creep' },
      { id: 2, artist: 'Mitski', title: 'Nobody' },
    ]);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/cover-art');
    expect(init.method).toBe('POST');
    expect(result['1']).toBe('https://example.com/art.jpg');
    expect(result['2']).toBeNull();
  });

  it('returns empty object on server error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    const result = await fetchCoverArt([{ id: 1, artist: 'A', title: 'T' }]);
    expect(result).toEqual({});
  });
});

describe('searchMusicBrainz', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends GET with artist and title params and returns results array', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        results: [
          { mbid: 'abc-123', title: 'Creep', artist_credit: 'Radiohead', release: 'Pablo Honey' },
        ],
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const results = await searchMusicBrainz('Radiohead', 'Creep');

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.url).toContain('/api/mb/search');
    expect(req.url).toContain('artist=Radiohead');
    expect(req.url).toContain('title=Creep');
    expect(results).toHaveLength(1);
    expect(results[0].mbid).toBe('abc-123');
  });
});

describe('searchCoverArt', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends GET with artist, album, and optional mbid params and returns results array', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        results: [
          { release_mbid: 'rel-123', release_title: 'Pablo Honey', artist_credit: 'Radiohead' },
        ],
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const results = await searchCoverArt('Radiohead', 'Pablo Honey', 'mbid-xyz');

    const [req] = fetchMock.mock.calls[0] as [Request];
    expect(req.url).toContain('/api/cover-art/search');
    expect(req.url).toContain('artist=Radiohead');
    expect(results).toHaveLength(1);
    expect(results[0].release_mbid).toBe('rel-123');
  });
});
