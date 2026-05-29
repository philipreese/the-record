export interface StatsInfo {
  total_listens: number;
  unique_artists: number;
  unique_tracks: number;
  days_active: number;
  avg_per_day: number;
  top_source: string;
}

export interface StreakInfo {
  current_streak: number;
  longest_streak: number;
}

export interface ArtistInfo {
  artist: string;
  play_count: number;
}

export interface TrackInfo {
  artist: string;
  title: string;
  play_count: number;
}

export interface WrappedDataInfo {
  total_plays: number;
  top_artist: { name: string; plays: number } | null;
  top_track: { artist: string; title: string; plays: number } | null;
  peak_day: { date: string; plays: number } | null;
  minutes_listened: number;
}

export interface SyncStatusInfo {
  running: boolean;
  finished: boolean;
  mode: string;
  batches_fetched: number;
  synced_count: number;
  lb_total: number;
  local_total: number;
  error: string | null;
}

export interface MonthlyTrendInfo {
  month: string;
  count: number;
}

export async function fetchStats(): Promise<StatsInfo> {
  const res = await fetch('/api/stats');
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchStreak(): Promise<StreakInfo> {
  const res = await fetch('/api/trends/streak');
  if (!res.ok) throw new Error('Failed to fetch streak');
  return res.json();
}

export async function fetchHeatmap(year: number): Promise<Record<string, number>> {
  const res = await fetch(`/api/heatmap?year=${year}`);
  if (!res.ok) throw new Error('Failed to fetch heatmap data');
  return res.json();
}

export async function fetchHourlyTrends(): Promise<Record<string, number>> {
  const res = await fetch('/api/trends/hourly');
  if (!res.ok) throw new Error('Failed to fetch hourly trends');
  return res.json();
}

export async function fetchMonthlyTrends(): Promise<MonthlyTrendInfo[]> {
  const res = await fetch('/api/trends/monthly');
  if (!res.ok) throw new Error('Failed to fetch monthly trends');
  return res.json();
}

export async function fetchTopArtists(range: string, limit: number = 15): Promise<ArtistInfo[]> {
  const res = await fetch(`/api/top-artists?range=${range}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch top artists');
  return res.json();
}

export async function fetchTopTracks(range: string, limit: number = 15): Promise<TrackInfo[]> {
  const res = await fetch(`/api/top-tracks?range=${range}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch top tracks');
  return res.json();
}

export async function generateWrapped(
  period: 'year' | 'quarter' | 'month',
  year: number,
  quarter: string,
  month: string
): Promise<WrappedDataInfo> {
  const queryParams: string[] = [];
  queryParams.push(`year=${year}`);
  if (period === 'quarter') queryParams.push(`quarter=${quarter}`);
  if (period === 'month') queryParams.push(`month=${month}`);

  const res = await fetch(`/api/wrapped?${queryParams.join('&')}`);
  if (!res.ok) {
    const errData = await res.json();
    throw new Error(errData.detail || "Failed to generate Wrapped.");
  }
  return res.json();
}

export async function triggerSync(forceFull: boolean): Promise<any> {
  const url = forceFull ? '/api/sync?mode=full' : '/api/sync';
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    const errData = await res.json();
    throw new Error(errData.detail || 'Sync failed to start.');
  }
  return res.json();
}

export async function getSyncStatus(): Promise<SyncStatusInfo> {
  const res = await fetch('/api/sync/status');
  if (!res.ok) throw new Error('Failed to fetch sync status');
  return res.json();
}
