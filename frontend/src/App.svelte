<script lang="ts">
  import { onMount } from 'svelte';
  import Heatmap from './components/Heatmap.svelte';
  import HourlyHeatClock from './components/HourlyHeatClock.svelte';
  import StreakTracker from './components/StreakTracker.svelte';

  interface StatsInfo {
    total_listens: number;
    unique_artists: number;
    unique_tracks: number;
    days_active: number;
    avg_per_day: number;
    top_source: string;
  }

  interface StreakInfo {
    current_streak: number;
    longest_streak: number;
  }

  interface ArtistInfo {
    artist: string;
    play_count: number;
  }

  interface TrackInfo {
    artist: string;
    title: string;
    play_count: number;
  }

  interface WrappedDataInfo {
    total_plays: number;
    top_artist: { name: string; plays: number } | null;
    top_track: { artist: string; title: string; plays: number } | null;
    peak_day: { date: string; plays: number } | null;
    minutes_listened: number;
  }

  interface SyncStatusInfo {
    running: boolean;
    finished: boolean;
    mode: string;
    batches_fetched: number;
    synced_count: number;
    lb_total: number;
    local_total: number;
    error: string | null;
  }

  // Navigation state
  let activeTab: 'dashboard' | 'charts' | 'wrapped' = 'dashboard';
  
  // Theme state
  const themes = ["dark", "synthwave", "dracula", "luxury", "night", "cyberpunk", "dim", "coffee"];
  let currentTheme = 'dark';

  // Stats and dashboard data state
  let stats: StatsInfo = { total_listens: 0, unique_artists: 0, unique_tracks: 0, days_active: 0, avg_per_day: 0, top_source: 'None' };
  let streak: StreakInfo = { current_streak: 0, longest_streak: 0 };
  let heatmapData: Record<string, number> = {};
  let hourlyTrends: Record<string, number> = {};
  let monthlyTrends: { month: string; count: number }[] = [];
  let heatmapYear = new Date().getFullYear();
  let loadingStats = true;

  // Top Charts state
  let topRange = 'all'; // 30, 90, 365, all
  let topArtists: ArtistInfo[] = [];
  let topTracks: TrackInfo[] = [];
  let loadingCharts = false;

  // Wrapped / Periodic Review state
  let wrappedPeriod: 'year' | 'quarter' | 'month' | 'decade' = 'year';
  let wrappedYear = 2025;
  let wrappedQuarter = 'Q1';
  let wrappedMonth = 'M1';
  let wrappedDecade = '20s';
  let wrappedData: WrappedDataInfo | null = null;
  let loadingWrapped = false;
  let wrappedError: string | null = null;

  // Sync state
  let syncing = false;
  let syncStatus: SyncStatusInfo | null = null;
  let syncError: string | null = null;
  let forceFullSync = false;
  let syncPollInterval: ReturnType<typeof setInterval> | null = null;

  onMount(() => {
    // Load theme from localStorage or fallback to default
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme && themes.includes(savedTheme)) {
      currentTheme = savedTheme;
    }
    applyTheme(currentTheme);

    // Initial data fetch
    fetchDashboardData();
  });

  function applyTheme(theme: string) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem("theme", theme);
  }

  async function fetchDashboardData() {
    loadingStats = true;
    try {
      const [statsRes, streakRes, heatmapRes, hourlyRes, monthlyRes] = await Promise.all([
        fetch('/api/stats').then(res => res.json()),
        fetch('/api/trends/streak').then(res => res.json()),
        fetch(`/api/heatmap?year=${heatmapYear}`).then(res => res.json()),
        fetch('/api/trends/hourly').then(res => res.json()),
        fetch('/api/trends/monthly').then(res => res.json())
      ]);

      stats = statsRes;
      streak = streakRes;
      heatmapData = heatmapRes;
      hourlyTrends = hourlyRes;
      monthlyTrends = monthlyRes;
    } catch (e) {
      console.error("Failed to fetch dashboard data:", e);
    } finally {
      loadingStats = false;
    }
  }

  async function fetchTopCharts() {
    loadingCharts = true;
    try {
      const [artistsRes, tracksRes] = await Promise.all([
        fetch(`/api/top-artists?range=${topRange}&limit=15`).then(res => res.json()),
        fetch(`/api/top-tracks?range=${topRange}&limit=15`).then(res => res.json())
      ]);
      topArtists = artistsRes;
      topTracks = tracksRes;
    } catch (e) {
      console.error("Failed to fetch top charts:", e);
    } finally {
      loadingCharts = false;
    }
  }

  async function generateWrapped() {
    loadingWrapped = true;
    wrappedError = null;
    wrappedData = null;
    
    let queryParams = [];
    if (wrappedPeriod === 'decade') {
      queryParams.push(`decade=${wrappedDecade}`);
    } else {
      queryParams.push(`year=${wrappedYear}`);
      if (wrappedPeriod === 'quarter') queryParams.push(`quarter=${wrappedQuarter}`);
      if (wrappedPeriod === 'month') queryParams.push(`month=${wrappedMonth}`);
    }

    try {
      const res = await fetch(`/api/wrapped?${queryParams.join('&')}`);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to generate Wrapped.");
      }
      wrappedData = await res.json();
    } catch (e) {
      wrappedError = e instanceof Error ? e.message : String(e);
    } finally {
      loadingWrapped = false;
    }
  }

  async function runSync() {
    syncing = true;
    syncError = null;
    syncStatus = null;

    // Clear any previous poll
    if (syncPollInterval !== null) {
      clearInterval(syncPollInterval);
      syncPollInterval = null;
    }

    try {
      const url = forceFullSync ? '/api/sync?mode=full' : '/api/sync';
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Sync failed to start.');
      }
      // Returned immediately — now poll for status
      syncPollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch('/api/sync/status');
          const data: SyncStatusInfo = await statusRes.json();
          syncStatus = data;
          if (data.finished) {
            clearInterval(syncPollInterval!);
            syncPollInterval = null;
            syncing = false;
            forceFullSync = false;
            if (data.error) {
              syncError = data.error;
            } else {
              // Refresh dashboard now that new scrobbles are in the DB
              await fetchDashboardData();
            }
          }
        } catch (e) {
          clearInterval(syncPollInterval!);
          syncPollInterval = null;
          syncing = false;
          syncError = e instanceof Error ? e.message : String(e);
        }
      }, 2000);
    } catch (e) {
      syncing = false;
      syncError = e instanceof Error ? e.message : String(e);
    }
  }

  // Trigger charts fetch when range or active tab changes
  $: if (activeTab === 'charts') {
    fetchTopCharts();
  }
  $: if (topRange) {
    if (activeTab === 'charts') fetchTopCharts();
  }

  // Auto trigger Wrapped when controls change
  $: if (activeTab === 'wrapped' && (wrappedPeriod || wrappedYear || wrappedQuarter || wrappedMonth || wrappedDecade)) {
    generateWrapped();
  }

  // Reload heatmap when selected year changes
  $: if (heatmapYear) {
    fetch(`/api/heatmap?year=${heatmapYear}`)
      .then(res => res.json())
      .then(data => { heatmapData = data; })
      .catch(err => console.error(err));
  }
</script>

<div class="drawer lg:drawer-open min-h-screen bg-base-100">
  <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" />
  
  <!-- Drawer content (Main Screen) -->
  <div class="drawer-content flex flex-col bg-base-100 text-base-content min-h-screen">
    
    <!-- Navbar (Mobile only) -->
    <div class="navbar bg-base-200 border-b border-base-content/10 lg:hidden flex justify-between px-4">
      <div class="flex items-center gap-2">
        <label for="sidebar-drawer" class="btn btn-ghost btn-square drawer-button">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
        </label>
        <span class="text-lg font-extrabold tracking-wider">The Record</span>
      </div>
      
      <!-- Quick Theme Switcher -->
      <select class="select select-sm select-bordered max-w-xs" bind:value={currentTheme} on:change={() => applyTheme(currentTheme)}>
        {#each themes as theme}
          <option value={theme}>{theme}</option>
        {/each}
      </select>
    </div>

    <!-- Main Content Area -->
    <main class="flex-grow p-4 lg:p-8 max-w-[1400px] w-full mx-auto">
      
      <!-- DASHBOARD OVERVIEW -->
      {#if activeTab === 'dashboard'}
        <div class="flex flex-col gap-6">
          
          <!-- Header and Sync -->
          <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-base-200/40 border border-base-content/5 rounded-2xl p-6 backdrop-blur-md">
            <div>
              <h1 class="text-3xl font-extrabold tracking-tight">Music History</h1>
              <p class="text-sm opacity-60 mt-1">Self-hosted scrobble archives and listening insight analytics.</p>
            </div>
            
            <!-- Sync Action -->
            <div class="flex flex-col items-end gap-2 w-full sm:w-auto">
              <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
                <label class="label cursor-pointer gap-2 py-0">
                  <span class="label-text text-[10px] opacity-60">Force Full Sync</span>
                  <input type="checkbox" bind:checked={forceFullSync} class="checkbox checkbox-xs checkbox-primary" />
                </label>
                <button 
                  class="btn btn-primary btn-md w-full sm:w-auto shadow-lg" 
                  disabled={syncing}
                  on:click={runSync}
                >
                  {#if syncing}
                    <span class="loading loading-spinner loading-xs"></span>
                    Syncing ListenBrainz...
                  {:else}
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                    </svg>
                    Sync Now
                  {/if}
                </button>
              </div>
              
              {#if syncing && syncStatus}
                <span class="text-[10px] opacity-70 font-semibold">
                  Batch {Math.max(1, syncStatus.batches_fetched)}{syncStatus.mode === 'full' && syncStatus.lb_total ? ' of ' + Math.ceil(syncStatus.lb_total / 1000) : ''} · {syncStatus.synced_count} new
                </span>
              {/if}
              {#if !syncing && syncStatus?.finished && !syncStatus.error}
                <span class="text-[10px] text-success font-semibold">
                  ✓ Synced {syncStatus.synced_count} new play{syncStatus.synced_count === 1 ? '' : 's'}
                  ({syncStatus.batches_fetched} batch{syncStatus.batches_fetched === 1 ? '' : 'es'})
                </span>
              {/if}
              {#if syncError}
                <span class="text-[10px] text-error font-semibold max-w-[250px] text-right">
                  {syncError}
                </span>
              {/if}
            </div>
          </div>

          <!-- Stats Grid -->
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

            <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4">
              <div class="stat-title text-xs font-semibold uppercase opacity-60">Active Days</div>
              <div class="stat-value text-2xl font-black mt-1">{stats.days_active.toLocaleString()}</div>
              <div class="stat-desc text-[9px] opacity-40 mt-1">total days logged</div>
            </div>

            <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4">
              <div class="stat-title text-xs font-semibold uppercase opacity-60">Scrobbles/Day</div>
              <div class="stat-value text-2xl font-black mt-1">{stats.avg_per_day}</div>
              <div class="stat-desc text-[9px] opacity-40 mt-1">daily play rate</div>
            </div>

            <div class="stat bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10 p-4">
              <div class="stat-title text-xs font-semibold uppercase opacity-60">Top Source</div>
              <div class="stat-value text-xl font-bold truncate mt-1 capitalize">{stats.top_source.replace('_', ' ')}</div>
              <div class="stat-desc text-[9px] opacity-40 mt-1">primary music pipeline</div>
            </div>
          </div>

          <!-- Heatmap Contribution Board -->
          <div class="flex flex-col gap-4">
            <div class="flex justify-between items-center px-2">
              <h2 class="text-xl font-bold tracking-tight">Listening Activity</h2>
              <div class="join">
                <button class="join-item btn btn-xs btn-outline" aria-label="Previous Year" on:click={() => heatmapYear--}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M11.78 5.22a.75.75 0 010 1.06L8.06 10l3.72 3.72a.75.75 0 11-1.06 1.06l-4.25-4.25a.75.75 0 010-1.06l4.25-4.25a.75.75 0 011.06 0z" clip-rule="evenodd" /></svg>
                </button>
                <span class="join-item btn btn-xs btn-active bg-base-300 font-bold px-4">{heatmapYear}</span>
                <button class="join-item btn btn-xs btn-outline" aria-label="Next Year" on:click={() => heatmapYear++}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 011.06 0l4.25 4.25a.75.75 0 010 1.06l-4.25 4.25a.75.75 0 01-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 010-1.06z" clip-rule="evenodd" /></svg>
                </button>
              </div>
            </div>
            <Heatmap data={heatmapData} year={heatmapYear} />
          </div>

          <!-- Sub Grid for Hourly clock + Streaks -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <HourlyHeatClock hourlyData={hourlyTrends} />
            <StreakTracker streakData={streak} />
          </div>

        </div>

      <!-- TOP CHARTS VIEW -->
      {:else if activeTab === 'charts'}
        <div class="flex flex-col gap-6">
          <div class="flex justify-between items-center bg-base-200/40 border border-base-content/5 rounded-2xl p-6 backdrop-blur-md">
            <div>
              <h1 class="text-3xl font-extrabold tracking-tight">Top Charts</h1>
              <p class="text-sm opacity-60 mt-1">Your most played tracks and artists over time.</p>
            </div>
            
            <!-- Range Selector Tabs -->
            <div class="tabs tabs-boxed">
              <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === '30'} on:click={() => topRange = '30'}>30 Days</button>
              <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === '90'} on:click={() => topRange = '90'}>90 Days</button>
              <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === '365'} on:click={() => topRange = '365'}>1 Year</button>
              <button class="tab tab-sm sm:tab-md" class:tab-active={topRange === 'all'} on:click={() => topRange = 'all'}>All Time</button>
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

      <!-- PERIODIC REVIEWS / WRAPPED -->
      {:else if activeTab === 'wrapped'}
        <div class="flex flex-col gap-6">
          <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-base-200/40 border border-base-content/5 rounded-2xl p-6 backdrop-blur-md">
            <div>
              <h1 class="text-3xl font-extrabold tracking-tight">Periodic Reviews</h1>
              <p class="text-sm opacity-60 mt-1">Spotify Wrapped style summaries for custom time ranges.</p>
            </div>
            
            <!-- Type Selector Tabs -->
            <div class="tabs tabs-boxed">
              <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'year'} on:click={() => { wrappedPeriod = 'year'; }}>Year</button>
              <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'quarter'} on:click={() => { wrappedPeriod = 'quarter'; }}>Quarter</button>
              <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'month'} on:click={() => { wrappedPeriod = 'month'; }}>Month</button>
              <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'decade'} on:click={() => { wrappedPeriod = 'decade'; }}>Decade</button>
            </div>
          </div>

          <!-- Review Controls -->
          <div class="flex flex-wrap gap-4 bg-base-200/30 border border-base-content/5 p-4 rounded-xl items-center">
            
            {#if wrappedPeriod !== 'decade'}
              <div class="form-control">
                <span class="label-text text-xs uppercase font-bold opacity-60 mb-1">Select Year</span>
                <select class="select select-sm select-bordered w-32" bind:value={wrappedYear}>
                  <option value={2026}>2026</option>
                  <option value={2025}>2025</option>
                  <option value={2024}>2024</option>
                  <option value={2023}>2023</option>
                  <option value={2022}>2022</option>
                </select>
              </div>
            {/if}

            {#if wrappedPeriod === 'quarter'}
              <div class="form-control">
                <span class="label-text text-xs uppercase font-bold opacity-60 mb-1">Select Quarter</span>
                <select class="select select-sm select-bordered w-32" bind:value={wrappedQuarter}>
                  <option value="Q1">Q1 (Jan-Mar)</option>
                  <option value="Q2">Q2 (Apr-Jun)</option>
                  <option value="Q3">Q3 (Jul-Sep)</option>
                  <option value="Q4">Q4 (Oct-Dec)</option>
                </select>
              </div>
            {/if}

            {#if wrappedPeriod === 'month'}
              <div class="form-control">
                <span class="label-text text-xs uppercase font-bold opacity-60 mb-1">Select Month</span>
                <select class="select select-sm select-bordered w-40" bind:value={wrappedMonth}>
                  <option value="M1">January</option>
                  <option value="M2">February</option>
                  <option value="M3">March</option>
                  <option value="M4">April</option>
                  <option value="M5">May</option>
                  <option value="M6">June</option>
                  <option value="M7">July</option>
                  <option value="M8">August</option>
                  <option value="M9">September</option>
                  <option value="M10">October</option>
                  <option value="M11">November</option>
                  <option value="M12">December</option>
                </select>
              </div>
            {/if}

            {#if wrappedPeriod === 'decade'}
              <div class="form-control">
                <span class="label-text text-xs uppercase font-bold opacity-60 mb-1">Select Decade</span>
                <select class="select select-sm select-bordered w-36" bind:value={wrappedDecade}>
                  <option value="20s">2020s</option>
                  <option value="10s">2010s</option>
                </select>
              </div>
            {/if}
          </div>

          <!-- Wrapped Result Card -->
          {#if loadingWrapped}
            <div class="flex justify-center items-center py-20">
              <span class="loading loading-spinner loading-lg text-secondary"></span>
            </div>
          {:else if wrappedError}
            <div class="alert alert-error bg-error/15 border-error/20 text-error">
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <span>{wrappedError}</span>
            </div>
          {:else if wrappedData}
            <div class="card max-w-xl mx-auto w-full bg-gradient-to-br from-indigo-900/40 via-purple-900/40 to-pink-900/40 border border-white/10 p-8 rounded-3xl relative overflow-hidden shadow-2xl group">
              <!-- Glow backings -->
              <div class="absolute -top-12 -left-12 w-40 h-40 bg-primary/20 rounded-full blur-3xl transition-transform duration-700 group-hover:scale-150"></div>
              <div class="absolute -bottom-12 -right-12 w-40 h-40 bg-secondary/20 rounded-full blur-3xl transition-transform duration-700 group-hover:scale-150"></div>

              <div class="relative flex flex-col gap-6">
                <!-- Card Header -->
                <div class="flex justify-between items-center border-b border-white/10 pb-4">
                  <div class="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-pink-400">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 0L5.25 7.5M19.5 6v10.5m-15-9v10.5m0 0a3 3 0 103 3 3 3 0 00-3-3zm15-3a3 3 0 103 3 3 3 0 00-3-3z" />
                    </svg>
                    <span class="text-sm font-bold uppercase tracking-widest text-pink-400">The Record Wrapped</span>
                  </div>
                  <span class="badge badge-accent uppercase font-black text-[10px]">
                    {#if wrappedPeriod === 'decade'}
                      {wrappedDecade === '20s' ? '2020s' : '2010s'}
                    {:else if wrappedPeriod === 'year'}
                      {wrappedYear}
                    {:else if wrappedPeriod === 'quarter'}
                      {wrappedYear} {wrappedQuarter}
                    {:else}
                      {wrappedYear} {wrappedMonth.replace('M', 'Month ')}
                    {/if}
                  </span>
                </div>

                <!-- Big Statistics -->
                <div class="flex flex-col items-center justify-center py-4 text-center">
                  <div class="text-[11px] font-extrabold uppercase tracking-widest opacity-60">Total Plays</div>
                  <div class="text-5xl font-black mt-2 text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent">
                    {wrappedData.total_plays.toLocaleString()}
                  </div>
                  <div class="text-xs font-semibold opacity-70 mt-2">
                    Approximately <span class="text-pink-400 font-extrabold">{wrappedData.minutes_listened.toLocaleString()}</span> minutes of music
                  </div>
                </div>

                <!-- Metrics breakdown -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
                  
                  <!-- Top Artist -->
                  <div class="bg-white/5 border border-white/5 rounded-2xl p-4 flex flex-col">
                    <span class="text-[9px] font-bold uppercase tracking-wider opacity-50">Top Creator</span>
                    {#if wrappedData.top_artist}
                      <span class="text-md font-extrabold text-white mt-1 truncate">{wrappedData.top_artist.name}</span>
                      <span class="text-xs opacity-60 mt-1">{wrappedData.top_artist.plays.toLocaleString()} plays</span>
                    {:else}
                      <span class="text-sm opacity-40 mt-1">No plays logged.</span>
                    {/if}
                  </div>

                  <!-- Top Track -->
                  <div class="bg-white/5 border border-white/5 rounded-2xl p-4 flex flex-col">
                    <span class="text-[9px] font-bold uppercase tracking-wider opacity-50">Top Track</span>
                    {#if wrappedData.top_track}
                      <span class="text-md font-extrabold text-white mt-1 truncate">{wrappedData.top_track.title}</span>
                      <span class="text-xs opacity-60 truncate mt-0.5">{wrappedData.top_track.artist}</span>
                      <span class="text-xs opacity-40 mt-1">{wrappedData.top_track.plays.toLocaleString()} plays</span>
                    {:else}
                      <span class="text-sm opacity-40 mt-1">No plays logged.</span>
                    {/if}
                  </div>

                </div>

                <!-- Peak Day -->
                {#if wrappedData.peak_day}
                  <div class="bg-white/5 border border-white/5 rounded-2xl p-4 flex items-center justify-between mt-2">
                    <div class="flex flex-col">
                      <span class="text-[9px] font-bold uppercase tracking-wider opacity-50">Peak Listening Day</span>
                      <span class="text-sm font-extrabold text-white mt-1">
                        {new Date(wrappedData.peak_day.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    </div>
                    <div class="text-right">
                      <span class="text-lg font-black text-secondary">{wrappedData.peak_day.plays}</span>
                      <span class="text-[9px] block uppercase opacity-40 font-bold">plays</span>
                    </div>
                  </div>
                {/if}

              </div>
            </div>
          {/if}
        </div>
      {/if}
      
    </main>
  </div> 

  <!-- Sidebar Container -->
  <div class="drawer-side border-r border-base-content/10">
    <label for="sidebar-drawer" class="drawer-overlay"></label> 
    
    <div class="menu p-4 w-64 min-h-screen bg-base-200 text-base-content flex flex-col justify-between">
      
      <!-- Top Section -->
      <div>
        <!-- Logo Branding -->
        <div class="flex items-center gap-3 px-2 py-4 mb-6">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-8 h-8 text-primary">
            <circle cx="12" cy="12" r="10" stroke-width="1.5" class="stroke-current" />
            <circle cx="12" cy="12" r="7" stroke-width="0.5" stroke-dasharray="2 1" class="stroke-current opacity-80" />
            <circle cx="12" cy="12" r="4" stroke-width="0.5" stroke-dasharray="1 1" class="stroke-current opacity-60" />
            <circle cx="12" cy="12" r="2.5" class="fill-secondary stroke-none" />
            <circle cx="12" cy="12" r="0.8" class="fill-base-100 stroke-none" />
          </svg>
          <span class="text-xl font-black tracking-widest uppercase bg-clip-text bg-gradient-to-r from-primary to-secondary text-transparent">
            The Record
          </span>
        </div>

        <!-- Navigation Tabs -->
        <ul class="flex flex-col gap-2">
          <li>
            <button 
              class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm transition-all duration-300"
              class:bg-primary={activeTab === 'dashboard'}
              class:text-primary-content={activeTab === 'dashboard'}
              class:bg-transparent={activeTab !== 'dashboard'}
              on:click={() => activeTab = 'dashboard'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v4.875h4.875c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
              Overview
            </button>
          </li>
          
          <li>
            <button 
              class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm transition-all duration-300"
              class:bg-primary={activeTab === 'charts'}
              class:text-primary-content={activeTab === 'charts'}
              class:bg-transparent={activeTab !== 'charts'}
              on:click={() => activeTab = 'charts'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v16.5M21 19.5H3.75M6.75 15v-4.5m3.75 4.5V8.25m3.75 11.25v-8.25m3.75 8.25V6" />
              </svg>
              Top Charts
            </button>
          </li>

          <li>
            <button 
              class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm transition-all duration-300"
              class:bg-primary={activeTab === 'wrapped'}
              class:text-primary-content={activeTab === 'wrapped'}
              class:bg-transparent={activeTab !== 'wrapped'}
              on:click={() => activeTab = 'wrapped'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
              Reviews
            </button>
          </li>
        </ul>
      </div>
      
      <!-- Bottom Theme Switcher Section (Desktop only) -->
      <div class="border-t border-base-content/10 pt-4 flex flex-col gap-2">
        <span class="text-[10px] font-bold uppercase opacity-50 px-2 tracking-wider">Select Theme</span>
        <select class="select select-sm select-bordered w-full" bind:value={currentTheme} on:change={() => applyTheme(currentTheme)}>
          {#each themes as theme}
            <option value={theme}>{theme}</option>
          {/each}
        </select>
      </div>

    </div>
  </div>
</div>
