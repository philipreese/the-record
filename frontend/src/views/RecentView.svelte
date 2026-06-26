<script lang="ts">
  import { onMount, onDestroy, untrack } from 'svelte';
  import {
    fetchRecentListens,
    fetchTrackStats,
    fetchMonthlyTrends,
    fetchCoverArt,
    type ListenEntry,
  } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import ListenRow from '../components/dashboard/ListenRow.svelte';
  import DatePicker from '../components/layout/DatePicker.svelte';

  const PAGE_SIZE = 50;

  let loading = $state(false);
  let sentinel: HTMLElement | undefined = $state(undefined);
  let observer: IntersectionObserver | undefined;
  let scrollThrottle: ReturnType<typeof setTimeout> | undefined;

  let expandedId: number | null = $state(null);

  // Date jump states
  let selectedDate = $state('');
  let currentDate = $state('');

  $effect(() => {
    const listens = appCache.recentListens;
    if (listens.length > 0) {
      untrack(() => {
        appCache.fetchTrackStatsForListens(listens);
      });
    }
  });

  $effect(() => {
    const listens = appCache.recentListens;
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
    const statsKey = appCache.trackKey(entry);
    if (!(statsKey in appCache.trackStats)) {
      try {
        appCache.trackStats[statsKey] = await fetchTrackStats(
          entry.artist,
          entry.title,
          entry.album,
        );
      } catch {
        appCache.trackStats[statsKey] = null;
      }
    }
  }

  function dayKey(unix_ts: number): string {
    return new Date(unix_ts * 1000).toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  }

  let grouped = $derived.by(() => {
    const result: { day: string; entries: ListenEntry[] }[] = [];
    let currentDay = '';
    for (const entry of appCache.recentListens) {
      const d = dayKey(entry.unix_ts);
      if (d !== currentDay) {
        result.push({ day: d, entries: [] });
        currentDay = d;
      }
      result[result.length - 1].entries.push(entry);
    }
    return result;
  });

  function getAnchorDate(dateStr: string): string {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length === 2) {
      // YYYY-MM -> last day of month
      const year = parseInt(parts[0]);
      const month = parseInt(parts[1]);
      const lastDay = new Date(year, month, 0).getDate();
      return `${parts[0]}-${parts[1]}-${String(lastDay).padStart(2, '0')}`;
    }
    return dateStr;
  }

  async function loadMore() {
    if (loading || appCache.recentExhausted) return;
    loading = true;
    try {
      const last = appCache.recentListens[appCache.recentListens.length - 1];
      const anchor = !last && selectedDate ? getAnchorDate(selectedDate) : undefined;
      const page = await fetchRecentListens(PAGE_SIZE, last?.unix_ts, last?.id, anchor);
      appCache.recentListens = [...appCache.recentListens, ...page];
      if (page.length < PAGE_SIZE) appCache.recentExhausted = true;
    } catch (e) {
      console.error('Failed to load more listens:', e);
    } finally {
      loading = false;
    }
  }

  function onScroll() {
    if (scrollThrottle) return;
    scrollThrottle = setTimeout(() => {
      appCache.recentScrollOffset = window.scrollY;
      scrollThrottle = undefined;
    }, 200);
  }

  onMount(async () => {
    window.addEventListener('scroll', onScroll, { passive: true });

    if (appCache.monthlyTrends.length === 0) {
      try {
        appCache.monthlyTrends = await fetchMonthlyTrends();
      } catch (e) {
        console.error('Failed to load monthly trends:', e);
      }
    }

    if (appCache.recentListens.length === 0) {
      await loadMore();
    } else {
      requestAnimationFrame(() => {
        window.scrollTo({ top: appCache.recentScrollOffset, behavior: 'instant' });
      });
    }

    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { rootMargin: '200px' },
    );
    if (sentinel) observer.observe(sentinel);
  });

  onDestroy(() => {
    window.removeEventListener('scroll', onScroll);
    observer?.disconnect();
    if (scrollThrottle) clearTimeout(scrollThrottle);
  });

  $effect(() => {
    if (sentinel && observer) observer.observe(sentinel);
  });

  // Trigger reload when selectedDate changes
  $effect(() => {
    const date = selectedDate;
    if (date !== currentDate) {
      currentDate = date;
      untrack(() => {
        appCache.recentListens = [];
        appCache.recentExhausted = false;
        appCache.recentScrollOffset = 0;
        expandedId = null;
        loadMore();
      });
    }
  });

  // Re-fetch when a sync invalidates the cache while this view is mounted
  $effect(() => {
    if (appCache.recentListens.length === 0 && !loading && !appCache.recentExhausted) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      if (appCache.monthlyTrends.length === 0) {
        fetchMonthlyTrends()
          .then((t) => (appCache.monthlyTrends = t))
          .catch(() => {});
      }
      loadMore();
    }
  });
</script>

<div class="w-full pb-28">
  <PageHeader title="journal" subtitle="your complete listening history">
    {#snippet actions(_isShrunk)}
      <div class="hidden lg:block">
        <div class="flex items-center gap-3">
          {#if selectedDate}
            <button
              type="button"
              class="btn-nav-text text-xs uppercase tracking-widest font-mono text-theme-accent hover:text-theme-accent/80 transition-colors"
              onclick={() => (selectedDate = '')}
            >
              back to today ↑
            </button>
          {/if}

          <DatePicker
            bind:value={selectedDate}
            monthlyTrends={appCache.monthlyTrends}
            class="w-50"
          />
        </div>
      </div>
    {/snippet}
  </PageHeader>

  <!-- Mobile Sticky Sub-Header: Stuck month selector on mobile -->
  <div class="sticky-sub-header lg:hidden flex items-center justify-between gap-3 py-2">
    <DatePicker bind:value={selectedDate} monthlyTrends={appCache.monthlyTrends} class="w-47.5" />

    {#if selectedDate}
      <button
        type="button"
        class="btn-nav-text text-xs uppercase tracking-widest font-mono text-theme-accent hover:text-theme-accent/80 transition-colors shrink-0"
        onclick={() => (selectedDate = '')}
      >
        back to today ↑
      </button>
    {/if}
  </div>

  {#if appCache.recentListens.length === 0 && loading}
    <div class="space-y-1 mt-6">
      {#each { length: 14 } as _}
        <div class="flex items-center gap-4 py-3 px-2 animate-pulse">
          <div class="h-3 bg-base-300 rounded w-24 shrink-0"></div>
          <div class="flex-1 h-3 bg-base-300 rounded"></div>
          <div class="h-3 bg-base-300 rounded w-32 shrink-0"></div>
        </div>
      {/each}
    </div>
  {:else if grouped.length === 0}
    <div class="text-center text-base-content/40 mt-16 text-sm">No listens yet.</div>
  {:else}
    <div class="space-y-10 mt-6">
      {#each grouped as group}
        <div>
          <div
            class="flex items-baseline justify-between border-b border-base-content/10 pb-1.5 mb-1"
          >
            <span class="text-xs uppercase tracking-widest text-base-content/50 font-mono">
              {group.day}
            </span>
            <span class="text-xs font-mono text-base-content/35 tabular-nums">
              {group.entries.length}
              {group.entries.length === 1 ? 'play' : 'plays'}
            </span>
          </div>

          <div>
            {#each group.entries as entry (entry.id)}
              <ListenRow
                {entry}
                showAbsoluteTime={true}
                expanded={expandedId === entry.id}
                stats={appCache.trackStats[appCache.trackKey(entry)]}
                coverArtUrl={appCache.coverArt[entry.id] ?? entry.cover_art_url}
                onToggle={() => handleToggle(entry)}
              />
            {/each}
          </div>
        </div>
      {/each}
    </div>

    {#if !appCache.recentExhausted}
      <div bind:this={sentinel} class="h-8 mt-4"></div>
      {#if loading}
        <div class="text-center py-4">
          <span class="loading loading-dots loading-sm text-base-content/30"></span>
        </div>
      {/if}
    {:else}
      <div
        class="text-center text-base-content/30 text-xs font-mono mt-10 py-4 border-t border-base-content/10"
      >
        — end of history —
      </div>
    {/if}
  {/if}
</div>
