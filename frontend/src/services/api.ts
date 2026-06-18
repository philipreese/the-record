import createClient from 'openapi-fetch';
import type { components, paths } from './api-types';

export type TimeRange = NonNullable<
  NonNullable<paths['/api/top-artists']['get']['parameters']['query']>['range']
>;
export type SyncMode = NonNullable<
  NonNullable<paths['/api/sync']['post']['parameters']['query']>['mode']
>;
export type WrappedQuarter = NonNullable<
  NonNullable<paths['/api/wrapped']['get']['parameters']['query']>['quarter']
>;
export type WrappedMonth = NonNullable<
  NonNullable<paths['/api/wrapped']['get']['parameters']['query']>['month']
>;

export type StatsInfo = components['schemas']['StatsSummaryResponse'];
export type StreakInfo = components['schemas']['StreakStatsResponse'];
export type ArtistInfo = components['schemas']['ArtistInfo'];
export type TrackInfo = components['schemas']['TrackInfo'];
export type TopArtistsResponse = components['schemas']['TopArtistsResponse'];
export type TopTracksResponse = components['schemas']['TopTracksResponse'];
export type MonthlyTrendInfo = components['schemas']['MonthlyTrendInfo'];
export type SyncStatusInfo = components['schemas']['SyncStatusResponse'];
export type WrappedDataInfo = components['schemas']['WrappedDataResponse'];
export type ListenEntry = components['schemas']['ListenEntry'];
export type SyncStartInfo = components['schemas']['SyncStartResponse'];
export type PlayingNowInfo = components['schemas']['PlayingNowResponse'];
export type TrackStatsInfo = components['schemas']['TrackStatsResponse'];
export type OnThisDayGroup = components['schemas']['OnThisDayGroup'];
export type TrackBatchRequestItem = components['schemas']['TrackBatchRequestItem'];
export type TrackBatchResponseItem = components['schemas']['TrackBatchResponseItem'];
export type WeeklyBreakdownItem = components['schemas']['WeeklyBreakdownItem'];
export type TopArtistTrendsResponse = components['schemas']['TopArtistTrendsResponse'];
export type ArtistTrendResponse = components['schemas']['ArtistTrendResponse'];

const API_BASE = import.meta.env.VITE_API_BASE || '';

// Cold-start resilience: Neon free-tier suspends after inactivity, so the first
// request after a wake fails with a connection error or a gateway status while the
// backend/DB spin up. Briefly retry idempotent GETs to ride out that window.
const RETRY_ATTEMPTS = 6;
const RETRY_DELAY_MS = 2000;
const COLD_START_STATUSES = new Set([502, 503, 504]);

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

type WakingListener = (waking: boolean) => void;
let wakingListener: WakingListener | null = null;
let activeRetries = 0;

/** Register a callback notified when a cold-start retry is in progress. */
export function registerWakingListener(listener: WakingListener): void {
  wakingListener = listener;
}

function beginWaking(): void {
  activeRetries += 1;
  if (activeRetries === 1) wakingListener?.(true);
}

function endWaking(): void {
  if (activeRetries === 0) return;
  activeRetries -= 1;
  if (activeRetries === 0) wakingListener?.(false);
}

async function resilientFetch(input: Request): Promise<Response> {
  if (input.method !== 'GET') return fetch(input);

  let waking = false;
  const markWaking = () => {
    if (!waking) {
      waking = true;
      beginWaking();
    }
  };

  try {
    let lastError: unknown;
    for (let attempt = 0; attempt <= RETRY_ATTEMPTS; attempt++) {
      try {
        const res = await fetch(input.clone());
        if (COLD_START_STATUSES.has(res.status) && attempt < RETRY_ATTEMPTS) {
          markWaking();
          await delay(RETRY_DELAY_MS);
          continue;
        }
        return res;
      } catch (err) {
        lastError = err;
        if (attempt < RETRY_ATTEMPTS) {
          markWaking();
          await delay(RETRY_DELAY_MS);
          continue;
        }
      }
    }
    throw lastError;
  } finally {
    if (waking) endWaking();
  }
}

const client = createClient<paths>({ baseUrl: API_BASE, fetch: resilientFetch });

export async function fetchStats(): Promise<StatsInfo> {
  const { data, error } = await client.GET('/api/stats');
  if (error) throw new Error('Failed to fetch stats');
  return data;
}

export async function fetchStreak(): Promise<StreakInfo> {
  const { data, error } = await client.GET('/api/trends/streak');
  if (error) throw new Error('Failed to fetch streak');
  return data;
}

export async function fetchNarrative(seed?: string): Promise<Record<string, string>> {
  // @ts-expect-error - /api/narrative not yet in openapi-types if not regenerated
  const { data, error } = await client.GET('/api/narrative', {
    params: { query: { ...(seed ? { seed } : {}) } },
  });
  if (error) throw new Error('Failed to fetch narrative');
  return data as Record<string, string>;
}

export async function fetchHeatmap(year: number): Promise<Record<string, number>> {
  const { data, error } = await client.GET('/api/heatmap', { params: { query: { year } } });
  if (error) throw new Error('Failed to fetch heatmap data');
  return data;
}

export async function fetchHourlyTrends(): Promise<Record<string, number>> {
  const { data, error } = await client.GET('/api/trends/hourly');
  if (error) throw new Error('Failed to fetch hourly trends');
  return data;
}

export async function fetchPunchcard(): Promise<Record<string, number>> {
  const { data, error } = await client.GET('/api/trends/punchcard');
  if (error) throw new Error('Failed to fetch punchcard data');
  return data;
}

export async function fetchMonthlyTrends(): Promise<MonthlyTrendInfo[]> {
  const { data, error } = await client.GET('/api/trends/monthly');
  if (error) throw new Error('Failed to fetch monthly trends');
  return data;
}

export async function fetchTopArtists(
  range: TimeRange,
  limit: number = 15,
  page: number = 1,
  search?: string,
): Promise<TopArtistsResponse> {
  const { data, error } = await client.GET('/api/top-artists', {
    params: { query: { range, limit, page, ...(search ? { search } : {}) } },
  });
  if (error) throw new Error('Failed to fetch top artists');
  return data;
}

export async function fetchTopTracks(
  range: TimeRange,
  limit: number = 15,
  page: number = 1,
  search?: string,
): Promise<TopTracksResponse> {
  const { data, error } = await client.GET('/api/top-tracks', {
    params: { query: { range, limit, page, ...(search ? { search } : {}) } },
  });
  if (error) throw new Error('Failed to fetch top tracks');
  return data;
}

export async function generateWrapped(
  period: 'year' | 'quarter' | 'month',
  year: number,
  quarter: WrappedQuarter,
  month: WrappedMonth,
): Promise<WrappedDataInfo> {
  const { data, error } = await client.GET('/api/wrapped', {
    params: {
      query: {
        year,
        ...(period === 'quarter' ? { quarter } : {}),
        ...(period === 'month' ? { month } : {}),
      },
    },
  });
  if (error) {
    throw new Error((error as { detail?: string }).detail || 'Failed to generate Wrapped.');
  }
  return data;
}

export async function triggerSync(mode: SyncMode): Promise<SyncStartInfo> {
  const token = localStorage.getItem('syncToken') ?? '';
  const { data, error } = await client.POST('/api/sync', {
    params: { query: { mode } },
    headers: { 'X-Sync-Token': token },
  });
  if (error) {
    throw new Error((error as { detail?: string }).detail || 'Sync failed to start.');
  }
  return data;
}

export async function fetchRecentListens(
  limit: number = 50,
  before_ts?: number,
  before_id?: number,
  anchor_date?: string,
): Promise<ListenEntry[]> {
  const { data, error } = await client.GET('/api/recent', {
    params: {
      query: {
        limit,
        ...(before_ts !== undefined ? { before_ts } : {}),
        ...(before_id !== undefined ? { before_id } : {}),
        ...(anchor_date !== undefined ? { anchor_date } : {}),
      },
    },
  });
  if (error) throw new Error('Failed to fetch recent listens');
  return data;
}

export async function getSyncStatus(): Promise<SyncStatusInfo> {
  const { data, error } = await client.GET('/api/sync/status');
  if (error) throw new Error('Failed to fetch sync status');
  return data;
}

export async function fetchPlayingNow(): Promise<PlayingNowInfo> {
  try {
    const { data } = await client.GET('/api/playing-now');
    return data ?? { is_playing: false };
  } catch {
    return { is_playing: false };
  }
}

/** DB-only pre-population: no LB call, responds in ~50ms. */
export async function fetchLastPlayed(): Promise<PlayingNowInfo> {
  try {
    const { data } = await client.GET('/api/last-played');
    return data ?? { is_playing: false };
  } catch {
    return { is_playing: false };
  }
}

export async function fetchTrackStats(
  artist: string,
  title: string,
  album?: string | null,
): Promise<TrackStatsInfo> {
  const { data, error } = await client.GET('/api/track-stats', {
    params: { query: { artist, title, ...(album ? { album } : {}) } },
  });
  if (error) throw new Error('Failed to fetch track stats');
  return data;
}

export async function fetchTrackStatsBatch(
  tracks: TrackBatchRequestItem[],
): Promise<TrackBatchResponseItem[]> {
  const { data, error } = await client.POST('/api/track-stats/batch', { body: tracks });
  if (error) throw new Error('Failed to fetch batch track stats');
  return data;
}

export async function fetchOnThisDay(): Promise<OnThisDayGroup[]> {
  const { data, error } = await client.GET('/api/on-this-day');
  if (error) throw new Error('Failed to fetch on-this-day data');
  return data;
}

export async function fetchDayListens(dateStr: string): Promise<ListenEntry[]> {
  const { data, error } = await client.GET('/api/day/{date_str}', {
    params: { path: { date_str: dateStr } },
  });
  if (error) throw new Error('Failed to fetch day listens');
  return data;
}

export async function fetchWeeklyBreakdown(
  year: number,
  month: number,
): Promise<WeeklyBreakdownItem[]> {
  const { data, error } = await client.GET('/api/trends/monthly/{year}/{month}/weekly', {
    params: { path: { year, month } },
  });
  if (error) throw new Error('Failed to fetch weekly breakdown');
  return data;
}

export async function fetchTopArtistTrends(
  year: number,
  limit?: number,
): Promise<TopArtistTrendsResponse> {
  const { data, error } = await client.GET('/api/top-artist-trends', {
    params: { query: { year, ...(limit !== undefined ? { limit } : {}) } },
  });
  if (error) throw new Error('Failed to fetch top artist trends');
  return data;
}

export async function fetchArtistTrackTrends(
  artist: string,
  year: number,
  limit?: number,
): Promise<ArtistTrendResponse> {
  const { data, error } = await client.GET('/api/artist-trend', {
    params: { query: { artist, year, ...(limit !== undefined ? { limit } : {}) } },
  });
  if (error) throw new Error('Failed to fetch artist track trends');
  return data;
}
