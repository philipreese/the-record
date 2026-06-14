const LB_SOURCES = new Set(['listenbrainz', 'listenbrainz_sync']);

const SOURCE_LABELS: Record<string, string> = {
  youtube: 'YouTube Music',
  youtube_music: 'YouTube Music',
  google_takeout: 'Takeout',
  last_fm: 'Last.fm',
};

/** Returns a display label for non-LB sources, or null for ListenBrainz entries. */
export function sourceLabel(source: string): string | null {
  if (LB_SOURCES.has(source)) return null;
  return SOURCE_LABELS[source] ?? 'Other';
}

/** HH:MM in the user's locale. */
export function timeOnly(unix_ts: number): string {
  return new Date(unix_ts * 1000).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Short relative time for entries within the last 7 days.
 * Returns empty string for older entries — the day divider already provides the date.
 */
export function relativeTimeShort(unix_ts: number): string {
  const diff = Math.floor(Date.now() / 1000) - unix_ts;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  return '';
}

/** Full absolute datetime string for use in title/tooltip attributes. */
export function absoluteTime(unix_ts: number): string {
  return new Date(unix_ts * 1000).toLocaleString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
    year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}
