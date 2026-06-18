<script lang="ts">
  import type { StatsInfo } from '../../services/api';
  import AnimatedCounter from './AnimatedCounter.svelte';
  import { tooltip } from '../../utils/tooltip';
  import { appCache } from '../../services/store.svelte';

  // Svelte 5 props
  let { stats }: { stats: StatsInfo } = $props();
</script>

<div class="grid grid-cols-2 sm:grid-cols-3 2xl:grid-cols-6 gap-x-8 gap-y-10 px-2">
  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">
      {appCache.narrative['stats.total_listens.label'] || 'Total Scrobbles'}
    </div>
    <div class="text-display-medium text-theme-text">
      <AnimatedCounter value={stats.total_listens} />
    </div>
    <div class="text-detail text-theme-faint">
      {appCache.narrative['stats.total_listens.detail'] || 'all-time collection'}
    </div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">
      {appCache.narrative['stats.unique_creators.label'] || 'Unique Creators'}
    </div>
    <div class="text-display-medium text-theme-accent">
      <AnimatedCounter value={stats.unique_artists} />
    </div>
    <div class="text-detail text-theme-faint">
      {appCache.narrative['stats.unique_creators.detail'] || 'diverse artists'}
    </div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">
      {appCache.narrative['stats.unique_tracks.label'] || 'Unique Tracks'}
    </div>
    <div class="text-display-medium text-theme-secondary">
      <AnimatedCounter value={stats.unique_tracks} />
    </div>
    <div class="text-detail text-theme-faint">
      {appCache.narrative['stats.unique_tracks.detail'] || 'different songs'}
    </div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">
      {appCache.narrative['stats.active_days.label'] || 'Active Days'}
    </div>
    <div class="text-display-medium text-theme-text">
      <AnimatedCounter value={stats.days_active} />
    </div>
    <div class="text-detail text-theme-faint">
      {appCache.narrative['stats.active_days.detail'] || 'total days logged'}
    </div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">
      {appCache.narrative['stats.avg_per_day.label'] || 'Daily Play Rate'}
    </div>
    <div class="text-display-medium text-theme-text">
      <AnimatedCounter value={stats.avg_per_day} />
    </div>
    <div class="text-detail text-theme-faint">
      {appCache.narrative['stats.avg_per_day.detail'] || 'plays per day'}
    </div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">
      {appCache.narrative['stats.top_source.label'] || 'Top Source'}
    </div>
    <div
      class="text-lg font-light tracking-wide truncate h-12 flex items-center capitalize text-theme-text"
      use:tooltip
    >
      {stats.top_source.replace('_', ' ')}
    </div>
    <div class="text-detail text-theme-faint">
      {appCache.narrative['stats.top_source.detail'] || 'music pipeline'}
    </div>
  </div>
</div>
