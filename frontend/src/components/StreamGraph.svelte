<script lang="ts">
  import { untrack } from 'svelte';
  import { fetchTopArtistTrends, fetchArtistTrackTrends } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import { stringToColor } from '../services/theme.svelte';

  interface MonthTrend {
    month: string;
    count: number;
  }

  interface TrendSeries {
    artist?: string;
    track?: string;
    play_count: number;
    monthly_counts: MonthTrend[];
  }

  // Props definition
  let { year }: { year: number } = $props();

  let trends = $state<TrendSeries[]>([]);
  let loading = $state(false);
  let focusedArtist = $state<string | null>(null);

  let width = $state(800);
  const height = 300;
  const paddingLeft = 45;
  const paddingRight = 45;
  const paddingTop = 35;
  const paddingBottom = 45;

  let hoveredSeriesIndex = $state<number | null>(null);
  let hoveredMonthIndex = $state<number | null>(null);

  let tooltipX = $state(0);
  let tooltipY = $state(0);

  const monthNames = [
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
  const monthNamesFull = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  // Reactively fetch trends when year, focusedArtist, or cache invalidation changes
  $effect(() => {
    const currentYear = year;
    const artist = focusedArtist;
    void appCache.statsLoaded;

    if (appCache.isSyncing) return;

    untrack(() => {
      loading = true;
      if (artist) {
        fetchArtistTrackTrends(artist, currentYear, 5)
          .then((res) => {
            trends = res.trends;
          })
          .catch((err) => {
            console.error('Failed to fetch artist track trends:', err);
          })
          .finally(() => {
            loading = false;
          });
      } else {
        fetchTopArtistTrends(currentYear, 5)
          .then((res) => {
            trends = res.trends;
          })
          .catch((err) => {
            console.error('Failed to fetch top artist trends:', err);
          })
          .finally(() => {
            loading = false;
          });
      }
    });
  });

  // Reset focus when year changes
  $effect(() => {
    void year;
    untrack(() => {
      focusedArtist = null;
    });
  });

  // Normalize series data for rendering
  let normalizedSeries = $derived.by(() => {
    if (!trends || trends.length === 0) return [];
    return trends.map((item: TrendSeries) => {
      const name = item.artist || item.track || 'Unknown';
      const monthly_counts = item.monthly_counts.map((m) => m.count);
      return {
        name,
        play_count: item.play_count,
        monthly_counts,
        color: stringToColor(name),
      };
    });
  });

  // Dynamic Catmull-Rom Bezier tangents generator
  function getBezierPath(
    topPoints: { x: number; y: number }[],
    bottomPoints: { x: number; y: number }[],
  ) {
    if (topPoints.length === 0) return '';

    const calculateTangents = (points: { x: number; y: number }[]) => {
      const tangents = [];
      const len = points.length;
      for (let i = 0; i < len; i++) {
        if (i === 0) {
          tangents.push((points[1].y - points[0].y) / (points[1].x - points[0].x));
        } else if (i === len - 1) {
          tangents.push((points[i].y - points[i - 1].y) / (points[i].x - points[i - 1].x));
        } else {
          // Average slope, damped to prevent overshoot
          tangents.push(
            0.42 * ((points[i + 1].y - points[i - 1].y) / (points[i + 1].x - points[i - 1].x)),
          );
        }
      }
      return tangents;
    };

    const topTangents = calculateTangents(topPoints);
    const bottomTangents = calculateTangents(bottomPoints);

    let topPath = `M ${topPoints[0].x} ${topPoints[0].y}`;
    for (let i = 0; i < topPoints.length - 1; i++) {
      const p0 = topPoints[i];
      const p1 = topPoints[i + 1];
      const dx = (p1.x - p0.x) / 3;
      const cp1x = p0.x + dx;
      const cp1y = p0.y + dx * topTangents[i];
      const cp2x = p1.x - dx;
      const cp2y = p1.y - dx * topTangents[i + 1];
      topPath += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p1.x} ${p1.y}`;
    }

    let bottomPath = ` L ${bottomPoints[bottomPoints.length - 1].x} ${bottomPoints[bottomPoints.length - 1].y}`;
    for (let i = bottomPoints.length - 1; i > 0; i--) {
      const p0 = bottomPoints[i];
      const p1 = bottomPoints[i - 1];
      const dx = (p0.x - p1.x) / 3;
      const cp1x = p0.x - dx;
      const cp1y = p0.y - dx * bottomTangents[i];
      const cp2x = p1.x + dx;
      const cp2y = p1.y + dx * bottomTangents[i - 1];
      bottomPath += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p1.x} ${p1.y}`;
    }

    return topPath + bottomPath + ' Z';
  }

  // Calculate streamgraph coordinates and paths
  let chartData = $derived.by(() => {
    if (normalizedSeries.length === 0 || width <= 0) return [];

    const S = normalizedSeries.length;
    const N = 12;

    const monthlyTotals = Array(N).fill(0);
    for (let k = 0; k < N; k++) {
      for (let s = 0; s < S; s++) {
        monthlyTotals[k] += normalizedSeries[s].monthly_counts[k];
      }
    }

    const maxTotal = Math.max(...monthlyTotals, 1);
    const chartHeight = height - paddingTop - paddingBottom;
    const scale = (chartHeight * 0.82) / maxTotal;

    const stepX = (width - paddingLeft - paddingRight) / 11;

    // Centered silhouette baseline calculation
    const y0 = Array(N).fill(0);
    for (let k = 0; k < N; k++) {
      y0[k] = paddingTop + (chartHeight - monthlyTotals[k] * scale) / 2;
    }

    const seriesPoints = Array(S)
      .fill(null)
      .map(() => ({
        top: [] as { x: number; y: number }[],
        bottom: [] as { x: number; y: number }[],
      }));

    const currentBaseline = [...y0];

    for (let s = 0; s < S; s++) {
      const series = normalizedSeries[s];
      for (let k = 0; k < N; k++) {
        const x = paddingLeft + k * stepX;
        const count = series.monthly_counts[k];
        const bottomY = currentBaseline[k];
        const topY = bottomY + count * scale;

        seriesPoints[s].bottom.push({ x, y: bottomY });
        seriesPoints[s].top.push({ x, y: topY });

        currentBaseline[k] = topY;
      }
    }

    return normalizedSeries.map((series, s) => {
      const pts = seriesPoints[s];
      const pathD = getBezierPath(pts.top, pts.bottom);
      return {
        ...series,
        pathD,
        points: pts,
      };
    });
  });

  // Reactive tooltip content
  let tooltipContent = $derived.by(() => {
    if (hoveredSeriesIndex === null || hoveredMonthIndex === null || chartData.length === 0) {
      return null;
    }
    const series = chartData[hoveredSeriesIndex];
    if (!series) return null;
    const count = series.monthly_counts[hoveredMonthIndex];
    return {
      title: series.name,
      subtitle: `${monthNamesFull[hoveredMonthIndex]} ${year}`,
      count,
    };
  });

  function handleMouseMove(e: MouseEvent) {
    const target = e.currentTarget as SVGElement | null;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const chartWidth = rect.width - paddingLeft - paddingRight;
    const stepX = chartWidth / 11;
    const k = Math.min(11, Math.max(0, Math.round((mouseX - paddingLeft) / stepX)));
    hoveredMonthIndex = k;

    tooltipX = mouseX;
    tooltipY = mouseY;
  }

  function handleMouseLeave() {
    hoveredMonthIndex = null;
    hoveredSeriesIndex = null;
  }
</script>

<div
  bind:clientWidth={width}
  class="memory-surface p-6! relative overflow-visible flex flex-col justify-between h-96 select-none"
>
  <div class="flex justify-between items-center mb-2 z-10">
    <div class="flex flex-col gap-1">
      <span class="text-caps text-[10px] text-theme-muted tracking-widest uppercase">
        {#if focusedArtist}
          {focusedArtist} — top track trends
        {:else}
          top artist trends ({year})
        {/if}
      </span>
    </div>
    {#if focusedArtist}
      <button
        class="btn-nav-text flex items-center gap-1 text-[10px] tracking-widest uppercase font-mono"
        onclick={() => (focusedArtist = null)}
      >
        ← Back to Artists
      </button>
    {/if}
  </div>

  <div class="grow relative min-h-60 mt-2">
    {#if loading && trends.length === 0}
      <div
        class="absolute inset-0 flex items-center justify-center bg-base-100/10 backdrop-blur-xs rounded-xl z-20"
      >
        <span class="loading loading-spinner text-theme-accent"></span>
      </div>
    {/if}

    {#if !loading && trends.length === 0}
      <div
        class="absolute inset-0 flex items-center justify-center z-10 text-theme-muted font-mono text-xs"
      >
        No trend data available for {year}.
      </div>
    {:else}
      <!-- Interactive SVG Streamgraph -->
      <svg
        class="w-full h-full overflow-visible"
        viewBox="0 0 {width} {height}"
        preserveAspectRatio="none"
        onmousemove={handleMouseMove}
        onmouseleave={handleMouseLeave}
        role="img"
        aria-label="Artist listening trends streamgraph"
      >
        <!-- Dotted Month Grid Lines -->
        <g class="month-grid-lines pointer-events-none">
          {#each Array(12) as _, idx}
            {@const x = paddingLeft + idx * ((width - paddingLeft - paddingRight) / 11)}
            <line
              x1={x}
              y1={paddingTop - 10}
              x2={x}
              y2={height - paddingBottom + 10}
              stroke="var(--color-theme-border-soft)"
              stroke-dasharray="2 3"
              class="transition-opacity duration-150"
              opacity={hoveredMonthIndex === idx ? 0.75 : 0.2}
              stroke-width={hoveredMonthIndex === idx ? 1.5 : 1}
            />
          {/each}
        </g>

        <!-- Area Streams -->
        <g class="streams">
          {#each chartData as series, idx}
            <path
              d={series.pathD}
              fill={series.color}
              stroke={series.color}
              stroke-width="0.75"
              class="transition-all duration-300 cursor-pointer focus:outline-none focus-visible:stroke-white focus-visible:stroke-[1.5px]"
              opacity={hoveredSeriesIndex === null
                ? 0.75
                : hoveredSeriesIndex === idx
                  ? 0.95
                  : 0.15}
              role="button"
              tabindex="0"
              aria-label={focusedArtist
                ? `Listening counts for ${series.name}`
                : `Zoom into listening trends for ${series.name}`}
              onmouseenter={() => (hoveredSeriesIndex = idx)}
              onclick={() => {
                if (!focusedArtist) {
                  focusedArtist = series.name;
                }
              }}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  if (!focusedArtist) {
                    focusedArtist = series.name;
                  }
                }
              }}
            />
          {/each}
        </g>

        <!-- X-Axis Month Labels -->
        <g class="month-labels font-mono text-[9px] fill-theme-muted uppercase select-none">
          {#each monthNames as month, idx}
            <text
              x={paddingLeft + idx * ((width - paddingLeft - paddingRight) / 11)}
              y={height - 15}
              text-anchor="middle"
              class="transition-opacity duration-150"
              opacity={hoveredMonthIndex === idx ? 1 : 0.5}
            >
              {month}
            </text>
          {/each}
        </g>
      </svg>
    {/if}

    <!-- Dynamic Micro-card Tooltip -->
    {#if tooltipContent}
      <div
        class="absolute z-30 pointer-events-none border px-3 py-2 rounded-lg text-xs font-mono shadow-xl select-none"
        style="
          left: {tooltipX}px;
          top: {tooltipY}px;
          background-color: var(--bg-base);
          border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);
          transform: translate(-50%, -125%);
        "
      >
        <div class="text-[9px] text-theme-muted uppercase tracking-widest mb-0.5">
          {tooltipContent.subtitle}
        </div>
        <div class="font-sans font-medium text-theme-text text-xs mb-0.5 truncate max-w-44">
          {tooltipContent.title}
        </div>
        <div class="text-theme-accent font-semibold">
          {tooltipContent.count.toLocaleString()}
          <span class="text-theme-secondary font-normal text-[9px] italic">plays</span>
        </div>
      </div>
    {/if}
  </div>
</div>
