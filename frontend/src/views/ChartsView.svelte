<script lang="ts">
  // Layout refresh trigger
  import { untrack } from 'svelte';
  import { inView } from '../utils/inView';
  import {
    fetchTopArtists,
    fetchTopTracks,
    type TimeRange,
    type ArtistInfo,
    type TrackInfo,
  } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import { themeManager, stringToColor } from '../services/theme.svelte';
  import { tooltip } from '../utils/tooltip';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import LoadingSpinner from '../components/layout/LoadingSpinner.svelte';

  let topRange = $state<TimeRange>('all');

  const rangeOptions: [TimeRange, string][] = [
    ['30', '30 Days'],
    ['90', '90 Days'],
    ['365', '1 Year'],
    ['all', 'All Time'],
  ];
  let loadingCharts = $state(false);

  // Automatically fetch when the selected range changes. Reading the cache entry here
  // keeps the effect reactive to invalidation: a sync clears appCache.charts and this refetches.
  $effect(() => {
    const range = topRange;
    if (appCache.charts[range]) {
      loadingCharts = false;
      return;
    }
    untrack(() => {
      fetchTopCharts(range);
    });
  });

  // Tracks pending fetches per range so rapid switching (A->B->A) reuses the
  // in-flight request for A instead of firing a second, racing one.
  const inFlight = new Map<TimeRange, Promise<{ artists: ArtistInfo[]; tracks: TrackInfo[] }>>();

  async function fetchTopCharts(range: TimeRange) {
    loadingCharts = true;
    try {
      let request = inFlight.get(range);
      if (!request) {
        request = Promise.all([fetchTopArtists(range, 15), fetchTopTracks(range, 15)])
          .then(([artists, tracks]) => ({ artists, tracks }))
          .finally(() => {
            inFlight.delete(range);
          });
        inFlight.set(range, request);
      }
      appCache.charts[range] = await request;
    } catch (e) {
      console.error('Failed to fetch top charts:', e);
    } finally {
      // Only clear the spinner if this resolution is for the range still selected.
      if (range === topRange) loadingCharts = false;
    }
  }

  let currentArtists = $derived(appCache.charts[topRange]?.artists || []);
  let currentTracks = $derived(appCache.charts[topRange]?.tracks || []);

  let focusedArtist = $state<string | null>(null);
  let focusedTrack = $state<string | null>(null);

  // Track hovered element to trigger progressive focus dimming
  let hoveredArtist = $state<string | null>(null);
  let hoveredTrack = $state<string | null>(null);

  // Capture the music-mood ambient color at mount time so we can restore it when
  // clearing chart focus or navigating away. persist=false keeps chart-focus colors
  // from overwriting the album-art color in localStorage.
  const preChartsAmbientColor = themeManager.ambientColor;

  $effect(() => {
    // Restore the pre-Charts ambient color when unmounting (navigating away).
    return () => {
      themeManager.setAmbientColor(preChartsAmbientColor, false);
    };
  });

  // Clear focus when range selection changes — restore instead of resetting to null.
  $effect(() => {
    const _range = topRange;
    focusedArtist = null;
    focusedTrack = null;
    hoveredArtist = null;
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

<PageHeader title="top charts" subtitle="Your most played creators and tracks over time.">
  {#snippet actions(isShrunk)}
    <div class="hidden lg:block">
      <div
        class="nav-selector transition-all duration-300"
        class:text-xs={isShrunk}
        class:text-sm={!isShrunk}
      >
        {#each rangeOptions as [val, label]}
          <button
            class="nav-selector-item"
            class:active={topRange === val}
            onclick={() => (topRange = val)}
          >
            {label}
          </button>
        {/each}
      </div>
    </div>
  {/snippet}
</PageHeader>

<!-- Mobile Sticky Range Selector -->
<div class="sticky-sub-header lg:hidden">
  <div class="nav-selector w-full justify-between gap-1">
    {#each rangeOptions as [val, label]}
      <button
        class="nav-selector-item flex-1 text-center justify-center py-1 text-xs"
        class:active={topRange === val}
        onclick={() => (topRange = val)}
      >
        {label}
      </button>
    {/each}
  </div>
</div>

<div class="flex flex-col gap-12 text-base-content">
  {#if loadingCharts}
    <LoadingSpinner />
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 mt-12">
      <!-- Top Artists List -->
      <div class="space-y-6">
        <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Top Creators</h2>

        <div use:inView={{ once: true }} class="flex flex-col gap-3 reveal-list-container">
          {#each currentArtists as artist, idx}
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
                {String(idx + 1).padStart(2, '0')}
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

      <!-- Top Tracks List -->
      <div class="space-y-6">
        <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Top Tracks</h2>

        <div use:inView={{ once: true }} class="flex flex-col gap-3 reveal-list-container">
          {#each currentTracks as track, idx}
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
                {String(idx + 1).padStart(2, '0')}
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
    </div>
  {/if}
</div>
