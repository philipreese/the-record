<script lang="ts">
  let { hourlyData = {} }: { hourlyData?: Record<string, number> } = $props();

  // Determine max play count to scale opacities dynamically
  let maxCount = $derived(Math.max(...Object.values(hourlyData), 1));

  // Helper: Convert polar coordinates to Cartesian
  function polarToCartesian(centerX: number, centerY: number, radius: number, angleInDegrees: number) {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  }

  // Helper: Generate SVG Path for a donut segment
  function getSegmentPath(x: number, y: number, rInner: number, rOuter: number, startAngle: number, endAngle: number): string {
    const startOuter = polarToCartesian(x, y, rOuter, startAngle);
    const endOuter = polarToCartesian(x, y, rOuter, endAngle);
    const startInner = polarToCartesian(x, y, rInner, startAngle);
    const endInner = polarToCartesian(x, y, rInner, endAngle);
    
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    
    return [
      `M ${startOuter.x} ${startOuter.y}`,
      `A ${rOuter} ${rOuter} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
      `L ${endInner.x} ${endInner.y}`,
      `A ${rInner} ${rInner} 0 ${largeArcFlag} 0 ${startInner.x} ${startInner.y}`,
      "Z"
    ].join(" ");
  }

  // Get opacity weight based on count
  function getOpacity(count: number): number {
    if (count === 0) return 0.08;
    return 0.2 + (count / maxCount) * 0.8;
  }

  // Structure of clock segments: 12 segments for AM (0-11) and 12 for PM (12-23)
  const segments = Array.from({ length: 12 }, (_, i) => {
    // We want 12 o'clock to be at the top, which is index 0.
    // Index 0 represents 12 (AM/PM), index 1 represents 1 (AM/PM)
    const hourAM = i === 0 ? "00" : String(i).padStart(2, '0');
    const hourPM = String(i + 12);
    
    // Angles for the 12 clock ticks (each is 30 degrees)
    // Add a tiny 2-degree padding between sectors
    const startAngle = i * 30 + 1;
    const endAngle = (i + 1) * 30 - 1;
    
    const amLabel = i === 0 ? "12 AM" : `${i} AM`;
    const pmLabel = i === 0 ? "12 PM" : `${i} PM`;
    
    return {
      amKey: hourAM,
      pmKey: hourPM,
      amLabel,
      pmLabel,
      startAngle,
      endAngle,
      hourNumber: i === 0 ? 12 : i
    };
  });
</script>

<div class="memory-surface flex flex-col items-center justify-center">
  <h3 class="text-sm font-semibold mb-4 text-base-content opacity-80 uppercase tracking-wider text-center">
    Hourly Listening Density
  </h3>
  
  <div class="relative w-[240px] h-[240px] flex items-center justify-center">
    <svg width="240" height="240" viewBox="0 0 240 240" class="text-base-content">
      <!-- Outer circle boundary -->
      <circle cx="120" cy="120" r="105" fill="none" class="stroke-base-content/5" stroke-width="1" />
      <!-- Mid-divider between AM and PM -->
      <circle cx="120" cy="120" r="71" fill="none" class="stroke-base-content/10" stroke-dasharray="3 3" />
      <!-- Inner boundary -->
      <circle cx="120" cy="120" r="37" fill="none" class="stroke-base-content/5" stroke-width="1" />
      
      <!-- Hour text labels (12, 3, 6, 9) -->
      <text x="120" y="25" text-anchor="middle" class="text-xs font-bold fill-current opacity-60">12</text>
      <text x="215" y="124" text-anchor="middle" class="text-xs font-bold fill-current opacity-60">3</text>
      <text x="120" y="222" text-anchor="middle" class="text-xs font-bold fill-current opacity-60">6</text>
      <text x="25" y="124" text-anchor="middle" class="text-xs font-bold fill-current opacity-60">9</text>

      <g transform="translate(0, 0)">
        {#each segments as seg}
          <!-- AM Segment (Inner Ring: rInner=40, rOuter=70) -->
          {@const amCount = hourlyData[seg.amKey] || 0}
          <path
            d={getSegmentPath(120, 120, 40, 70, seg.startAngle, seg.endAngle)}
            class="fill-primary transition-all duration-300 hover:scale-103 hover:stroke-primary hover:stroke-1 cursor-pointer"
            class:opacity-10={amCount === 0}
            style="opacity: {getOpacity(amCount)};"
          >
            <title>{seg.amLabel}: {amCount} plays</title>
          </path>
          
          <!-- PM Segment (Outer Ring: rInner=72, rOuter=102) -->
          {@const pmCount = hourlyData[seg.pmKey] || 0}
          <path
            d={getSegmentPath(120, 120, 72, 102, seg.startAngle, seg.endAngle)}
            class="fill-secondary transition-all duration-300 hover:scale-103 hover:stroke-secondary hover:stroke-1 cursor-pointer"
            class:opacity-10={pmCount === 0}
            style="opacity: {getOpacity(pmCount)};"
          >
            <title>{seg.pmLabel}: {pmCount} plays</title>
          </path>
        {/each}
      </g>
    </svg>
    
    <!-- Center visual core -->
    <div class="absolute w-[70px] h-[70px] rounded-full bg-base-300 border border-base-content/10 shadow-inner flex flex-col items-center justify-center text-center p-1 select-none">
      <div class="text-xs font-bold uppercase opacity-50 tracking-wider">AM / PM</div>
      <div class="text-xs font-extrabold text-primary">Inner / Outer</div>
    </div>
  </div>
  
  <!-- Heat clock legend -->
  <div class="flex gap-4 mt-4 text-xs opacity-75">
    <div class="flex items-center gap-1.5">
      <div class="w-2.5 h-2.5 rounded-full bg-primary"></div>
      <span>AM (Morning)</span>
    </div>
    <div class="flex items-center gap-1.5">
      <div class="w-2.5 h-2.5 rounded-full bg-secondary"></div>
      <span>PM (Afternoon/Night)</span>
    </div>
  </div>
</div>
