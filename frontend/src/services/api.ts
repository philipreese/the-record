import type { components, paths } from './api-types';

type _TopArtistsQuery = NonNullable<paths['/api/top-artists']['get']['parameters']['query']>;
export type TimeRange = NonNullable<_TopArtistsQuery['range']>;

type _SyncQuery = NonNullable<paths['/api/sync']['post']['parameters']['query']>;
export type SyncMode = NonNullable<_SyncQuery['mode']>;

type _WrappedQuery = NonNullable<paths['/api/wrapped']['get']['parameters']['query']>;
export type WrappedQuarter = NonNullable<_WrappedQuery['quarter']>;
export type WrappedMonth = NonNullable<_WrappedQuery['month']>;

export type StatsInfo = components['schemas']['StatsSummaryResponse'];
export type StreakInfo = components['schemas']['StreakStatsResponse'];
export type ArtistInfo = components['schemas']['ArtistInfo'];
export type TrackInfo = components['schemas']['TrackInfo'];
export type MonthlyTrendInfo = components['schemas']['MonthlyTrendInfo'];
export type SyncStatusInfo = components['schemas']['SyncStatusResponse'];
export type WrappedDataInfo = components['schemas']['WrappedDataResponse'];
export type ListenEntry = components['schemas']['ListenEntry'];
export type SyncStartInfo = components['schemas']['SyncStartResponse'];

const API_BASE = import.meta.env.VITE_API_BASE || '';

async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  return fetch(url, options);
}

export async function fetchStats(): Promise<StatsInfo> {
  const res = await apiFetch('/api/stats');
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchStreak(): Promise<StreakInfo> {
  const res = await apiFetch('/api/trends/streak');
  if (!res.ok) throw new Error('Failed to fetch streak');
  return res.json();
}

export async function fetchHeatmap(year: number): Promise<Record<string, number>> {
  const res = await apiFetch(`/api/heatmap?year=${year}`);
  if (!res.ok) throw new Error('Failed to fetch heatmap data');
  return res.json();
}

export async function fetchHourlyTrends(): Promise<Record<string, number>> {
  const res = await apiFetch('/api/trends/hourly');
  if (!res.ok) throw new Error('Failed to fetch hourly trends');
  return res.json();
}

export async function fetchMonthlyTrends(): Promise<MonthlyTrendInfo[]> {
  const res = await apiFetch('/api/trends/monthly');
  if (!res.ok) throw new Error('Failed to fetch monthly trends');
  return res.json();
}

export async function fetchTopArtists(range: TimeRange, limit: number = 15): Promise<ArtistInfo[]> {
  const res = await apiFetch(`/api/top-artists?range=${range}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch top artists');
  return res.json();
}

export async function fetchTopTracks(range: TimeRange, limit: number = 15): Promise<TrackInfo[]> {
  const res = await apiFetch(`/api/top-tracks?range=${range}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch top tracks');
  return res.json();
}

export async function generateWrapped(
  period: 'year' | 'quarter' | 'month',
  year: number,
  quarter: WrappedQuarter,
  month: WrappedMonth,
): Promise<WrappedDataInfo> {
  const queryParams: string[] = [];
  queryParams.push(`year=${year}`);
  if (period === 'quarter') queryParams.push(`quarter=${quarter}`);
  if (period === 'month') queryParams.push(`month=${month}`);

  const res = await apiFetch(`/api/wrapped?${queryParams.join('&')}`);
  if (!res.ok) {
    const errData = await res.json();
    throw new Error(errData.detail || 'Failed to generate Wrapped.');
  }
  return res.json();
}

export async function triggerSync(forceFull: boolean): Promise<SyncStartInfo> {
  const url = forceFull ? '/api/sync?mode=full' : '/api/sync';
  const token = localStorage.getItem('syncToken') ?? '';
  const res = await apiFetch(url, {
    method: 'POST',
    headers: { 'X-Sync-Token': token },
  });
  if (!res.ok) {
    const errData = await res.json();
    throw new Error(errData.detail || 'Sync failed to start.');
  }
  return res.json();
}

export async function fetchRecentListens(
  limit: number = 50,
  before_ts?: number,
  before_id?: number,
): Promise<ListenEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (before_ts !== undefined) params.set('before_ts', String(before_ts));
  if (before_id !== undefined) params.set('before_id', String(before_id));
  const res = await apiFetch(`/api/recent?${params}`);
  if (!res.ok) throw new Error('Failed to fetch recent listens');
  return res.json();
}

export async function getSyncStatus(): Promise<SyncStatusInfo> {
  const res = await apiFetch('/api/sync/status');
  if (!res.ok) throw new Error('Failed to fetch sync status');
  return res.json();
}
