<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fetchRecentListens, type ListenEntry } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import { sourceLabel, timeOnly, relativeTimeShort, absoluteTime } from '../utils/listens';

  const PAGE_SIZE = 50;

  let loading = $state(false);
  let sentinel: HTMLElement | undefined = $state(undefined);
  let observer: IntersectionObserver | undefined;
  let scrollThrottle: ReturnType<typeof setTimeout> | undefined;

  function dayKey(unix_ts: number): string {
    return new Date(unix_ts * 1000).toLocaleDateString(undefined, {
      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
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

  async function loadMore() {
    if (loading || appCache.recentExhausted) return;
    loading = true;
    try {
      const last = appCache.recentListens[appCache.recentListens.length - 1];
      const page = await fetchRecentListens(PAGE_SIZE, last?.unix_ts, last?.id);
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
    if (appCache.recentListens.length === 0) {
      await loadMore();
    } else {
      requestAnimationFrame(() => {
        window.scrollTo({ top: appCache.recentScrollOffset, behavior: 'instant' });
      });
    }
    observer = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore(); },
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

  // Re-fetch when a sync invalidates the cache while this view is mounted
  $effect(() => {
    if (appCache.recentListens.length === 0 && !loading && !appCache.recentExhausted) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      loadMore();
    }
  });
</script>

<div class="w-full pb-28">
  <PageHeader title="journal" subtitle="your complete listening history" />

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
          <!-- Day divider with play count -->
          <div class="flex items-baseline justify-between border-b border-base-content/10 pb-1.5 mb-1">
            <span class="text-xs uppercase tracking-widest text-base-content/50 font-mono">
              {group.day}
            </span>
            <span class="text-xs font-mono text-base-content/35 tabular-nums">
              {group.entries.length} {group.entries.length === 1 ? 'play' : 'plays'}
            </span>
          </div>

          <!-- Entries -->
          <div>
            {#each group.entries as entry (entry.id)}
              {@const label = sourceLabel(entry.source)}
              <div class="flex items-center gap-4 py-2 px-2 rounded hover:bg-base-200/50 transition-colors group">
                <!-- Timestamp: HH:MM · relative -->
                <div class="w-36 shrink-0 text-right" title={absoluteTime(entry.unix_ts)}>
                  <span class="text-xs font-mono tabular-nums text-base-content/55 group-hover:text-base-content/70 transition-colors">
                    {timeOnly(entry.unix_ts)}
                    {#if relativeTimeShort(entry.unix_ts)}
                      <span class="text-base-content/35"> · {relativeTimeShort(entry.unix_ts)}</span>
                    {/if}
                  </span>
                </div>

                <!-- Title + artist -->
                <div class="flex-1 min-w-0">
                  <span class="text-sm font-medium leading-snug truncate block text-base-content">{entry.title}</span>
                  <span class="text-xs text-base-content/65 truncate block">{entry.artist}</span>
                </div>

                <!-- Source badge: only for non-LB sources -->
                {#if label}
                  <div class="shrink-0">
                    <span class="badge badge-ghost badge-xs text-base-content/45 font-mono">{label}</span>
                  </div>
                {/if}
              </div>
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
      <div class="text-center text-base-content/30 text-xs font-mono mt-10 py-4 border-t border-base-content/10">
        — end of history —
      </div>
    {/if}
  {/if}
</div>
