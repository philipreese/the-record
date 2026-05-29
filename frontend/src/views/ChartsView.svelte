<script lang="ts">
  import { fetchTopArtists, fetchTopTracks, type ArtistInfo, type TrackInfo } from '../services/api';

  let topRange = $state('all'); // 30, 90, 365, all
  let topArtists = $state<ArtistInfo[]>([]);
  let topTracks = $state<TrackInfo[]>([]);
  let loadingCharts = $state(false);

  // Automatically fetch when the selected range changes
  $effect(() => {
    const range = topRange;
    fetchTopCharts(range);
  });

  async function fetchTopCharts(range: string) {
    loadingCharts = true;
    try {
      const [artistsRes, tracksRes] = await Promise.all([
        fetchTopArtists(range, 15),
        fetchTopTracks(range, 15)
      ]);
      topArtists = artistsRes;
      topTracks = tracksRes;
    } catch (e) {
      console.error("Failed to fetch top charts:", e);
    } finally {
      loadingCharts = false;
    }
  }
</script>

<div class="flex flex-col gap-6 text-base-content">
  <div class="flex justify-between items-center bg-base-200/40 border border-base-content/5 rounded-2xl p-6 backdrop-blur-md">
    <div>
      <h1 class="text-3xl font-extrabold tracking-tight">Top Charts</h1>
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
      <div class="card bg-base-200/50 border border-base-content/10 p-6 backdrop-blur-md">
        <h2 class="text-xl font-bold mb-6 text-primary border-b border-base-content/10 pb-3 flex justify-between items-center">
          <span>Top Artists</span>
          <span class="badge badge-primary">{topArtists.length} items</span>
        </h2>
        
        <div class="flex flex-col gap-3">
          {#each topArtists as artist, idx}
            <div class="flex items-center gap-4 bg-base-300/30 rounded-xl p-3 border border-base-content/5 hover:bg-base-300/50 transition-colors duration-300">
              <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center font-bold text-primary text-sm">
                {idx + 1}
              </div>
              <div class="flex-grow">
                <div class="font-extrabold text-base-content">{artist.artist}</div>
              </div>
              <div class="text-right">
                <div class="text-md font-black">{artist.play_count.toLocaleString()}</div>
                <div class="text-[9px] opacity-40 uppercase font-semibold">plays</div>
              </div>
            </div>
          {:else}
            <p class="text-sm opacity-50 text-center py-10">No history found for this range.</p>
          {/each}
        </div>
      </div>

      <!-- Top Tracks List -->
      <div class="card bg-base-200/50 border border-base-content/10 p-6 backdrop-blur-md">
        <h2 class="text-xl font-bold mb-6 text-secondary border-b border-base-content/10 pb-3 flex justify-between items-center">
          <span>Top Tracks</span>
          <span class="badge badge-secondary">{topTracks.length} items</span>
        </h2>
        
        <div class="flex flex-col gap-3">
          {#each topTracks as track, idx}
            <div class="flex items-center gap-4 bg-base-300/30 rounded-xl p-3 border border-base-content/5 hover:bg-base-300/50 transition-colors duration-300">
              <div class="w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center font-bold text-secondary text-sm">
                {idx + 1}
              </div>
              <div class="flex-grow min-w-0">
                <div class="font-extrabold text-base-content truncate">{track.title}</div>
                <div class="text-xs opacity-60 truncate">{track.artist}</div>
              </div>
              <div class="text-right flex-shrink-0">
                <div class="text-md font-black">{track.play_count.toLocaleString()}</div>
                <div class="text-[9px] opacity-40 uppercase font-semibold">plays</div>
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
