<script lang="ts">
  // Layout refresh trigger
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { inView } from '../utils/inView';
  import AnimatedCounter from '../components/dashboard/AnimatedCounter.svelte';
  import Heatmap from '../components/Heatmap.svelte';
  import MonthlyBarChart from '../components/MonthlyBarChart.svelte';
  import HourlyHeatClock from '../components/HourlyHeatClock.svelte';
  import StreakTracker from '../components/StreakTracker.svelte';
  import StatsGrid from '../components/dashboard/StatsGrid.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import listeningJournalImg from '../assets/listening_journal.png';
  
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
  let scrollY = $state(0);
  
  // State for progressive focus dimming
  let currentFocusZone = $state<string | null>(null);

  let currentTarget = $derived.by(() => {
    const y = scrollY; // register dependency on scrollY
    if (typeof document === 'undefined') return { id: 'insights-section', label: 'insights' };

    // If we are at the very top of the page, target the first section
    if (scrollY < 10) {
      return { id: 'insights-section', label: 'insights' };
    }

    // Check if we are at the bottom of the page (within 24px buffer) and have actually scrolled down
    const isAtBottom = scrollY > 50 && (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 24);
    if (isAtBottom) {
      return { id: 'top', label: 'top' };
    }

    const sections = [
      { id: 'insights-section', label: 'insights' },
      { id: 'diurnal-patterns', label: 'patterns' },
      { id: 'telemetry-volumes', label: 'volumes' }
    ];

    for (const sec of sections) {
      const el = document.getElementById(sec.id);
      if (el) {
        const rect = el.getBoundingClientRect();
        // If the top of this section is below the top margin of the viewport (with 120px threshold)
        if (rect.top > 120) {
          return sec;
        }
      }
    }
    return { id: 'top', label: 'top' };
  });

  function handleScrollClick() {
    if (currentTarget.id === 'top') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      const el = document.getElementById(currentTarget.id);
      if (el) {
        const elementPosition = el.getBoundingClientRect().top + window.scrollY;
        const offsetPosition = elementPosition - 85; // accounts for sticky header
        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });
      }
    }
  }
 
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
  let firstListenYear = $derived(appCache.stats?.first_year || new Date().getFullYear());
  let currentYear = $derived(new Date().getFullYear());

</script>

<svelte:window bind:scrollY />
 
<div class="flex flex-col gap-12 text-base-content">
  
  <!-- Sticky Header Section -->
  <PageHeader title="music journal" subtitle="Self-hosted scrobble archives and listening insights.">
    {#snippet actions(isShrunk)}
      {#if !loadingStats && appCache.statsLoaded}
        <div class="flex items-center gap-4 transition-all duration-300">
          {#if !isShrunk}
            <span transition:fade={{ duration: 120 }} class="text-caps text-[10px] text-theme-muted uppercase tracking-widest hidden md:inline">Archived Volume</span>
          {/if}
          <div class="flex items-baseline gap-1.5">
            <span 
              class="font-light font-sans tracking-tighter text-theme-accent transition-all duration-[var(--t-responsive)] var(--ease-fluid)"
              class:text-2xl={isShrunk}
              class:text-4xl={!isShrunk}
              class:lg:text-3xl={isShrunk}
              class:lg:text-5xl={!isShrunk}
            >
              <AnimatedCounter value={currentStats.total_listens} />
            </span>
            <span class="text-xs font-serif italic text-theme-secondary">plays</span>
          </div>
        </div>
      {/if}
    {/snippet}
  </PageHeader>

  <!-- Layer 1: High-Signal Emotional/Reflective Narrative Hero Splash -->
  <div class="hero-splash-container min-h-[62vh] lg:min-h-[72vh] flex flex-col justify-between">
    <!-- Middle Row: Narrative Text + Watermarked Artwork -->
    <div class="relative flex-grow flex items-center py-6 lg:py-10">
      
      <!-- Background artwork watermark -->
      <div class="absolute -right-8 -bottom-10 lg:right-12 lg:bottom-0 w-[260px] md:w-[340px] lg:w-[400px] aspect-square opacity-[0.06] dark:opacity-[0.09] pointer-events-none select-none overflow-hidden rounded-full">
        <img 
          src={listeningJournalImg} 
          alt="" 
          class="w-full h-full object-cover"
        />
      </div>

      <!-- Left side: Narrative paragraph -->
      {#if !loadingStats && appCache.statsLoaded}
        <div class="max-w-3xl relative z-20">
          <p class="text-2xl md:text-3xl xl:text-4xl font-serif font-light leading-relaxed italic text-theme-secondary">
            A period of active musical recollection. You have integrated music into &nbsp;<span class="font-sans font-normal text-theme-accent">{currentStats.days_active} days</span>&nbsp; of your journey, averaging &nbsp;<span class="font-sans font-normal text-theme-accent">{currentStats.avg_per_day} tracks</span>&nbsp; daily. Your primary sonic gateway is &nbsp;<span class="font-sans font-normal capitalize text-theme-accent">{currentStats.top_source.replace('_', ' ')}</span>,&nbsp; sustaining a continuous streak of &nbsp;<span class="font-sans font-normal text-theme-accent">{currentStreak.current_streak} days</span>&nbsp; of conscious listening.
          </p>
        </div>
      {/if}
    </div>

    <!-- Bottom dissolve gradient overlay -->
    <div class="absolute bottom-0 left-0 right-0 h-28 bg-gradient-to-t from-[var(--bg-base)] to-transparent pointer-events-none z-10"></div>
  </div>

  <!-- Layer 2: Behavioral Patterns -->
  <div class="space-y-40 pt-60" id="insights-section">
    
    <!-- 01 / Heatmap & Monthly Section -->
    <div 
      use:inView={{ once: true }}
      class="flex flex-col gap-6 transition-all duration-[var(--t-responsive)] var(--ease-fluid) reveal-container"
      class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'heatmap'}
      role="region"
      onmouseenter={() => currentFocusZone = 'heatmap'}
      onmouseleave={() => currentFocusZone = null}
    >
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 px-2 reveal-label pb-2 border-b border-theme-border-soft">
        <div>
          <h2 class="editorial-text-h2">01 / Temporal Archive & Trends</h2>
          <p class="text-[11px] text-theme-muted font-mono tracking-wide mt-1">Calendar activity grid and monthly play volume (selector affects both)</p>
        </div>
        
        <div class="flex items-center gap-4">
          <span class="text-[10px] font-mono uppercase tracking-widest text-theme-muted select-none">Select Year</span>
          <div class="flex items-center gap-4 bg-theme-neutral-soft px-3 py-1 rounded-lg border border-theme-border-soft">
            <button 
              class="btn-nav-text text-2xl! leading-none" 
              aria-label="Previous Year" 
              disabled={heatmapYear <= firstListenYear}
              onclick={() => heatmapYear--}
            >
              &larr;
            </button>
            <span class="text-lg font-mono tracking-wider font-light text-theme-text select-none">{heatmapYear}</span>
            <button 
              class="btn-nav-text text-2xl! leading-none" 
              aria-label="Next Year" 
              disabled={heatmapYear >= currentYear}
              onclick={() => heatmapYear++}
            >
              &rarr;
            </button>
          </div>
        </div>
      </div>
      
      <div class="reveal-content space-y-6">
        <Heatmap data={appCache.heatmap[heatmapYear] || {}} year={heatmapYear} />
        <MonthlyBarChart monthlyTrends={appCache.monthlyTrends} year={heatmapYear} />
      </div>
    </div>

    <!-- 02 / Clock & Streaks Sub Grid -->
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-16 lg:gap-20 pt-30 items-start" id="diurnal-patterns">
      
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
    class="pt-30 space-y-8 transition-all duration-[var(--t-responsive)] var(--ease-fluid) reveal-container" 
    class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'telemetry'}
    role="region"
    onmouseenter={() => currentFocusZone = 'telemetry'}
    onmouseleave={() => currentFocusZone = null}
    id="telemetry-volumes"
  >
    <div class="pb-2 border-b border-theme-border-soft reveal-label">
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

<div class="fixed bottom-12 left-1/2 -translate-x-1/2 lg:left-[calc(50%+128px)] z-40 flex justify-center">
  <button 
    onclick={handleScrollClick}
    class="group flex flex-col items-center gap-2 cursor-pointer focus:outline-none bg-base-200/60 hover:bg-base-200/90 backdrop-blur-md px-5 py-2 rounded-full border border-theme-border-soft shadow-xl transition-all"
    aria-label="Scroll Navigation"
  >
    <div class="flex items-center gap-2">
      {#key currentTarget.label}
        <span in:fade={{ duration: 150 }} class="font-mono text-theme-muted uppercase tracking-widest group-hover:text-theme-accent transition-colors select-none">
          {currentTarget.id === 'top' ? 'return to top' : `scroll to ${currentTarget.label}`}
        </span>
      {/key}
      
      {#if currentTarget.id === 'top'}
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="1.5" 
          class="w-4 h-4 text-theme-muted group-hover:text-theme-accent group-hover:-translate-y-0.5 transition-all duration-300"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
        </svg>
      {:else}
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="1.5" 
          class="w-4 h-4 text-theme-muted group-hover:text-theme-accent group-hover:translate-y-0.5 transition-all duration-300 animate-bounce"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      {/if}
    </div>
  </button>
</div>
