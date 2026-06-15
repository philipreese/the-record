import {
  triggerSync,
  getSyncStatus,
  fetchStats,
  type StatsInfo,
  type StreakInfo,
  type ArtistInfo,
  type TrackInfo,
  type WrappedDataInfo,
  type MonthlyTrendInfo,
  type SyncStatusInfo,
  type ListenEntry,
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
    typeof window !== 'undefined' ? (localStorage.getItem('syncToken') ?? '') : ''
  );

  setSyncToken(token: string) {
    this.syncToken = token.trim();
    if (typeof window !== 'undefined') localStorage.setItem('syncToken', this.syncToken);
  }

  // Centralized Sync State
  isSyncing = $state(false);
  syncStatus = $state<SyncStatusInfo | null>(null);
  syncError = $state<string | null>(null);
  private pollInterval: any = null;

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
    console.log("[cache] Store cache cleared.");
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
