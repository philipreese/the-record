<script lang="ts">
  import { inView } from '../../utils/inView';
  import { fetchTrackStats, type ListenEntry, type TrackStatsInfo } from '../../services/api';
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

  function trackKey(entry: ListenEntry): string {
    return `${entry.artist}||${entry.title}`;
  }

  async function handleToggle(entry: ListenEntry): Promise<void> {
    if (expandedId === entry.id) {
      expandedId = null;
      return;
    }
    expandedId = entry.id;
    const key = trackKey(entry);
    if (!(key in trackStatsCache)) {
      try {
        trackStatsCache[key] = await fetchTrackStats(entry.artist, entry.title);
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
      <div class="pt-2">
        <button
          class="text-xs font-mono text-theme-muted hover:text-theme-accent transition-colors cursor-pointer focus:outline-none"
          onclick={onViewAll}
        >
          View full journal →
        </button>
      </div>
    {/if}
  </div>
</div>
