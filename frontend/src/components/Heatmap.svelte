<script lang="ts">
  import { inView } from '../utils/inView';
  import DayDetailOverlay from './DayDetailOverlay.svelte';
  import { getLegendText } from '../utils/listens';
  import { appCache } from '../services/store.svelte';
  import { router } from '../services/router.svelte';

  interface DayInfo {
    date: Date;
    dateStr: string;
    count: number;
    weight: number;
    isFuture: boolean;
  }

  let {
    data = {},
    year = new Date().getFullYear(),
  }: { data?: Record<string, number>; year?: number } = $props();

  let daysOfYear = $derived(getDaysOfYear(year));
  let weeks = $derived(chunkIntoWeeks(daysOfYear));

  let selectedDate = $derived(router.params.get('date') ?? null);

  // Custom HTML Popover State
  let hoveredDay = $state<DayInfo | null>(null);
  let popoverX = $state(0);
  let popoverY = $state(0);
  let containerElement = $state<HTMLDivElement | null>(null);

  function showPopover(day: DayInfo, event: MouseEvent) {
    hoveredDay = day;
    updatePopoverPosition(event);
  }

  function showPopoverFromFocus(day: DayInfo, event: FocusEvent) {
    hoveredDay = day;
    if (!containerElement) return;
    const target = event.currentTarget as SVGRectElement;
    const cellRect = target.getBoundingClientRect();
    const containerRect = containerElement.getBoundingClientRect();
    popoverX = cellRect.left - containerRect.left + cellRect.width + 4;
    popoverY = cellRect.top - containerRect.top - 68;
  }

  function movePopover(event: MouseEvent) {
    updatePopoverPosition(event);
  }

  function hidePopover() {
    hoveredDay = null;
  }

  function updatePopoverPosition(event: MouseEvent) {
    if (!containerElement) return;
    const rect = containerElement.getBoundingClientRect();
    // Offset above the cursor
    popoverX = event.clientX - rect.left + 12;
    popoverY = event.clientY - rect.top - 68;
  }

  function getDaysOfYear(y: number): (DayInfo | null)[] {
    const days: (DayInfo | null)[] = [];
    const startDate = new Date(y, 0, 1);
    const endDate = new Date(y, 11, 31);

    const today = new Date();
    today.setHours(23, 59, 59, 999);

    // Compute max count for the active year first
    let maxVal = 1;
    const yearPrefix = `${y}-`;
    for (const [dateStr, count] of Object.entries(data)) {
      if (dateStr.startsWith(yearPrefix)) {
        if (count > maxVal) maxVal = count;
      }
    }

    // Fill leading empty days of the first week
    const firstDayOfWeek = startDate.getDay(); // 0 = Sunday, 6 = Saturday
    for (let i = 0; i < firstDayOfWeek; i++) {
      days.push(null);
    }

    let currentDate = new Date(startDate);
    while (currentDate <= endDate) {
      const dateStr = currentDate.toISOString().split('T')[0];
      const count = data[dateStr] || 0;
      const isFuture = currentDate > today;

      let weight = 0;
      if (!isFuture && count > 0) {
        const ratio = count / maxVal;
        if (ratio <= 0.25) weight = 1;
        else if (ratio <= 0.5) weight = 2;
        else if (ratio <= 0.75) weight = 3;
        else weight = 4;
      }

      days.push({
        date: new Date(currentDate),
        dateStr,
        count,
        weight,
        isFuture,
      });
      currentDate.setDate(currentDate.getDate() + 1);
    }

    // Fill trailing empty days of the last week
    while (days.length % 7 !== 0) {
      days.push(null);
    }

    return days;
  }

  function chunkIntoWeeks(days: (DayInfo | null)[]): (DayInfo | null)[][] {
    const result: (DayInfo | null)[][] = [];
    for (let i = 0; i < days.length; i += 7) {
      result.push(days.slice(i, i + 7));
    }
    return result;
  }

  const monthLabels = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  // Find which week column each month starts in
  let monthHeaders = $derived(getMonthHeaders(weeks));

  function getMonthHeaders(weeksList: (DayInfo | null)[][]) {
    const headers: { name: string; x: number }[] = [];
    let lastMonth = -1;

    weeksList.forEach((week, weekIndex) => {
      // Find the first non-null day in the week
      const firstDay = week.find((d): d is DayInfo => d !== null);
      if (firstDay) {
        const currentMonth = firstDay.date.getMonth();
        if (currentMonth !== lastMonth) {
          headers.push({
            name: monthLabels[currentMonth],
            x: weekIndex * 15 + 30,
          });
          lastMonth = currentMonth;
        }
      }
    });

    return headers;
  }

  let hoveredLegendText = $state<string | null>(null);

  let maxCountOfYear = $derived.by(() => {
    let maxVal = 1;
    const yearPrefix = `${year}-`;
    for (const [dateStr, count] of Object.entries(data)) {
      if (dateStr.startsWith(yearPrefix)) {
        if (count > maxVal) maxVal = count;
      }
    }
    return maxVal;
  });

  function showLegendTooltip(level: number, event: MouseEvent) {
    if (!containerElement) return;
    const rect = containerElement.getBoundingClientRect();
    popoverX = event.clientX - rect.left - 40;
    popoverY = event.clientY - rect.top - 45;
    hoveredLegendText = getLegendText(level, maxCountOfYear);
  }

  function hideLegendTooltip() {
    hoveredLegendText = null;
  }

  $effect(() => {
    const handleDocumentClick = () => {
      hoveredLegendText = null;
    };
    document.addEventListener('click', handleDocumentClick);
    return () => {
      document.removeEventListener('click', handleDocumentClick);
    };
  });

  function formatDate(d: Date | null | undefined): string {
    if (!d) return '';
    return d.toLocaleDateString(undefined, {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
</script>

<div
  bind:this={containerElement}
  use:inView={{ once: true }}
  class="w-full memory-surface heatmap-container p-6! relative overflow-visible"
  style="min-width: 320px; max-width: 100%;"
>
  <div class="w-full overflow-x-auto scrollbar-thin">
    <svg
      viewBox="0 0 835 150"
      class="min-w-195 w-full h-auto"
      preserveAspectRatio="xMidYMid meet"
      style="color: var(--text-primary);"
      aria-label="Listening activity heatmap for {year}"
    >
      <!-- Month Labels -->
      {#each monthHeaders as header}
        <text
          x={header.x}
          y="15"
          font-size="11"
          font-family="var(--font-mono)"
          class="fill-current opacity-60"
        >
          {header.name}
        </text>
      {/each}

      <!-- Weekday Labels -->
      <text
        x="5"
        y="44"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-50">Mon</text
      >
      <text
        x="5"
        y="74"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-50">Wed</text
      >
      <text
        x="5"
        y="104"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-50">Fri</text
      >

      <!-- Heatmap Grid -->
      <g transform="translate(30, 20)">
        {#each weeks as week, wIndex}
          <g transform="translate({wIndex * 15}, 0)">
            {#each week as day, dIndex}
              {#if day}
                {#if day.isFuture}
                  <rect
                    y={dIndex * 15}
                    width="12"
                    height="12"
                    rx="2.5"
                    fill="transparent"
                    class="heatmap-cell"
                    style="
                        stroke: var(--text-primary);
                        stroke-opacity: 0.15;
                        stroke-width: 1px;
                        animation-delay: {wIndex * 12}ms;
                      "
                    stroke-dasharray="1.5 1.5"
                    aria-label="{formatDate(day.date)} — unwritten moment"
                  />
                {:else}
                  <rect
                    y={dIndex * 15}
                    width="12"
                    height="12"
                    rx="2.5"
                    role="button"
                    tabindex="0"
                    class="heatmap-cell transition-all duration-(--t-immediate) var(--ease-fluid) hover:stroke-(--text-primary) hover:stroke-1 cursor-pointer focus:outline-none focus:stroke-(--text-primary) focus:stroke-1"
                    class:fill-base-300={day.weight === 0}
                    style="
                       fill: {day.weight > 0 ? 'var(--accent)' : ''};
                       --target-opacity: {day.weight === 0
                      ? '0.1'
                      : day.weight === 1
                        ? '0.22'
                        : day.weight === 2
                          ? '0.5'
                          : day.weight === 3
                            ? '0.75'
                            : '1.0'};
                       animation-delay: {wIndex * 12}ms;
                     "
                    aria-label="{formatDate(day.date)} — {day.count} play{day.count === 1
                      ? ''
                      : 's'}"
                    onmouseenter={(e) => showPopover(day, e)}
                    onmousemove={movePopover}
                    onmouseleave={hidePopover}
                    onfocus={(e) => showPopoverFromFocus(day, e)}
                    onblur={hidePopover}
                    onclick={() => {
                      const p = new URLSearchParams(router.params);
                      const alreadyOpen = p.has('date');
                      p.set('date', day.dateStr);
                      router.navigate(`/dashboard?${p}`, alreadyOpen);
                      hidePopover();
                    }}
                    onkeydown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        const p = new URLSearchParams(router.params);
                        const alreadyOpen = p.has('date');
                        p.set('date', day.dateStr);
                        router.navigate(`/dashboard?${p}`, alreadyOpen);
                        hidePopover();
                      }
                    }}
                  />
                {/if}
              {:else}
                <rect y={dIndex * 15} width="12" height="12" rx="2.5" fill="transparent" />
              {/if}
            {/each}
          </g>
        {/each}
      </g>
    </svg>
  </div>

  <!-- Legend -->
  <div
    class="flex items-center justify-end gap-2 mt-4 px-2 text-xs font-mono"
    style="color: var(--text-muted);"
  >
    <span>{appCache.narrative.plain['heatmap.legend_quiet'] || 'Quiet'}</span>
    <button
      type="button"
      class="w-3 h-3 rounded-sm bg-base-300 opacity-10 cursor-pointer block p-0 border-none outline-none focus:scale-110"
      onmouseenter={(e) => showLegendTooltip(0, e)}
      onmouseleave={hideLegendTooltip}
      onclick={(e) => {
        e.stopPropagation();
        showLegendTooltip(0, e);
      }}
      aria-label="0 plays legend"
    ></button>
    <button
      type="button"
      class="w-3 h-3 rounded-sm cursor-pointer block p-0 border-none outline-none focus:scale-110"
      style="background-color: var(--accent); opacity: 0.22;"
      onmouseenter={(e) => showLegendTooltip(1, e)}
      onmouseleave={hideLegendTooltip}
      onclick={(e) => {
        e.stopPropagation();
        showLegendTooltip(1, e);
      }}
      aria-label="Level 1 plays legend"
    ></button>
    <button
      type="button"
      class="w-3 h-3 rounded-sm cursor-pointer block p-0 border-none outline-none focus:scale-110"
      style="background-color: var(--accent); opacity: 0.50;"
      onmouseenter={(e) => showLegendTooltip(2, e)}
      onmouseleave={hideLegendTooltip}
      onclick={(e) => {
        e.stopPropagation();
        showLegendTooltip(2, e);
      }}
      aria-label="Level 2 plays legend"
    ></button>
    <button
      type="button"
      class="w-3 h-3 rounded-sm cursor-pointer block p-0 border-none outline-none focus:scale-110"
      style="background-color: var(--accent); opacity: 0.75;"
      onmouseenter={(e) => showLegendTooltip(3, e)}
      onmouseleave={hideLegendTooltip}
      onclick={(e) => {
        e.stopPropagation();
        showLegendTooltip(3, e);
      }}
      aria-label="Level 3 plays legend"
    ></button>
    <button
      type="button"
      class="w-3 h-3 rounded-sm cursor-pointer block p-0 border-none outline-none focus:scale-110"
      style="background-color: var(--accent); opacity: 1.00;"
      onmouseenter={(e) => showLegendTooltip(4, e)}
      onmouseleave={hideLegendTooltip}
      onclick={(e) => {
        e.stopPropagation();
        showLegendTooltip(4, e);
      }}
      aria-label="Level 4 plays legend"
    ></button>
    <span>{appCache.narrative.plain['heatmap.legend_resonant'] || 'Resonant'}</span>
  </div>

  <!-- Custom Floating HTML Popover -->
  {#if hoveredDay}
    <div
      class="absolute z-50 pointer-events-none p-3 rounded-lg text-xs leading-relaxed shadow-xl border border-theme-border-heavy backdrop-blur-md text-theme-text"
      style="
          left: {popoverX}px; 
          top: {popoverY}px;
          background-color: var(--bg-base);
          opacity: 0.96;
        "
    >
      <div class="font-mono text-micro uppercase tracking-wider opacity-60">
        {formatDate(hoveredDay.date)}
      </div>
      <div class="font-semibold mt-1">
        {hoveredDay.count} play{hoveredDay.count === 1 ? '' : 's'}
      </div>
      {#if hoveredDay.count > 0}
        <div class="text-micro opacity-75 mt-0.5" style="color: var(--text-secondary);">
          {#if hoveredDay.weight === 1}
            {appCache.narrative.plain['heatmap.tooltip.weight1'] || 'Quiet, observed resonance'}
          {:else if hoveredDay.weight === 2}
            {appCache.narrative.plain['heatmap.tooltip.weight2'] || 'Active connection'}
          {:else if hoveredDay.weight === 3}
            {appCache.narrative.plain['heatmap.tooltip.weight3'] || 'Deep musical immersion'}
          {:else}
            {appCache.narrative.plain['heatmap.tooltip.weight4'] || 'Intense emotional archaeology'}
          {/if}
        </div>
      {:else if hoveredDay.isFuture}
        <div class="text-micro opacity-50 mt-0.5" style="color: var(--text-muted);">
          {appCache.narrative.plain['heatmap.tooltip.unwritten'] || 'Unwritten moment'}
        </div>
      {:else}
        <div class="text-micro opacity-50 mt-0.5" style="color: var(--text-muted);">
          {appCache.narrative.plain['heatmap.tooltip.silence'] || 'Silence and space'}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Legend Popover -->
  {#if hoveredLegendText}
    <div
      class="absolute z-50 pointer-events-none p-2 rounded-lg text-xs font-mono leading-normal shadow-xl border border-theme-border-heavy backdrop-blur-md text-theme-text"
      style="
          left: {popoverX}px; 
          top: {popoverY}px;
          background-color: var(--bg-base);
          opacity: 0.96;
        "
    >
      {hoveredLegendText}
    </div>
  {/if}
</div>

<DayDetailOverlay
  date={selectedDate}
  onclose={() => {
    const p = new URLSearchParams(router.params);
    p.delete('date');
    const qs = p.toString();
    router.navigate(`/dashboard${qs ? '?' + qs : ''}`, true);
  }}
/>
