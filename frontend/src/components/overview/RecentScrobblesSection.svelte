<script lang="ts">
  import { untrack } from 'svelte';
  import { inView } from '../../utils/inView';
  import {
    fetchTrackStats,
    fetchTrackStatsBatch,
    type ListenEntry,
    type TrackStatsInfo,
  } from '../../services/api';
  import ListenRow from '../dashboard/ListenRow.svelte';

  let {
    recentListens,
    loading,
    onViewAll,
    sectionNumber = '04',
  }: {
    recentListens: ListenEntry[];
    loading: boolean;
    onViewAll: () => void;
    sectionNumber?: string;
  } = $props();

  let expandedId = $state<number | null>(null);
  let trackStatsCache = $state<Record<string, TrackStatsInfo | null>>({});
  const inFlightKeys = new Set<string>();

  function trackKey(entry: ListenEntry): string {
    return `${entry.artist}||${entry.title}||${entry.album || ''}`;
  }

  async function fetchStatsForPage(page: ListenEntry[]) {
    const uniqueTracksToFetch: { artist: string; title: string; key: string }[] = [];

    for (const entry of page) {
      const statsKey = trackKey(entry);
      if (!(statsKey in trackStatsCache) && !inFlightKeys.has(statsKey)) {
        inFlightKeys.add(statsKey);
        uniqueTracksToFetch.push({
          artist: entry.artist,
          title: entry.title,
          key: statsKey,
        });
      }
    }

    if (uniqueTracksToFetch.length === 0) return;

    try {
      const batchRes = await fetchTrackStatsBatch(
        uniqueTracksToFetch.map((t) => ({ artist: t.artist, title: t.title })),
      );

      for (let i = 0; i < uniqueTracksToFetch.length; i++) {
        const statsKey = uniqueTracksToFetch[i].key;
        const resItem = batchRes[i];
        if (resItem) {
          trackStatsCache[statsKey] = {
            play_count: resItem.play_count,
            duration_secs: resItem.duration_secs ?? null,
          };
        } else {
          trackStatsCache[statsKey] = { play_count: 0, duration_secs: null };
        }
      }
    } catch (err) {
      console.error('Failed to fetch batch track stats:', err);
      for (const t of uniqueTracksToFetch) {
        inFlightKeys.delete(t.key);
      }
    }
  }

  $effect(() => {
    const listens = recentListens;
    if (listens.length > 0) {
      const missing = listens.filter((entry) => !(trackKey(entry) in trackStatsCache));
      if (missing.length > 0) {
        untrack(() => {
          fetchStatsForPage(missing);
        });
      }
    }
  });

  async function handleToggle(entry: ListenEntry): Promise<void> {
    if (expandedId === entry.id) {
      expandedId = null;
      return;
    }
    expandedId = entry.id;
    const key = trackKey(entry);
    if (!(key in trackStatsCache)) {
      try {
        trackStatsCache[key] = await fetchTrackStats(entry.artist, entry.title, entry.album);
      } catch {
        trackStatsCache[key] = null;
      }
    }
  }
</script>

<div
  use:inView={{ once: true }}
  class="space-y-8 reveal-container"
  role="region"
  id="recent-scrobbles"
>
  <div
    class="pb-2 border-b border-theme-border-soft reveal-label flex items-center justify-between"
  >
    <h2 class="editorial-text-h2">{sectionNumber} / Recent Scrobbles</h2>
    <button
      class="text-xs font-mono text-theme-muted hover:text-theme-accent transition-colors cursor-pointer focus:outline-none"
      onclick={onViewAll}
    >
      View full journal →
    </button>
  </div>
  <div class="reveal-content">
    {#if recentListens.length === 0 && loading}
      <div class="space-y-1">
        {#each { length: 5 } as _}
          <div class="flex items-center gap-3 py-2.5 px-2 animate-pulse">
            <div class="h-3 bg-base-300 rounded w-20 shrink-0"></div>
            <div class="flex-1 h-3 bg-base-300 rounded"></div>
          </div>
        {/each}
      </div>
    {:else if recentListens.length === 0}
      <p class="text-sm text-base-content/40 font-mono">No listens yet.</p>
    {:else}
      <div class="space-y-0">
        {#each recentListens.slice(0, 10) as entry (entry.id)}
          <ListenRow
            {entry}
            expanded={expandedId === entry.id}
            stats={trackStatsCache[trackKey(entry)]}
            onToggle={() => handleToggle(entry)}
          />
        {/each}
      </div>
    {/if}
  </div>
</div>
