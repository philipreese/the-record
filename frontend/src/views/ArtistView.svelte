<script lang="ts">
  import { fetchArtistStats, type ArtistStatsInfo, type TimeRange } from '../services/api';
  import { router } from '../services/router.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import HourlyHeatClock from '../components/HourlyHeatClock.svelte';

  let artistName = $derived(router.route.type === 'artist' ? router.route.name : '');
  let timeRange = $derived<TimeRange>((router.params.get('range') as TimeRange) ?? 'all');

  let stats = $state<ArtistStatsInfo | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  const rangeOptions: [TimeRange, string][] = [
    ['30', '30 Days'],
    ['90', '90 Days'],
    ['365', '1 Year'],
    ['all', 'All Time'],
  ];

  $effect(() => {
    const name = artistName;
    const range = timeRange;
    if (!name) return;

    loading = true;
    error = null;

    fetchArtistStats(name, range)
      .then((data) => {
        stats = data;
      })
      .catch(() => {
        error = 'Failed to load artist stats. Please try again.';
      })
      .finally(() => {
        loading = false;
      });
  });

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

  let maxMonthlyCount = $derived(
    stats ? Math.max(...stats.monthly_trends.map((t) => t.count), 1) : 1,
  );
</script>

<PageHeader title={artistName}>
  {#snippet actions()}
    <button
      class="btn-nav-text text-sm font-mono tracking-widest uppercase shrink-0"
      onclick={() => router.navigate('/charts')}
    >
      &larr; Charts
    </button>
  {/snippet}
</PageHeader>

<div class="flex flex-col gap-10 mt-6 text-base-content">
  <!-- Range Selector -->
  <div class="nav-selector w-full md:w-auto justify-between md:justify-start gap-2 md:gap-8">
    {#each rangeOptions as [val, label]}
      <button
        class="nav-selector-item flex-1 md:flex-initial text-center md:text-left py-1 md:py-0 text-xs md:text-sm"
        class:active={timeRange === val}
        onclick={() =>
          router.navigate(`/artist/${encodeURIComponent(artistName)}?range=${val}`, true)}
      >
        {label}
      </button>
    {/each}
  </div>

  {#if loading}
    <div class="flex justify-center py-20">
      <span class="loading loading-spinner loading-md text-theme-accent"></span>
    </div>
  {:else if error}
    <p class="text-sm font-mono text-error text-center py-12">{error}</p>
  {:else if stats && stats.total_plays === 0}
    <p class="text-sm font-mono text-theme-muted text-center py-12">
      No listens found for <span class="text-theme-text">{artistName}</span> in this time range.
    </p>
  {:else if stats}
    <!-- Stats Strip -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div class="stats-box flex flex-col gap-1 p-5">
        <div class="text-2xl font-mono font-light text-theme-text">
          {stats.total_plays.toLocaleString()}
        </div>
        <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">Plays</div>
      </div>

      <div class="stats-box flex flex-col gap-1 p-5">
        <div class="text-2xl font-mono font-light text-theme-text">
          {stats.rank != null ? `#${stats.rank}` : '—'}
        </div>
        <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">
          All-time rank
        </div>
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

    <!-- Top Tracks -->
    <div class="flex flex-col gap-4">
      <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Top Tracks</h2>
      <div class="flex flex-col gap-3">
        {#each stats.top_tracks as track, idx}
          <div class="list-row-interactive pointer-events-none select-text">
            <div class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0">
              {String(idx + 1).padStart(2, '0')}
            </div>
            <div class="grow min-w-0">
              <div class="text-base md:text-lg font-light tracking-wide truncate text-theme-text">
                {track.title}
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-lg font-mono font-light text-theme-text">
                {track.play_count.toLocaleString()}
              </div>
              <div class="text-xs font-mono tracking-widest text-theme-muted uppercase mt-0.5">
                plays
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Monthly Trend -->
    {#if stats.monthly_trends.length > 0}
      <div class="flex flex-col gap-4">
        <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Listening History</h2>
        <div class="memory-surface !p-6">
          <div class="flex items-end gap-[2px] h-28 w-full overflow-x-auto">
            {#each stats.monthly_trends as trend}
              {@const pct = (trend.count / maxMonthlyCount) * 100}
              {@const opacity =
                trend.count > 0 ? 0.18 + (trend.count / maxMonthlyCount) * 0.82 : 0.06}
              <div
                class="relative flex flex-col items-center justify-end shrink-0"
                style="flex: 1 0 6px; min-width: 4px; max-width: 24px; height: 100%;"
                title="{trend.month}: {trend.count.toLocaleString()} plays"
              >
                <div
                  class="w-full rounded-sm bg-theme-accent transition-all duration-300"
                  style="height: {Math.max(pct, trend.count > 0 ? 2 : 0)}%; opacity: {opacity};"
                ></div>
              </div>
            {/each}
          </div>
          <div class="flex justify-between mt-2 text-[10px] font-mono text-theme-muted/60">
            <span>{stats.monthly_trends[0]?.month ?? ''}</span>
            <span>{stats.monthly_trends[stats.monthly_trends.length - 1]?.month ?? ''}</span>
          </div>
        </div>
      </div>
    {/if}

    <!-- Hourly Heat Clock -->
    <div class="flex flex-col gap-4">
      <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Listening by Hour</h2>
      <HourlyHeatClock hourlyData={stats.hourly} />
    </div>

    <!-- Discovery date footer note -->
    {#if stats.first_listen_ts}
      <p class="text-xs font-mono text-theme-muted/60 text-center pb-2">
        First heard {formatTs(stats.first_listen_ts)}
      </p>
    {/if}
  {/if}
</div>
