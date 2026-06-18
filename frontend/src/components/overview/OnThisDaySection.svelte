<script lang="ts">
  import { untrack } from 'svelte';
  import { inView } from '../../utils/inView';
  import { fetchTrackStats, type OnThisDayGroup, type ListenEntry } from '../../services/api';
  import { appCache } from '../../services/store.svelte';
  import ListenRow from '../dashboard/ListenRow.svelte';

  let {
    groups,
  }: {
    groups: OnThisDayGroup[];
  } = $props();

  const currentYear = new Date().getFullYear();
  const todayLabel = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric' });

  function yearsAgo(year: number): string {
    const n = currentYear - year;
    return n === 1 ? '1 year ago' : `${n} years ago`;
  }

  let expandedYears = $state<Set<number>>(new Set());

  function toggleYear(year: number) {
    const next = new Set(expandedYears);
    if (next.has(year)) {
      next.delete(year);
    } else {
      next.add(year);
    }
    expandedYears = next;
  }

  let expandedId = $state<number | null>(null);

  $effect(() => {
    const listens = groups.flatMap((g) => g.listens);
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
  class="mt-30 space-y-8 reveal-container"
  role="region"
  id="on-this-day"
>
  <div class="pb-2 border-b border-theme-border-soft reveal-label">
    <h2 class="editorial-text-h2">04 / On This Day &mdash; {todayLabel}</h2>
  </div>

  <div class="reveal-content space-y-2">
    {#each groups as group (group.year)}
      {@const isExpanded = expandedYears.has(group.year)}
      <div class="rounded border border-theme-border-soft/60 overflow-hidden">
        <button
          class="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-base-200/40 transition-colors cursor-pointer"
          onclick={() => toggleYear(group.year)}
          aria-expanded={isExpanded}
        >
          <span class="text-xs font-mono text-theme-accent tabular-nums">{group.year}</span>
          <span class="text-xs font-mono text-theme-muted">&bull;</span>
          <span class="text-xs font-mono text-theme-muted">{yearsAgo(group.year)}</span>
          <span class="text-xs font-mono text-theme-faint ml-auto">
            {group.listens.length}
            {group.listens.length === 1 ? 'track' : 'tracks'}
          </span>
          <span
            class="text-xs text-theme-muted/60 transition-transform duration-200"
            class:rotate-90={isExpanded}
          >
            ›
          </span>
        </button>

        {#if isExpanded}
          <div class="border-t border-theme-border-soft/40">
            {#each group.listens as entry (entry.id)}
              <ListenRow
                {entry}
                showAbsoluteTime={true}
                showRelativeTime={false}
                expanded={expandedId === entry.id}
                stats={appCache.trackStats[appCache.trackKey(entry)]}
                onToggle={() => handleToggle(entry)}
              />
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>
</div>
