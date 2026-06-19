import {
  triggerSync,
  getSyncStatus,
  fetchStats,
  fetchRecentListens,
  fetchPlayingNow,
  fetchLastPlayed,
  fetchNarrative,
  registerWakingListener,
  fetchTrackStatsBatch,
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
import type { OnThisDayGroup } from './api';
import { getDominantColor } from '../utils/dominantColor';
import { themeManager } from './theme.svelte';

class AppCache {
  // Track Stats Cache (unified across all views)
  trackStats = $state<Record<string, TrackStatsInfo | null>>({});
  private inFlightStatsKeys = new Set<string>();

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

  // Recent Listens Cache
  recentListens = $state<ListenEntry[]>([]);
  recentScrollOffset = $state(0);
  recentExhausted = $state(false);

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
  lastMirrorResult = $state<{ synced: number; deleted: number } | null>(null);
  private pollInterval: ReturnType<typeof setInterval> | null = null;

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
    this.recentListens = [];
    this.recentScrollOffset = 0;
    this.recentExhausted = false;
    this.trackStats = {};
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

  // Now Playing
  playingNow = $state<PlayingNowInfo | null>(null);
  private _playingPollInterval: ReturnType<typeof setInterval> | null = null;
  private _pollingInFlight = false;
  // How many consecutive empty polls while we were showing "now playing".
  // LB's playing-now endpoint has brief keep-alive gaps; don't flip to "last played"
  // on a single miss — wait for 2 consecutive empty responses (~40s) before switching.
  private _notPlayingCount = 0;
  private readonly NOT_PLAYING_GRACE = 3;
  // Tracks the last URL we extracted a color from, so we don't re-extract on every poll.
  private _lastExtractedCoverUrl: string | null = null;

  private _poll = async () => {
    if (document.visibilityState === 'hidden') return;
    if (this._pollingInFlight) return;
    this._pollingInFlight = true;
    try {
      const result = await fetchPlayingNow();
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
      // _poll already runs every 20s, so within one cycle of the backend coming back
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
      // LB result. During the grace period this.playingNow still holds the previous
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
    } catch {
      // silently skip failed polls
    } finally {
      this._pollingInFlight = false;
    }
  };

  private _onVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      this._poll();
    }
  };

  startPlayingNowPolling() {
    if (this._playingPollInterval !== null) return;
    // Pre-populate immediately from DB (no LB call, ~50ms) so the widget is
    // visible at once rather than blank for the duration of the first LB fetch.
    fetchLastPlayed()
      .then((result) => {
        if (!this.playingNow && result.last_played) {
          this.playingNow = result;
        }
      })
      .catch(() => {});
    // Eagerly fetch stats + narrative so the UI has content immediately,
    // independent of playing-now polling and sync completion timing.
    Promise.all([fetchStats(), fetchNarrative(this.narrativeSeed)])
      .then(([s, n]) => {
        this.stats = s;
        this.narrative = n;
        this.statsLoaded = true;
      })
      .catch(() => {});

    this._poll();
    this._playingPollInterval = setInterval(this._poll, 20_000);
    document.addEventListener('visibilitychange', this._onVisibilityChange);

    // Trigger an initial soft background sync on page load to fetch new scrobbles
    // since the last session even if no music is actively playing right now.
    this.runSync('normal', true);
  }

  // Centralized sync task runner.
  // soft=true: only refresh recentListens after completion (auto track-change syncs).
  // soft=false (default): full cache wipe, used for user-triggered syncs.
  async runSync(mode: SyncMode = 'normal', soft = false) {
    if (this.isSyncing) return;
    this.isSyncing = true;
    this.syncError = null;
    this.syncStatus = null;
    if (mode === 'mirror') this.lastMirrorResult = null;

    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }

    try {
      await triggerSync(mode);

      // Poll every 2 seconds
      this.pollInterval = setInterval(async () => {
        try {
          const status = await getSyncStatus();
          this.syncStatus = status;

          if (status.finished) {
            if (this.pollInterval) {
              clearInterval(this.pollInterval);
              this.pollInterval = null;
            }
            this.isSyncing = false;
            if (!status.error && status.mode === 'mirror') {
              this.lastMirrorResult = {
                synced: status.synced_count,
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
                const [s, n] = await Promise.all([
                  fetchStats(),
                  fetchNarrative(this.narrativeSeed),
                ]);
                this.stats = s;
                this.narrative = n;
              } catch {
                // Non-fatal
              }
            } else {
              this.invalidate();
              try {
                const [s, n] = await Promise.all([
                  fetchStats(),
                  fetchNarrative(this.narrativeSeed),
                ]);
                this.stats = s;
                this.narrative = n;
                this.statsLoaded = true;
              } catch {
                // Non-fatal — sidebar shows "Connecting…" until OverviewView mounts.
              }
            }
          }
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
