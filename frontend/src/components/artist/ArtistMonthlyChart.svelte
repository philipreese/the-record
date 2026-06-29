<script lang="ts">
  let {
    trends,
  }: {
    trends: { month: string; count: number }[];
  } = $props();

  let logMax = $derived(Math.log(Math.max(...trends.map((t) => t.count), 1) + 1));
  let hoveredBar = $state<{ month: string; count: number } | null>(null);

  function fmtMonth(ym: string): string {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
  }
</script>

<div class="flex flex-col gap-4">
  <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Listening History</h2>
  <div class="memory-surface p-6!">
    <div class="flex items-end mb-3 h-8">
      {#if hoveredBar}
        <div class="flex flex-col gap-0.5">
          <span class="text-[11px] font-mono text-theme-text leading-none">
            {fmtMonth(hoveredBar.month)}
          </span>
          <span class="text-[11px] font-mono text-theme-accent leading-none">
            {hoveredBar.count.toLocaleString()} plays
          </span>
        </div>
      {:else}
        <div class="flex w-full justify-between items-end">
          <span class="text-[10px] font-mono text-theme-muted/60">
            {trends[0]?.month ?? ''}
          </span>
          <span class="text-[10px] font-mono text-theme-muted/60">
            {trends[trends.length - 1]?.month ?? ''}
          </span>
        </div>
      {/if}
    </div>
    <div class="flex items-end gap-0.5 h-28 w-full">
      {#each trends as trend}
        {@const logPct = (Math.log(trend.count + 1) / logMax) * 100}
        {@const isHovered = hoveredBar?.month === trend.month}
        {@const opacity = isHovered
          ? 1
          : trend.count > 0
            ? 0.18 + (Math.log(trend.count + 1) / logMax) * 0.82
            : 0.06}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="relative flex flex-col items-center justify-end"
          style="flex: 1; min-width: 2px; height: 100%;"
          onmouseenter={() => (hoveredBar = trend)}
          onmouseleave={() => (hoveredBar = null)}
        >
          <div
            class="w-full rounded-sm bg-theme-accent transition-all duration-150"
            style="height: {Math.max(
              logPct,
              trend.count > 0 ? 2 : 0,
            )}%; opacity: {opacity}; transform: scaleY({isHovered
              ? 1.15
              : 1}); transform-origin: bottom;"
          ></div>
        </div>
      {/each}
    </div>
  </div>
</div>
