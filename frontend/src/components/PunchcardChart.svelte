<script lang="ts">
  import { inView } from '../utils/inView';

  let { data = {} }: { data?: Record<string, number> } = $props();

  // DB returns 0=Sun..6=Sat; display Mon..Sun (row → DB dow)
  const DISPLAY_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const DOW_MAP = [1, 2, 3, 4, 5, 6, 0];

  const HOUR_LABELS: [number, string][] = [
    [0, '12am'],
    [6, '6am'],
    [12, '12pm'],
    [18, '6pm'],
  ];

  const CELL = 18;
  const GAP = 2;
  const STEP = CELL + GAP;
  const LEFT_MARGIN = 36;
  const TOP_MARGIN = 20;
  const W = LEFT_MARGIN + 24 * STEP + 4;
  const H = TOP_MARGIN + 7 * STEP + 4;

  let maxCount = $derived(Math.max(...Object.values(data), 1));

  function getCount(row: number, hour: number): number {
    const dow = DOW_MAP[row];
    return data[`${dow}_${String(hour).padStart(2, '0')}`] ?? 0;
  }

  function getOpacity(count: number): number {
    if (count === 0) return 0;
    return 0.15 + (count / maxCount) * 0.85;
  }

  function formatHour(h: number): string {
    if (h === 0) return '12am';
    if (h === 12) return '12pm';
    return h < 12 ? `${h}am` : `${h - 12}pm`;
  }

  let hoveredCell = $state<{ day: string; hour: string; count: number } | null>(null);
  let popoverX = $state(0);
  let popoverY = $state(0);
  let containerEl = $state<HTMLDivElement | null>(null);

  function showTooltip(row: number, hour: number, event: MouseEvent) {
    if (!containerEl) return;
    const rect = containerEl.getBoundingClientRect();
    popoverX = event.clientX - rect.left + 12;
    popoverY = event.clientY - rect.top - 60;
    hoveredCell = { day: DISPLAY_DAYS[row], hour: formatHour(hour), count: getCount(row, hour) };
  }

  function hideTooltip() {
    hoveredCell = null;
  }
</script>

<div
  bind:this={containerEl}
  use:inView={{ once: true }}
  class="w-full memory-surface punchcard-container p-6! relative overflow-visible"
>
  <div class="w-full overflow-x-auto scrollbar-thin">
    <svg
      viewBox="0 0 {W} {H}"
      class="w-full h-auto"
      style="min-width: {Math.round(W * 0.6)}px; color: var(--text-primary);"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- Hour labels -->
      {#each HOUR_LABELS as [h, label]}
        <text
          x={LEFT_MARGIN + h * STEP + CELL / 2}
          y="12"
          text-anchor="middle"
          font-size="9"
          font-family="var(--font-mono)"
          class="fill-current opacity-50">{label}</text
        >
      {/each}

      <!-- Day labels -->
      {#each DISPLAY_DAYS as day, row}
        <text
          x={LEFT_MARGIN - 4}
          y={TOP_MARGIN + row * STEP + CELL * 0.72}
          text-anchor="end"
          font-size="9"
          font-family="var(--font-mono)"
          class="fill-current opacity-50">{day}</text
        >
      {/each}

      <!-- Grid cells -->
      <g transform="translate({LEFT_MARGIN}, {TOP_MARGIN})">
        {#each DISPLAY_DAYS as _, row}
          {#each Array.from({ length: 24 }, (_, h) => h) as hour}
            {@const count = getCount(row, hour)}
            {@const opacity = getOpacity(count)}
            {@const idx = row * 24 + hour}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <rect
              x={hour * STEP}
              y={row * STEP}
              width={CELL}
              height={CELL}
              rx="2"
              class="punchcard-cell transition-all duration-(--t-immediate) var(--ease-fluid) cursor-pointer hover:brightness-110 hover:stroke-1"
              style="
                fill: {opacity > 0 ? 'var(--accent)' : 'var(--text-primary)'};
                --target-opacity: {opacity > 0 ? opacity : 0.07};
                animation-delay: {idx * 6}ms;
              "
              onmouseenter={(e) => showTooltip(row, hour, e)}
              onmousemove={(e) => showTooltip(row, hour, e)}
              onmouseleave={hideTooltip}
            />
          {/each}
        {/each}
      </g>
    </svg>
  </div>

  <!-- Legend -->
  <div
    class="flex items-center justify-end gap-2 mt-4 px-2 text-xs font-mono"
    style="color: var(--text-muted);"
  >
    <span>Quiet</span>
    <div class="w-3 h-3 rounded-sm" style="background-color: var(--text-primary); opacity: 0.07;"></div>
    <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 0.22;"></div>
    <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 0.50;"></div>
    <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 0.75;"></div>
    <div class="w-3 h-3 rounded-sm" style="background-color: var(--accent); opacity: 1.00;"></div>
    <span>Resonant</span>
  </div>

  <!-- Tooltip -->
  {#if hoveredCell}
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
        {hoveredCell.day} &bull; {hoveredCell.hour}
      </div>
      <div class="font-semibold mt-1">
        {hoveredCell.count} play{hoveredCell.count === 1 ? '' : 's'}
      </div>
    </div>
  {/if}
</div>
