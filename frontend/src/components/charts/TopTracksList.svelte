<script lang="ts">
  import { inView } from '../../utils/inView';
  import { tooltip } from '../../utils/tooltip';
  import type { TrackInfo } from '../../services/api';

  let {
    tracks,
    trackPage,
    totalTrackPages,
    loadingTracks,
    hasMoreTracks,
    pageSize,
    focusedTrack,
    onpreviouspage,
    onnextpage,
  }: {
    tracks: TrackInfo[];
    trackPage: number;
    totalTrackPages: number;
    loadingTracks: boolean;
    hasMoreTracks: boolean;
    pageSize: number;
    focusedTrack: string | null;
    onpreviouspage: () => void;
    onnextpage: () => void;
  } = $props();
</script>

<div class="flex flex-col justify-between h-full min-h-125">
  <div class="space-y-6">
    <h2
      class="editorial-text-h2 pb-2 border-b border-theme-border-soft flex justify-between items-center"
    >
      <span>Top Tracks</span>
      {#if loadingTracks}
        <span class="loading loading-spinner loading-xs text-theme-accent"></span>
      {/if}
    </h2>

    <div use:inView={{ once: true }} class="flex flex-col gap-3 reveal-list-container">
      {#each tracks as track, idx}
        <div
          role="textbox"
          class="list-row-interactive cursor-default!"
          style="animation-delay: {idx * 40}ms;"
          class:border-theme-accent={focusedTrack === `${track.artist} - ${track.title}`}
          class:bg-theme-accent-soft={focusedTrack === `${track.artist} - ${track.title}`}
        >
          <div class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0">
            {String(track.rank ?? (trackPage - 1) * pageSize + idx + 1).padStart(2, '0')}
          </div>
          <div class="grow min-w-0">
            <div
              class="text-base md:text-lg font-light tracking-wide truncate text-theme-text"
              use:tooltip
            >
              {track.title}
            </div>
            <div
              class="text-sm font-normal truncate mt-1 text-theme-secondary opacity-80"
              use:tooltip
            >
              {track.artist}
            </div>
          </div>
          <div class="text-right shrink-0">
            <div class="text-lg font-mono font-light text-theme-text">
              {track.play_count.toLocaleString()}
            </div>
            <div class="text-xs font-mono tracking-widest text-theme-muted uppercase mt-0.5">
              plays
            </div>
          </div>
        </div>
      {:else}
        <p class="text-xs font-mono opacity-50 text-center py-10">
          No history found for this range.
        </p>
      {/each}
    </div>
  </div>

  <!-- Tracks Paginator -->
  <div
    class="flex items-center justify-between mt-8 pt-4 border-t border-theme-border-soft font-mono text-xs"
  >
    <button
      class="btn-nav-text"
      disabled={trackPage === 1 || loadingTracks}
      onclick={onpreviouspage}
    >
      ← Prev
    </button>
    <span class="text-xs uppercase tracking-widest text-theme-muted/50 font-mono"
      >Page {trackPage} of {totalTrackPages || 1}</span
    >
    <button class="btn-nav-text" disabled={!hasMoreTracks || loadingTracks} onclick={onnextpage}>
      Next →
    </button>
  </div>
</div>
