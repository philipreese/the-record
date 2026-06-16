<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { fade } from 'svelte/transition';
  import { inView } from '../utils/inView';
  import AnimatedCounter from '../components/dashboard/AnimatedCounter.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import NowPlaying from '../components/NowPlaying.svelte';
  import ScrollNavButton from '../components/layout/ScrollNavButton.svelte';
  import HeatmapSection from '../components/overview/HeatmapSection.svelte';
  import DiurnalSection from '../components/overview/DiurnalSection.svelte';
  import TelemetrySection from '../components/overview/TelemetrySection.svelte';
  import RecentScrobblesSection from '../components/overview/RecentScrobblesSection.svelte';
  import OnThisDaySection from '../components/overview/OnThisDaySection.svelte';
  import listeningJournalImg from '../assets/listening_journal.png';

  import {
    fetchStats,
    fetchStreak,
    fetchHeatmap,
    fetchHourlyTrends,
    fetchPunchcard,
    fetchMonthlyTrends,
    fetchRecentListens,
    fetchOnThisDay,
  } from '../services/api';

  import { appCache } from '../services/store.svelte';

  let {
    activeTab = $bindable(),
  }: { activeTab: 'dashboard' | 'charts' | 'wrapped' | 'settings' | 'recent' } = $props();

  let heatmapYear = $state(new Date().getFullYear());
  let loadingStats = $state(!appCache.statsLoaded);
  let scrollY = $state(0);

  let currentFocusZone = $state<string | null>(null);

  let currentTarget = $derived.by(() => {
    void scrollY;
    if (typeof document === 'undefined') return { id: 'insights-section', label: 'insights' };

    if (scrollY < 10) {
      return { id: 'insights-section', label: 'insights' };
    }

    const isAtBottom =
      scrollY > 50 &&
      window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 24;
    if (isAtBottom) {
      return { id: 'top', label: 'top' };
    }

    const sections = [
      { id: 'insights-section', label: 'insights' },
      { id: 'diurnal-patterns', label: 'patterns' },
      { id: 'telemetry-volumes', label: 'volumes' },
      { id: 'on-this-day', label: 'on this day' },
      { id: 'recent-scrobbles', label: 'recent' },
    ];

    for (const sec of sections) {
      const el = document.getElementById(sec.id);
      if (el) {
        const rect = el.getBoundingClientRect();
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
        const offsetPosition = elementPosition - 85;
        window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
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
      const [statsRes, streakRes, hourlyRes, punchcardRes, monthlyRes, onThisDayRes] = await Promise.all([
        fetchStats(),
        fetchStreak(),
        fetchHourlyTrends(),
        fetchPunchcard(),
        fetchMonthlyTrends(),
        fetchOnThisDay(),
      ]);

      appCache.stats = statsRes;
      appCache.streak = streakRes;
      appCache.hourlyTrends = hourlyRes;
      appCache.punchcardData = punchcardRes;
      appCache.monthlyTrends = monthlyRes;
      appCache.onThisDay = onThisDayRes;
      appCache.statsLoaded = true;

      if (appCache.recentListens.length === 0) {
        const recent = await fetchRecentListens(10);
        appCache.recentListens = recent;
        if (recent.length < 10) appCache.recentExhausted = true;
      }
    } catch (e) {
      console.error('Failed to fetch dashboard data:', e);
    } finally {
      loadingStats = false;
    }
  }

  $effect(() => {
    if (!appCache.isSyncing && !appCache.statsLoaded) {
      fetchDashboardData();
    }
  });

  const heatmapInFlight = new Map<number, Promise<Record<string, number>>>();

  async function loadHeatmap(year: number) {
    let request = heatmapInFlight.get(year);
    if (!request) {
      request = fetchHeatmap(year).finally(() => {
        heatmapInFlight.delete(year);
      });
      heatmapInFlight.set(year, request);
    }
    try {
      appCache.heatmap[year] = await request;
    } catch (err) {
      console.error(err);
    }
  }

  // Handle heatmap refresh automatically when selected year changes (including mount).
  // Reading the cache entry here keeps the effect reactive to invalidation: a sync clears
  // appCache.heatmap and this refetches the visible year.
  $effect(() => {
    const year = heatmapYear;
    if (appCache.heatmap[year]) return;
    untrack(() => loadHeatmap(year));
  });

  let currentStats = $derived(
    appCache.stats || {
      total_listens: 0,
      unique_artists: 0,
      unique_tracks: 0,
      days_active: 0,
      avg_per_day: 0,
      top_source: 'None',
    },
  );
  let currentStreak = $derived(appCache.streak || { current_streak: 0, longest_streak: 0 });
  let firstListenYear = $derived(appCache.stats?.first_year || new Date().getFullYear());
  let currentYear = $derived(new Date().getFullYear());
</script>

<svelte:window bind:scrollY />

<div class="flex flex-col gap-12 text-base-content">
  <PageHeader
    title="music journal"
    subtitle="Self-hosted scrobble archives and listening insights."
  >
    {#snippet actions(isShrunk)}
      {#if !loadingStats && appCache.statsLoaded}
        <div class="flex items-center gap-4 transition-all duration-300">
          {#if !isShrunk}
            <span
              transition:fade={{ duration: 120 }}
              class="text-caps text-[10px] text-theme-muted uppercase tracking-widest hidden md:inline"
              >Archived Volume</span
            >
          {/if}
          <div class="flex items-baseline gap-1.5">
            <span
              class="font-light font-sans tracking-tighter text-theme-accent transition-all duration-(--t-responsive) var(--ease-fluid)"
              class:text-2xl={isShrunk}
              class:text-4xl={!isShrunk}
              class:lg:text-3xl={isShrunk}
              class:lg:text-5xl={!isShrunk}
            >
              <AnimatedCounter value={currentStats.total_listens} />
            </span>
            <span class="text-xs font-serif italic text-theme-secondary pr-2">plays</span>
          </div>
        </div>
      {/if}
    {/snippet}
  </PageHeader>

  <!-- Hero Splash -->
  <div class="hero-splash-container min-h-[62vh] lg:min-h-[72vh] flex flex-col justify-between">
    <div class="relative grow flex items-center py-6 lg:py-10">
      <div
        class="absolute -right-8 -bottom-10 lg:right-12 lg:bottom-0 w-65 md:w-85 lg:w-100 aspect-square opacity-[0.06] dark:opacity-[0.09] pointer-events-none select-none overflow-hidden rounded-full"
      >
        <img src={listeningJournalImg} alt="" class="w-full h-full object-cover" />
      </div>

      {#if !loadingStats && appCache.statsLoaded}
        <div class="max-w-3xl relative z-20">
          <p
            class="text-2xl md:text-3xl xl:text-4xl font-serif font-light leading-relaxed italic text-theme-secondary"
          >
            A period of active musical recollection. You have integrated music into &nbsp;<span
              class="font-sans font-normal text-theme-accent">{currentStats.days_active} days</span
            >&nbsp; of your journey, averaging &nbsp;<span
              class="font-sans font-normal text-theme-accent"
              >{currentStats.avg_per_day} tracks</span
            >&nbsp; daily. Your primary sonic gateway is &nbsp;<span
              class="font-sans font-normal capitalize text-theme-accent"
              >{currentStats.top_source.replace('_', ' ')}</span
            >,&nbsp; sustaining a continuous streak of &nbsp;<span
              class="font-sans font-normal text-theme-accent"
              >{currentStreak.current_streak} days</span
            >&nbsp; of conscious listening.
          </p>
        </div>
      {/if}
    </div>

    <div
      class="absolute bottom-0 left-0 right-0 h-28 bg-linear-to-t from-(--bg-base) to-transparent pointer-events-none z-10"
    ></div>
  </div>

  <!-- Sections -->
  <div class="space-y-40 pt-60" id="insights-section">
    <HeatmapSection
      bind:heatmapYear
      {firstListenYear}
      {currentYear}
      heatmapData={appCache.heatmap[heatmapYear] || {}}
      monthlyTrends={appCache.monthlyTrends || []}
      dimmed={currentFocusZone !== null && currentFocusZone !== 'heatmap'}
      onfocusenter={() => (currentFocusZone = 'heatmap')}
      onfocusclear={() => (currentFocusZone = null)}
    />

    <DiurnalSection
      hourlyData={appCache.hourlyTrends || {}}
      punchcardData={appCache.punchcardData || {}}
      streakData={currentStreak}
      clockDimmed={currentFocusZone !== null && currentFocusZone !== 'clock'}
      streakDimmed={currentFocusZone !== null && currentFocusZone !== 'streak'}
      punchcardDimmed={currentFocusZone !== null && currentFocusZone !== 'punchcard'}
      onClockFocusEnter={() => (currentFocusZone = 'clock')}
      onClockFocusClear={() => (currentFocusZone = null)}
      onStreakFocusEnter={() => (currentFocusZone = 'streak')}
      onStreakFocusClear={() => (currentFocusZone = null)}
      onPunchcardFocusEnter={() => (currentFocusZone = 'punchcard')}
      onPunchcardFocusClear={() => (currentFocusZone = null)}
    />
  </div>

  <TelemetrySection
    loading={loadingStats}
    stats={currentStats}
    dimmed={currentFocusZone !== null && currentFocusZone !== 'telemetry'}
    onfocusenter={() => (currentFocusZone = 'telemetry')}
    onfocusclear={() => (currentFocusZone = null)}
  />

  {#if appCache.onThisDay.length > 0}
    <OnThisDaySection
      groups={appCache.onThisDay}
      dimmed={currentFocusZone !== null && currentFocusZone !== 'on-this-day'}
      onfocusenter={() => (currentFocusZone = 'on-this-day')}
      onfocusclear={() => (currentFocusZone = null)}
    />
  {/if}

  <div class="pt-30 grid grid-cols-1 xl:grid-cols-2 gap-16 lg:gap-20 items-start">
    <RecentScrobblesSection
      recentListens={appCache.recentListens}
      loading={loadingStats}
      dimmed={currentFocusZone !== null && currentFocusZone !== 'recent'}
      onfocusenter={() => (currentFocusZone = 'recent')}
      onfocusclear={() => (currentFocusZone = null)}
      onViewAll={() => (activeTab = 'recent')}
      sectionNumber={appCache.onThisDay.length > 0 ? '05' : '04'}
    />

    <!-- Now Playing / Last Played column -->
    <div
      use:inView={{ once: true }}
      class="space-y-8 transition-all duration-(--t-responsive) var(--ease-fluid) reveal-container"
      class:opacity-80={currentFocusZone !== null && currentFocusZone !== 'recent'}
      role="region"
      onmouseenter={() => (currentFocusZone = 'recent')}
      onmouseleave={() => (currentFocusZone = null)}
    >
      <NowPlaying />
    </div>
  </div>
</div>

<ScrollNavButton target={currentTarget} onclick={handleScrollClick} />
