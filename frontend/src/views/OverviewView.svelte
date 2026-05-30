<script lang="ts">
  // Layout refresh trigger
  import { onMount } from 'svelte';
  import { inView } from '../utils/inView';
  import AnimatedCounter from '../components/dashboard/AnimatedCounter.svelte';
  import Heatmap from '../components/Heatmap.svelte';
  import HourlyHeatClock from '../components/HourlyHeatClock.svelte';
  import StreakTracker from '../components/StreakTracker.svelte';
  import StatsGrid from '../components/dashboard/StatsGrid.svelte';
  
  import {
    fetchStats,
    fetchStreak,
    fetchHeatmap,
    fetchHourlyTrends,
    fetchMonthlyTrends
  } from '../services/api';
  
  import { appCache } from '../services/store.svelte';
 
  let heatmapYear = $state(new Date().getFullYear());
  let loadingStats = $state(!appCache.statsLoaded);
  
  // State for progressive focus dimming
  let currentFocusZone = $state<string | null>(null);
 
  onMount(() => {
    fetchDashboardData();
  });
 
  async function fetchDashboardData() {
    if (!appCache.statsLoaded) {
      loadingStats = true;
    }
    try {
      const [statsRes, streakRes, hourlyRes, monthlyRes] = await Promise.all([
        fetchStats(),
        fetchStreak(),
        fetchHourlyTrends(),
        fetchMonthlyTrends()
      ]);
 
      appCache.stats = statsRes;
      appCache.streak = streakRes;
      appCache.hourlyTrends = hourlyRes;
      appCache.monthlyTrends = monthlyRes;
      appCache.statsLoaded = true;
    } catch (e) {
      console.error("Failed to fetch dashboard data:", e);
    } finally {
      loadingStats = false;
    }
  }
 
  // Automatically refresh stats when background sync finishes and invalidates the cache
  $effect(() => {
    if (!appCache.isSyncing && !appCache.statsLoaded) {
      fetchDashboardData();
    }
  });

  // Handle heatmap refresh automatically when selected year changes (including mount)
  $effect(() => {
    const year = heatmapYear;
    fetchHeatmap(year)
      .then(data => { appCache.heatmap[year] = data; })
      .catch(err => console.error(err));
  });
 
  let currentStats = $derived(appCache.stats || { total_listens: 0, unique_artists: 0, unique_tracks: 0, days_active: 0, avg_per_day: 0, top_source: 'None' });
  let currentStreak = $derived(appCache.streak || { current_streak: 0, longest_streak: 0 });
</script>
 
<div class="flex flex-col gap-12 text-base-content">
  
  <!-- Header / Hero Section -->
  <div class="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-8 pb-8 border-b border-theme-border-soft">
    <div>
      <h1 class="editorial-text-h1 lowercase italic">music journal</h1>
      <p class="text-caps mt-2">Self-hosted scrobble archives and listening insights.</p>
    </div>
    
    <!-- Hero Total Counter (Highly Prominent) -->
    {#if !loadingStats && appCache.statsLoaded}
      <div class="flex flex-col items-start lg:items-end gap-1 px-2">
        <span class="text-caps text-xs text-theme-muted">Archived Volume</span>
        <div class="flex items-baseline gap-2">
          <span class="text-5xl md:text-6xl font-light font-sans tracking-tighter text-theme-accent animate-pulse-slow">
            <AnimatedCounter value={currentStats.total_listens} />
          </span>
          <span class="text-lg font-serif italic text-theme-secondary">plays</span>
        </div>
      </div>
    {/if}
  </div>

  <!-- Layer 1: High-Signal Emotional/Reflective Narrative Summary -->
  {#if !loadingStats && appCache.statsLoaded}
    <div 
      use:inView={{ once: true }} 
      class="max-w-4xl px-2 reveal-container"
    >
      <p class="text-3xl md:text-4xl font-serif font-light leading-relaxed italic text-theme-secondary">
        A period of active musical recollection. You have integrated music into &nbsp;<span class="font-sans font-normal text-theme-accent">{currentStats.days_active} days</span>&nbsp; of your journey, averaging &nbsp;<span class="font-sans font-normal text-theme-accent">{currentStats.avg_per_day} tracks</span>&nbsp; daily. Your primary sonic gateway is &nbsp;<span class="font-sans font-normal capitalize text-theme-accent">{currentStats.top_source.replace('_', ' ')}</span>,&nbsp; sustaining a continuous streak of &nbsp;<span class="font-sans font-normal text-theme-accent">{currentStreak.current_streak} days</span>&nbsp; of conscious listening.
      </p>
    </div>
  {/if}

  <!-- Layer 2: Behavioral Patterns -->
  <div class="space-y-12">
    
    <!-- 01 / Heatmap Section -->
    <div 
      use:inView={{ once: true }}
      class="flex flex-col gap-4 transition-all duration-[var(--t-responsive)] var(--ease-fluid) reveal-container"
      class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'heatmap'}
      role="region"
      onmouseenter={() => currentFocusZone = 'heatmap'}
      onmouseleave={() => currentFocusZone = null}
    >
      <div class="flex justify-between items-center px-2 reveal-label">
        <h2 class="editorial-text-h2">01 / Temporal Archive</h2>
        
        <div class="join border border-theme-border-heavy">
          <button class="join-item btn btn-xs btn-ghost hover:bg-transparent" aria-label="Previous Year" onclick={() => heatmapYear--}>
            &larr;
          </button>
          <span class="join-item text-xs font-mono font-bold px-4 flex items-center">{heatmapYear}</span>
          <button class="join-item btn btn-xs btn-ghost hover:bg-transparent" aria-label="Next Year" onclick={() => heatmapYear++}>
            &rarr;
          </button>
        </div>
      </div>
      <div class="reveal-content">
        <Heatmap data={appCache.heatmap[heatmapYear] || {}} year={heatmapYear} />
      </div>
    </div>

    <!-- 02 / Clock & Streaks Sub Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-start">
      
      <!-- Hourly clock -->
      <div 
        use:inView={{ once: true }}
        class="space-y-4 transition-all duration-[var(--t-responsive)] var(--ease-fluid) reveal-container"
        class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'clock'}
        role="region"
        onmouseenter={() => currentFocusZone = 'clock'}
        onmouseleave={() => currentFocusZone = null}
      >
        <div class="pb-2 border-b border-theme-border-soft reveal-label">
          <h3 class="editorial-text-h2">02A / Diurnal Intensity</h3>
        </div>
        <div class="reveal-content">
          <HourlyHeatClock hourlyData={appCache.hourlyTrends} />
        </div>
      </div>

      <!-- Streak tracker -->
      <div 
        use:inView={{ once: true }}
        class="space-y-4 transition-all duration-[var(--t-responsive)] var(--ease-fluid) reveal-container"
        class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'streak'}
        role="region"
        onmouseenter={() => currentFocusZone = 'streak'}
        onmouseleave={() => currentFocusZone = null}
      >
        <div class="pb-2 border-b border-theme-border-soft reveal-label">
          <h3 class="editorial-text-h2">02B / Recollection Continuous</h3>
        </div>
        <div class="reveal-content">
          <StreakTracker streakData={currentStreak} />
        </div>
      </div>

    </div>

  </div>

  <!-- Layer 3: Telemetry & Raw Counts -->
  <div 
    use:inView={{ once: true }}
    class="pt-12 border-t border-theme-border-soft transition-all duration-[var(--t-responsive)] var(--ease-fluid) reveal-container" 
    class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'telemetry'}
    role="region"
    onmouseenter={() => currentFocusZone = 'telemetry'}
    onmouseleave={() => currentFocusZone = null}
  >
    <div class="mb-6 reveal-label">
      <h2 class="editorial-text-h2">03 / Telemetry & Volumes</h2>
    </div>
    <div class="reveal-content">
      {#if loadingStats}
        <div class="flex justify-center items-center py-10">
          <span class="loading loading-spinner loading-md text-primary"></span>
        </div>
      {:else}
        <StatsGrid stats={currentStats} />
      {/if}
    </div>
  </div>

</div>
