<script lang="ts">
  import { untrack } from 'svelte';
  import { inView } from '../../utils/inView';
  import { fetchTrackStats, type ListenEntry } from '../../services/api';
  import { appCache } from '../../services/store.svelte';
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

  $effect(() => {
    const listens = recentListens;
    if (listens.length > 0) {
      untrack(() => {
        appCache.fetchTrackStatsForListens(listens);
      });
    }
  });

  async function handleToggle(entry: ListenEntry): Promise<void> {
    if (expandedId === entry.id) {
      expandedId = null;
      return;
    }
    expandedId = entry.id;
    const key = appCache.trackKey(entry);
    if (!(key in appCache.trackStats)) {
      try {
        appCache.trackStats[key] = await fetchTrackStats(entry.artist, entry.title, entry.album);
      } catch {
        appCache.trackStats[key] = null;
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
    <h2 class="editorial-text-h2">
      {(appCache.narrative['recent.section'] || '{number} / Recent Scrobbles').replace(
        '{number}',
        sectionNumber,
      )}
    </h2>
    <button
      class="text-xs font-mono text-theme-muted hover:text-theme-accent transition-colors cursor-pointer focus:outline-none"
      onclick={onViewAll}
    >
      {appCache.narrative['recent.view_all'] || 'View full journal &rarr;'}
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
      <p class="text-sm text-base-content/40 font-mono">
        {appCache.narrative['recent.empty'] || 'No listens yet.'}
      </p>
    {:else}
      <div class="space-y-0">
        {#each recentListens.slice(0, 10) as entry (entry.id)}
          <ListenRow
            {entry}
            expanded={expandedId === entry.id}
            stats={appCache.trackStats[appCache.trackKey(entry)]}
            onToggle={() => handleToggle(entry)}
          />
        {/each}
      </div>
    {/if}
  </div>
</div>
