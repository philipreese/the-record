import type { ListenEntry } from '../services/api';

const LB_SOURCES = new Set(['listenbrainz', 'listenbrainz_sync']);

const SOURCE_LABELS: Record<string, string> = {
  listenbrainz: 'ListenBrainz',
  listenbrainz_sync: 'ListenBrainz',
  youtube: 'YouTube Music',
  youtube_music: 'YouTube Music',
  google_takeout: 'Takeout',
  last_fm: 'Last.fm',
};

/** Returns a display label for non-LB sources, or null for ListenBrainz entries (badge hidden by design). */
export function sourceLabel(source: string): string | null {
  if (LB_SOURCES.has(source)) return null;
  return SOURCE_LABELS[source] ?? 'Other';
}

/** Always returns a display label — use in detail panels where the source should always be shown. */
export function sourceLabelFull(source: string): string {
  return SOURCE_LABELS[source] ?? 'Other';
}

/** HH:MM in the user's locale. */
export function timeOnly(unix_ts: number): string {
  return new Date(unix_ts * 1000).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Short relative time for any entry, always returns a non-empty string. */
export function relativeTimeShort(unix_ts: number): string {
  const diff = Math.floor(Date.now() / 1000) - unix_ts;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  if (diff < 86400 * 30) return `${Math.floor(diff / (86400 * 7))}w ago`;
  if (diff < 86400 * 365) return `${Math.floor(diff / (86400 * 30))}mo ago`;
  return `${Math.floor(diff / (86400 * 365))}yr ago`;
}

/** Full absolute datetime string for use in title/tooltip attributes. */
export function absoluteTime(unix_ts: number): string {
  return new Date(unix_ts * 1000).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Patch a listen list after a correction save or revert.
 * The exact listen (by id) is replaced; sibling listens of the same track are
 * updated by their artist/title fields when a track-scope correction was applied.
 */
export function patchWithCorrection(listens: ListenEntry[], updated: ListenEntry): ListenEntry[] {
  return listens.map((e) => {
    if (e.id === updated.id) return updated;
    // Track-scope: match by canonical_track_id (update) or by raw artist/title (initial save)
    const sameTrack =
      (updated.track_id != null && e.track_id === updated.track_id) ||
      (updated.original_artist != null &&
        updated.original_title != null &&
        e.artist === updated.original_artist &&
        e.title === updated.original_title);
    if (!sameTrack) return e;
    return {
      ...e,
      artist: updated.artist,
      title: updated.title,
      album: updated.album,
      duration_secs: updated.duration_secs,
      recording_mbid: updated.recording_mbid,
      has_track_correction: updated.has_track_correction,
      track_id: updated.track_id,
    };
  });
}

/** Computes dynamic play count range text for legend tooltips relative to the maximum count of the dataset. */
export function getLegendText(level: number, maxCount: number): string {
  if (level === 0) return '0 plays';
  if (maxCount <= 1) {
    return level === 1 ? '1 play' : '0 plays';
  }
  const low = Math.round(maxCount * 0.25);
  const med = Math.round(maxCount * 0.5);
  const high = Math.round(maxCount * 0.75);

  if (level === 1) {
    const to = Math.max(1, low);
    return to === 1 ? '1 play' : `1–${to} plays`;
  }
  if (level === 2) {
    const from = Math.max(1, low) + 1;
    const to = Math.max(from, med);
    return from === to ? `${from} play${from === 1 ? '' : 's'}` : `${from}–${to} plays`;
  }
  if (level === 3) {
    const from = Math.max(2, med) + 1;
    const to = Math.max(from, high);
    return from === to ? `${from} play${from === 1 ? '' : 's'}` : `${from}–${to} plays`;
  }
  if (level === 4) {
    const from = Math.max(3, high) + 1;
    const to = maxCount;
    if (from >= to) return `${to} play${to === 1 ? '' : 's'}`;
    return `${from}–${to} plays`;
  }
  return '';
}
