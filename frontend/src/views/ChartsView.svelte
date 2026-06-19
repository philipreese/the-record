<script lang="ts">
  import { untrack, onMount } from 'svelte';
  import { inView } from '../utils/inView';
  import {
    fetchTopArtists,
    fetchTopTracks,
    fetchStats,
    type TimeRange,
    type ArtistInfo,
    type TrackInfo,
  } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import { themeManager, stringToColor } from '../services/theme.svelte';
  import { router } from '../services/router.svelte';
  import { tooltip } from '../utils/tooltip';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import Icon from '../components/layout/Icon.svelte';
  import StreamGraph from '../components/StreamGraph.svelte';

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

  let focusedArtist = $state<string | null>(null);
  let focusedTrack = $state<string | null>(null);

  // Track hovered element to trigger progressive focus dimming
  let hoveredArtist = $state<string | null>(null);
  let hoveredTrack = $state<string | null>(null);

  // Capture the music-mood ambient color at mount time so we can restore it when
  // clearing chart focus or navigating away. persist=false keeps chart-focus colors
  // from overwriting the album-art color in localStorage.
  const preChartsAmbientColor = themeManager.ambientColor;

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

  $effect(() => {
    // Restore the pre-Charts ambient color when unmounting (navigating away).
    return () => {
      themeManager.setAmbientColor(preChartsAmbientColor, false);
    };
  });

  // Clear focus when range selection or search changes
  $effect(() => {
    const _range = topRange;
    const _search = debouncedSearch;
    focusedArtist = null;
    focusedTrack = null;
    hoveredArtist = null;
    hoveredTrack = null;
    themeManager.setAmbientColor(preChartsAmbientColor, false);
  });

  // Clear focus when pagination page changes
  $effect(() => {
    const _artistPage = artistPage;
    focusedArtist = null;
    hoveredArtist = null;
    themeManager.setAmbientColor(preChartsAmbientColor, false);
  });

  $effect(() => {
    const _trackPage = trackPage;
    focusedTrack = null;
    hoveredTrack = null;
    themeManager.setAmbientColor(preChartsAmbientColor, false);
  });

  function toggleArtistFocus(name: string) {
    if (focusedArtist === name) {
      focusedArtist = null;
      themeManager.setAmbientColor(preChartsAmbientColor, false);
    } else {
      focusedArtist = name;
      focusedTrack = null;
      themeManager.setAmbientColor(stringToColor(name), false);
    }
  }

  function toggleTrackFocus(title: string, artistName: string) {
    const key = `${artistName} - ${title}`;
    if (focusedTrack === key) {
      focusedTrack = null;
      themeManager.setAmbientColor(preChartsAmbientColor, false);
    } else {
      focusedTrack = key;
      focusedArtist = null;
      themeManager.setAmbientColor(stringToColor(artistName), false);
    }
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
    <!-- Top Creators List -->
    <div class="flex flex-col justify-between h-full min-h-125">
      <div class="space-y-6">
        <h2
          class="editorial-text-h2 pb-2 border-b border-theme-border-soft flex justify-between items-center"
        >
          <span>Top Creators</span>
          {#if loadingArtists}
            <span class="loading loading-spinner loading-xs text-theme-accent"></span>
          {/if}
        </h2>

        <div use:inView={{ once: true }} class="flex flex-col gap-3 reveal-list-container">
          {#each artists as artist, idx}
            <div
              role="button"
              tabindex="0"
              class="list-row-interactive"
              style="animation-delay: {idx * 40}ms;"
              class:opacity-35={(hoveredArtist || focusedArtist) &&
                hoveredArtist !== artist.artist &&
                focusedArtist !== artist.artist}
              class:border-theme-accent={focusedArtist === artist.artist}
              class:bg-theme-accent-soft={focusedArtist === artist.artist}
              onmouseenter={() => {
                hoveredArtist = artist.artist;
              }}
              onmouseleave={() => {
                hoveredArtist = null;
              }}
              onclick={() => toggleArtistFocus(artist.artist)}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') toggleArtistFocus(artist.artist);
              }}
            >
              <div
                class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0"
              >
                {String(artist.rank ?? (artistPage - 1) * PAGE_SIZE + idx + 1).padStart(2, '0')}
              </div>
              <div class="grow">
                <div class="text-base md:text-lg font-light tracking-wide text-theme-text">
                  {artist.artist}
                </div>
              </div>
              <div class="text-right">
                <div class="text-lg font-mono font-light text-theme-text">
                  {artist.play_count.toLocaleString()}
                </div>
                <div class="text-xs font-mono tracking-widest text-theme-muted uppercase mt-0.5">
                  plays
                </div>
              </div>
            </div>
          {:else}
            <p class="text-xs font-mono opacity-50 text-center py-10">
              No history found for this range.
            </p>
          {/each}
        </div>
      </div>

      <!-- Artists Paginator -->
      <div
        class="flex items-center justify-between mt-8 pt-4 border-t border-theme-border-soft font-mono text-xs"
      >
        <button
          class="btn-nav-text"
          disabled={artistPage === 1 || loadingArtists}
          onclick={() => artistPage--}
        >
          ← Prev
        </button>
        <span class="text-xs uppercase tracking-widest text-theme-muted/50 font-mono"
          >Page {artistPage} of {totalArtistPages || 1}</span
        >
        <button
          class="btn-nav-text"
          disabled={!hasMoreArtists || loadingArtists}
          onclick={() => artistPage++}
        >
          Next →
        </button>
      </div>
    </div>

    <!-- Top Tracks List -->
    <div class="flex flex-col justify-between h-full min-h-125">
      <div class="space-y-6">
        <h2
          class="editorial-text-h2 pb-2 border-b border-theme-border-soft flex justify-between items-center"
        >
          <span>Top Tracks</span>
          {#if loadingTracks}
            <span class="loading loading-spinner loading-xs text-theme-accent"></span>
          {/if}
        </h2>

        <div use:inView={{ once: true }} class="flex flex-col gap-3 reveal-list-container">
          {#each tracks as track, idx}
            <div
              role="button"
              tabindex="0"
              class="list-row-interactive"
              style="animation-delay: {idx * 40}ms;"
              class:opacity-35={(hoveredTrack || focusedTrack) &&
                hoveredTrack !== `${track.artist} - ${track.title}` &&
                focusedTrack !== `${track.artist} - ${track.title}`}
              class:border-theme-accent={focusedTrack === `${track.artist} - ${track.title}`}
              class:bg-theme-accent-soft={focusedTrack === `${track.artist} - ${track.title}`}
              onmouseenter={() => {
                hoveredTrack = `${track.artist} - ${track.title}`;
              }}
              onmouseleave={() => {
                hoveredTrack = null;
              }}
              onclick={() => toggleTrackFocus(track.title, track.artist)}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') toggleTrackFocus(track.title, track.artist);
              }}
            >
              <div
                class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0"
              >
                {String(track.rank ?? (trackPage - 1) * PAGE_SIZE + idx + 1).padStart(2, '0')}
              </div>
              <div class="grow min-w-0">
                <div
                  class="text-base md:text-lg font-light tracking-wide truncate text-theme-text"
                  use:tooltip
                >
                  {track.title}
                </div>
                <div
                  class="text-sm font-normal truncate mt-1 text-theme-secondary opacity-80"
                  use:tooltip
                >
                  {track.artist}
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
          {:else}
            <p class="text-xs font-mono opacity-50 text-center py-10">
              No history found for this range.
            </p>
          {/each}
        </div>
      </div>

      <!-- Tracks Paginator -->
      <div
        class="flex items-center justify-between mt-8 pt-4 border-t border-theme-border-soft font-mono text-xs"
      >
        <button
          class="btn-nav-text"
          disabled={trackPage === 1 || loadingTracks}
          onclick={() => trackPage--}
        >
          ← Prev
        </button>
        <span class="text-xs uppercase tracking-widest text-theme-muted/50 font-mono"
          >Page {trackPage} of {totalTrackPages || 1}</span
        >
        <button
          class="btn-nav-text"
          disabled={!hasMoreTracks || loadingTracks}
          onclick={() => trackPage++}
        >
          Next →
        </button>
      </div>
    </div>
  </div>
</div>
