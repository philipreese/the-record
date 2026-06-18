<script lang="ts">
  import { untrack } from 'svelte';
  import { inView } from '../../utils/inView';
  import {
    fetchTrackStats,
    fetchTrackStatsBatch,
    type OnThisDayGroup,
    type ListenEntry,
    type TrackStatsInfo,
  } from '../../services/api';
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
    const listens = groups.flatMap((g) => g.listens);
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
                stats={trackStatsCache[trackKey(entry)]}
                onToggle={() => handleToggle(entry)}
              />
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>
</div>
