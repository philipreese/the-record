<script lang="ts">
  import type { StatsInfo } from '../../services/api';

  // Svelte 5 props
  let { stats }: { stats: StatsInfo } = $props();
</script>

<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-8 gap-y-10 px-2">
  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">Total Scrobbles</div>
    <div class="text-display-medium text-theme-text">{stats.total_listens.toLocaleString()}</div>
    <div class="text-detail text-theme-faint">all-time collection</div>
  </div>
  
  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">Unique Creators</div>
    <div class="text-display-medium text-theme-accent">{stats.unique_artists.toLocaleString()}</div>
    <div class="text-detail text-theme-faint">diverse artists</div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">Unique Tracks</div>
    <div class="text-display-medium text-theme-secondary">{stats.unique_tracks.toLocaleString()}</div>
    <div class="text-detail text-theme-faint">different songs</div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">Active Days</div>
    <div class="text-display-medium text-theme-text">{stats.days_active.toLocaleString()}</div>
    <div class="text-detail text-theme-faint">total days logged</div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">Daily Play Rate</div>
    <div class="text-display-medium text-theme-text">{stats.avg_per_day}</div>
    <div class="text-detail text-theme-faint">plays per day</div>
  </div>

  <div class="space-y-1.5">
    <div class="text-caps text-theme-muted">Top Source</div>
    <div class="text-lg font-light tracking-wide truncate h-[3rem] flex items-center capitalize text-theme-text">
      {stats.top_source.replace('_', ' ')}
    </div>
    <div class="text-detail text-theme-faint">music pipeline</div>
  </div>
</div>
