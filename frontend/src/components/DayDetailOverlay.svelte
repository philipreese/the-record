<script lang="ts">
  import { scale, fade } from 'svelte/transition';
  import { fetchDayListens, fetchCoverArt } from '../services/api';
  import type { ListenEntry } from '../services/api';
  import ListenRow from './dashboard/ListenRow.svelte';
  import { portal } from '../utils/portal';
  import { appCache } from '../services/store.svelte';
  import Icon from './layout/Icon.svelte';
  import { patchWithCorrection } from '../utils/listens';

  let { date, onclose }: { date: string | null; onclose: () => void } = $props();

  let tracks = $state<ListenEntry[]>([]);
  let loading = $state(false);
  let fetchError = $state<string | null>(null);
  let closeButton = $state<HTMLButtonElement | null>(null);
  let expandedId = $state<number | null>(null);

  $effect(() => {
    if (date) {
      document.body.classList.add('overflow-hidden');
      document.documentElement.classList.add('overflow-hidden');
      return () => {
        document.body.classList.remove('overflow-hidden');
        document.documentElement.classList.remove('overflow-hidden');
      };
    }
  });

  $effect(() => {
    if (date) {
      loadTracks(date);
    } else {
      tracks = [];
      fetchError = null;
      expandedId = null;
    }
  });

  $effect(() => {
    if (date && closeButton) {
      closeButton.focus({ preventScroll: true });
    }
  });

  $effect(() => {
    if (tracks.length > 0) {
      appCache.fetchTrackStatsForListens(tracks);
    }
  });

  $effect(() => {
    const nullArt = tracks.filter((e) => !e.cover_art_url && !(e.id in appCache.coverArt));
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

  async function loadTracks(d: string) {
    loading = true;
    fetchError = null;
    try {
      tracks = await fetchDayListens(d);
    } catch {
      fetchError = 'Failed to load tracks.';
    } finally {
      loading = false;
    }
  }

  function close() {
    onclose();
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  function formatOverlayDate(dateStr: string): string {
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
</script>

{#if date}
  <!-- Backdrop — portaled to body so fixed positioning is relative to the viewport,
       not the transformed .memory-surface ancestor -->
  <div
    use:portal
    role="presentation"
    class="fixed inset-0 z-9998 bg-black/40 backdrop-blur-sm"
    transition:fade={{ duration: 200 }}
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  ></div>

  <!-- Dialog wrapper to position centered on desktop and bottom on mobile -->
  <div
    use:portal
    class="fixed inset-0 z-9999 flex items-end justify-center pointer-events-none md:items-center p-0"
  >
    <!-- Panel -->
    <div
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      aria-label="Tracks played on {formatOverlayDate(date)}"
      class="pointer-events-auto w-full max-h-[80vh] md:max-h-[85vh] md:max-w-2xl flex flex-col memory-surface p-4! rounded-t-2xl md:rounded-2xl shadow-2xl"
      transition:scale={{ start: 0.93, duration: 220 }}
      onkeydown={handleKeydown}
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between px-6 py-4 border-b shrink-0"
        style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);"
      >
        <div>
          <div class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">
            Daily Journal
          </div>
          <div class="font-light text-lg text-theme-text mt-0.5">{formatOverlayDate(date)}</div>
        </div>
        <button
          bind:this={closeButton}
          onclick={close}
          class="p-2 rounded-lg transition-colors text-theme-muted hover:text-theme-text cursor-pointer"
          style="background-color: transparent;"
          aria-label="Close daily journal"
        >
          <Icon name="close" size="w-4 h-4" />
        </button>
      </div>

      <!-- Track list -->
      <div class="overflow-y-auto grow px-2 py-2">
        {#if loading}
          <div class="flex items-center justify-center py-12 text-theme-muted text-sm font-mono">
            Loading…
          </div>
        {:else if fetchError}
          <div class="flex items-center justify-center py-12 text-sm font-mono opacity-60">
            {fetchError}
          </div>
        {:else if tracks.length === 0}
          <div class="flex items-center justify-center py-12 text-theme-muted text-sm font-mono">
            No tracks recorded this day.
          </div>
        {:else}
          <div class="text-[10px] font-mono text-theme-muted py-2 uppercase tracking-widest">
            {tracks.length} play{tracks.length === 1 ? '' : 's'}
          </div>
          {#each tracks as entry (entry.id)}
            <ListenRow
              {entry}
              showAbsoluteTime={true}
              showRelativeTime={false}
              expanded={expandedId === entry.id}
              stats={appCache.trackStats[appCache.trackKey(entry)]}
              coverArtUrl={appCache.coverArt[entry.id] ?? entry.cover_art_url}
              onToggle={() => {
                expandedId = expandedId === entry.id ? null : entry.id;
              }}
              onCorrectionSaved={(updated) => {
                tracks = patchWithCorrection(tracks, updated);
                if (updated.cover_art_url) appCache.coverArt[updated.id] = updated.cover_art_url;
              }}
            />
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}
