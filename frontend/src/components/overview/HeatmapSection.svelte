<script lang="ts">
  import { inView } from '../../utils/inView';
  import type { MonthlyTrendInfo } from '../../services/api';
  import Heatmap from '../Heatmap.svelte';
  import MonthlyBarChart from '../MonthlyBarChart.svelte';
  import { appCache } from '../../services/store.svelte';

  let {
    heatmapYear = $bindable(),
    firstListenYear,
    currentYear,
    heatmapData,
    monthlyTrends,
  }: {
    heatmapYear: number;
    firstListenYear: number;
    currentYear: number;
    heatmapData: Record<string, number>;
    monthlyTrends: MonthlyTrendInfo[];
  } = $props();
</script>

<div
  use:inView={{ once: true }}
  class="mt-30 flex flex-col gap-6 reveal-container"
  role="region"
  id="heatmap-section"
>
  <div
    class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 px-2 reveal-label pb-2 border-b border-theme-border-soft"
  >
    <div>
      <h2 class="editorial-text-h2">
        {appCache.narrative['heatmap.section_title'] || '01 / Temporal Archive & Trends'}
      </h2>
      <p class="text-[11px] text-theme-muted font-mono tracking-wide mt-1">
        {appCache.narrative['heatmap.section_desc'] ||
          'Calendar activity grid and monthly play volume (selector affects both)'}
      </p>
    </div>

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
          disabled={heatmapYear <= firstListenYear}
          onclick={() => heatmapYear--}
        >
          &larr;
        </button>
        <span class="text-lg font-mono tracking-wider font-light text-theme-text select-none"
          >{heatmapYear}</span
        >
        <button
          class="btn-nav-text text-2xl! leading-none"
          aria-label="Next Year"
          disabled={heatmapYear >= currentYear}
          onclick={() => heatmapYear++}
        >
          &rarr;
        </button>
      </div>
    </div>
  </div>

  <div class="reveal-content space-y-6">
    <Heatmap data={heatmapData} year={heatmapYear} />
    <MonthlyBarChart {monthlyTrends} year={heatmapYear} />
  </div>
</div>
