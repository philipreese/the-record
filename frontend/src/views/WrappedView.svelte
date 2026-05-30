<script lang="ts">
  import { untrack } from 'svelte';
  import { fade } from 'svelte/transition';
  import { generateWrapped, type WrappedDataInfo } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import AnimatedCounter from '../components/dashboard/AnimatedCounter.svelte';

  let wrappedPeriod = $state<'year' | 'quarter' | 'month'>('year');
  let wrappedYear = $state(2026);
  let wrappedQuarter = $state('Q1');
  let wrappedMonth = $state('M1');
  let loadingWrapped = $state(false);
  let wrappedError = $state<string | null>(null);

  // Pagination slide index
  let currentStep = $state(0);

  // Unique key to cache different review periods
  let cacheKey = $derived(`${wrappedPeriod}-${wrappedYear}-${wrappedQuarter}-${wrappedMonth}`);

  // Reset pagination step when target parameters change
  $effect(() => {
    const _key = cacheKey;
    currentStep = 0;
  });

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

  function getMonthName(m: string): string {
    const monthIndex = parseInt(m.replace('M', ''), 10);
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months[monthIndex - 1] || m;
  }
</script>

<div class="flex flex-col gap-12 text-base-content">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 pb-4 border-b">
    <div>
      <h1 class="editorial-text-h1 lowercase italic">periodic reviews</h1>
      <p class="text-caps mt-2">Spotify Wrapped style summaries for custom time ranges.</p>
    </div>
    
    <!-- Type Selector Options -->
    <div class="flex items-center gap-6 font-mono text-xs tracking-widest uppercase py-1">
      {#each [['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']] as [period, label]}
        <button 
          class="hover:text-theme-accent cursor-pointer transition-colors duration-200 focus:outline-none" 
          class:text-theme-accent={wrappedPeriod === period}
          class:text-theme-muted={wrappedPeriod !== period}
          onclick={() => { wrappedPeriod = period as 'year' | 'quarter' | 'month'; }}
        >
          {label}
        </button>
      {/each}
    </div>
  </div>

  <!-- Review Controls (Borderless Selects) -->
  <div class="flex flex-wrap gap-8 items-center px-2">
    
    {#if wrappedPeriod === 'year'}
      <div class="flex items-center gap-3">
        <span class="text-caps text-xs text-theme-muted">Year</span>
        <select 
          class="bg-transparent border-b font-mono text-sm focus:outline-none py-1 cursor-pointer border-theme-border-heavy text-theme-text" 
          bind:value={wrappedYear}
        >
          <option value={2026} class="bg-base-100">2026</option>
          <option value={2025} class="bg-base-100">2025</option>
          <option value={2024} class="bg-base-100">2024</option>
          <option value={2023} class="bg-base-100">2023</option>
          <option value={2022} class="bg-base-100">2022</option>
          <option value={2021} class="bg-base-100">2021</option>
          <option value={2020} class="bg-base-100">2020</option>
        </select>
      </div>
    {/if}

    {#if wrappedPeriod === 'quarter'}
      <div class="flex items-center gap-3">
        <span class="text-caps text-xs text-theme-muted">Quarter</span>
        <select 
          class="bg-transparent border-b font-mono text-sm focus:outline-none py-1 cursor-pointer border-theme-border-heavy text-theme-text" 
          bind:value={wrappedQuarter}
        >
          <option value="Q1" class="bg-base-100">Q1 (Jan-Mar)</option>
          <option value="Q2" class="bg-base-100">Q2 (Apr-Jun)</option>
          <option value="Q3" class="bg-base-100">Q3 (Jul-Sep)</option>
          <option value="Q4" class="bg-base-100">Q4 (Oct-Dec)</option>
        </select>
      </div>
    {/if}

    {#if wrappedPeriod === 'month'}
      <div class="flex items-center gap-3">
        <span class="text-caps text-xs text-theme-muted">Month</span>
        <select 
          class="bg-transparent border-b font-mono text-sm focus:outline-none py-1 cursor-pointer border-theme-border-heavy text-theme-text" 
          bind:value={wrappedMonth}
        >
          <option value="M1" class="bg-base-100">January</option>
          <option value="M2" class="bg-base-100">February</option>
          <option value="M3" class="bg-base-100">March</option>
          <option value="M4" class="bg-base-100">April</option>
          <option value="M5" class="bg-base-100">May</option>
          <option value="M6" class="bg-base-100">June</option>
          <option value="M7" class="bg-base-100">July</option>
          <option value="M8" class="bg-base-100">August</option>
          <option value="M9" class="bg-base-100">September</option>
          <option value="M10" class="bg-base-100">October</option>
          <option value="M11" class="bg-base-100">November</option>
          <option value="M12" class="bg-base-100">December</option>
        </select>
      </div>
    {/if}
  </div>

  <!-- Wrapped Result Card -->
  {#if loadingWrapped}
    <div class="flex justify-center items-center py-20">
      <span class="loading loading-spinner loading-md text-primary"></span>
    </div>
  {:else if wrappedError}
    <div class="max-w-xl mx-auto w-full p-4 rounded-xl text-center text-sm font-mono text-theme-secondary bg-theme-neutral-soft border border-dashed border-theme-border-heavy">
      {wrappedError}
    </div>
  {:else if currentWrappedData}
    <div class="max-w-xl mx-auto w-full memory-surface relative overflow-visible flex flex-col justify-between min-h-[380px] p-8 shadow-2xl">
      <!-- Glow backings for ambient warmth (desaturated) -->
      <div class="absolute -top-12 -left-12 w-40 h-40 rounded-full blur-3xl pointer-events-none transition-transform duration-700 bg-theme-accent-soft"></div>
      <div class="absolute -bottom-12 -right-12 w-40 h-40 rounded-full blur-3xl pointer-events-none transition-transform duration-700 bg-theme-accent-soft/80"></div>
 
      <div class="flex-grow flex flex-col justify-center">
        <!-- Reflective view transitions -->
        {#key currentStep}
          <div in:fade={{ duration: 380, delay: 100 }} out:fade={{ duration: 220 }}>
            
            {#if currentStep === 0}
              <!-- Slide 0: Cover & Summary Dashboard -->
              <div class="grid grid-cols-1 md:grid-cols-5 gap-8 items-center py-4">
                <!-- Left side: Narrative & CTA -->
                <div class="md:col-span-2 space-y-5 text-center md:text-left">
                  <span class="text-xs font-mono tracking-widest text-zinc-500 uppercase">01 / The Archeology</span>
                  <h2 class="editorial-text-h1 lowercase text-3xl">
                    reviewing the <span class="italic text-theme-accent">resonance</span>
                  </h2>
                  <p class="text-sm font-light leading-relaxed text-theme-secondary">
                    Unfolding the musical residue of your archive for 
                    <span class="text-theme-accent font-normal">
                    {#if wrappedPeriod === 'year'}
                      the year {wrappedYear}.
                    {:else if wrappedPeriod === 'quarter'}
                      {wrappedYear} {wrappedQuarter}.
                    {:else}
                      {getMonthName(wrappedMonth)} {wrappedYear}.
                    {/if}
                    </span>
                  </p>
                  <div class="pt-2">
                    <button 
                      class="btn btn-md btn-outline rounded-full font-mono text-xs tracking-widest uppercase cursor-pointer px-6 text-theme-accent border-theme-accent/30"
                      onclick={() => currentStep++}
                    >
                      Begin Deep Dive &rarr;
                    </button>
                  </div>
                </div>

                <!-- Right side: The Resonance Log Grid -->
                <div class="md:col-span-3 border-t md:border-t-0 md:border-l border-theme-border-soft pt-6 md:pt-0 md:pl-8">
                  <div class="grid grid-cols-2 gap-6">
                    <!-- Col 1: Total Plays -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Total Plays</span>
                      <div class="text-xl font-light font-sans tracking-tight text-theme-text">
                        <AnimatedCounter value={currentWrappedData.total_plays} />
                      </div>
                    </div>

                    <!-- Col 2: Minutes Listened -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Minutes Listened</span>
                      <div class="text-xl font-light font-sans tracking-tight text-theme-text">
                        <AnimatedCounter value={currentWrappedData.minutes_listened} />
                      </div>
                    </div>

                    <!-- Col 3: Top Creator -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Top Creator</span>
                      {#if currentWrappedData.top_artist}
                        <div class="text-base font-light truncate text-theme-text">
                          {currentWrappedData.top_artist.name}
                        </div>
                        <div class="text-xs font-mono text-zinc-400">
                          {currentWrappedData.top_artist.plays.toLocaleString()} plays
                        </div>
                      {:else}
                        <div class="text-xs opacity-40">No records</div>
                      {/if}
                    </div>

                    <!-- Col 4: Top Track -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Top Track</span>
                      {#if currentWrappedData.top_track}
                        <div class="text-base font-light truncate text-theme-text">
                          {currentWrappedData.top_track.title}
                        </div>
                        <div class="text-xs font-light opacity-60 truncate text-theme-secondary">
                          by {currentWrappedData.top_track.artist}
                        </div>
                      {:else}
                        <div class="text-xs opacity-40">No records</div>
                      {/if}
                    </div>

                    <!-- Peak Intensity -->
                    {#if currentWrappedData.peak_day}
                      <div class="col-span-2 pt-6 border-t border-theme-border-soft">
                        <span class="text-caps text-xs text-theme-muted">Peak Intensity</span>
                        <div class="flex justify-between items-baseline">
                          <div class="text-base font-light truncate text-theme-text">
                            {new Date(currentWrappedData.peak_day.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}
                          </div>
                          <div class="text-base font-light text-theme-accent">
                            {currentWrappedData.peak_day.plays} plays
                          </div>
                        </div>
                      </div>
                    {/if}
                  </div>
                </div>
              </div>

            {:else if currentStep === 1}
              <!-- Slide 1: Volume / Duration -->
              <div class="text-center space-y-4 py-4">
                <span class="text-xs font-mono tracking-widest text-zinc-500 uppercase">02 / Duration & Echo</span>
                <div class="space-y-1">
                  <div class="text-display-large text-theme-accent">
                    <AnimatedCounter value={currentWrappedData.total_plays} />
                  </div>
                  <div class="text-caps text-xs text-theme-muted">Total Plays Logged</div>
                </div>
                <div class="pt-4 text-sm font-light max-w-sm mx-auto leading-relaxed text-theme-secondary">
                  This volume amounts to approximately <span class="font-normal font-mono text-sm text-theme-accent">{currentWrappedData.minutes_listened.toLocaleString()}</span> minutes of active listening, a steady acoustic flow in your memory space.
                </div>
              </div>

            {:else if currentStep === 2}
              <!-- Slide 2: Companions (Top Artist / Track) -->
              <div class="space-y-6 py-2">
                <div class="text-center">
                  <span class="text-xs font-mono tracking-widest text-zinc-500 uppercase">03 / Key Companions</span>
                </div>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-4">
                  <div class="p-6 rounded-2xl border text-center space-y-2 border-theme-border-soft bg-theme-neutral-soft">
                    <div class="text-xs font-mono tracking-widest text-zinc-500 uppercase">Top Creator</div>
                    {#if currentWrappedData.top_artist}
                      <div class="text-lg font-light truncate text-theme-text">{currentWrappedData.top_artist.name}</div>
                      <div class="text-xs font-mono text-zinc-400 mt-1">{currentWrappedData.top_artist.plays.toLocaleString()} plays</div>
                    {:else}
                      <div class="text-sm opacity-40">No records</div>
                    {/if}
                  </div>

                  <div class="p-6 rounded-2xl border text-center space-y-2 border-theme-border-soft bg-theme-neutral-soft">
                    <div class="text-xs font-mono tracking-widest text-zinc-500 uppercase">Top Track</div>
                    {#if currentWrappedData.top_track}
                      <div class="text-lg font-light truncate text-theme-text">{currentWrappedData.top_track.title}</div>
                      <div class="text-xs font-light opacity-60 truncate text-theme-secondary">{currentWrappedData.top_track.artist}</div>
                      <div class="text-xs font-mono text-zinc-400 mt-0.5">{currentWrappedData.top_track.plays.toLocaleString()} plays</div>
                    {:else}
                      <div class="text-sm opacity-40">No records</div>
                    {/if}
                  </div>
                </div>
              </div>

            {:else if currentStep === 3}
              <!-- Slide 3: Peak Day -->
              <div class="text-center space-y-6 py-4">
                <span class="text-xs font-mono tracking-widest text-zinc-500 uppercase">04 / Peak Intensity</span>
                
                {#if currentWrappedData.peak_day}
                  <div class="space-y-2">
                    <div class="text-xs font-mono uppercase tracking-widest text-zinc-500">Peak listening day</div>
                    <h3 class="text-3xl font-serif italic text-theme-text">
                      {new Date(currentWrappedData.peak_day.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}
                    </h3>
                  </div>
                  <div class="text-xl font-light text-theme-accent">
                    {currentWrappedData.peak_day.plays} plays <span class="text-xs font-mono text-zinc-400">in 24 hours</span>
                  </div>
                  <p class="text-sm font-light max-w-sm mx-auto leading-relaxed text-theme-secondary">
                    A day of intense musical immersion, leaving a distinct marker in your temporal archive.
                  </p>
                {:else}
                  <p class="text-sm opacity-50">No peak anomalies identified.</p>
                {/if}
              </div>
            {/if}

          </div>
        {/key}
      </div>

      <!-- Slide Navigation Controls -->
      <div class="flex items-center justify-between border-t border-theme-border-soft mt-8 pt-4">
        <button 
          class="text-xs font-mono tracking-widest uppercase focus:outline-none disabled:opacity-20 cursor-pointer text-theme-secondary"
          disabled={currentStep === 0}
          onclick={() => currentStep--}
        >
          &larr; Back
        </button>

        <div class="flex gap-2.5">
          {#each Array.from({ length: 4 }) as _, idx}
            <div class="w-1.5 h-1.5 rounded-full transition-all duration-300" 
                 style="background-color: {currentStep === idx ? 'var(--accent)' : 'color-mix(in srgb, var(--text-primary) 20%, transparent)'};">
            </div>
          {/each}
        </div>

        {#if currentStep < 3}
          <button 
            class="text-xs font-mono tracking-widest uppercase focus:outline-none cursor-pointer text-theme-accent"
            onclick={() => currentStep++}
          >
            Next &rarr;
          </button>
        {:else}
          <button 
            class="text-xs font-mono tracking-widest uppercase focus:outline-none cursor-pointer text-theme-accent"
            onclick={() => currentStep = 0}
          >
            Restart
          </button>
        {/if}
      </div>

    </div>
  {/if}
</div>
