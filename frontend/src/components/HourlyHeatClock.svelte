<script lang="ts">
  import { inView } from '../utils/inView';
  import { appCache } from '../services/store.svelte';

  let { hourlyData = {} }: { hourlyData?: Record<string, number> } = $props();

  // Determine max play count to scale opacities dynamically
  let maxCount = $derived(Math.max(...Object.values(hourlyData), 1));

  // Helper: Convert polar coordinates to Cartesian
  function polarToCartesian(
    centerX: number,
    centerY: number,
    radius: number,
    angleInDegrees: number,
  ) {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
    return {
      x: centerX + radius * Math.cos(angleInRadians),
      y: centerY + radius * Math.sin(angleInRadians),
    };
  }

  // Helper: Generate SVG Path for a donut segment
  function getSegmentPath(
    x: number,
    y: number,
    rInner: number,
    rOuter: number,
    startAngle: number,
    endAngle: number,
  ): string {
    const startOuter = polarToCartesian(x, y, rOuter, startAngle);
    const endOuter = polarToCartesian(x, y, rOuter, endAngle);
    const startInner = polarToCartesian(x, y, rInner, startAngle);
    const endInner = polarToCartesian(x, y, rInner, endAngle);

    const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

    return [
      `M ${startOuter.x} ${startOuter.y}`,
      `A ${rOuter} ${rOuter} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
      `L ${endInner.x} ${endInner.y}`,
      `A ${rInner} ${rInner} 0 ${largeArcFlag} 0 ${startInner.x} ${startInner.y}`,
      'Z',
    ].join(' ');
  }

  // Get opacity weight based on count
  function getOpacity(count: number): number {
    if (count === 0) return 0.05;
    return 0.15 + (count / maxCount) * 0.85;
  }

  // Structure of clock segments: 12 segments for AM (0-11) and 12 for PM (12-23)
  const segments = Array.from({ length: 12 }, (_, i) => {
    const hourAM = i === 0 ? '00' : String(i).padStart(2, '0');
    const hourPM = String(i + 12);

    const startAngle = i * 30 + 1;
    const endAngle = (i + 1) * 30 - 1;

    const amLabel = i === 0 ? '12 AM' : `${i} AM`;
    const pmLabel = i === 0 ? '12 PM' : `${i} PM`;

    return {
      amKey: hourAM,
      pmKey: hourPM,
      amLabel,
      pmLabel,
      startAngle,
      endAngle,
      hourNumber: i === 0 ? 12 : i,
    };
  });

  // Hovered state for center visual core
  let hoveredSegment = $state<{ label: string; count: number } | null>(null);

  // Calculate average plays per day for the hovered hour
  let daysActive = $derived(appCache.stats?.days_active || 1);
  let average = $derived(hoveredSegment ? hoveredSegment.count / daysActive : 0);
  let formattedAverage = $derived(
    average === 0 ? '0' : average < 0.1 ? average.toFixed(2) : average.toFixed(1),
  );
</script>

<div
  use:inView={{ once: true }}
  class="memory-surface heatclock-container flex flex-col items-center justify-center relative overflow-visible"
>
  <div class="relative w-[320px] h-80 flex items-center justify-center">
    <svg width="320" height="320" viewBox="0 0 240 240" style="color: var(--text-primary);">
      <!-- Outer circle boundary -->
      <circle
        cx="120"
        cy="120"
        r="105"
        fill="none"
        style="stroke: var(--text-primary); stroke-opacity: 0.06;"
        stroke-width="1"
      />
      <!-- Mid-divider between AM and PM -->
      <circle
        cx="120"
        cy="120"
        r="71"
        fill="none"
        style="stroke: var(--text-primary); stroke-opacity: 0.12;"
        stroke-dasharray="3 3"
      />
      <!-- Inner boundary -->
      <circle
        cx="120"
        cy="120"
        r="37"
        fill="none"
        style="stroke: var(--text-primary); stroke-opacity: 0.06;"
        stroke-width="1"
      />

      <!-- Hour text labels (12, 3, 6, 9) shifted outside the clock to prevent overlap -->
      <text
        x="120"
        y="10"
        text-anchor="middle"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-40">12</text
      >
      <text
        x="233"
        y="124"
        text-anchor="middle"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-40">3</text
      >
      <text
        x="120"
        y="235"
        text-anchor="middle"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-40">6</text
      >
      <text
        x="7"
        y="124"
        text-anchor="middle"
        font-size="10"
        font-family="var(--font-mono)"
        class="fill-current opacity-40">9</text
      >

      <g transform="translate(0, 0)">
        {#each segments as seg, idx}
          <!-- AM Segment (Inner Ring: rInner=40, rOuter=70) -->
          {@const amCount = hourlyData[seg.amKey] || 0}
          <path
            d={getSegmentPath(120, 120, 40, 70, seg.startAngle, seg.endAngle)}
            role="button"
            tabindex="0"
            class="clock-segment transition-all duration-(--t-immediate) var(--ease-fluid) hover:stroke-(--text-primary) hover:stroke-1 hover:brightness-110 cursor-pointer focus:outline-none focus:stroke-(--text-primary) focus:stroke-1"
            style="fill: var(--accent); --target-opacity: {getOpacity(
              amCount,
            )}; animation-delay: {idx * 40}ms;"
            aria-label="{seg.amLabel}: {amCount} play{amCount === 1 ? '' : 's'}"
            onmouseenter={() => (hoveredSegment = { label: seg.amLabel, count: amCount })}
            onmouseleave={() => (hoveredSegment = null)}
            onfocus={() => (hoveredSegment = { label: seg.amLabel, count: amCount })}
            onblur={() => (hoveredSegment = null)}
            onkeydown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') e.preventDefault();
            }}
          />

          <!-- PM Segment (Outer Ring: rInner=72, rOuter=102) -->
          {@const pmCount = hourlyData[seg.pmKey] || 0}
          <path
            d={getSegmentPath(120, 120, 72, 102, seg.startAngle, seg.endAngle)}
            role="button"
            tabindex="0"
            class="clock-segment transition-all duration-(--t-immediate) var(--ease-fluid) hover:stroke-(--text-primary) hover:stroke-1 hover:brightness-110 cursor-pointer focus:outline-none focus:stroke-(--text-primary) focus:stroke-1"
            style="fill: color-mix(in srgb, var(--accent) 60%, var(--text-primary) 40%); --target-opacity: {getOpacity(
              pmCount,
            )}; animation-delay: {(idx + 12) * 40}ms;"
            aria-label="{seg.pmLabel}: {pmCount} play{pmCount === 1 ? '' : 's'}"
            onmouseenter={() => (hoveredSegment = { label: seg.pmLabel, count: pmCount })}
            onmouseleave={() => (hoveredSegment = null)}
            onfocus={() => (hoveredSegment = { label: seg.pmLabel, count: pmCount })}
            onblur={() => (hoveredSegment = null)}
            onkeydown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') e.preventDefault();
            }}
          />
        {/each}
      </g>
    </svg>

    <!-- Center visual core - Displays hovered details or base instructions -->
    <div
      class="absolute w-26.5 h-26.5 rounded-full flex flex-col items-center justify-center text-center p-2 select-none border transition-all duration-(--t-responsive) var(--ease-fluid)"
      style="
        background-color: color-mix(in srgb, var(--bg-base) 96%, transparent);
        border-color: color-mix(in srgb, var(--text-primary) 8%, transparent);
      "
    >
      {#if hoveredSegment}
        <div class="text-xs font-mono uppercase text-theme-muted leading-none">
          {hoveredSegment.label}
        </div>
        <div class="text-[16px] font-light tracking-tight mt-1.5 text-theme-text leading-none">
          {hoveredSegment.count}
          <span class="text-[10px] font-mono uppercase tracking-normal text-theme-faint">plays</span
          >
        </div>
        <div class="text-[11px] font-mono text-theme-muted mt-1.5 leading-none">
          {formattedAverage} <span class="opacity-60">/ day</span>
        </div>
      {:else}
        <div class="text-xs font-mono uppercase tracking-wider text-theme-muted leading-none">
          Diurnal
        </div>
        <div class="text-[11px] font-light leading-normal text-theme-secondary mt-1.5">
          inner &bull; am<br />outer &bull; pm
        </div>
      {/if}
    </div>
  </div>

  <!-- Heat clock legend -->
  <div class="flex gap-6 mt-4 text-micro font-mono" style="color: var(--text-muted);">
    <div class="flex items-center gap-1.5">
      <div class="w-2.5 h-2.5 rounded-full" style="background-color: var(--accent);"></div>
      <span>AM (Morning)</span>
    </div>
    <div class="flex items-center gap-1.5">
      <div
        class="w-2.5 h-2.5 rounded-full"
        style="background-color: color-mix(in srgb, var(--accent) 60%, var(--text-primary) 40%);"
      ></div>
      <span>PM (Noon/Night)</span>
    </div>
  </div>
</div>
