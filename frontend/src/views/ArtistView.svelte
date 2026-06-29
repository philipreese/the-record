<script lang="ts">
  import type { TimeRange, ListenEntry } from '../services/api';
  import { fetchListen, deleteTrackListens } from '../services/api';
  import { fetchArtistStatsGql, type ArtistStatsWithAlbums } from '../services/artist-graphql';
  import type { ArtistTopTrack } from '../services/api';
  import { router } from '../services/router.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import HourlyHeatClock from '../components/HourlyHeatClock.svelte';
  import MetadataCorrectionDrawer from '../components/dashboard/MetadataCorrectionDrawer.svelte';
  import TrackListensModal from '../components/dashboard/TrackListensModal.svelte';
  import ArtistStatsStrip from '../components/artist/ArtistStatsStrip.svelte';
  import ArtistMonthlyChart from '../components/artist/ArtistMonthlyChart.svelte';
  import ArtistTrackList from '../components/artist/ArtistTrackList.svelte';
  import ArtistAlbums from '../components/artist/ArtistAlbums.svelte';

  let artistName = $derived(router.route.type === 'artist' ? router.route.name : '');
  let timeRange = $derived<TimeRange>((router.params.get('range') as TimeRange) ?? 'all');

  let stats = $state<ArtistStatsWithAlbums | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  const rangeOptions: [TimeRange, string][] = [
    ['30', '30 Days'],
    ['90', '90 Days'],
    ['365', '1 Year'],
    ['all', 'All Time'],
  ];

  $effect(() => {
    const name = artistName;
    const range = timeRange;
    if (!name) return;

    loading = true;
    error = null;

    fetchArtistStatsGql(name, range)
      .then((data) => {
        stats = data;
      })
      .catch(() => {
        error = 'Failed to load artist stats. Please try again.';
      })
      .finally(() => {
        loading = false;
      });
  });

  // Track edit drawer state
  let editingEntry = $state<ListenEntry | null>(null);
  let editingTrackPlayCount = $state(0);
  let loadingEditEntry = $state(false);

  async function openTrackEdit(repId: number, playCount: number) {
    loadingEditEntry = true;
    try {
      editingEntry = await fetchListen(repId);
      editingTrackPlayCount = playCount;
    } catch {
      // ignore — button stays un-highlighted
    } finally {
      loadingEditEntry = false;
    }
  }

  async function onTrackEditSaved(_updated: ListenEntry) {
    editingEntry = null;
    // Soft refresh — no loading=true so the DOM stays mounted and scroll position is preserved
    if (artistName) {
      try {
        stats = await fetchArtistStatsGql(artistName, timeRange);
      } catch {
        // keep stale data
      }
    }
  }

  // Track listens modal state
  let listeningToTrack = $state<ArtistTopTrack | null>(null);

  async function refreshStats() {
    if (!artistName) return;
    try {
      stats = await fetchArtistStatsGql(artistName, timeRange);
    } catch {
      // keep stale data
    }
  }

  async function handleDeleteTrack(trackTitle: string): Promise<void> {
    await deleteTrackListens(artistName, trackTitle);
    await refreshStats();
  }
</script>

<PageHeader title={artistName}>
  {#snippet actions()}
    <button
      class="btn-nav-text text-sm font-mono tracking-widest uppercase shrink-0"
      onclick={() => router.navigate('/charts')}
    >
      &larr; Charts
    </button>
  {/snippet}
</PageHeader>

<div class="flex flex-col gap-10 mt-6 text-base-content">
  <!-- Range Selector -->
  <div class="nav-selector w-full md:w-auto justify-between md:justify-start gap-2 md:gap-8">
    {#each rangeOptions as [val, label]}
      <button
        class="nav-selector-item flex-1 md:flex-initial text-center md:text-left py-1 md:py-0 text-xs md:text-sm"
        class:active={timeRange === val}
        onclick={() =>
          router.navigate(`/artist/${encodeURIComponent(artistName)}?range=${val}`, true)}
      >
        {label}
      </button>
    {/each}
  </div>

  {#if loading}
    <div class="flex justify-center py-20">
      <span class="loading loading-spinner loading-md text-theme-accent"></span>
    </div>
  {:else if error}
    <p class="text-sm font-mono text-error text-center py-12">{error}</p>
  {:else if stats && stats.total_plays === 0}
    <p class="text-sm font-mono text-theme-muted text-center py-12">
      No listens found for <span class="text-theme-text">{artistName}</span> in this time range.
    </p>
  {:else if stats}
    <ArtistStatsStrip {stats} {timeRange} />

    {#if stats.monthly_trends.length > 0}
      <ArtistMonthlyChart trends={stats.monthly_trends} />
    {/if}

    <ArtistTrackList
      tracks={stats.top_tracks}
      totalTrackCount={stats.total_track_count}
      {loadingEditEntry}
      onView={(track) => (listeningToTrack = track)}
      onEdit={openTrackEdit}
      onDeleteTrack={handleDeleteTrack}
    />

    {#if stats.top_albums && stats.top_albums.length > 0}
      <ArtistAlbums
        albums={stats.top_albums}
        tracks={stats.top_tracks}
        {loadingEditEntry}
        onView={(track) => (listeningToTrack = track)}
        onEdit={openTrackEdit}
        onDeleteTrack={handleDeleteTrack}
      />
    {/if}

    <!-- Hourly Heat Clock -->
    <div class="flex flex-col gap-4">
      <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Listening by Hour</h2>
      <HourlyHeatClock hourlyData={stats.hourly} />
    </div>
  {/if}
</div>

{#if editingEntry}
  <MetadataCorrectionDrawer
    entry={editingEntry}
    forcedScope="track"
    trackPlayCount={editingTrackPlayCount}
    onClose={() => (editingEntry = null)}
    onSaved={onTrackEditSaved}
  />
{/if}

{#if listeningToTrack && artistName}
  <TrackListensModal
    track={listeningToTrack}
    {artistName}
    onClose={() => (listeningToTrack = null)}
    onChanged={refreshStats}
  />
{/if}
