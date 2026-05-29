<script lang="ts">
  import { untrack } from 'svelte';
  import { generateWrapped, type WrappedDataInfo } from '../services/api';
  import { appCache } from '../services/store.svelte';

  let wrappedPeriod = $state<'year' | 'quarter' | 'month'>('year');
  let wrappedYear = $state(2025);
  let wrappedQuarter = $state('Q1');
  let wrappedMonth = $state('M1');
  let loadingWrapped = $state(false);
  let wrappedError = $state<string | null>(null);

  // Unique key to cache different review periods
  let cacheKey = $derived(`${wrappedPeriod}-${wrappedYear}-${wrappedQuarter}-${wrappedMonth}`);

  // Auto trigger Wrapped when controls change
  $effect(() => {
    const period = wrappedPeriod;
    const year = wrappedYear;
    const quarter = wrappedQuarter;
    const month = wrappedMonth;
    const key = cacheKey;
    
    untrack(() => {
      runGenerateWrapped(period, year, quarter, month, key);
    });
  });

  async function runGenerateWrapped(
    period: 'year' | 'quarter' | 'month',
    year: number,
    quarter: string,
    month: string,
    key: string
  ) {
    if (appCache.wrapped[key]) {
      wrappedError = null;
      return;
    }
    loadingWrapped = true;
    wrappedError = null;
    try {
      const data = await generateWrapped(period, year, quarter, month);
      appCache.wrapped[key] = data;
    } catch (e) {
      wrappedError = e instanceof Error ? e.message : String(e);
    } finally {
      loadingWrapped = false;
    }
  }

  let currentWrappedData = $derived(appCache.wrapped[cacheKey] || null);
</script>

<div class="flex flex-col gap-6 text-base-content">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 memory-surface">
    <div>
      <h1 class="editorial-text-h1">Periodic Reviews</h1>
      <p class="text-sm opacity-60 mt-1">Spotify Wrapped style summaries for custom time ranges.</p>
    </div>
    
    <!-- Type Selector Tabs -->
    <div class="tabs tabs-boxed">
      <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'year'} onclick={() => { wrappedPeriod = 'year'; }}>Year</button>
      <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'quarter'} onclick={() => { wrappedPeriod = 'quarter'; }}>Quarter</button>
      <button class="tab tab-sm" class:tab-active={wrappedPeriod === 'month'} onclick={() => { wrappedPeriod = 'month'; }}>Month</button>
    </div>
  </div>

  <!-- Review Controls -->
  <div class="flex flex-wrap gap-4 bg-base-200/30 border border-base-content/5 p-4 rounded-xl items-center">
    
    {#if wrappedPeriod === 'year'}
      <div class="form-control">
        <span class="label-text text-xs uppercase font-bold opacity-60 mb-1">Select Year</span>
        <select class="select select-sm select-bordered w-32" bind:value={wrappedYear}>
          <option value={2026}>2026</option>
          <option value={2025}>2025</option>
          <option value={2024}>2024</option>
          <option value={2023}>2023</option>
          <option value={2022}>2022</option>
          <option value={2021}>2021</option>
          <option value={2020}>2020</option>
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
  {:else if currentWrappedData}
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
          <span class="chip-neutral">
            {#if wrappedPeriod === 'year'}
              {wrappedYear}
            {:else}
              {wrappedYear} {wrappedQuarter || wrappedMonth.replace('M', 'Month ')}
            {/if}
          </span>
        </div>

        <!-- Big Statistics -->
        <div class="flex flex-col items-center justify-center py-4 text-center">
          <div class="text-caps text-white opacity-60">Total Plays</div>
          <div class="text-display-large mt-2 text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent">
            {currentWrappedData.total_plays.toLocaleString()}
          </div>
          <div class="text-xs font-semibold opacity-70 mt-2 text-white">
            Approximately <span class="text-pink-400 font-extrabold">{currentWrappedData.minutes_listened.toLocaleString()}</span> minutes of music
          </div>
        </div>

        <!-- Metrics breakdown -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
          
          <!-- Top Artist -->
          <div class="memory-surface-nested bg-white/5 border-white/5 !p-4 flex flex-col">
            <span class="text-caps text-white opacity-50">Top Creator</span>
            {#if currentWrappedData.top_artist}
              <span class="text-md font-extrabold text-white mt-1 truncate">{currentWrappedData.top_artist.name}</span>
              <span class="text-xs opacity-60 mt-1 text-white/80">{currentWrappedData.top_artist.plays.toLocaleString()} plays</span>
            {:else}
              <span class="text-sm opacity-40 mt-1 text-white/40">No plays logged.</span>
            {/if}
          </div>

          <!-- Top Track -->
          <div class="memory-surface-nested bg-white/5 border-white/5 !p-4 flex flex-col">
            <span class="text-caps text-white opacity-50">Top Track</span>
            {#if currentWrappedData.top_track}
              <span class="text-md font-extrabold text-white mt-1 truncate">{currentWrappedData.top_track.title}</span>
              <span class="text-xs opacity-60 truncate mt-0.5 text-white/80">{currentWrappedData.top_track.artist}</span>
              <span class="text-xs opacity-40 mt-1 text-white/50">{currentWrappedData.top_track.plays.toLocaleString()} plays</span>
            {:else}
              <span class="text-sm opacity-40 mt-1 text-white/40">No plays logged.</span>
            {/if}
          </div>

        </div>

        <!-- Peak Day -->
        {#if currentWrappedData.peak_day}
          <div class="memory-surface-nested bg-white/5 border-white/5 !p-4 flex items-center justify-between mt-2">
            <div class="flex flex-col">
              <span class="text-caps text-white opacity-50">Peak Listening Day</span>
              <span class="text-sm font-extrabold text-white mt-1">
                {new Date(currentWrappedData.peak_day.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
            <div class="text-right">
              <span class="text-lg font-black text-secondary">{currentWrappedData.peak_day.plays}</span>
              <span class="text-detail block uppercase font-bold text-white opacity-40 mt-0.5">plays</span>
            </div>
          </div>
        {/if}

      </div>
    </div>
  {/if}
</div>
