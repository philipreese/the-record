<script lang="ts">
  import { untrack } from 'svelte';
  import { inView } from '../../utils/inView';
  import {
    fetchTrackStats,
    fetchCoverArt,
    type OnThisDayGroup,
    type ArtistAnniversary,
    type ListenEntry,
  } from '../../services/api';
  import { appCache } from '../../services/store.svelte';
  import { patchWithCorrection } from '../../utils/listens';
  import { router } from '../../services/router.svelte';
  import ListenRow from '../dashboard/ListenRow.svelte';

  let {
    groups,
    anniversaries = [],
  }: {
    groups: OnThisDayGroup[];
    anniversaries?: ArtistAnniversary[];
  } = $props();

  const currentYear = new Date().getFullYear();
  const todayLabel = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric' });

  function yearsAgo(year: number): string {
    const n = currentYear - year;
    return n === 1 ? '1 year ago' : `${n} years ago`;
  }

  function formatFirstHeard(ts: number): string {
    return new Date(ts * 1000).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
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

  $effect(() => {
    const listens = groups.flatMap((g) => g.listens);
    const nullArt = listens.filter((e) => !e.cover_art_url && !(e.id in appCache.coverArt));
    if (nullArt.length === 0) return;
    const t = setTimeout(() => {
      fetchCoverArt(
        nullArt.map((e) => ({
          id: e.id,
          artist: e.artist,
          title: e.title,
          recording_mbid: e.recording_mbid,
        })),
      ).then((result) => {
        for (const [idStr, url] of Object.entries(result)) {
          if (url) appCache.coverArt[Number(idStr)] = url;
        }
      });
    }, 2000);
    return () => clearTimeout(t);
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
    <h2 class="editorial-text-h2">
      {(appCache.narrative.plain['on_this_day.section'] || '04 / On This Day — {date}').replace(
        '{date}',
        todayLabel,
      )}
    </h2>
  </div>

  {#if anniversaries.length > 0}
    <div class="reveal-content space-y-2 mb-6">
      {#each anniversaries as ann (ann.artist)}
        <div
          class="rounded border border-theme-accent/30 bg-theme-accent-soft/20 px-4 py-3 flex items-center gap-4 hover:border-theme-accent/60 transition-colors cursor-pointer group"
          onclick={() => router.navigate(`/artist/${encodeURIComponent(ann.artist)}`)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ')
              router.navigate(`/artist/${encodeURIComponent(ann.artist)}`);
          }}
          role="button"
          tabindex="0"
        >
          <div class="shrink-0 text-theme-accent text-xs font-mono tabular-nums">
            {ann.years}y
          </div>
          <div class="grow min-w-0">
            <div
              class="text-sm font-light tracking-wide text-theme-text group-hover:text-theme-accent transition-colors truncate"
            >
              {ann.artist}
            </div>
            <div class="text-xs font-mono text-theme-muted mt-0.5">
              first heard {formatFirstHeard(ann.first_listen_ts)} &bull;
              {ann.total_plays.toLocaleString()} plays total
            </div>
          </div>
          <div class="shrink-0 text-xs font-mono text-theme-accent/70 uppercase tracking-widest">
            anniversary
          </div>
        </div>
      {/each}
    </div>
  {/if}

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
                coverArtUrl={appCache.coverArt[entry.id] ?? entry.cover_art_url}
                onToggle={() => handleToggle(entry)}
                onCorrectionSaved={(updated) => {
                  appCache.onThisDay = appCache.onThisDay.map((g) => ({
                    ...g,
                    listens: patchWithCorrection(g.listens, updated),
                  }));
                  if (updated.cover_art_url) appCache.coverArt[updated.id] = updated.cover_art_url;
                }}
                onDeleted={(id) => {
                  appCache.onThisDay = appCache.onThisDay.map((g) => ({
                    ...g,
                    listens: g.listens.filter((e) => e.id !== id),
                  }));
                }}
              />
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>
</div>
