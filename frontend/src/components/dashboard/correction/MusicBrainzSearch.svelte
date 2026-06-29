<script lang="ts">
  import { searchMusicBrainz } from '../../../services/api';
  import type { MBRecordingResult } from '../../../services/api';
  import Icon from '../../layout/Icon.svelte';

  let {
    artist,
    title,
    selectedMbid = $bindable(''),
    album = $bindable(''),
    duration = $bindable(''),
    artUrl = $bindable(''),
  }: {
    artist: string;
    title: string;
    selectedMbid: string;
    album: string;
    duration: string;
    artUrl: string;
  } = $props();

  let mbSearching = $state(false);
  let mbResults = $state<MBRecordingResult[]>([]);
  let mbError = $state('');

  function msToMmSs(ms: number | null | undefined): string {
    if (!ms) return '';
    const s = Math.round(ms / 1000);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }

  async function handleMbSearch() {
    mbError = '';
    mbResults = [];
    mbSearching = true;
    try {
      mbResults = await searchMusicBrainz(artist, title);
      if (mbResults.length === 0) mbError = 'No results found.';
    } catch {
      mbError = 'Search failed.';
    } finally {
      mbSearching = false;
    }
  }

  function applyMbResult(result: MBRecordingResult) {
    selectedMbid = result.mbid;
    if (result.release) album = result.release;
    if (result.length_ms) duration = msToMmSs(result.length_ms);
    if (result.release_mbid) {
      artUrl = `https://coverartarchive.org/release/${result.release_mbid}/front-250`;
    }
    mbResults = [];
  }
</script>

<div class="rounded-lg border border-theme-accent/20 bg-theme-accent/5 p-3 space-y-3">
  <div class="flex items-center gap-2">
    <Icon name="magic-wand" size="w-4 h-4" class="text-theme-accent" />
    <span class="text-xs font-medium text-theme-accent uppercase tracking-widest flex-1">
      Auto-Fix Metadata
    </span>
    <button
      type="button"
      class="btn btn-xs btn-outline btn-accent font-mono tracking-widest"
      onclick={handleMbSearch}
      disabled={mbSearching}
    >
      {mbSearching ? 'searching…' : 'Search MusicBrainz'}
    </button>
  </div>

  {#if selectedMbid}
    <p class="text-[11px] font-mono text-theme-muted break-all">
      mbid: {selectedMbid}
    </p>
  {/if}

  {#if mbError}
    <p class="text-xs text-error">{mbError}</p>
  {/if}

  {#if mbResults.length > 0}
    <div
      class="rounded border border-base-content/10 divide-y divide-base-content/5 bg-base-100 max-h-64 overflow-y-auto"
    >
      {#each mbResults as result, i (result.mbid)}
        {@const artUrlThumb = result.release_mbid
          ? `https://coverartarchive.org/release/${result.release_mbid}/front-250`
          : null}
        <button
          type="button"
          class="w-full text-left px-2 py-2 hover:bg-base-content/5 transition-colors flex gap-2.5 items-start"
          onclick={() => applyMbResult(result)}
        >
          <div
            class="w-9 h-9 shrink-0 rounded bg-base-200 overflow-hidden flex items-center justify-center mt-0.5"
          >
            {#if artUrlThumb}
              <img
                src={artUrlThumb}
                alt=""
                class="w-full h-full object-cover"
                loading="lazy"
                onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
              />
            {/if}
            <span class="text-[9px] font-mono text-theme-muted/30">{i + 1}</span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-medium text-theme-primary truncate">{result.title}</p>
            <p class="text-[11px] text-theme-muted truncate">{result.artist_credit}</p>
            {#if result.release}
              <p class="text-[11px] text-theme-muted/70 truncate">{result.release}</p>
            {/if}
            {#if result.release_date || result.length_ms}
              <p class="text-[11px] text-theme-muted/40">
                {#if result.release_date}{result.release_date.slice(0, 4)}{/if}{result.length_ms
                  ? `${result.release_date ? ' · ' : ''}${msToMmSs(result.length_ms)}`
                  : ''}
              </p>
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>
