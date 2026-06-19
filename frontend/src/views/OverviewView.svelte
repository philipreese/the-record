<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { fade } from 'svelte/transition';
  import { inView } from '../utils/inView';
  import AnimatedCounter from '../components/dashboard/AnimatedCounter.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import NarrativeText from '../components/layout/NarrativeText.svelte';
  import NowPlaying from '../components/NowPlaying.svelte';
  import ScrollNavButton from '../components/layout/ScrollNavButton.svelte';
  import HeatmapSection from '../components/overview/HeatmapSection.svelte';
  import DiurnalSection from '../components/overview/DiurnalSection.svelte';
  import TelemetrySection from '../components/overview/TelemetrySection.svelte';
  import RecentScrobblesSection from '../components/overview/RecentScrobblesSection.svelte';
  import OnThisDaySection from '../components/overview/OnThisDaySection.svelte';
  import StreakTracker from '../components/StreakTracker.svelte';
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

  let currentTarget = $derived.by(() => {
    void scrollY;
    if (typeof document === 'undefined')
      return {
        id: 'heatmap-section',
        label: appCache.narrative.plain['overview.nav.insights'] || 'insights',
      };

    if (scrollY < 10) {
      return {
        id: 'heatmap-section',
        label: appCache.narrative.plain['overview.nav.insights'] || 'insights',
      };
    }

    const isAtBottom =
      scrollY > 50 &&
      window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 24;
    if (isAtBottom) {
      return { id: 'top', label: 'top' };
    }

    const sections = [
      {
        id: 'heatmap-section',
        label: appCache.narrative.plain['overview.nav.insights'] || 'insights',
      },
      {
        id: 'diurnal-patterns',
        label: appCache.narrative.plain['overview.nav.patterns'] || 'patterns',
      },
      { id: 'streak-tracker', label: appCache.narrative.plain['overview.nav.streak'] || 'streak' },
      {
        id: 'on-this-day',
        label: appCache.narrative.plain['overview.nav.on_this_day'] || 'on this day',
      },
      {
        id: 'recent-scrobbles',
        label: appCache.narrative.plain['overview.nav.recent'] || 'recent',
      },
      {
        id: 'telemetry-volumes',
        label: appCache.narrative.plain['overview.nav.telemetry'] || 'telemetry',
      },
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

  let scrollAnimationId: number | null = null;

  function smoothScrollTo(elementId: string, offset = 85) {
    if (scrollAnimationId) cancelAnimationFrame(scrollAnimationId);

    const target = document.getElementById(elementId);
    if (!target) return;

    const start = window.scrollY;
    const startTime = performance.now();
    const duration = 400; // ms

    function easeInOutQuad(t: number) {
      return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }

    function step(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = easeInOutQuad(progress);

      // Re-evaluate target position on every frame to handle layout shifts dynamically
      const targetY = target!.getBoundingClientRect().top + window.scrollY - offset;
      const currentScroll = start + (targetY - start) * ease;

      window.scrollTo(0, currentScroll);

      if (progress < 1) {
        scrollAnimationId = requestAnimationFrame(step);
      } else {
        scrollAnimationId = null;
      }
    }

    scrollAnimationId = requestAnimationFrame(step);
  }

  function handleScrollClick() {
    if (currentTarget.id === 'top') {
      if (scrollAnimationId) cancelAnimationFrame(scrollAnimationId);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      smoothScrollTo(currentTarget.id, 85);
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
      const [statsRes, streakRes, hourlyRes, punchcardRes, monthlyRes, onThisDayRes] =
        await Promise.all([
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
  <div class="hero-splash-container flex flex-col justify-between">
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
            <NarrativeText
              text={appCache.narrative.rich['overview.hero'] || 'A continuous stream of sounds.'}
              accentClass="font-sans font-normal text-theme-accent"
            />
          </p>
        </div>
      {/if}
    </div>

    <div
      class="absolute bottom-0 left-0 right-0 h-28 bg-linear-to-t from-(--bg-base) to-transparent pointer-events-none z-10"
    ></div>
  </div>

  <HeatmapSection
    bind:heatmapYear
    {firstListenYear}
    {currentYear}
    heatmapData={appCache.heatmap[heatmapYear] || {}}
    monthlyTrends={appCache.monthlyTrends || []}
  />

  <DiurnalSection
    hourlyData={appCache.hourlyTrends || {}}
    punchcardData={appCache.punchcardData || {}}
  />

  <!-- 03 / Recollection Continuous — Streak -->
  <div
    use:inView={{ once: true }}
    class="mt-30 space-y-4 reveal-container"
    role="region"
    id="streak-tracker"
  >
    <div class="pb-2 border-b border-theme-border-soft reveal-label">
      <h2 class="editorial-text-h2">
        03 / {appCache.narrative.plain['overview.insight.streak_header'] ||
          'Recollection Continuous'}
      </h2>
    </div>
    <div class="reveal-content">
      <StreakTracker streakData={currentStreak} />
    </div>
  </div>

  {#if appCache.onThisDay.length > 0}
    <OnThisDaySection groups={appCache.onThisDay} />
  {/if}

  <div class="mt-30 grid grid-cols-1 xl:grid-cols-2 gap-16 lg:gap-20 items-start">
    <RecentScrobblesSection
      recentListens={appCache.recentListens}
      loading={loadingStats}
      onViewAll={() => (activeTab = 'recent')}
      sectionNumber={appCache.onThisDay.length > 0 ? '05' : '04'}
    />

    <!-- Now Playing / Last Played column -->
    <div use:inView={{ once: true }} class="space-y-8 reveal-container" role="region">
      <NowPlaying />
    </div>
  </div>

  <!-- Telemetry & Volumes — reference panel, collapsible -->
  <TelemetrySection
    loading={loadingStats}
    stats={currentStats}
    sectionNumber={appCache.onThisDay.length > 0 ? '06' : '05'}
  />
</div>

<ScrollNavButton target={currentTarget} onclick={handleScrollClick} />
