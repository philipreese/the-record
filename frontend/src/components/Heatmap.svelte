<script lang="ts">
  interface DayInfo {
    date: Date;
    dateStr: string;
    count: number;
    weight: number;
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
    
    // Fill leading empty days of the first week
    const firstDayOfWeek = startDate.getDay(); // 0 = Sunday, 6 = Saturday
    for (let i = 0; i < firstDayOfWeek; i++) {
      days.push(null);
    }
    
    let currentDate = new Date(startDate);
    while (currentDate <= endDate) {
      const dateStr = currentDate.toISOString().split('T')[0];
      const count = data[dateStr] || 0;
      
      let weight = 0;
      if (count > 0 && count <= 2) weight = 1;
      else if (count > 2 && count <= 5) weight = 2;
      else if (count > 5 && count <= 10) weight = 3;
      else if (count > 10) weight = 4;
      
      days.push({
        date: new Date(currentDate),
        dateStr,
        count,
        weight
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

<div class="overflow-x-auto w-full p-4 bg-base-200/50 backdrop-blur-md rounded-2xl border border-base-content/10">
  <div class="min-w-[820px]">
    <svg width="835" height="150" class="mx-auto text-base-content">
      <!-- Month Labels -->
      {#each monthHeaders as header}
        <text x={header.x} y="15" class="text-[10px] font-medium fill-current opacity-70">
          {header.name}
        </text>
      {/each}

      <!-- Weekday Labels -->
      <text x="5" y="38" class="text-[10px] font-medium fill-current opacity-70">Mon</text>
      <text x="5" y="68" class="text-[10px] font-medium fill-current opacity-70">Wed</text>
      <text x="5" y="98" class="text-[10px] font-medium fill-current opacity-70">Fri</text>

      <!-- Heatmap Grid -->
      <g transform="translate(30, 20)">
        {#each weeks as week, wIndex}
          <g transform="translate({wIndex * 15}, 0)">
            {#each week as day, dIndex}
              {#if day}
                <!-- Grid square with tooltip -->
                <g class="tooltip tooltip-primary" data-tip="{day.count} plays on {formatDate(day.date)}">
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
                  />
                </g>
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
    <div class="flex items-center justify-end gap-2 mt-2 px-6 text-xs opacity-75">
      <span>Less</span>
      <div class="w-3 h-3 rounded bg-base-300 opacity-10"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-30"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-55"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-80"></div>
      <div class="w-3 h-3 rounded bg-primary opacity-100"></div>
      <span>More</span>
    </div>
  </div>
</div>

<style>
  /* Ensure SVG elements can trigger Tooltips */
  .tooltip {
    display: block;
  }
</style>
