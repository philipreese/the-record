<script lang="ts">
  import { onMount } from 'svelte';
  import Heatmap from '../components/Heatmap.svelte';
  import HourlyHeatClock from '../components/HourlyHeatClock.svelte';
  import StreakTracker from '../components/StreakTracker.svelte';
  import StatsGrid from '../components/dashboard/StatsGrid.svelte';
  import SyncControl from '../components/sync/SyncControl.svelte';
  
  import {
    fetchStats,
    fetchStreak,
    fetchHeatmap,
    fetchHourlyTrends,
    fetchMonthlyTrends,
    type StatsInfo,
    type StreakInfo
  } from '../services/api';

  let stats = $state<StatsInfo>({ total_listens: 0, unique_artists: 0, unique_tracks: 0, days_active: 0, avg_per_day: 0, top_source: 'None' });
  let streak = $state<StreakInfo>({ current_streak: 0, longest_streak: 0 });
  let heatmapData = $state<Record<string, number>>({});
  let hourlyTrends = $state<Record<string, number>>({});
  let monthlyTrends = $state<{ month: string; count: number }[]>([]);
  let heatmapYear = $state(new Date().getFullYear());
  let loadingStats = $state(true);

  onMount(() => {
    fetchDashboardData();
  });

  async function fetchDashboardData() {
    loadingStats = true;
    try {
      const [statsRes, streakRes, hourlyRes, monthlyRes] = await Promise.all([
        fetchStats(),
        fetchStreak(),
        fetchHourlyTrends(),
        fetchMonthlyTrends()
      ]);

      stats = statsRes;
      streak = streakRes;
      hourlyTrends = hourlyRes;
      monthlyTrends = monthlyRes;
    } catch (e) {
      console.error("Failed to fetch dashboard data:", e);
    } finally {
      loadingStats = false;
    }
  }

  // Handle heatmap refresh automatically when selected year changes (including mount)
  $effect(() => {
    const year = heatmapYear;
    fetchHeatmap(year)
      .then(data => { heatmapData = data; })
      .catch(err => console.error(err));
  });
</script>

<div class="flex flex-col gap-6">
  
  <!-- Header and Sync -->
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-base-200/40 border border-base-content/5 rounded-2xl p-6 backdrop-blur-md">
    <div>
      <h1 class="text-3xl font-extrabold tracking-tight text-base-content">Music History</h1>
      <p class="text-sm opacity-60 mt-1 text-base-content/80">Self-hosted scrobble archives and listening insight analytics.</p>
    </div>
    
    <!-- Sync Action -->
    <SyncControl onSyncComplete={fetchDashboardData} />
  </div>

  <!-- Stats Grid -->
  {#if loadingStats}
    <div class="flex justify-center items-center py-10">
      <span class="loading loading-spinner loading-md text-primary"></span>
    </div>
  {:else}
    <StatsGrid {stats} />
  {/if}

  <!-- Heatmap Contribution Board -->
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center px-2">
      <h2 class="text-xl font-bold tracking-tight text-base-content">Listening Activity</h2>
      <div class="join">
        <button class="join-item btn btn-xs btn-outline text-base-content" aria-label="Previous Year" onclick={() => heatmapYear--}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M11.78 5.22a.75.75 0 010 1.06L8.06 10l3.72 3.72a.75.75 0 11-1.06 1.06l-4.25-4.25a.75.75 0 010-1.06l4.25-4.25a.75.75 0 011.06 0z" clip-rule="evenodd" /></svg>
        </button>
        <span class="join-item btn btn-xs btn-active bg-base-300 font-bold px-4 text-base-content">{heatmapYear}</span>
        <button class="join-item btn btn-xs btn-outline text-base-content" aria-label="Next Year" onclick={() => heatmapYear++}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 011.06 0l4.25 4.25a.75.75 0 010 1.06l-4.25 4.25a.75.75 0 01-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 010-1.06z" clip-rule="evenodd" /></svg>
        </button>
      </div>
    </div>
    <Heatmap data={heatmapData} year={heatmapYear} />
  </div>

  <!-- Sub Grid for Hourly clock + Streaks -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <HourlyHeatClock hourlyData={hourlyTrends} />
    <StreakTracker streakData={streak} />
  </div>

</div>
