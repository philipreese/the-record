<script lang="ts">
  import { searchCoverArt } from '../../../services/api';
  import type { CoverArtResult } from '../../../services/api';

  let {
    artist,
    album,
    mbid,
    artUrl = $bindable(''),
    originalArtUrl = undefined,
  }: {
    artist: string;
    album: string;
    mbid: string;
    artUrl: string;
    originalArtUrl?: string;
  } = $props();

  let artSearching = $state(false);
  let artResults = $state<CoverArtResult[]>([]);
  let artError = $state('');
  let artLoadFailures = $state(0);

  async function handleArtSearch() {
    artError = '';
    artResults = [];
    artLoadFailures = 0;
    artSearching = true;
    try {
      artResults = await searchCoverArt(artist, album, mbid || undefined);
      if (artResults.length === 0) artError = 'No releases found.';
    } catch {
      artError = 'Search failed.';
    } finally {
      artSearching = false;
    }
  }

  function applyArtResult(result: CoverArtResult) {
    artUrl = `https://coverartarchive.org/release/${result.release_mbid}/front-250`;
    artResults = [];
  }
</script>

<div class="space-y-3">
  <h3
    class="text-[11px] font-mono text-theme-muted tracking-widest uppercase border-b border-base-content/10 pb-1"
  >
    Cover Art
  </h3>

  <div class="space-y-2">
    <div class="flex items-center justify-between">
      <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Image URL</span
      >
      <button
        type="button"
        class="btn btn-xs btn-ghost border border-base-content/10 font-mono text-[10px] tracking-widest"
        onclick={handleArtSearch}
        disabled={artSearching}
      >
        {artSearching ? 'searching…' : 'find art'}
      </button>
    </div>
    <input
      type="url"
      class="input input-sm w-full bg-base-200 border-base-content/10 font-mono text-xs"
      placeholder="https://..."
      bind:value={artUrl}
    />

    {#if artUrl}
      <img
        src={artUrl}
        alt="preview"
        class="w-16 h-16 rounded object-cover mt-2 shadow"
        onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
      />
    {/if}

    {#if originalArtUrl && originalArtUrl !== artUrl}
      <div class="flex items-center gap-3 mt-2 p-2 rounded-lg bg-base-200">
        <img
          src={originalArtUrl}
          alt="original art"
          class="w-10 h-10 rounded object-cover shrink-0 shadow"
          onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
        />
        <div class="flex flex-col gap-0.5 grow min-w-0">
          <span class="text-[10px] font-mono text-theme-muted uppercase tracking-widest"
            >Original art</span
          >
          <button
            type="button"
            class="btn btn-xs btn-ghost text-theme-accent self-start"
            onclick={() => (artUrl = originalArtUrl!)}
          >
            Use original
          </button>
        </div>
      </div>
    {/if}

    {#if artError}
      <p class="text-xs text-error mt-1">{artError}</p>
    {/if}

    {#if artResults.length > 0}
      {#if artLoadFailures === artResults.length}
        <p class="text-xs text-theme-muted mt-2 italic">No artwork found for these releases.</p>
      {:else}
        <div class="grid grid-cols-4 gap-1.5 pt-2">
          {#each artResults as result (result.release_mbid)}
            {@const caaUrl = `https://coverartarchive.org/release/${result.release_mbid}/front-250`}
            <button
              type="button"
              class="relative aspect-square rounded overflow-hidden bg-base-200 hover:ring-2 hover:ring-theme-accent transition-all group"
              title="{result.release_title}{result.date ? ` (${result.date.slice(0, 4)})` : ''}"
              onclick={() => applyArtResult(result)}
            >
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="loading loading-spinner loading-xs text-base-content/30"></span>
              </div>
              <img
                src={caaUrl}
                alt={result.release_title}
                class="relative z-10 w-full h-full object-cover transition-opacity duration-200"
                style="opacity: 0;"
                onload={(e) => ((e.currentTarget as HTMLImageElement).style.opacity = '1')}
                onerror={(e) => {
                  const img = e.currentTarget as HTMLImageElement;
                  if (img.src.endsWith('/front-250')) {
                    img.src = img.src.replace('/front-250', '/front');
                  } else {
                    const btn = img.closest('button');
                    if (btn) btn.style.display = 'none';
                    artLoadFailures++;
                  }
                }}
              />
              <span
                class="absolute inset-x-0 bottom-0 bg-black/60 text-[8px] text-white px-1 py-0.5 truncate opacity-0 group-hover:opacity-100 transition-opacity z-30"
              >
                {result.date?.slice(0, 4) ?? ''}
              </span>
            </button>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</div>
