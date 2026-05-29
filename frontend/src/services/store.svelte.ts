import type { StatsInfo, StreakInfo, ArtistInfo, TrackInfo, WrappedDataInfo, MonthlyTrendInfo } from './api';

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
    console.log("[cache] Store cache cleared.");
  }
}

export const appCache = new AppCache();
