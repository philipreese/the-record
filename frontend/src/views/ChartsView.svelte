<script lang="ts">
  // Layout refresh trigger
  import { onMount, untrack } from 'svelte';
  import { fetchTopArtists, fetchTopTracks, type ArtistInfo, type TrackInfo } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import { themeManager, stringToColor } from '../services/theme.svelte';

  let topRange = $state('all'); // 30, 90, 365, all
  let loadingCharts = $state(false);

  // Automatically fetch when the selected range changes
  $effect(() => {
    const range = topRange;
    untrack(() => {
      fetchTopCharts(range);
    });
  });

  async function fetchTopCharts(range: string) {
    if (!appCache.charts[range]) {
      loadingCharts = true;
    }
    try {
      const [artistsRes, tracksRes] = await Promise.all([
        fetchTopArtists(range, 15),
        fetchTopTracks(range, 15)
      ]);
      appCache.charts[range] = { artists: artistsRes, tracks: tracksRes };
    } catch (e) {
      console.error("Failed to fetch top charts:", e);
    } finally {
      loadingCharts = false;
    }
  }

  let currentArtists = $derived(appCache.charts[topRange]?.artists || []);
  let currentTracks = $derived(appCache.charts[topRange]?.tracks || []);

  let focusedArtist = $state<string | null>(null);
  let focusedTrack = $state<string | null>(null);
  
  // Track hovered element to trigger progressive focus dimming
  let hoveredArtist = $state<string | null>(null);
  let hoveredTrack = $state<string | null>(null);

  // Clear focus when range selection changes
  $effect(() => {
    const _range = topRange;
    focusedArtist = null;
    focusedTrack = null;
    hoveredArtist = null;
    hoveredTrack = null;
    themeManager.setAmbientColor(null);
  });

  function toggleArtistFocus(name: string) {
    if (focusedArtist === name) {
      focusedArtist = null;
      themeManager.setAmbientColor(null);
    } else {
      focusedArtist = name;
      focusedTrack = null;
      themeManager.setAmbientColor(stringToColor(name));
    }
  }

  function toggleTrackFocus(title: string, artistName: string) {
    const key = `${artistName} - ${title}`;
    if (focusedTrack === key) {
      focusedTrack = null;
      themeManager.setAmbientColor(null);
    } else {
      focusedTrack = key;
      focusedArtist = null;
      themeManager.setAmbientColor(stringToColor(artistName));
    }
  }
</script>

<div class="flex flex-col gap-12 text-base-content">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 pb-4 border-b">
    <div>
      <h1 class="editorial-text-h1 lowercase italic">top charts</h1>
      <p class="text-caps mt-2">Your most played creators and tracks over time.</p>
    </div>
    
    <!-- Range Selector Options -->
    <div class="flex items-center gap-6 font-mono text-xs tracking-widest uppercase py-1">
      {#each [['30', '30 Days'], ['90', '90 Days'], ['365', '1 Year'], ['all', 'All Time']] as [val, label]}
        <button 
          class="hover:text-theme-accent cursor-pointer transition-colors duration-200 focus:outline-none" 
          class:text-theme-accent={topRange === val}
          class:text-theme-muted={topRange !== val}
          onclick={() => topRange = val}
        >
          {label}
        </button>
      {/each}
    </div>
  </div>

  {#if loadingCharts}
    <div class="flex justify-center items-center py-20">
      <span class="loading loading-spinner loading-md text-primary"></span>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12">
      
      <!-- Top Artists List -->
      <div class="space-y-6">
        <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">
          Top Creators
        </h2>
        
        <div class="flex flex-col gap-3">
          {#each currentArtists as artist, idx}
            <!-- svelte-ignore a11y_mouse_events_have_key_events -->
            <div 
              role="button"
              tabindex="0"
              class="list-row-interactive"
              class:opacity-35={(hoveredArtist || focusedArtist) && hoveredArtist !== artist.artist && focusedArtist !== artist.artist}
              class:border-theme-accent={focusedArtist === artist.artist}
              class:bg-theme-accent-soft={focusedArtist === artist.artist}
              onmouseenter={() => { hoveredArtist = artist.artist; themeManager.setAmbientColor(stringToColor(artist.artist)); }}
              onmouseleave={() => { hoveredArtist = null; themeManager.setAmbientColor(focusedArtist ? stringToColor(focusedArtist) : null); }}
              onclick={() => toggleArtistFocus(artist.artist)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleArtistFocus(artist.artist); }}
            >
              <div class="w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs bg-theme-neutral-soft text-theme-muted">
                {String(idx + 1).padStart(2, '0')}
              </div>
              <div class="flex-grow">
                <div class="font-light tracking-wide text-theme-text">{artist.artist}</div>
              </div>
              <div class="text-right">
                <div class="text-md font-mono font-light text-theme-text">{artist.play_count.toLocaleString()}</div>
                <div class="text-micro font-mono tracking-widest text-zinc-500 uppercase mt-0.5">plays</div>
              </div>
            </div>
          {:else}
            <p class="text-xs font-mono opacity-50 text-center py-10">No history found for this range.</p>
          {/each}
        </div>
      </div>

      <!-- Top Tracks List -->
      <div class="space-y-6">
        <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">
          Top Tracks
        </h2>
        
        <div class="flex flex-col gap-3">
          {#each currentTracks as track, idx}
            <!-- svelte-ignore a11y_mouse_events_have_key_events -->
            <div 
              role="button"
              tabindex="0"
              class="list-row-interactive"
              class:opacity-35={(hoveredTrack || focusedTrack) && hoveredTrack !== `${track.artist} - ${track.title}` && focusedTrack !== `${track.artist} - ${track.title}`}
              class:border-theme-accent={focusedTrack === `${track.artist} - ${track.title}`}
              class:bg-theme-accent-soft={focusedTrack === `${track.artist} - ${track.title}`}
              onmouseenter={() => { hoveredTrack = `${track.artist} - ${track.title}`; themeManager.setAmbientColor(stringToColor(track.artist)); }}
              onmouseleave={() => { hoveredTrack = null; themeManager.setAmbientColor(focusedTrack ? stringToColor(focusedTrack.split(' - ')[0]) : null); }}
              onclick={() => toggleTrackFocus(track.title, track.artist)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleTrackFocus(track.title, track.artist); }}
            >
              <div class="w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs bg-theme-neutral-soft text-theme-muted">
                {String(idx + 1).padStart(2, '0')}
              </div>
              <div class="flex-grow min-w-0">
                <div class="font-light tracking-wide truncate text-theme-text">{track.title}</div>
                <div class="text-xs font-light truncate opacity-60 mt-0.5 text-theme-secondary">{track.artist}</div>
              </div>
              <div class="text-right flex-shrink-0">
                <div class="text-md font-mono font-light text-theme-text">{track.play_count.toLocaleString()}</div>
                <div class="text-micro font-mono tracking-widest text-zinc-500 uppercase mt-0.5">plays</div>
              </div>
            </div>
          {:else}
            <p class="text-xs font-mono opacity-50 text-center py-10">No history found for this range.</p>
          {/each}
        </div>
      </div>

    </div>
  {/if}
</div>
