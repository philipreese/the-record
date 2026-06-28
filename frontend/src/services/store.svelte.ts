import {
  triggerSync,
  getSyncStatus,
  fetchStats,
  fetchRecentListens,
  fetchLastPlayed,
  fetchNarrative,
  registerWakingListener,
  fetchTrackStatsBatch,
  fetchCoverArt,
  type NarrativeData,
  type SyncMode,
  type StatsInfo,
  type StreakInfo,
  type ArtistInfo,
  type TrackInfo,
  type WrappedDataInfo,
  type MonthlyTrendInfo,
  type SyncStatusInfo,
  type ListenEntry,
  type PlayingNowInfo,
  type TrackStatsInfo,
} from './api';
import type { OnThisDayGroup, ArtistAnniversary } from './api';
import { getDominantColor } from '../utils/dominantColor';
import { themeManager } from './theme.svelte';
import { SyncSocket } from './sync-socket';
import { PlayingNowSSE } from './playing-now-sse';

class AppCache {
  // Track Stats Cache (unified across all views)
  trackStats = $state<Record<string, TrackStatsInfo | null>>({});
  private inFlightStatsKeys = new Set<string>();

  // Cover Art Cache (keyed by listen ID)
  coverArt = $state<Record<number, string | null>>({});

  // Dashboard / Stats Cache
  stats = $state<StatsInfo | null>(null);
  streak = $state<StreakInfo | null>(null);
  heatmap = $state<Record<number, Record<string, number>>>({});
  hourlyTrends = $state<Record<string, number>>({});
  punchcardData = $state<Record<string, number>>({});
  monthlyTrends = $state<MonthlyTrendInfo[]>([]);
  statsLoaded = $state(false);

  // Narrative Engine Cache
  narrative = $state<NarrativeData>({ plain: {}, rich: {} });
  narrativeSeed = $state<string | undefined>(undefined);

  // Top Charts Cache (keyed by range: '30' | '90' | '365' | 'all')
  charts = $state<
    Record<
      string,
      { artists: ArtistInfo[]; totalArtists?: number; tracks: TrackInfo[]; totalTracks?: number }
    >
  >({});

  // Wrapped/Reviews Cache (keyed by period + parameters)
  wrapped = $state<Record<string, WrappedDataInfo>>({});

  // On This Day Cache
  onThisDay = $state<OnThisDayGroup[]>([]);
  onThisDayAnniversaries = $state<ArtistAnniversary[]>([]);

  // Recent Listens Cache
  recentListens = $state<ListenEntry[]>([]);
  recentScrollOffset = $state(0);
  recentExhausted = $state(false);
  recentAnchorDate = $state('');

  // Sync Authentication
  syncToken = $state<string>(
    typeof window !== 'undefined' ? (localStorage.getItem('syncToken') ?? '') : '',
  );

  setSyncToken(token: string) {
    this.syncToken = token.trim();
    if (typeof window !== 'undefined') localStorage.setItem('syncToken', this.syncToken);
  }

  // Centralized Sync State
  isSyncing = $state(false);
  syncStatus = $state<SyncStatusInfo | null>(null);
  syncError = $state<string | null>(null);
  lastMirrorResult = $state<{ synced: number; updated: number; deleted: number } | null>(null);
  private pollInterval: ReturnType<typeof setInterval> | null = null;
  private _currentSyncSoft = false;
  private _syncSocket: SyncSocket | null = null;

  // True while a cold-start retry is riding out a suspended backend/DB wake.
  isWakingUp = $state(false);

  constructor() {
    registerWakingListener((waking) => {
      this.isWakingUp = waking;
    });
  }

  // Clear cache on sync completion
  invalidate() {
    this.stats = null;
    this.streak = null;
    this.heatmap = {};
    this.hourlyTrends = {};
    this.punchcardData = {};
    this.monthlyTrends = [];
    this.statsLoaded = false;
    this.narrative = { plain: {}, rich: {} };
    this.charts = {};
    this.wrapped = {};
    this.onThisDay = [];
    this.onThisDayAnniversaries = [];
    this.recentListens = [];
    this.recentScrollOffset = 0;
    this.recentExhausted = false;
    this.recentAnchorDate = '';
    this.trackStats = {};
    this.coverArt = {};
    console.log('[cache] Store cache cleared.');
  }

  async refreshNarrative() {
    this.narrativeSeed = Math.random().toString(36).substring(7);
    try {
      this.narrative = await fetchNarrative(this.narrativeSeed);
    } catch {
      // ignore
    }
  }

  trackKey(entry: { artist: string; title: string; album?: string | null }): string {
    return `${entry.artist}||${entry.title}||${entry.album || ''}`;
  }

  async fetchTrackStatsForListens(listens: ListenEntry[]) {
    const uniqueTracksToFetch: { artist: string; title: string; key: string }[] = [];
    for (const entry of listens) {
      const statsKey = this.trackKey(entry);
      if (!(statsKey in this.trackStats) && !this.inFlightStatsKeys.has(statsKey)) {
        this.inFlightStatsKeys.add(statsKey);
        uniqueTracksToFetch.push({
          artist: entry.artist,
          title: entry.title,
          key: statsKey,
        });
      }
    }

    if (uniqueTracksToFetch.length === 0) return;

    try {
      const batchRes = await fetchTrackStatsBatch(
        uniqueTracksToFetch.map((t) => ({ artist: t.artist, title: t.title })),
      );

      for (let i = 0; i < uniqueTracksToFetch.length; i++) {
        const statsKey = uniqueTracksToFetch[i].key;
        const resItem = batchRes[i];
        if (resItem) {
          this.trackStats[statsKey] = {
            play_count: resItem.play_count,
            duration_secs: resItem.duration_secs ?? null,
          };
        } else {
          this.trackStats[statsKey] = { play_count: 0, duration_secs: null };
        }
      }
    } catch (err) {
      console.error('Failed to fetch batch track stats:', err);
      for (const t of uniqueTracksToFetch) {
        this.inFlightStatsKeys.delete(t.key);
      }
    }
  }

  async fetchCoverArtForListens(listens: ListenEntry[]) {
    const missing = listens.filter((e) => !(e.id in this.coverArt) && !e.cover_art_url);
    if (missing.length === 0) return;
    try {
      const result = await fetchCoverArt(
        missing.map((e) => ({
          id: e.id,
          artist: e.artist,
          title: e.title,
          recording_mbid: e.recording_mbid,
        })),
      );
      for (const [idStr, url] of Object.entries(result)) {
        if (url) this.coverArt[Number(idStr)] = url;
      }
    } catch {
      // silent — cover art is non-critical
    }
  }

  // Now Playing
  playingNow = $state<PlayingNowInfo | null>(null);
  private _playingNowSSE: PlayingNowSSE | null = null;
  private _sseInFlight = false;
  // How many consecutive empty pushes while we were showing "now playing".
  // LB's playing-now endpoint has brief keep-alive gaps; don't flip to "last played"
  // on a single miss — wait for 3 consecutive empty responses (~45s) before switching.
  private _notPlayingCount = 0;
  private readonly NOT_PLAYING_GRACE = 3;
  // Tracks the last URL we extracted a color from, so we don't re-extract on every push.
  private _lastExtractedCoverUrl: string | null = null;

  private _handlePlayingNow = async (result: PlayingNowInfo) => {
    if (document.visibilityState === 'hidden') return;
    if (this._sseInFlight) return;
    this._sseInFlight = true;
    try {
      const prev = this.playingNow;
      const wasPlaying = prev?.is_playing ?? false;

      if (result.is_playing) {
        this._notPlayingCount = 0;
        // Sync whenever we start playing or the track changes — the previous track was
        // just scrobbled and runSync's isSyncing guard prevents concurrent syncs.
        const trackChanged =
          !wasPlaying || result.artist !== prev?.artist || result.title !== prev?.title;
        this.playingNow = result;
        if (trackChanged) {
          this.runSync('normal', true);
        }
      } else if (wasPlaying) {
        // Grace period: hold the "now playing" state through brief LB API gaps.
        this._notPlayingCount++;
        if (this._notPlayingCount >= this.NOT_PLAYING_GRACE) {
          this.playingNow = result;
        }
      } else {
        this.playingNow = result;
      }

      // If baseline data never loaded (backend was down at startup), recover it now.
      // SSE pushes every 15s, so within one cycle of the backend coming back
      // the page will populate without a manual refresh.
      if (!this.statsLoaded) {
        Promise.all([fetchStats(), fetchNarrative(this.narrativeSeed)])
          .then(([s, n]) => {
            this.stats = s;
            this.narrative = n;
            this.statsLoaded = true;
          })
          .catch(() => {});
      }
      if (this.recentListens.length === 0 && !this.recentExhausted) {
        fetchRecentListens(50)
          .then((r) => {
            this.recentListens = r;
            if (r.length < 50) this.recentExhausted = true;
          })
          .catch(() => {});
      }

      // Extract ambient color from the *displayed* state (this.playingNow), not the raw
      // SSE payload. During the grace period this.playingNow still holds the previous
      // "now playing" entry, so we keep the track's color rather than switching to
      // last_played (which may have no art and would reset the accent to blue).
      const displayed = this.playingNow;
      const coverUrl = displayed?.is_playing
        ? (displayed.cover_art_url ?? null)
        : (displayed?.last_played?.cover_art_url ?? null);
      if (coverUrl !== this._lastExtractedCoverUrl) {
        this._lastExtractedCoverUrl = coverUrl;
        if (coverUrl) {
          getDominantColor(coverUrl).then((color) => {
            if (color) themeManager.setAmbientColor(color);
          });
        }
        // No art → keep last extracted color. setAmbientColor(null) would reset to
        // default blue, which is jarring when art is missing for one track mid-session.
      }
    } finally {
      this._sseInFlight = false;
    }
  };

  startPlayingNowPolling() {
    if (this._playingNowSSE !== null) return;
    // Pre-populate immediately from DB (no LB call, ~50ms) so the widget is
    // visible at once rather than blank until the first SSE push arrives.
    fetchLastPlayed()
      .then((result) => {
        if (!this.playingNow && result.last_played) {
          this.playingNow = result;
        }
      })
      .catch(() => {});
    // Eagerly fetch stats + narrative so the UI has content immediately,
    // independent of SSE push timing.
    Promise.all([fetchStats(), fetchNarrative(this.narrativeSeed)])
      .then(([s, n]) => {
        this.stats = s;
        this.narrative = n;
        this.statsLoaded = true;
      })
      .catch(() => {});

    this._playingNowSSE = new PlayingNowSSE(this._handlePlayingNow);
    this._playingNowSSE.connect();

    this._syncSocket = new SyncSocket(
      async (event) => {
        if (event.type === 'sync_complete' && this.isSyncing) {
          try {
            const status = await getSyncStatus();
            this.syncStatus = status;
            await this._finishSync(status, this._currentSyncSoft);
          } catch {
            // Fall through to polling loop
          }
        }
      },
      () => {
        // Trigger startup sync only once the WS is connected so sync_complete
        // is guaranteed to be received rather than firing before the socket is ready.
        this.runSync('normal', true);
      },
    );
    this._syncSocket.connect();
  }

  private async _finishSync(status: SyncStatusInfo, soft: boolean): Promise<void> {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.isSyncing = false;
    if (!status.error && status.mode === 'mirror') {
      this.lastMirrorResult = {
        synced: status.synced_count,
        updated: status.updated_count,
        deleted: status.deleted_count,
      };
    }
    if (status.error) {
      this.syncError = status.error;
    } else if (soft) {
      // Soft refresh: prepend any new listens without blanking the list.
      // Charts/heatmap are untouched so the page doesn't flash through loading states.
      try {
        const fresh = await fetchRecentListens(10);
        const existingIds = new Set(this.recentListens.map((e) => e.id));
        const newItems = fresh.filter((e) => !existingIds.has(e.id));
        if (newItems.length > 0) {
          this.recentListens = [...newItems, ...this.recentListens];
        }
      } catch {
        // Non-fatal
      }
      try {
        const [s, n] = await Promise.all([fetchStats(), fetchNarrative(this.narrativeSeed)]);
        this.stats = s;
        this.narrative = n;
      } catch {
        // Non-fatal
      }
    } else {
      this.invalidate();
      try {
        const [s, n] = await Promise.all([fetchStats(), fetchNarrative(this.narrativeSeed)]);
        this.stats = s;
        this.narrative = n;
        this.statsLoaded = true;
      } catch {
        // Non-fatal — sidebar shows "Connecting…" until OverviewView mounts.
      }
    }
  }

  // Centralized sync task runner.
  // soft=true: only refresh recentListens after completion (auto track-change syncs).
  // soft=false (default): full cache wipe, used for user-triggered syncs.
  async runSync(mode: SyncMode = 'normal', soft = false) {
    if (this.isSyncing) return;
    this.isSyncing = true;
    this._currentSyncSoft = soft;
    this.syncError = null;
    this.syncStatus = null;
    if (mode === 'mirror') this.lastMirrorResult = null;

    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }

    try {
      await triggerSync(mode);

      // Poll every 2 seconds as a fallback; the WebSocket sync_complete event
      // will short-circuit this loop when the socket is connected.
      this.pollInterval = setInterval(async () => {
        try {
          const status = await getSyncStatus();
          this.syncStatus = status;
          if (status.finished) await this._finishSync(status, soft);
        } catch (err) {
          if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
          }
          this.isSyncing = false;
          this.syncError = err instanceof Error ? err.message : String(err);
        }
      }, 2000);
    } catch (err) {
      this.isSyncing = false;
      this.syncError = err instanceof Error ? err.message : String(err);
    }
  }
}

export const appCache = new AppCache();
