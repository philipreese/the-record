<script lang="ts">
  import { untrack, onMount } from 'svelte';
  import {
    fetchTopArtists,
    fetchTopTracks,
    fetchStats,
    type TimeRange,
    type ArtistInfo,
    type TrackInfo,
  } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import { router } from '../services/router.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import Icon from '../components/layout/Icon.svelte';
  import StreamGraph from '../components/StreamGraph.svelte';
  import TopArtistsList from '../components/charts/TopArtistsList.svelte';
  import TopTracksList from '../components/charts/TopTracksList.svelte';

  let selectedYear = $derived(
    parseInt(router.params.get('year') ?? String(new Date().getFullYear()), 10),
  );

  let firstListenYear = $derived(appCache.stats?.first_year || new Date().getFullYear());
  let currentYear = $derived(new Date().getFullYear());

  onMount(() => {
    if (!appCache.statsLoaded) {
      fetchStats()
        .then((s) => {
          appCache.stats = s;
          appCache.statsLoaded = true;
        })
        .catch((e) => console.error('Failed to fetch stats for charts view:', e));
    }
  });

  let topRange = $derived<TimeRange>((router.params.get('range') as TimeRange) ?? 'all');

  const rangeOptions: [TimeRange, string][] = [
    ['30', '30 Days'],
    ['90', '90 Days'],
    ['365', '1 Year'],
    ['all', 'All Time'],
  ];

  const PAGE_SIZE = 15;

  let artistPage = $state(1);
  let trackPage = $state(1);

  let searchQuery = $state(router.params.get('q') ?? '');
  let debouncedSearch = $derived(router.params.get('q') ?? '');
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  let loadingArtists = $state(false);
  let loadingTracks = $state(false);

  let artists = $state<ArtistInfo[]>([]);
  let tracks = $state<TrackInfo[]>([]);

  let totalArtists = $state(0);
  let totalTracks = $state(0);

  let totalArtistPages = $derived(Math.ceil(totalArtists / PAGE_SIZE));
  let totalTrackPages = $derived(Math.ceil(totalTracks / PAGE_SIZE));

  let hasMoreArtists = $derived(artistPage < totalArtistPages);
  let hasMoreTracks = $derived(trackPage < totalTrackPages);

  let focusedTrack = $state<string | null>(null);

  // Debounce search: write to URL (which drives debouncedSearch $derived) after 300ms
  $effect(() => {
    const q = searchQuery;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const p = new URLSearchParams();
      p.set('range', topRange);
      p.set('year', String(selectedYear));
      const trimmed = q.trim();
      if (trimmed) p.set('q', trimmed);
      router.navigate(`/charts?${p}`, true);
    }, 300);
  });

  // Keep search input in sync when URL changes (e.g. browser back button)
  $effect(() => {
    const urlQ = router.params.get('q') ?? '';
    untrack(() => {
      if (searchQuery !== urlQ) searchQuery = urlQ;
    });
  });

  // Reset pagination when range or search query changes
  $effect(() => {
    const _range = topRange;
    const _search = debouncedSearch;
    untrack(() => {
      artistPage = 1;
      trackPage = 1;
    });
  });

  // Fetch artists when range, page, search changes, or store cache is invalidated
  $effect(() => {
    const range = topRange;
    const search = debouncedSearch;
    const page = artistPage;

    // Read this from the store cache to be reactive to invalidation (e.g. store.invalidate clears charts)
    const cached = appCache.charts[range];

    loadingArtists = true;

    // If first page and no search, use cache if available
    if (page === 1 && !search && cached?.artists?.length) {
      artists = cached.artists;
      totalArtists = cached.totalArtists ?? cached.artists.length;
      loadingArtists = false;
      return;
    }

    untrack(() => {
      fetchTopArtists(range, PAGE_SIZE, page, search)
        .then((data) => {
          artists = data.items;
          totalArtists = data.total_count;
          // Pre-populate cache if it was empty, page 1, and no search
          if (page === 1 && !search) {
            if (!appCache.charts[range]) {
              appCache.charts[range] = { artists: [], tracks: [] };
            }
            appCache.charts[range].artists = artists;
            appCache.charts[range].totalArtists = totalArtists;
          }
        })
        .catch((e) => {
          console.error('Failed to fetch top artists:', e);
        })
        .finally(() => {
          loadingArtists = false;
        });
    });
  });

  // Fetch tracks when range, page, search changes, or store cache is invalidated
  $effect(() => {
    const range = topRange;
    const search = debouncedSearch;
    const page = trackPage;

    const cached = appCache.charts[range];

    loadingTracks = true;

    // If first page and no search, use cache if available
    if (page === 1 && !search && cached?.tracks?.length) {
      tracks = cached.tracks;
      totalTracks = cached.totalTracks ?? cached.tracks.length;
      loadingTracks = false;
      return;
    }

    untrack(() => {
      fetchTopTracks(range, PAGE_SIZE, page, search)
        .then((data) => {
          tracks = data.items;
          totalTracks = data.total_count;
          // Pre-populate cache if it was empty, page 1, and no search
          if (page === 1 && !search) {
            if (!appCache.charts[range]) {
              appCache.charts[range] = { artists: [], tracks: [] };
            }
            appCache.charts[range].tracks = tracks;
            appCache.charts[range].totalTracks = totalTracks;
          }
        })
        .catch((e) => {
          console.error('Failed to fetch top tracks:', e);
        })
        .finally(() => {
          loadingTracks = false;
        });
    });
  });

  // Clear focus when range selection or search changes
  $effect(() => {
    const _range = topRange;
    const _search = debouncedSearch;
    focusedTrack = null;
  });

  $effect(() => {
    const _trackPage = trackPage;
    focusedTrack = null;
  });

  function navigateToArtist(name: string) {
    router.navigate(`/artist/${encodeURIComponent(name)}`);
  }
</script>

<PageHeader title="top charts" subtitle="Your most played creators and tracks over time." />

<div class="flex flex-col sm:gap-8 gap-12 text-base-content mt-6">
  <!-- Streamgraph section -->
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center pb-2 border-b border-theme-border-soft">
      <h2 class="editorial-text-h2">temporal trends</h2>

      <!-- Year Selector -->
      <div class="flex items-center gap-4">
        <span class="text-[10px] font-mono uppercase tracking-widest text-theme-muted select-none"
          >Select Year</span
        >
        <div
          class="flex items-center gap-4 bg-theme-neutral-soft px-3 py-1 rounded-lg border border-theme-border-soft"
        >
          <button
            class="btn-nav-text text-2xl! leading-none"
            aria-label="Previous Year"
            disabled={selectedYear <= firstListenYear}
            onclick={() =>
              router.navigate(`/charts?range=${topRange}&year=${selectedYear - 1}`, true)}
          >
            &larr;
          </button>
          <span class="text-lg font-mono tracking-wider font-light text-theme-text select-none"
            >{selectedYear}</span
          >
          <button
            class="btn-nav-text text-2xl! leading-none"
            aria-label="Next Year"
            disabled={selectedYear >= currentYear}
            onclick={() =>
              router.navigate(`/charts?range=${topRange}&year=${selectedYear + 1}`, true)}
          >
            &rarr;
          </button>
        </div>
      </div>
    </div>

    <StreamGraph year={selectedYear} />
  </div>

  <!-- Range Selector & Search Bar Row -->
  <div class="sticky-sub-header flex flex-col md:flex-row md:items-center justify-between gap-6">
    <div class="nav-selector w-full md:w-auto justify-between md:justify-start gap-2 md:gap-8">
      {#each rangeOptions as [val, label]}
        <button
          class="nav-selector-item flex-1 md:flex-initial text-center md:text-left py-1 md:py-0 text-xs md:text-sm"
          class:active={topRange === val}
          onclick={() => router.navigate(`/charts?range=${val}&year=${selectedYear}`, true)}
        >
          {label}
        </button>
      {/each}
    </div>

    <div class="relative w-full md:max-w-md">
      <input
        type="text"
        placeholder="Search creators or tracks..."
        class="input input-sm pl-8 pr-8 w-full bg-base-200 border border-base-content/10 rounded-md focus:border-theme-accent focus:outline-none transition-colors text-sm"
        bind:value={searchQuery}
      />
      <span
        class="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none opacity-40 z-10"
      >
        <Icon name="search" size="w-4 h-4" class="text-base-content" />
      </span>
      {#if searchQuery}
        <button
          class="absolute inset-y-0 right-0 flex items-center pr-3 opacity-40 hover:opacity-100 transition-opacity z-10"
          aria-label="Clear search"
          onclick={() => {
            searchQuery = '';
            if (searchTimeout) clearTimeout(searchTimeout);
            router.navigate(`/charts?range=${topRange}&year=${selectedYear}`, true);
          }}
        >
          <Icon name="close" size="w-4 h-4" />
        </button>
      {/if}
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-12 mt-4 sm:mt-0">
    <TopArtistsList
      {artists}
      {artistPage}
      {totalArtistPages}
      {loadingArtists}
      {hasMoreArtists}
      pageSize={PAGE_SIZE}
      onpreviouspage={() => artistPage--}
      onnextpage={() => artistPage++}
      onartistclick={navigateToArtist}
    />
    <TopTracksList
      {tracks}
      {trackPage}
      {totalTrackPages}
      {loadingTracks}
      {hasMoreTracks}
      pageSize={PAGE_SIZE}
      {focusedTrack}
      onpreviouspage={() => trackPage--}
      onnextpage={() => trackPage++}
    />
  </div>
</div>
