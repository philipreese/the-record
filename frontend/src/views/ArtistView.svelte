<script lang="ts">
  import { untrack } from 'svelte';
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

  let logMax = $derived(
    stats ? Math.log(Math.max(...stats.monthly_trends.map((t) => t.count), 1) + 1) : 1,
  );

  let hoveredBar = $state<{ month: string; count: number } | null>(null);

  function fmtMonth(ym: string): string {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
  }

  type TrackSort = 'plays' | 'name' | 'oldest' | 'recent';
  let trackSort = $state<TrackSort>('plays');
  let trackPage = $state(1);
  const PAGE_SIZE = 10;

  const sortOptions: [TrackSort, string][] = [
    ['plays', 'Plays'],
    ['name', 'Name'],
    ['oldest', 'Oldest'],
    ['recent', 'Recent'],
  ];

  function formatDuration(secs: number): string {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function sortTracks(
    tracks: ArtistStatsInfo['top_tracks'],
    sort: TrackSort,
  ): ArtistStatsInfo['top_tracks'] {
    const copy = [...tracks];
    switch (sort) {
      case 'plays':
        return copy.sort((a, b) => b.play_count - a.play_count);
      case 'name':
        return copy.sort((a, b) => a.title.localeCompare(b.title));
      case 'oldest':
        return copy.sort((a, b) => (a.first_listen_ts ?? 0) - (b.first_listen_ts ?? 0));
      case 'recent':
        return copy.sort((a, b) => (b.last_listen_ts ?? 0) - (a.last_listen_ts ?? 0));
    }
  }

  let sortedTracks = $derived(stats ? sortTracks(stats.top_tracks, trackSort) : []);
  let totalTrackPages = $derived(Math.ceil(sortedTracks.length / PAGE_SIZE));
  let pagedTracks = $derived(
    sortedTracks.slice((trackPage - 1) * PAGE_SIZE, trackPage * PAGE_SIZE),
  );

  // Reset to page 1 whenever sort or artist data changes
  $effect(() => {
    void trackSort;
    void stats;
    untrack(() => {
      trackPage = 1;
    });
  });
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

    <!-- Monthly Trend -->
    {#if stats.monthly_trends.length > 0}
      <div class="flex flex-col gap-4">
        <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Listening History</h2>
        <div class="memory-surface p-6!">
          <div class="flex items-end mb-3 h-8">
            {#if hoveredBar}
              <div class="flex flex-col gap-0.5">
                <span class="text-[11px] font-mono text-theme-text leading-none">
                  {fmtMonth(hoveredBar.month)}
                </span>
                <span class="text-[11px] font-mono text-theme-accent leading-none">
                  {hoveredBar.count.toLocaleString()} plays
                </span>
              </div>
            {:else}
              <div class="flex w-full justify-between items-end">
                <span class="text-[10px] font-mono text-theme-muted/60">
                  {stats.monthly_trends[0]?.month ?? ''}
                </span>
                <span class="text-[10px] font-mono text-theme-muted/60">
                  {stats.monthly_trends[stats.monthly_trends.length - 1]?.month ?? ''}
                </span>
              </div>
            {/if}
          </div>
          <div class="flex items-end gap-0.5 h-28 w-full">
            {#each stats.monthly_trends as trend}
              {@const logPct = (Math.log(trend.count + 1) / logMax) * 100}
              {@const isHovered = hoveredBar?.month === trend.month}
              {@const opacity = isHovered
                ? 1
                : trend.count > 0
                  ? 0.18 + (Math.log(trend.count + 1) / logMax) * 0.82
                  : 0.06}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="relative flex flex-col items-center justify-end"
                style="flex: 1; min-width: 2px; height: 100%;"
                onmouseenter={() => (hoveredBar = trend)}
                onmouseleave={() => (hoveredBar = null)}
              >
                <div
                  class="w-full rounded-sm bg-theme-accent transition-all duration-150"
                  style="height: {Math.max(
                    logPct,
                    trend.count > 0 ? 2 : 0,
                  )}%; opacity: {opacity}; transform: scaleY({isHovered
                    ? 1.15
                    : 1}); transform-origin: bottom;"
                ></div>
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}

    <!-- Tracks -->
    <div class="flex flex-col gap-4">
      <div class="flex items-center justify-between pb-2 border-b border-theme-border-soft">
        <h2 class="editorial-text-h2">Tracks</h2>
        <div class="nav-selector gap-3 md:gap-6">
          {#each sortOptions as [val, label]}
            <button
              class="nav-selector-item text-xs py-0.5"
              class:active={trackSort === val}
              onclick={() => (trackSort = val)}
            >
              {label}
            </button>
          {/each}
        </div>
      </div>
      <div class="flex flex-col gap-3">
        {#each pagedTracks as track, idx}
          {@const globalIdx = (trackPage - 1) * PAGE_SIZE + idx + 1}
          {@const meta = [
            trackSort === 'oldest' && track.first_listen_ts
              ? `first ${formatTs(track.first_listen_ts)}`
              : null,
            trackSort === 'recent' && track.last_listen_ts
              ? `last ${formatTs(track.last_listen_ts)}`
              : null,
            track.album ?? null,
            track.duration_secs ? formatDuration(track.duration_secs) : null,
          ]
            .filter(Boolean)
            .join(' · ')}
          <div class="list-row-interactive pointer-events-none select-text">
            <div class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0">
              {String(globalIdx).padStart(2, '0')}
            </div>
            <div class="grow min-w-0">
              <div class="text-base md:text-lg font-light tracking-wide truncate text-theme-text">
                {track.title}
              </div>
              {#if meta}
                <div class="text-xs font-mono text-theme-muted/60 mt-0.5 truncate">{meta}</div>
              {/if}
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

      {#if totalTrackPages > 1}
        <div
          class="flex items-center justify-between pt-4 border-t border-theme-border-soft font-mono text-xs"
        >
          <button class="btn-nav-text" disabled={trackPage === 1} onclick={() => trackPage--}>
            ← Prev
          </button>
          <span class="text-xs uppercase tracking-widest text-theme-muted/50">
            Page {trackPage} of {totalTrackPages}
          </span>
          <button
            class="btn-nav-text"
            disabled={trackPage === totalTrackPages}
            onclick={() => trackPage++}
          >
            Next →
          </button>
        </div>
      {/if}
    </div>

    <!-- Hourly Heat Clock -->
    <div class="flex flex-col gap-4">
      <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Listening by Hour</h2>
      <HourlyHeatClock hourlyData={stats.hourly} />
    </div>
  {/if}
</div>
