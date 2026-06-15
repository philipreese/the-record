<script lang="ts">
  import { untrack } from 'svelte';
  import { fade } from 'svelte/transition';
  import {
    generateWrapped,
    type WrappedQuarter,
    type WrappedMonth,
    type WrappedDataInfo,
  } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import AnimatedCounter from '../components/dashboard/AnimatedCounter.svelte';
  import SelectDropdown from '../components/layout/SelectDropdown.svelte';
  import { tooltip } from '../utils/tooltip';
  import PageHeader from '../components/layout/PageHeader.svelte';

  const yearOptions = [
    { value: 2026, label: '2026' },
    { value: 2025, label: '2025' },
    { value: 2024, label: '2024' },
    { value: 2023, label: '2023' },
    { value: 2022, label: '2022' },
    { value: 2021, label: '2021' },
    { value: 2020, label: '2020' },
  ];

  const quarterOptions = [
    { value: 'Q1', label: 'Q1 (Jan-Mar)' },
    { value: 'Q2', label: 'Q2 (Apr-Jun)' },
    { value: 'Q3', label: 'Q3 (Jul-Sep)' },
    { value: 'Q4', label: 'Q4 (Oct-Dec)' },
  ];

  const monthOptions = [
    { value: 'M1', label: 'January' },
    { value: 'M2', label: 'February' },
    { value: 'M3', label: 'March' },
    { value: 'M4', label: 'April' },
    { value: 'M5', label: 'May' },
    { value: 'M6', label: 'June' },
    { value: 'M7', label: 'July' },
    { value: 'M8', label: 'August' },
    { value: 'M9', label: 'September' },
    { value: 'M10', label: 'October' },
    { value: 'M11', label: 'November' },
    { value: 'M12', label: 'December' },
  ];

  let wrappedPeriod = $state<'year' | 'quarter' | 'month'>('year');
  let wrappedYear = $state(2026);
  let wrappedQuarter = $state<WrappedQuarter>('Q1');
  let wrappedMonth = $state<WrappedMonth>('M1');
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

  // Auto trigger Wrapped when controls change. Reading the cache entry here keeps the
  // effect reactive to invalidation: a sync clears appCache.wrapped and this refetches.
  $effect(() => {
    const period = wrappedPeriod;
    const year = wrappedYear;
    const quarter = wrappedQuarter;
    const month = wrappedMonth;
    const key = cacheKey;

    if (appCache.wrapped[key]) {
      wrappedError = null;
      loadingWrapped = false;
      return;
    }
    untrack(() => {
      runGenerateWrapped(period, year, quarter, month, key);
    });
  });

  // Tracks pending fetches per cache key so rapid period switching (A->B->A)
  // reuses the in-flight request for A instead of firing a second, racing one.
  const inFlight = new Map<string, Promise<WrappedDataInfo>>();

  async function runGenerateWrapped(
    period: 'year' | 'quarter' | 'month',
    year: number,
    quarter: WrappedQuarter,
    month: WrappedMonth,
    key: string,
  ) {
    loadingWrapped = true;
    wrappedError = null;
    try {
      let request = inFlight.get(key);
      if (!request) {
        request = generateWrapped(period, year, quarter, month).finally(() => {
          inFlight.delete(key);
        });
        inFlight.set(key, request);
      }
      const data = await request;
      appCache.wrapped[key] = data;
    } catch (e) {
      wrappedError = e instanceof Error ? e.message : String(e);
    } finally {
      // Only clear the spinner if this resolution is for the period still selected.
      if (key === cacheKey) loadingWrapped = false;
    }
  }

  let currentWrappedData = $derived(appCache.wrapped[cacheKey] || null);

  function getMonthName(m: string): string {
    const monthIndex = parseInt(m.replace('M', ''), 10);
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return months[monthIndex - 1] || m;
  }
</script>

<PageHeader
  title="periodic reviews"
  subtitle="Spotify Wrapped style summaries for custom time ranges."
>
  {#snippet actions(isShrunk)}
    <div
      class="nav-selector hidden lg:flex transition-all duration-300"
      class:text-xs={isShrunk}
      class:text-sm={!isShrunk}
    >
      {#each [['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']] as [period, label]}
        <button
          class="nav-selector-item"
          class:active={wrappedPeriod === period}
          onclick={() => {
            wrappedPeriod = period as 'year' | 'quarter' | 'month';
          }}
        >
          {label}
        </button>
      {/each}
    </div>
  {/snippet}
</PageHeader>

<!-- Mobile Sticky Controls -->
<div class="sticky-sub-header lg:hidden flex flex-col gap-3">
  <div class="nav-selector w-full justify-between gap-1">
    {#each [['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']] as [period, label]}
      <button
        class="nav-selector-item flex-1 text-center justify-center py-1 text-xs"
        class:active={wrappedPeriod === period}
        onclick={() => {
          wrappedPeriod = period as 'year' | 'quarter' | 'month';
        }}
      >
        {label}
      </button>
    {/each}
  </div>

  <div class="flex flex-wrap gap-4 items-center justify-start px-1 text-xs">
    <!-- Always show Year Selector -->
    <div class="flex items-center gap-2">
      <span class="text-caps text-[10px] text-theme-muted uppercase tracking-wider">Year</span>
      <SelectDropdown bind:value={wrappedYear} options={yearOptions} />
    </div>

    {#if wrappedPeriod === 'quarter'}
      <div class="flex items-center gap-2">
        <span class="text-caps text-[10px] text-theme-muted uppercase tracking-wider">Quarter</span>
        <SelectDropdown bind:value={wrappedQuarter} options={quarterOptions} />
      </div>
    {/if}

    {#if wrappedPeriod === 'month'}
      <div class="flex items-center gap-2">
        <span class="text-caps text-[10px] text-theme-muted uppercase tracking-wider">Month</span>
        <SelectDropdown bind:value={wrappedMonth} options={monthOptions} />
      </div>
    {/if}
  </div>
</div>

<div class="flex flex-col gap-12 text-base-content">
  <!-- Review Controls (Borderless Selects - Desktop only) -->
  <div class="hidden lg:flex flex-wrap gap-8 items-center px-2">
    <!-- Always show Year Selector -->
    <div class="flex items-center gap-3">
      <span class="text-caps text-xs text-theme-muted">Year</span>
      <SelectDropdown bind:value={wrappedYear} options={yearOptions} />
    </div>

    {#if wrappedPeriod === 'quarter'}
      <div class="flex items-center gap-3">
        <span class="text-caps text-xs text-theme-muted">Quarter</span>
        <SelectDropdown bind:value={wrappedQuarter} options={quarterOptions} />
      </div>
    {/if}

    {#if wrappedPeriod === 'month'}
      <div class="flex items-center gap-3">
        <span class="text-caps text-xs text-theme-muted">Month</span>
        <SelectDropdown bind:value={wrappedMonth} options={monthOptions} />
      </div>
    {/if}
  </div>

  <!-- Wrapped Result Card -->
  {#if loadingWrapped}
    <div class="flex flex-col justify-center items-center gap-3 py-20">
      <span class="loading loading-spinner loading-md text-primary"></span>
      {#if appCache.isWakingUp}
        <span class="text-xs font-mono tracking-widest uppercase text-theme-muted animate-pulse">
          Waking up the server…
        </span>
      {/if}
    </div>
  {:else if wrappedError}
    <div
      class="max-w-4xl mx-auto w-full p-4 rounded-xl text-center text-sm font-mono text-theme-secondary bg-theme-neutral-soft border border-dashed border-theme-border-heavy"
    >
      {wrappedError}
    </div>
  {:else if currentWrappedData}
    <div
      class="max-w-4xl mx-auto w-full memory-surface relative overflow-visible flex flex-col justify-between min-h-115 p-10 md:p-12 shadow-2xl"
    >
      <!-- Glow backings for ambient warmth (desaturated) -->
      <div
        class="absolute -top-12 -left-12 w-40 h-40 rounded-full blur-3xl pointer-events-none transition-transform duration-700 bg-theme-accent-soft"
      ></div>
      <div
        class="absolute -bottom-12 -right-12 w-40 h-40 rounded-full blur-3xl pointer-events-none transition-transform duration-700 bg-theme-accent-soft/80"
      ></div>

      <div class="grow grid grid-cols-1 grid-rows-1 items-center">
        <!-- Reflective view transitions -->
        {#key currentStep}
          <div
            class="col-start-1 row-start-1 w-full"
            in:fade={{ duration: 380, delay: 100 }}
            out:fade={{ duration: 220 }}
          >
            {#if currentStep === 0}
              <!-- Slide 0: Cover & Summary Dashboard -->
              <div class="grid grid-cols-1 xl:grid-cols-5 gap-8 xl:gap-12 items-center py-4">
                <!-- Left side: Narrative & CTA -->
                <div class="xl:col-span-2 space-y-5 text-center xl:text-left">
                  <span class="text-xs font-mono tracking-widest text-theme-muted uppercase"
                    >01 / The Archeology</span
                  >
                  <h2 class="editorial-text-h1 lowercase text-4xl lg:text-5xl">
                    reviewing the <span class="italic text-theme-accent">resonance</span>
                  </h2>
                  <p class="text-base font-light leading-relaxed text-theme-secondary">
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
                <div
                  class="xl:col-span-3 border-t xl:border-t-0 xl:border-l border-theme-border-soft pt-6 xl:pt-0 xl:pl-12"
                >
                  <div class="grid grid-cols-2 gap-6">
                    <!-- Col 1: Total Plays -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Total Plays</span>
                      <div class="text-2xl font-light font-sans tracking-tight text-theme-text">
                        <AnimatedCounter value={currentWrappedData.total_plays} />
                      </div>
                    </div>

                    <!-- Col 2: Minutes Listened -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Minutes Listened</span>
                      <div class="text-2xl font-light font-sans tracking-tight text-theme-text">
                        <AnimatedCounter value={currentWrappedData.minutes_listened} />
                      </div>
                    </div>

                    <!-- Col 3: Top Creator -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Top Creator</span>
                      {#if currentWrappedData.top_artist}
                        <div class="text-lg font-light truncate text-theme-text" use:tooltip>
                          {currentWrappedData.top_artist.name}
                        </div>
                        <div class="text-sm font-mono text-theme-accent mt-0.5">
                          {currentWrappedData.top_artist.plays.toLocaleString()} plays
                        </div>
                      {:else}
                        <div class="text-sm opacity-40">No records</div>
                      {/if}
                    </div>

                    <!-- Col 4: Top Track -->
                    <div class="space-y-1">
                      <span class="text-caps text-xs text-theme-muted">Top Track</span>
                      {#if currentWrappedData.top_track}
                        <div class="text-lg font-light truncate text-theme-text" use:tooltip>
                          {currentWrappedData.top_track.title}
                        </div>
                        <div
                          class="text-sm font-light opacity-80 truncate text-theme-secondary"
                          use:tooltip
                        >
                          by {currentWrappedData.top_track.artist}
                        </div>
                      {:else}
                        <div class="text-sm opacity-40">No records</div>
                      {/if}
                    </div>

                    <!-- Peak Intensity -->
                    {#if currentWrappedData.peak_day}
                      <div class="col-span-2 pt-6 border-t border-theme-border-soft">
                        <span class="text-caps text-xs text-theme-muted">Peak Intensity</span>
                        <div class="flex justify-between items-baseline">
                          <div class="text-base font-light truncate text-theme-text" use:tooltip>
                            {new Date(
                              currentWrappedData.peak_day.date + 'T12:00:00',
                            ).toLocaleDateString(undefined, {
                              month: 'long',
                              day: 'numeric',
                              year: 'numeric',
                            })}
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
                <span class="text-xs font-mono tracking-widest text-theme-muted uppercase"
                  >02 / Duration & Echo</span
                >
                <div class="space-y-1">
                  <div class="text-display-large text-theme-accent">
                    <AnimatedCounter value={currentWrappedData.total_plays} />
                  </div>
                  <div class="text-caps text-xs text-theme-muted">Total Plays Logged</div>
                </div>
                <div
                  class="pt-4 text-base font-light max-w-lg mx-auto leading-relaxed text-theme-secondary"
                >
                  This volume amounts to approximately <span
                    class="font-normal font-mono text-base text-theme-accent"
                    >{currentWrappedData.minutes_listened.toLocaleString()}</span
                  > minutes of active listening, a steady acoustic flow in your memory space.
                </div>
              </div>
            {:else if currentStep === 2}
              <!-- Slide 2: Companions (Top Artist / Track) -->
              <div class="space-y-8 py-2">
                <div class="text-center">
                  <span class="text-xs font-mono tracking-widest text-theme-muted uppercase"
                    >03 / Key Companions</span
                  >
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-4">
                  <div
                    class="p-8 rounded-2xl border text-center space-y-3 border-theme-border-soft bg-theme-neutral-soft"
                  >
                    <div class="text-xs font-mono tracking-widest text-theme-muted uppercase">
                      Top Creator
                    </div>
                    {#if currentWrappedData.top_artist}
                      <div
                        class="text-xl md:text-2xl font-light truncate text-theme-text"
                        use:tooltip
                      >
                        {currentWrappedData.top_artist.name}
                      </div>
                      <div class="text-sm font-mono text-theme-accent mt-1">
                        {currentWrappedData.top_artist.plays.toLocaleString()} plays
                      </div>
                    {:else}
                      <div class="text-base opacity-40">No records</div>
                    {/if}
                  </div>

                  <div
                    class="p-8 rounded-2xl border text-center space-y-3 border-theme-border-soft bg-theme-neutral-soft"
                  >
                    <div class="text-xs font-mono tracking-widest text-theme-muted uppercase">
                      Top Track
                    </div>
                    {#if currentWrappedData.top_track}
                      <div
                        class="text-xl md:text-2xl font-light truncate text-theme-text"
                        use:tooltip
                      >
                        {currentWrappedData.top_track.title}
                      </div>
                      <div
                        class="text-sm font-light opacity-80 truncate text-theme-secondary"
                        use:tooltip
                      >
                        {currentWrappedData.top_track.artist}
                      </div>
                      <div class="text-sm font-mono text-theme-accent mt-1">
                        {currentWrappedData.top_track.plays.toLocaleString()} plays
                      </div>
                    {:else}
                      <div class="text-base opacity-40">No records</div>
                    {/if}
                  </div>
                </div>
              </div>
            {:else if currentStep === 3}
              <!-- Slide 3: Peak Day -->
              <div class="text-center space-y-6 py-4">
                <span class="text-xs font-mono tracking-widest text-theme-muted uppercase"
                  >04 / Peak Intensity</span
                >

                {#if currentWrappedData.peak_day}
                  <div class="space-y-2">
                    <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">
                      Peak listening day
                    </div>
                    <h3 class="text-4xl lg:text-5xl font-serif italic text-theme-text">
                      {new Date(currentWrappedData.peak_day.date + 'T12:00:00').toLocaleDateString(
                        undefined,
                        { month: 'long', day: 'numeric', year: 'numeric' },
                      )}
                    </h3>
                  </div>
                  <div class="text-2xl font-light text-theme-accent">
                    {currentWrappedData.peak_day.plays} plays
                    <span class="text-sm font-mono text-theme-muted">in 24 hours</span>
                  </div>
                  <p
                    class="text-base font-light max-w-lg mx-auto leading-relaxed text-theme-secondary"
                  >
                    A day of intense musical immersion, leaving a distinct marker in your temporal
                    archive.
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
        <button class="btn-nav-text" disabled={currentStep === 0} onclick={() => currentStep--}>
          &larr; Back
        </button>

        <div class="flex gap-2.5">
          {#each Array.from({ length: 4 }) as _, idx}
            <button
              class="w-2 h-2 rounded-full transition-all duration-300 cursor-pointer focus:outline-none border-none p-0"
              style="background-color: {currentStep === idx
                ? 'var(--accent)'
                : 'color-mix(in srgb, var(--text-primary) 20%, transparent)'};"
              onclick={() => (currentStep = idx)}
              aria-label="Go to slide {idx + 1}"
            ></button>
          {/each}
        </div>

        {#if currentStep < 3}
          <button class="btn-nav-text" style="color: var(--accent);" onclick={() => currentStep++}>
            Next &rarr;
          </button>
        {:else}
          <button
            class="btn-nav-text"
            style="color: var(--accent);"
            onclick={() => (currentStep = 0)}
          >
            Restart
          </button>
        {/if}
      </div>
    </div>
  {/if}
</div>
