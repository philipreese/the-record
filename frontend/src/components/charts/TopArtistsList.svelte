<script lang="ts">
  import { inView } from '../../utils/inView';
  import type { ArtistInfo } from '../../services/api';

  let {
    artists,
    artistPage,
    totalArtistPages,
    loadingArtists,
    hasMoreArtists,
    pageSize,
    onpreviouspage,
    onnextpage,
    onartistclick,
  }: {
    artists: ArtistInfo[];
    artistPage: number;
    totalArtistPages: number;
    loadingArtists: boolean;
    hasMoreArtists: boolean;
    pageSize: number;
    onpreviouspage: () => void;
    onnextpage: () => void;
    onartistclick: (name: string) => void;
  } = $props();
</script>

<div class="flex flex-col justify-between h-full min-h-125">
  <div class="space-y-6">
    <h2
      class="editorial-text-h2 pb-2 border-b border-theme-border-soft flex justify-between items-center"
    >
      <span>Top Creators</span>
      {#if loadingArtists}
        <span class="loading loading-spinner loading-xs text-theme-accent"></span>
      {/if}
    </h2>

    <div use:inView={{ once: true }} class="flex flex-col gap-3 reveal-list-container">
      {#each artists as artist, idx}
        <div
          role="button"
          tabindex="0"
          class="list-row-interactive"
          style="animation-delay: {idx * 40}ms;"
          onclick={() => onartistclick(artist.artist)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onartistclick(artist.artist);
          }}
        >
          <div class="w-12 text-xl md:text-2xl font-mono font-light text-theme-muted/80 shrink-0">
            {String(artist.rank ?? (artistPage - 1) * pageSize + idx + 1).padStart(2, '0')}
          </div>
          <div class="grow">
            <div class="text-base md:text-lg font-light tracking-wide text-theme-text">
              {artist.artist}
            </div>
          </div>
          <div class="text-right">
            <div class="text-lg font-mono font-light text-theme-text">
              {artist.play_count.toLocaleString()}
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

  <!-- Artists Paginator -->
  <div
    class="flex items-center justify-between mt-8 pt-4 border-t border-theme-border-soft font-mono text-xs"
  >
    <button
      class="btn-nav-text"
      disabled={artistPage === 1 || loadingArtists}
      onclick={onpreviouspage}
    >
      ← Prev
    </button>
    <span class="text-xs uppercase tracking-widest text-theme-muted/50 font-mono"
      >Page {artistPage} of {totalArtistPages || 1}</span
    >
    <button class="btn-nav-text" disabled={!hasMoreArtists || loadingArtists} onclick={onnextpage}>
      Next →
    </button>
  </div>
</div>
