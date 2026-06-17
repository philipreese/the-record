<script lang="ts">
  import { fade } from 'svelte/transition';
  import type { WrappedDataInfo, WrappedQuarter, WrappedMonth } from '../../services/api';
  import AnimatedCounter from './AnimatedCounter.svelte';
  import { tooltip } from '../../utils/tooltip';

  let {
    data,
    period,
    year,
    quarter,
    month,
  }: {
    data: WrappedDataInfo;
    period: 'year' | 'quarter' | 'month';
    year: number;
    quarter: WrappedQuarter;
    month: WrappedMonth;
  } = $props();

  let currentStep = $state(0);

  // Reset step when the data changes (period switched)
  $effect(() => {
    void data;
    currentStep = 0;
  });

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

<div
  class="max-w-4xl mx-auto w-full memory-surface relative overflow-visible flex flex-col justify-between min-h-115 p-10 md:p-12 shadow-2xl"
>
  <!-- Glow backings -->
  <div
    class="absolute -top-12 -left-12 w-40 h-40 rounded-full blur-3xl pointer-events-none transition-transform duration-700 bg-theme-accent-soft"
    style="will-change: transform; transform: translateZ(0);"
  ></div>
  <div
    class="absolute -bottom-12 -right-12 w-40 h-40 rounded-full blur-3xl pointer-events-none transition-transform duration-700 bg-theme-accent-soft/80"
    style="will-change: transform; transform: translateZ(0);"
  ></div>

  <div class="grow grid grid-cols-1 grid-rows-1 items-center">
    {#key currentStep}
      <div
        class="col-start-1 row-start-1 w-full"
        in:fade={{ duration: 380, delay: 100 }}
        out:fade={{ duration: 220 }}
      >
        {#if currentStep === 0}
          <!-- Slide 0: Cover & Summary Dashboard -->
          <div class="grid grid-cols-1 xl:grid-cols-5 gap-8 xl:gap-12 items-center py-4">
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
                  {#if period === 'year'}
                    the year {year}.
                  {:else if period === 'quarter'}
                    {year} {quarter}.
                  {:else}
                    {getMonthName(month)} {year}.
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

            <div
              class="xl:col-span-3 border-t xl:border-t-0 xl:border-l border-theme-border-soft pt-6 xl:pt-0 xl:pl-12"
            >
              <div class="grid grid-cols-2 gap-6">
                <div class="space-y-1">
                  <span class="text-caps text-xs text-theme-muted">Total Plays</span>
                  <div class="text-2xl font-light font-sans tracking-tight text-theme-text">
                    <AnimatedCounter value={data.total_plays} />
                  </div>
                </div>

                <div class="space-y-1">
                  <span class="text-caps text-xs text-theme-muted">Minutes Listened</span>
                  <div class="text-2xl font-light font-sans tracking-tight text-theme-text">
                    <AnimatedCounter value={data.minutes_listened} />
                  </div>
                </div>

                <div class="space-y-1">
                  <span class="text-caps text-xs text-theme-muted">Top Creator</span>
                  {#if data.top_artist}
                    <div class="text-lg font-light truncate text-theme-text" use:tooltip>
                      {data.top_artist.name}
                    </div>
                    <div class="text-sm font-mono text-theme-accent mt-0.5">
                      {data.top_artist.plays.toLocaleString()} plays
                    </div>
                  {:else}
                    <div class="text-sm opacity-40">No records</div>
                  {/if}
                </div>

                <div class="space-y-1">
                  <span class="text-caps text-xs text-theme-muted">Top Track</span>
                  {#if data.top_track}
                    <div class="text-lg font-light truncate text-theme-text" use:tooltip>
                      {data.top_track.title}
                    </div>
                    <div
                      class="text-sm font-light opacity-80 truncate text-theme-secondary"
                      use:tooltip
                    >
                      by {data.top_track.artist}
                    </div>
                  {:else}
                    <div class="text-sm opacity-40">No records</div>
                  {/if}
                </div>

                {#if data.peak_day}
                  <div class="col-span-2 pt-6 border-t border-theme-border-soft">
                    <span class="text-caps text-xs text-theme-muted">Peak Intensity</span>
                    <div class="flex justify-between items-baseline">
                      <div class="text-base font-light truncate text-theme-text" use:tooltip>
                        {new Date(data.peak_day.date + 'T12:00:00').toLocaleDateString(undefined, {
                          month: 'long',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </div>
                      <div class="text-base font-light text-theme-accent">
                        {data.peak_day.plays} plays
                      </div>
                    </div>
                  </div>
                {/if}

                {#if data.on_repeat_peak}
                  <div class="col-span-2 pt-6 border-t border-theme-border-soft">
                    <span class="text-caps text-xs text-theme-muted">On Repeat</span>
                    <div class="flex justify-between items-baseline gap-2">
                      <div class="text-base font-light truncate text-theme-text" use:tooltip>
                        {data.on_repeat_peak.title}
                      </div>
                      <div class="text-base font-light text-theme-accent shrink-0">
                        {data.on_repeat_peak.count}× in a day
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
                <AnimatedCounter value={data.total_plays} />
              </div>
              <div class="text-caps text-xs text-theme-muted">Total Plays Logged</div>
            </div>
            <div
              class="pt-4 text-base font-light max-w-lg mx-auto leading-relaxed text-theme-secondary"
            >
              This volume amounts to approximately <span
                class="font-normal font-mono text-base text-theme-accent"
                >{data.minutes_listened.toLocaleString()}</span
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
                {#if data.top_artist}
                  <div class="text-xl md:text-2xl font-light truncate text-theme-text" use:tooltip>
                    {data.top_artist.name}
                  </div>
                  <div class="text-sm font-mono text-theme-accent mt-1">
                    {data.top_artist.plays.toLocaleString()} plays
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
                {#if data.top_track}
                  <div class="text-xl md:text-2xl font-light truncate text-theme-text" use:tooltip>
                    {data.top_track.title}
                  </div>
                  <div
                    class="text-sm font-light opacity-80 truncate text-theme-secondary"
                    use:tooltip
                  >
                    {data.top_track.artist}
                  </div>
                  <div class="text-sm font-mono text-theme-accent mt-1">
                    {data.top_track.plays.toLocaleString()} plays
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

            {#if data.peak_day}
              <div class="space-y-2">
                <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">
                  Peak listening day
                </div>
                <h3 class="text-4xl lg:text-5xl font-serif italic text-theme-text">
                  {new Date(data.peak_day.date + 'T12:00:00').toLocaleDateString(undefined, {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </h3>
              </div>
              <div class="text-2xl font-light text-theme-accent">
                {data.peak_day.plays} plays
                <span class="text-sm font-mono text-theme-muted">in 24 hours</span>
              </div>
              <p class="text-base font-light max-w-lg mx-auto leading-relaxed text-theme-secondary">
                A day of intense musical immersion, leaving a distinct marker in your temporal
                archive.
              </p>
            {:else}
              <p class="text-sm opacity-50">No peak anomalies identified.</p>
            {/if}
          </div>
        {:else if currentStep === 4}
          <!-- Slide 4: On Repeat -->
          <div class="text-center space-y-6 py-4">
            <span class="text-xs font-mono tracking-widest text-theme-muted uppercase"
              >05 / The Obsession</span
            >

            {#if data.on_repeat_peak}
              <div class="space-y-2">
                <div class="text-xs font-mono uppercase tracking-widest text-theme-muted">
                  Most replayed in a single day
                </div>
                <h3 class="text-3xl lg:text-4xl font-serif italic text-theme-text">
                  {data.on_repeat_peak.title}
                </h3>
                <div class="text-base font-light text-theme-secondary">
                  by {data.on_repeat_peak.artist}
                </div>
              </div>
              <div class="text-2xl font-light text-theme-accent">
                {data.on_repeat_peak.count} plays
                <span class="text-sm font-mono text-theme-muted">
                  on {new Date(data.on_repeat_peak.date + 'T12:00:00').toLocaleDateString(
                    undefined,
                    {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric',
                    },
                  )}
                </span>
              </div>
              <p class="text-base font-light max-w-lg mx-auto leading-relaxed text-theme-secondary">
                The single track you returned to most obsessively — a sonic loop that defined its
                day.
              </p>
            {:else}
              <p class="text-sm opacity-50">No repeat data available.</p>
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
      {#each Array.from({ length: 5 }) as _, idx}
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

    {#if currentStep < 4}
      <button class="btn-nav-text" style="color: var(--accent);" onclick={() => currentStep++}>
        Next &rarr;
      </button>
    {:else}
      <button class="btn-nav-text" style="color: var(--accent);" onclick={() => (currentStep = 0)}>
        Restart
      </button>
    {/if}
  </div>
</div>
