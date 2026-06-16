import {
  triggerSync,
  getSyncStatus,
  fetchStats,
  fetchRecentListens,
  fetchPlayingNow,
  fetchLastPlayed,
  registerWakingListener,
  type StatsInfo,
  type StreakInfo,
  type ArtistInfo,
  type TrackInfo,
  type WrappedDataInfo,
  type MonthlyTrendInfo,
  type SyncStatusInfo,
  type ListenEntry,
  type PlayingNowInfo,
} from './api';
import type { OnThisDayGroup } from './api';
import { getDominantColor } from '../utils/dominantColor';
import { themeManager } from './theme.svelte';

class AppCache {
  // Dashboard / Stats Cache
  stats = $state<StatsInfo | null>(null);
  streak = $state<StreakInfo | null>(null);
  heatmap = $state<Record<number, Record<string, number>>>({});
  hourlyTrends = $state<Record<string, number>>({});
  punchcardData = $state<Record<string, number>>({});
  monthlyTrends = $state<MonthlyTrendInfo[]>([]);
  statsLoaded = $state(false);

  // Top Charts Cache (keyed by range: '30' | '90' | '365' | 'all')
  charts = $state<Record<string, { artists: ArtistInfo[]; tracks: TrackInfo[] }>>({});

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
    this.charts = {};
    this.wrapped = {};
    this.onThisDay = [];
    this.recentListens = [];
    this.recentScrollOffset = 0;
    this.recentExhausted = false;
    console.log('[cache] Store cache cleared.');
  }

  // Now Playing
  playingNow = $state<PlayingNowInfo | null>(null);
  private _playingPollInterval: ReturnType<typeof setInterval> | null = null;
  // How many consecutive empty polls while we were showing "now playing".
  // LB's playing-now endpoint has brief keep-alive gaps; don't flip to "last played"
  // on a single miss — wait for 2 consecutive empty responses (~40s) before switching.
  private _notPlayingCount = 0;
  private readonly NOT_PLAYING_GRACE = 3;
  // Tracks the last URL we extracted a color from, so we don't re-extract on every poll.
  private _lastExtractedCoverUrl: string | null = null;

  private _poll = async () => {
    if (document.visibilityState === 'hidden') return;
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
          this.runSync(false, true);
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
        fetchStats()
          .then((s) => {
            this.stats = s;
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
    this._poll();
    this._playingPollInterval = setInterval(this._poll, 20_000);
    document.addEventListener('visibilitychange', this._onVisibilityChange);
  }

  // Centralized sync task runner.
  // soft=true: only refresh recentListens after completion (used by auto track-change syncs
  // so the rest of the page doesn't flash through loading states).
  // soft=false (default): full cache wipe, used for user-triggered syncs.
  async runSync(forceFull = false, soft = false) {
    if (this.isSyncing) return;
    this.isSyncing = true;
    this.syncError = null;
    this.syncStatus = null;

    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }

    try {
      await triggerSync(forceFull);

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
                this.stats = await fetchStats();
              } catch {
                // Non-fatal
              }
            } else {
              this.invalidate();
              try {
                this.stats = await fetchStats();
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
