import {
  triggerSync,
  getSyncStatus,
  fetchStats,
  fetchPlayingNow,
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

class AppCache {
  // Dashboard / Stats Cache
  stats = $state<StatsInfo | null>(null);
  streak = $state<StreakInfo | null>(null);
  heatmap = $state<Record<number, Record<string, number>>>({});
  hourlyTrends = $state<Record<string, number>>({});
  monthlyTrends = $state<MonthlyTrendInfo[]>([]);
  statsLoaded = $state(false);

  // Top Charts Cache (keyed by range: '30' | '90' | '365' | 'all')
  charts = $state<Record<string, { artists: ArtistInfo[]; tracks: TrackInfo[] }>>({});

  // Wrapped/Reviews Cache (keyed by period + parameters)
  wrapped = $state<Record<string, WrappedDataInfo>>({});

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
    this.monthlyTrends = [];
    this.statsLoaded = false;
    this.charts = {};
    this.wrapped = {};
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
  private readonly NOT_PLAYING_GRACE = 2;

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
          this.runSync(false);
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
    this._poll();
    this._playingPollInterval = setInterval(this._poll, 20_000);
    document.addEventListener('visibilitychange', this._onVisibilityChange);
  }

  // Centralized sync task runner
  async runSync(forceFull = false) {
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
