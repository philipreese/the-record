<script lang="ts">
  import { tick } from 'svelte';
  import type { ArtistTopTrack } from '../../services/api';
  import { tooltip } from '../../utils/tooltip';
  import MetaChip from '../ui/MetaChip.svelte';
  import Icon from '../layout/Icon.svelte';

  let {
    albums,
    tracks,
    loadingEditEntry,
    onView,
    onEdit,
    onDeleteTrack,
  }: {
    albums: { name: string; playCount: number }[];
    tracks: ArtistTopTrack[];
    loadingEditEntry: boolean;
    onView: (track: ArtistTopTrack) => void;
    onEdit: (repId: number, playCount: number) => void;
    onDeleteTrack: (title: string) => Promise<void>;
  } = $props();

  let expandedAlbum = $state<string | null>(null);
  let albumRowEls: Record<string, HTMLElement> = {};

  // Per-track delete state (local to this component)
  let deleteConfirmTrack = $state<string | null>(null);
  let deletingTrack = $state(false);
  let deleteTrackError = $state('');

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

  let tracksByAlbum = $derived(
    new Map(
      albums.map((a) => [
        a.name,
        tracks.filter((t) => t.album === a.name).sort((a, b) => b.play_count - a.play_count),
      ]),
    ),
  );

  async function toggleAlbum(name: string) {
    const wasExpanded = expandedAlbum === name;
    expandedAlbum = wasExpanded ? null : name;
    if (!wasExpanded) {
      await tick();
      albumRowEls[name]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

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
  <h2 class="editorial-text-h2 pb-2 border-b border-theme-border-soft">Albums</h2>
  <div class="flex flex-col gap-1">
    {#each albums as album, idx}
      {@const albumTracks = tracksByAlbum.get(album.name) ?? []}
      {@const isExpanded = expandedAlbum === album.name}
      <div bind:this={albumRowEls[album.name]}>
        <button
          type="button"
          class="list-row-interactive w-full text-left"
          onclick={() => toggleAlbum(album.name)}
        >
          <div class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0">
            {String(idx + 1).padStart(2, '0')}
          </div>
          <div class="grow min-w-0">
            <div class="text-base md:text-lg font-light tracking-wide truncate text-theme-text">
              {album.name}
            </div>
            {#if albumTracks.length > 0}
              <div class="text-xs font-mono text-theme-muted/50 mt-0.5">
                {albumTracks.length}
                {albumTracks.length === 1 ? 'track' : 'tracks'}
              </div>
            {/if}
          </div>
          <div class="flex items-center gap-3 shrink-0">
            <div class="text-right">
              <div class="text-lg font-mono font-light text-theme-text">
                {album.playCount.toLocaleString()}
              </div>
              <div class="text-xs font-mono tracking-widest text-theme-muted uppercase mt-0.5">
                plays
              </div>
            </div>
            <span
              class="text-theme-muted/50 text-xs font-mono transition-transform duration-150"
              class:rotate-90={isExpanded}>›</span
            >
          </div>
        </button>

        {#if isExpanded && albumTracks.length > 0}
          <div
            class="ml-4 md:ml-12 pl-2 md:pl-4 border-l border-theme-border-soft/40 py-1 flex flex-col gap-0"
          >
            {#each albumTracks as track}
              <div
                role="button"
                tabindex="0"
                class="list-row-interactive group w-full text-left py-2! cursor-pointer"
                onclick={() => onView(track)}
                onkeydown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') onView(track);
                }}
              >
                <div class="grow min-w-0">
                  <div
                    class="text-sm font-light tracking-wide truncate text-theme-text"
                    use:tooltip
                  >
                    {track.title}
                  </div>
                  {#if track.duration_secs || track.first_listen_ts}
                    <div class="flex items-center gap-1 mt-0.5">
                      {#if track.duration_secs}
                        <MetaChip value={formatDuration(track.duration_secs)} variant="primary" />
                      {/if}
                      {#if track.first_listen_ts}
                        <span class="chip-neutral text-[10px]">
                          {formatTsShort(track.first_listen_ts)}
                          {#if track.last_listen_ts && track.last_listen_ts !== track.first_listen_ts}
                            <span class="opacity-40">–</span>{formatTsShort(track.last_listen_ts)}
                          {/if}
                        </span>
                      {/if}
                    </div>
                  {/if}
                </div>
                <div class="flex items-center gap-1 shrink-0">
                  <div class="text-right mr-1">
                    <div class="text-sm font-mono font-light text-theme-text">
                      {track.play_count.toLocaleString()}
                    </div>
                    <div
                      class="text-[10px] font-mono tracking-widest text-theme-muted uppercase mt-0.5"
                    >
                      plays
                    </div>
                  </div>
                  {#if track.representative_listen_id}
                    <button
                      type="button"
                      class="hidden sm:flex items-center p-1 rounded opacity-0 group-hover:opacity-100 group-hover:text-theme-accent transition-all duration-150 text-theme-muted"
                      aria-label="Edit track metadata"
                      onclick={(e) => {
                        e.stopPropagation();
                        onEdit(track.representative_listen_id!, track.play_count);
                      }}
                      disabled={loadingEditEntry}
                    >
                      <Icon name="pencil" size="w-3.5 h-3.5" />
                    </button>
                  {/if}
                  <button
                    type="button"
                    class="hidden sm:flex items-center p-1 rounded opacity-0 group-hover:opacity-100 group-hover:text-error transition-all duration-150 text-theme-muted"
                    aria-label="Delete all listens for this track"
                    onclick={(e) => {
                      e.stopPropagation();
                      deleteConfirmTrack = track.title;
                      deletingTrack = false;
                      deleteTrackError = '';
                    }}
                  >
                    <Icon name="trash" size="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {#if deleteConfirmTrack === track.title}
                <div
                  class="mx-2 px-3 py-2 rounded-lg bg-error/5 border border-error/20 flex flex-col gap-2"
                >
                  {#if deleteTrackError}
                    <p class="text-xs text-error font-mono">{deleteTrackError}</p>
                  {:else}
                    <p class="text-xs text-theme-muted font-mono">
                      Delete all {track.play_count.toLocaleString()} listens for "{track.title}"?
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
        {/if}
      </div>
    {/each}
  </div>
</div>
