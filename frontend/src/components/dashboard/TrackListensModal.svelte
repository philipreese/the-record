<script lang="ts">
  import { scale, fade } from 'svelte/transition';
  import { fetchTrackListens, deleteTrackListens, fetchCoverArt } from '../../services/api';
  import type { ArtistTopTrack, ListenEntry } from '../../services/api';
  import ListenRow from './ListenRow.svelte';
  import { portal } from '../../utils/portal';
  import { appCache } from '../../services/store.svelte';
  import Icon from '../layout/Icon.svelte';
  import { patchWithCorrection } from '../../utils/listens';

  let {
    track,
    artistName,
    onClose,
    onChanged,
  }: {
    track: ArtistTopTrack;
    artistName: string;
    onClose: () => void;
    onChanged: () => void;
  } = $props();

  let listens = $state<ListenEntry[]>([]);
  let loading = $state(true);
  let fetchError = $state<string | null>(null);
  let expandedId = $state<number | null>(null);

  let deleteAllConfirm = $state(false);
  let deletingAll = $state(false);
  let deleteAllError = $state('');

  $effect(() => {
    document.body.classList.add('overflow-hidden');
    document.documentElement.classList.add('overflow-hidden');
    return () => {
      document.body.classList.remove('overflow-hidden');
      document.documentElement.classList.remove('overflow-hidden');
    };
  });

  $effect(() => {
    loadListens();
  });

  $effect(() => {
    if (listens.length > 0) {
      appCache.fetchTrackStatsForListens(listens);
    }
  });

  $effect(() => {
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

  async function loadListens() {
    loading = true;
    fetchError = null;
    try {
      listens = await fetchTrackListens(artistName, track.title);
    } catch {
      fetchError = 'Failed to load listens.';
    } finally {
      loading = false;
    }
  }

  function handleListenDeleted(id: number) {
    listens = listens.filter((e) => e.id !== id);
    if (listens.length === 0) {
      onChanged();
      onClose();
    }
  }

  function handleCorrectionSaved(updated: ListenEntry) {
    listens = patchWithCorrection(listens, updated);
    if (updated.cover_art_url) appCache.coverArt[updated.id] = updated.cover_art_url;
    onChanged();
  }

  async function handleDeleteAll() {
    deletingAll = true;
    deleteAllError = '';
    try {
      await deleteTrackListens(artistName, track.title);
      onChanged();
      onClose();
    } catch {
      deleteAllError = 'Delete failed.';
      deletingAll = false;
      deleteAllConfirm = false;
    }
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }
</script>

<!-- Backdrop -->
<div
  use:portal
  role="presentation"
  class="fixed inset-0 z-9998 bg-black/40 backdrop-blur-sm"
  transition:fade={{ duration: 200 }}
  onclick={handleBackdropClick}
  onkeydown={handleKeydown}
></div>

<!-- Panel -->
<div
  use:portal
  class="fixed inset-0 z-9999 flex items-end justify-center pointer-events-none md:items-center p-0"
>
  <div
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    aria-label="Listens for {track.title}"
    class="pointer-events-auto w-full max-h-[85vh] md:max-h-[80vh] md:max-w-2xl flex flex-col memory-surface p-4! rounded-t-2xl md:rounded-2xl shadow-2xl"
    transition:scale={{ start: 0.93, duration: 220 }}
    onkeydown={handleKeydown}
  >
    <!-- Header -->
    <div
      class="flex items-start justify-between px-6 py-4 border-b shrink-0"
      style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);"
    >
      <div class="min-w-0 pr-4">
        <div class="text-[10px] font-mono text-theme-muted tracking-widest uppercase mb-0.5">
          {artistName}
        </div>
        <div class="font-light text-lg text-theme-text truncate">{track.title}</div>
        {#if !loading && listens.length > 0}
          <div class="text-xs text-theme-muted mt-0.5 font-mono">
            {listens.length} listen{listens.length === 1 ? '' : 's'}
          </div>
        {/if}
      </div>
      <button
        onclick={onClose}
        class="p-2 rounded-lg transition-colors text-theme-muted hover:text-theme-text cursor-pointer shrink-0"
        style="background-color: transparent;"
        aria-label="Close"
      >
        <Icon name="close" size="w-4 h-4" />
      </button>
    </div>

    <!-- Listen list -->
    <div class="overflow-y-auto grow px-2 py-2">
      {#if loading}
        <div class="flex items-center justify-center py-12 text-theme-muted text-sm font-mono">
          Loading…
        </div>
      {:else if fetchError}
        <div class="flex items-center justify-center py-12 text-sm font-mono opacity-60">
          {fetchError}
        </div>
      {:else if listens.length === 0}
        <div class="flex items-center justify-center py-12 text-theme-muted text-sm font-mono">
          No listens found.
        </div>
      {:else}
        {#each listens as entry (entry.id)}
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
            onCorrectionSaved={handleCorrectionSaved}
            onDeleted={handleListenDeleted}
          />
        {/each}
      {/if}
    </div>

    <!-- Footer: delete all -->
    {#if !loading && listens.length > 0}
      <div
        class="px-6 py-4 border-t shrink-0"
        style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);"
      >
        {#if deleteAllConfirm}
          <div class="flex flex-col gap-2">
            {#if deleteAllError}
              <p class="text-xs text-error font-mono">{deleteAllError}</p>
            {:else}
              <p class="text-xs text-theme-muted font-mono">
                Delete all {listens.length} listen{listens.length === 1 ? '' : 's'} for this track? This
                cannot be undone.
              </p>
            {/if}
            <div class="flex gap-2">
              <button class="btn btn-sm btn-error" onclick={handleDeleteAll} disabled={deletingAll}>
                {deletingAll ? 'Deleting…' : 'Confirm delete all'}
              </button>
              <button
                class="btn btn-sm btn-ghost"
                onclick={() => {
                  deleteAllConfirm = false;
                  deleteAllError = '';
                }}
                disabled={deletingAll}
              >
                Cancel
              </button>
            </div>
          </div>
        {:else}
          <button
            class="btn btn-ghost text-error w-full"
            onclick={() => {
              deleteAllConfirm = true;
            }}
          >
            <Icon name="trash" size="w-4 h-4" />
            Delete all {listens.length} listen{listens.length === 1 ? '' : 's'}
          </button>
        {/if}
      </div>
    {/if}
  </div>
</div>
