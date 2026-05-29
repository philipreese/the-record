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

  // Clear focus when range selection changes
  $effect(() => {
    const _range = topRange;
    focusedArtist = null;
    focusedTrack = null;
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

<div class="flex flex-col gap-6 text-base-content">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 memory-surface">
    <div>
      <h1 class="editorial-text-h1">Top Charts</h1>
      <p class="text-sm opacity-60 mt-1">Your most played tracks and artists over time.</p>
    </div>
    
    <!-- Range Selector Tabs -->
    <div class="tabs tabs-boxed">
      <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === '30'} onclick={() => topRange = '30'}>30 Days</button>
      <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === '90'} onclick={() => topRange = '90'}>90 Days</button>
      <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === '365'} onclick={() => topRange = '365'}>1 Year</button>
      <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === 'all'} onclick={() => topRange = 'all'}>All Time</button>
    </div>
  </div>

  {#if loadingCharts}
    <div class="flex justify-center items-center py-20">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      
      <!-- Top Artists List -->
      <div class="memory-surface">
        <h2 class="editorial-text-h2 text-primary border-b border-base-content/10 pb-3 mb-6 flex justify-between items-center">
          <span>Top Artists</span>
          <span class="badge chip-primary">{currentArtists.length} items</span>
        </h2>
        
        <div class="flex flex-col gap-3">
          {#each currentArtists as artist, idx}
            <div 
              role="button"
              tabindex="0"
              class="list-row-interactive border {focusedArtist === artist.artist ? 'border-primary bg-primary/10 shadow-sm' : 'bg-base-300/30 border-base-content/5 hover:bg-base-300/50'}"
              onclick={() => toggleArtistFocus(artist.artist)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleArtistFocus(artist.artist); }}
            >
              <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center font-bold text-primary text-sm">
                {idx + 1}
              </div>
              <div class="flex-grow">
                <div class="font-extrabold">{artist.artist}</div>
              </div>
              <div class="text-right">
                <div class="text-md font-black">{artist.play_count.toLocaleString()}</div>
                <div class="text-detail uppercase font-bold mt-0.5">plays</div>
              </div>
            </div>
          {:else}
            <p class="text-sm opacity-50 text-center py-10">No history found for this range.</p>
          {/each}
        </div>
      </div>

      <!-- Top Tracks List -->
      <div class="memory-surface">
        <h2 class="editorial-text-h2 text-primary border-b border-base-content/10 pb-3 mb-6 flex justify-between items-center">
          <span>Top Tracks</span>
          <span class="badge chip-primary">{currentTracks.length} items</span>
        </h2>
        
        <div class="flex flex-col gap-3">
          {#each currentTracks as track, idx}
            <div 
              role="button"
              tabindex="0"
              class="list-row-interactive border {focusedTrack === `${track.artist} - ${track.title}` ? 'border-primary bg-primary/10 shadow-sm' : 'bg-base-300/30 border-base-content/5 hover:bg-base-300/50'}"
              onclick={() => toggleTrackFocus(track.title, track.artist)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleTrackFocus(track.title, track.artist); }}
            >
              <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center font-bold text-primary text-sm">
                {idx + 1}
              </div>
              <div class="flex-grow min-w-0">
                <div class="font-extrabold truncate">{track.title}</div>
                <div class="text-xs opacity-60 truncate">{track.artist}</div>
              </div>
              <div class="text-right flex-shrink-0">
                <div class="text-md font-black">{track.play_count.toLocaleString()}</div>
                <div class="text-detail uppercase font-bold mt-0.5">plays</div>
              </div>
            </div>
          {:else}
            <p class="text-sm opacity-50 text-center py-10">No history found for this range.</p>
          {/each}
        </div>
      </div>

    </div>
  {/if}
</div>
