<script lang="ts">
  import type { TimeRange } from '../../services/api';
  import type { ArtistStatsWithAlbums } from '../../services/artist-graphql';

  let {
    stats,
    timeRange,
  }: {
    stats: ArtistStatsWithAlbums;
    timeRange: TimeRange;
  } = $props();

  function formatDate(dateStr: string): string {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  function formatTs(ts: number): string {
    return new Date(ts * 1000).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
</script>

<div class="flex flex-col gap-3">
  <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
    <div class="stats-box flex flex-col gap-1 p-5">
      <div class="text-2xl font-mono font-light text-theme-text">
        {stats.total_plays.toLocaleString()}
      </div>
      <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">Plays</div>
      {#if timeRange !== 'all' && stats.plays_since_discovery != null && stats.plays_since_discovery !== stats.total_plays}
        <div class="text-[10px] font-mono text-theme-muted/50 mt-1">
          {stats.plays_since_discovery.toLocaleString()} all-time
        </div>
      {/if}
    </div>

    <div class="stats-box flex flex-col gap-1 p-5">
      <div class="text-2xl font-mono font-light text-theme-text">
        {stats.rank != null ? `#${stats.rank}` : '—'}
      </div>
      <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">All-time rank</div>
    </div>

    {#if stats.peak_day}
      <div class="stats-box flex flex-col gap-1 p-5 col-span-2 md:col-span-1">
        <div class="text-2xl font-mono font-light text-theme-text">
          {stats.peak_day.plays.toLocaleString()}
        </div>
        <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">
          Peak day · {formatDate(stats.peak_day.date)}
        </div>
      </div>
    {/if}
  </div>

  {#if stats.first_listen_ts}
    <div class="flex items-center gap-2 flex-wrap text-xs font-mono text-theme-muted/60 px-1">
      <span>First heard</span>
      <span class="text-theme-muted">{formatTs(stats.first_listen_ts)}</span>
      {#if stats.plays_since_discovery != null}
        <span>&bull;</span>
        <span>{stats.plays_since_discovery.toLocaleString()} plays in your library</span>
      {/if}
    </div>
  {/if}
</div>
