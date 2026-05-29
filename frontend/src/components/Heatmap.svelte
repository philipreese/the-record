<script lang="ts">
  interface DayInfo {
    date: Date;
    dateStr: string;
    count: number;
    weight: number;
    isFuture: boolean;
  }

  let { data = {}, year = new Date().getFullYear() }: { data?: Record<string, number>, year?: number } = $props();

  // Color palettes for weights (0-4) based on DaisyUI theme variables or manual colors
  // Here we use css opacity of the primary/secondary theme color to match any theme perfectly!
  // Weight 0: opacity 10% of base-300 or border-content
  // Weight 1-4: opacity 30%, 50%, 75%, 100% of primary color

  let daysOfYear = $derived(getDaysOfYear(year));
  let weeks = $derived(chunkIntoWeeks(daysOfYear));

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

<div class="w-full memory-surface !p-4" style="min-width: 320px; max-width: 900px;">
    <svg viewBox="0 0 835 150" width="100%" preserveAspectRatio="xMidYMid meet" class="text-base-content">
      <!-- Month Labels (absolute font-size so text doesn't scale with viewBox) -->
      {#each monthHeaders as header}
        <text x={header.x} y="15" font-size="11" font-weight="500" class="fill-current opacity-70">
          {header.name}
        </text>
      {/each}

      <!-- Weekday Labels (absolute font-size so text doesn't scale with viewBox) -->
      <text x="5" y="38" font-size="11" font-weight="500" class="fill-current opacity-70">Mon</text>
      <text x="5" y="68" font-size="11" font-weight="500" class="fill-current opacity-70">Wed</text>
      <text x="5" y="98" font-size="11" font-weight="500" class="fill-current opacity-70">Fri</text>

      <!-- Heatmap Grid -->
      <g transform="translate(30, 20)">
        {#each weeks as week, wIndex}
          <g transform="translate({wIndex * 15}, 0)">
            {#each week as day, dIndex}
              {#if day}
                 <!-- Grid square with standard browser tooltip (works on SVGs!) -->
                 {#if day.isFuture}
                    <rect
                      y={dIndex * 15}
                      width="12"
                      height="12"
                      rx="2"
                      fill="none"
                      style="stroke: var(--color-base-content); stroke-opacity: 0.35; stroke-width: 1px;"
                      stroke-dasharray="1.5 1.5"
                    >
                      <title>Future Date: {formatDate(day.date)}</title>
                    </rect>
                 {:else}
                   <rect
                     y={dIndex * 15}
                     width="12"
                     height="12"
                     rx="2"
                     class="transition-all duration-300 hover:stroke-primary hover:stroke-2 cursor-pointer"
                     class:fill-base-300={day.weight === 0}
                     class:opacity-10={day.weight === 0}
                     class:fill-primary={day.weight > 0}
                     class:opacity-30={day.weight === 1}
                     class:opacity-55={day.weight === 2}
                     class:opacity-80={day.weight === 3}
                     class:opacity-100={day.weight === 4}
                   >
                     <title>{day.count} plays on {formatDate(day.date)}</title>
                   </rect>
                 {/if}
              {:else}
                <!-- Place holder for empty leading/trailing days -->
                <rect
                  y={dIndex * 15}
                  width="12"
                  height="12"
                  rx="2"
                  fill="transparent"
                />
              {/if}
            {/each}
          </g>
        {/each}
      </g>
    </svg>
    
    <!-- Legend -->
    <div class="flex items-center justify-end gap-2 mt-2 px-2 text-xs opacity-75">
      <span>Less</span>
      <div class="w-3 h-3 rounded bg-base-300 opacity-10"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-30"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-55"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-80"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-100"></div>
      <span>More</span>
    </div>
</div>
