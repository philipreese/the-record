<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fetchRecentListens, type ListenEntry } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';

  const PAGE_SIZE = 50;

  let loading = $state(false);
  let sentinel: HTMLElement | undefined = $state(undefined);
  let observer: IntersectionObserver | undefined;
  let scrollThrottle: ReturnType<typeof setTimeout> | undefined;

  const SOURCE_LABELS: Record<string, string> = {
    listenbrainz: 'ListenBrainz',
    listenbrainz_sync: 'ListenBrainz',
    youtube: 'YouTube Music',
    google_takeout: 'Takeout',
  };

  function sourceLabel(source: string): string {
    return SOURCE_LABELS[source] ?? 'Other';
  }

  function relativeTime(unix_ts: number): string {
    const diff = Math.floor(Date.now() / 1000) - unix_ts;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(unix_ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function absoluteTime(unix_ts: number): string {
    return new Date(unix_ts * 1000).toLocaleString(undefined, {
      weekday: 'short', month: 'short', day: 'numeric',
      year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  }

  function dayKey(unix_ts: number): string {
    return new Date(unix_ts * 1000).toLocaleDateString(undefined, {
      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
    });
  }

  // Group entries: returns an array of {day, entries} blocks
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
      const page = await fetchRecentListens(
        PAGE_SIZE,
        last?.unix_ts,
        last?.id,
      );
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
      // Restore scroll position after Svelte renders the cached list
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

  // Re-observe sentinel when it mounts (Svelte may bind it after onMount)
  $effect(() => {
    if (sentinel && observer) observer.observe(sentinel);
  });
</script>

<div class="w-full max-w-2xl mx-auto pb-16">
  <PageHeader title="journal" subtitle="your complete listening history" />

  {#if appCache.recentListens.length === 0 && loading}
    <!-- Initial loading skeleton -->
    <div class="space-y-1 mt-4">
      {#each { length: 12 } as _}
        <div class="flex items-center gap-3 py-3 px-2 animate-pulse">
          <div class="h-3 bg-base-300 rounded w-28 shrink-0"></div>
          <div class="flex-1 h-3 bg-base-300 rounded"></div>
          <div class="h-3 bg-base-300 rounded w-20 shrink-0"></div>
        </div>
      {/each}
    </div>

  {:else if grouped.length === 0}
    <div class="text-center text-base-content/40 mt-16 text-sm">No listens yet.</div>

  {:else}
    <div class="space-y-8 mt-4">
      {#each grouped as group}
        <div>
          <div class="text-xs uppercase tracking-widest text-base-content/40 font-mono mb-2 pl-2 border-b border-base-content/10 pb-1">
            {group.day}
          </div>
          <div class="space-y-0">
            {#each group.entries as entry (entry.id)}
              <div class="flex items-center gap-3 py-2.5 px-2 rounded hover:bg-base-200/50 transition-colors group">
                <div class="w-28 shrink-0 text-right">
                  <span
                    class="text-xs text-base-content/40 group-hover:text-base-content/60 transition-colors font-mono tabular-nums"
                    title={absoluteTime(entry.unix_ts)}
                  >
                    {relativeTime(entry.unix_ts)}
                  </span>
                </div>
                <div class="flex-1 min-w-0">
                  <span class="text-sm font-medium truncate block">{entry.title}</span>
                  <span class="text-xs text-base-content/50 truncate block">{entry.artist}</span>
                </div>
                <div class="shrink-0">
                  <span class="badge badge-ghost badge-xs text-base-content/40 font-mono">
                    {sourceLabel(entry.source)}
                  </span>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/each}
    </div>

    <!-- Infinite scroll sentinel -->
    {#if !appCache.recentExhausted}
      <div bind:this={sentinel} class="h-8 mt-4"></div>
      {#if loading}
        <div class="text-center py-4">
          <span class="loading loading-dots loading-sm text-base-content/30"></span>
        </div>
      {/if}
    {:else}
      <div class="text-center text-base-content/30 text-xs font-mono mt-8 py-4 border-t border-base-content/10">
        — end of history —
      </div>
    {/if}
  {/if}
</div>
