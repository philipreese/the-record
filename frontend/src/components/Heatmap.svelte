<script lang="ts">
  interface DayInfo {
    date: Date;
    dateStr: string;
    count: number;
    weight: number;
    isFuture: boolean;
  }

  let { data = {}, year = new Date().getFullYear() }: { data?: Record<string, number>, year?: number } = $props();

  let daysOfYear = $derived(getDaysOfYear(year));
  let weeks = $derived(chunkIntoWeeks(daysOfYear));

  // Custom HTML Popover State
  let hoveredDay = $state<DayInfo | null>(null);
  let popoverX = $state(0);
  let popoverY = $state(0);
  let containerElement = $state<HTMLDivElement | null>(null);

  function showPopover(day: DayInfo, event: MouseEvent) {
    hoveredDay = day;
    updatePopoverPosition(event);
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
      if (!isFuture) {
        if (count > 0 && count <= 2) weight = 1;
        else if (count > 2 && count <= 5) weight = 2;
        else if (count > 5 && count <= 10) weight = 3;
        else if (count > 10) weight = 4;
      }
      
      days.push({
        date: new Date(currentDate),
        dateStr,
        count,
        weight,
        isFuture
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

  const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  
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
            x: weekIndex * 15 + 30
          });
          lastMonth = currentMonth;
        }
      }
    });
    
    return headers;
  }

  function formatDate(d: Date | null | undefined): string {
    if (!d) return "";
    return d.toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
  }
</script>

<div bind:this={containerElement} class="w-full memory-surface !p-6 relative overflow-visible" style="min-width: 320px; max-width: 1050px;">
    <svg viewBox="0 0 835 150" width="100%" preserveAspectRatio="xMidYMid meet" style="color: var(--text-primary);">
      <!-- Month Labels -->
      {#each monthHeaders as header}
        <text x={header.x} y="15" font-size="11" font-family="var(--font-mono)" class="fill-current opacity-60">
          {header.name}
        </text>
      {/each}

      <!-- Weekday Labels -->
      <text x="5" y="38" font-size="10" font-family="var(--font-mono)" class="fill-current opacity-50">Mon</text>
      <text x="5" y="68" font-size="10" font-family="var(--font-mono)" class="fill-current opacity-50">Wed</text>
      <text x="5" y="98" font-size="10" font-family="var(--font-mono)" class="fill-current opacity-50">Fri</text>

      <!-- Heatmap Grid -->
      <g transform="translate(30, 20)">
        {#each weeks as week, wIndex}
          <g transform="translate({wIndex * 15}, 0)">
            {#each week as day, dIndex}
              {#if day}
                 {#if day.isFuture}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <!-- svelte-ignore a11y_mouse_events_have_key_events -->
                    <rect
                      y={dIndex * 15}
                      width="12"
                      height="12"
                      rx="2.5"
                      fill="none"
                      style="stroke: var(--text-primary); stroke-opacity: 0.15; stroke-width: 1px;"
                      stroke-dasharray="1.5 1.5"
                      onmouseenter={(e) => showPopover(day, e)}
                      onmousemove={movePopover}
                      onmouseleave={hidePopover}
                    />
                 {:else}
                   <!-- svelte-ignore a11y_no_static_element_interactions -->
                   <!-- svelte-ignore a11y_mouse_events_have_key_events -->
                   <rect
                     y={dIndex * 15}
                     width="12"
                     height="12"
                     rx="2.5"
                     class="transition-all duration-[var(--t-immediate)] var(--ease-fluid) hover:stroke-[color:var(--text-primary)] hover:stroke-1 cursor-pointer"
                     class:fill-base-300={day.weight === 0}
                     class:opacity-10={day.weight === 0}
                     style="
                       fill: {day.weight > 0 ? 'var(--accent)' : ''};
                       opacity: {day.weight === 0 ? '' : day.weight === 1 ? '0.22' : day.weight === 2 ? '0.5' : day.weight === 3 ? '0.75' : '1.0'};
                     "
                     onmouseenter={(e) => showPopover(day, e)}
                     onmousemove={movePopover}
                     onmouseleave={hidePopover}
                   />
                 {/if}
              {:else}
                <rect
                  y={dIndex * 15}
                  width="12"
                  height="12"
                  rx="2.5"
                  fill="transparent"
                />
              {/if}
            {/each}
          </g>
        {/each}
      </g>
    </svg>
    
    <!-- Legend -->
    <div class="flex items-center justify-end gap-2 mt-4 px-2 text-xs font-mono" style="color: var(--text-muted);">
      <span>Quiet</span>
      <div class="w-3 h-3 rounded-sm bg-base-300 opacity-10"></div>
      <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 0.22;"></div>
      <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 0.50;"></div>
      <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 0.75;"></div>
      <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 1.00;"></div>
      <span>Resonant</span>
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
              Quiet, observed resonance
            {:else if hoveredDay.weight === 2}
              Active connection
            {:else if hoveredDay.weight === 3}
              Deep musical immersion
            {:else}
              Intense emotional archaeology
            {/if}
          </div>
        {:else if hoveredDay.isFuture}
          <div class="text-micro opacity-50 mt-0.5" style="color: var(--text-muted);">
            Unwritten moment
          </div>
        {:else}
          <div class="text-micro opacity-50 mt-0.5" style="color: var(--text-muted);">
            Silence and space
          </div>
        {/if}
      </div>
    {/if}
</div>
