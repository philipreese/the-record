<script lang="ts">
  import { untrack } from 'svelte';
  import type { ArtistTopTrack } from '../../services/api';
  import { tooltip } from '../../utils/tooltip';
  import MetaChip from '../ui/MetaChip.svelte';
  import Icon from '../layout/Icon.svelte';

  let {
    tracks,
    totalTrackCount,
    loadingEditEntry,
    onView,
    onEdit,
    onDeleteTrack,
  }: {
    tracks: ArtistTopTrack[];
    totalTrackCount: number;
    loadingEditEntry: boolean;
    onView: (track: ArtistTopTrack) => void;
    onEdit: (repId: number, playCount: number) => void;
    onDeleteTrack: (title: string) => Promise<void>;
  } = $props();

  type TrackSort = 'plays' | 'name' | 'oldest' | 'recent';
  let trackSort = $state<TrackSort>('plays');
  let trackPage = $state(1);
  const PAGE_SIZE = 10;

  const sortOptions: [TrackSort, string][] = [
    ['plays', 'Plays'],
    ['name', 'Name'],
    ['oldest', 'Oldest'],
    ['recent', 'Recent'],
  ];

  function formatDuration(secs: number): string {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function formatTsShort(ts: number): string {
    return new Date(ts * 1000).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: '2-digit',
    });
  }

  function sortTracks(src: ArtistTopTrack[], sort: TrackSort): ArtistTopTrack[] {
    const copy = [...src];
    switch (sort) {
      case 'plays':
        return copy.sort((a, b) => b.play_count - a.play_count);
      case 'name':
        return copy.sort((a, b) => a.title.localeCompare(b.title));
      case 'oldest':
        return copy.sort((a, b) => (a.first_listen_ts ?? 0) - (b.first_listen_ts ?? 0));
      case 'recent':
        return copy.sort((a, b) => (b.last_listen_ts ?? 0) - (a.last_listen_ts ?? 0));
    }
  }

  let sortedTracks = $derived(sortTracks(tracks, trackSort));
  let totalTrackPages = $derived(Math.ceil(sortedTracks.length / PAGE_SIZE));
  let pagedTracks = $derived(
    sortedTracks.slice((trackPage - 1) * PAGE_SIZE, trackPage * PAGE_SIZE),
  );

  $effect(() => {
    void trackSort;
    void tracks;
    untrack(() => {
      trackPage = 1;
    });
  });

  // Per-track delete state (local to this component)
  let deleteConfirmTrack = $state<string | null>(null);
  let deletingTrack = $state(false);
  let deleteTrackError = $state('');

  async function handleDeleteConfirm(title: string) {
    deletingTrack = true;
    deleteTrackError = '';
    try {
      await onDeleteTrack(title);
      deleteConfirmTrack = null;
    } catch {
      deleteTrackError = 'Delete failed.';
    } finally {
      deletingTrack = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between pb-2 border-b border-theme-border-soft">
    <h2 class="editorial-text-h2">
      Tracks{#if totalTrackCount > 0}<span
          class="text-sm font-mono font-normal text-theme-muted/40 ml-2"
          >{totalTrackCount.toLocaleString()}</span
        >{/if}
    </h2>
    <div class="nav-selector gap-3 md:gap-6">
      {#each sortOptions as [val, label]}
        <button
          class="nav-selector-item text-xs py-0.5"
          class:active={trackSort === val}
          onclick={() => (trackSort = val)}
        >
          {label}
        </button>
      {/each}
    </div>
  </div>

  <div class="flex flex-col gap-2">
    {#each pagedTracks as track, idx}
      {@const globalIdx = (trackPage - 1) * PAGE_SIZE + idx + 1}
      <div
        role="button"
        tabindex="0"
        class="list-row-interactive group w-full text-left cursor-pointer"
        onclick={() => onView(track)}
        onkeydown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onView(track);
        }}
      >
        <div class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0">
          {String(globalIdx).padStart(2, '0')}
        </div>
        <div class="grow min-w-0">
          <div
            class="text-base md:text-lg font-light tracking-wide truncate text-theme-text"
            use:tooltip
          >
            {track.title}
          </div>
          {#if track.album}
            <div class="text-xs font-mono text-theme-muted/70 mt-0.5 truncate" use:tooltip>
              {track.album}
            </div>
          {/if}
          {#if track.duration_secs || track.first_listen_ts || track.last_listen_ts}
            <div class="flex items-center gap-1 mt-1">
              {#if track.duration_secs}
                <MetaChip value={formatDuration(track.duration_secs)} variant="primary" />
              {/if}
              {#if track.first_listen_ts || track.last_listen_ts}
                <span class="chip-neutral inline-flex items-center gap-1.5">
                  {#if track.first_listen_ts}
                    <span class="opacity-50">{formatTsShort(track.first_listen_ts)}</span>
                  {/if}
                  {#if track.first_listen_ts && track.last_listen_ts && track.first_listen_ts !== track.last_listen_ts}
                    <span class="opacity-30">–</span>
                    <span>{formatTsShort(track.last_listen_ts)}</span>
                  {:else if !track.first_listen_ts && track.last_listen_ts}
                    <span>{formatTsShort(track.last_listen_ts)}</span>
                  {/if}
                </span>
              {/if}
            </div>
          {/if}
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <div class="text-right mr-2">
            <div class="text-lg font-mono font-light text-theme-text">
              {track.play_count.toLocaleString()}
            </div>
            <div class="text-xs font-mono tracking-widest text-theme-muted uppercase mt-0.5">
              plays
            </div>
          </div>
          {#if track.representative_listen_id}
            <button
              type="button"
              class="hidden sm:flex items-center p-1.5 rounded opacity-0 group-hover:opacity-100 group-hover:text-theme-accent transition-all duration-150 text-theme-muted"
              aria-label="Edit track metadata"
              onclick={(e) => {
                e.stopPropagation();
                onEdit(track.representative_listen_id!, track.play_count);
              }}
              disabled={loadingEditEntry}
            >
              <Icon name="pencil" size="w-4 h-4" />
            </button>
          {/if}
          <button
            type="button"
            class="hidden sm:flex items-center p-1.5 rounded opacity-0 group-hover:opacity-100 group-hover:text-error transition-all duration-150 text-theme-muted"
            aria-label="Delete all listens for this track"
            onclick={(e) => {
              e.stopPropagation();
              deleteConfirmTrack = track.title;
              deletingTrack = false;
              deleteTrackError = '';
            }}
          >
            <Icon name="trash" size="w-4 h-4" />
          </button>
        </div>
      </div>

      {#if deleteConfirmTrack === track.title}
        <div
          class="mx-4 px-4 py-3 rounded-xl bg-error/5 border border-error/20 flex flex-col gap-2"
        >
          {#if deleteTrackError}
            <p class="text-xs text-error font-mono">{deleteTrackError}</p>
          {:else}
            <p class="text-xs text-theme-muted font-mono">
              Delete all {track.play_count.toLocaleString()} listens for "{track.title}"? This
              cannot be undone.
            </p>
          {/if}
          <div class="flex gap-2">
            <button
              class="btn btn-sm btn-error"
              onclick={() => handleDeleteConfirm(track.title)}
              disabled={deletingTrack}
            >
              {deletingTrack ? 'Deleting…' : 'Confirm'}
            </button>
            <button
              class="btn btn-sm btn-ghost"
              onclick={() => {
                deleteConfirmTrack = null;
                deleteTrackError = '';
              }}
              disabled={deletingTrack}
            >
              Cancel
            </button>
          </div>
        </div>
      {/if}
    {/each}
  </div>

  {#if totalTrackPages > 1}
    <div
      class="flex items-center justify-between pt-4 border-t border-theme-border-soft font-mono text-xs"
    >
      <button class="btn-nav-text" disabled={trackPage === 1} onclick={() => trackPage--}>
        ← Prev
      </button>
      <span class="text-xs uppercase tracking-widest text-theme-muted/50">
        Page {trackPage} of {totalTrackPages}
      </span>
      <button
        class="btn-nav-text"
        disabled={trackPage === totalTrackPages}
        onclick={() => trackPage++}
      >
        Next →
      </button>
    </div>
  {/if}
</div>
