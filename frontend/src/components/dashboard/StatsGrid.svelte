<script lang="ts">
  import type { StatsInfo } from '../../services/api';

  // Svelte 5 props
  let { stats }: { stats: StatsInfo } = $props();
</script>

<div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
  <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4">
    <div class="stat-title text-xs font-semibold uppercase opacity-60">Total Scrobbles</div>
    <div class="stat-value text-2xl font-black text-primary mt-1">{stats.total_listens.toLocaleString()}</div>
    <div class="stat-desc text-[9px] opacity-40 mt-1">all-time collection</div>
  </div>
  
  <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4">
    <div class="stat-title text-xs font-semibold uppercase opacity-60">Unique Artists</div>
    <div class="stat-value text-2xl font-black text-secondary mt-1">{stats.unique_artists.toLocaleString()}</div>
    <div class="stat-desc text-[9px] opacity-40 mt-1">diverse creators</div>
  </div>

  <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4">
    <div class="stat-title text-xs font-semibold uppercase opacity-60">Unique Tracks</div>
    <div class="stat-value text-2xl font-black text-accent mt-1">{stats.unique_tracks.toLocaleString()}</div>
    <div class="stat-desc text-[9px] opacity-40 mt-1">different songs</div>
  </div>

  <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4 text-base-content">
    <div class="stat-title text-xs font-semibold uppercase opacity-60 text-base-content/60">Active Days</div>
    <div class="stat-value text-2xl font-black mt-1">{stats.days_active.toLocaleString()}</div>
    <div class="stat-desc text-[9px] opacity-40 mt-1">total days logged</div>
  </div>

  <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4 text-base-content">
    <div class="stat-title text-xs font-semibold uppercase opacity-60 text-base-content/60">Scrobbles/Day</div>
    <div class="stat-value text-2xl font-black mt-1">{stats.avg_per_day}</div>
    <div class="stat-desc text-[9px] opacity-40 mt-1">daily play rate</div>
  </div>

  <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4 text-base-content">
    <div class="stat-title text-xs font-semibold uppercase opacity-60 text-base-content/60">Top Source</div>
    <div class="stat-value text-xl font-bold truncate mt-1 capitalize">{stats.top_source.replace('_', ' ')}</div>
    <div class="stat-desc text-[9px] opacity-40 mt-1">primary music pipeline</div>
  </div>
</div>
