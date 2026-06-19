<script lang="ts">
  import type { MonthlyTrendInfo } from '../services/api';
  import WeeklyBreakdownOverlay from './WeeklyBreakdownOverlay.svelte';
  import { router } from '../services/router.svelte';

  // Svelte 5 props definition
  let { monthlyTrends = [], year }: { monthlyTrends: MonthlyTrendInfo[]; year: number } = $props();

  let selectedMonth = $derived(router.params.get('month') ?? null);

  // Compute 12 months of data for the selected year
  let monthsData = $derived.by(() => {
    const yearStr = year.toString();
    const months = Array.from({ length: 12 }, (_, i) => {
      const monthNum = String(i + 1).padStart(2, '0');
      const monthKey = `${yearStr}-${monthNum}`;
      const trend = monthlyTrends.find((t) => t.month === monthKey);

      return {
        key: monthKey,
        label: new Date(year, i).toLocaleDateString(undefined, { month: 'short' }),
        count: trend ? trend.count : 0,
      };
    });

    const maxCount = Math.max(...months.map((m) => m.count), 1);

    return months.map((m) => {
      const ratio = m.count / maxCount;
      return {
        ...m,
        percent: ratio * 100,
        // Opacity weights matching the calendar heatmap values (0.15 to 1.0)
        opacity: m.count > 0 ? 0.18 + ratio * 0.82 : 0.08,
      };
    });
  });
</script>

<!-- Using first-class memory-surface class with heatmap-matching padding !p-6 -->
<div
  class="memory-surface heatmap-container flex flex-col justify-between h-full min-h-55 p-4! relative overflow-visible"
>
  <div class="flex justify-between items-center mb-4">
    <span class="text-caps text-[10px] text-theme-muted tracking-widest uppercase"
      >Monthly Distribution</span
    >
  </div>

  <!-- Chart Area -->
  <div class="grow flex items-end gap-1.5 h-52 px-1 relative">
    {#each monthsData as month}
      <div
        class="grow h-full flex flex-col justify-end items-center group relative cursor-pointer"
        role="button"
        tabindex="0"
        aria-label="{month.label} {year}: {month.count} plays"
        onclick={() => {
          const p = new URLSearchParams(router.params);
          const alreadyOpen = p.has('month');
          p.set('month', month.key);
          router.navigate(`/dashboard?${p}`, alreadyOpen);
        }}
        onkeydown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            const p = new URLSearchParams(router.params);
            const alreadyOpen = p.has('month');
            p.set('month', month.key);
            router.navigate(`/dashboard?${p}`, alreadyOpen);
          }
        }}
      >
        <!-- Custom styled tooltip (matching heatmap hover states) -->
        <div
          class="absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center z-20 pointer-events-none"
        >
          <div
            class="border px-2.5 py-1 rounded text-[12px] font-mono text-theme-text shadow-xl whitespace-nowrap"
            style="
              background-color: var(--bg-base);
              border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);
            "
          >
            <span class="text-theme-accent font-semibold">{month.count.toLocaleString()}</span> plays
          </div>
          <div
            class="w-1.5 h-1.5 border-r border-b rotate-45 -mt-1"
            style="
              background-color: var(--bg-base);
              border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);
            "
          ></div>
        </div>

        <!-- The Bar (Flat Accent Solid Fill with Scaled Opacity) -->
        <div
          class="w-full rounded-t-sm transition-all duration-(--t-responsive) var(--ease-fluid) group-hover:brightness-110 cursor-pointer"
          style="
            height: {month.percent}%;
            background-color: var(--accent);
            opacity: {month.opacity};
          "
        ></div>

        <!-- Label (3-letter month in small mono typography) -->
        <span class="text-[10px] font-mono text-theme-muted mt-2 uppercase select-none">
          {month.label}
        </span>
      </div>
    {/each}
  </div>
</div>

<WeeklyBreakdownOverlay
  monthKey={selectedMonth}
  onclose={() => {
    const p = new URLSearchParams(router.params);
    p.delete('month');
    const qs = p.toString();
    router.navigate(`/dashboard${qs ? '?' + qs : ''}`, true);
  }}
/>
