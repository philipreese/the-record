<script lang="ts">
  import { untrack } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { portal } from '../../utils/portal';
  import { submitListenCorrection, searchMusicBrainz } from '../../services/api';
  import type { ListenEntry, MBRecordingResult } from '../../services/api';
  import Icon from '../layout/Icon.svelte';

  let {
    entry,
    onClose,
    onSaved,
  }: {
    entry: ListenEntry;
    onClose: () => void;
    onSaved: (updated: ListenEntry) => void;
  } = $props();

  // Form fields — pre-filled from entry (untrack: intentionally capturing initial value only)
  let formArtist = $state(untrack(() => entry.artist));
  let formTitle = $state(untrack(() => entry.title));
  let formAlbum = $state(untrack(() => entry.album ?? ''));
  let formDuration = $state(untrack(() => secsToDuration(entry.duration_secs)));
  let formArtUrl = $state(untrack(() => entry.cover_art_url ?? ''));
  let selectedMbid = $state(untrack(() => entry.recording_mbid ?? ''));

  // UI state
  let saving = $state(false);
  let saveError = $state('');
  let mbSearching = $state(false);
  let mbResults = $state<MBRecordingResult[]>([]);
  let mbError = $state('');
  let durationError = $state('');

  function secsToDuration(secs: number | null | undefined): string {
    if (!secs) return '';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function durationToSecs(str: string): number | null {
    const trimmed = str.trim();
    if (!trimmed) return null;
    const match = trimmed.match(/^(\d+):(\d{2})$/);
    if (!match) return null;
    return parseInt(match[1]) * 60 + parseInt(match[2]);
  }

  function validateDuration(val: string): boolean {
    if (!val.trim()) return true;
    if (!val.match(/^\d+:\d{2}$/)) {
      durationError = 'Format must be m:ss (e.g. 3:42)';
      return false;
    }
    durationError = '';
    return true;
  }

  async function handleMbSearch() {
    mbError = '';
    mbResults = [];
    mbSearching = true;
    try {
      mbResults = await searchMusicBrainz(formArtist, formTitle);
      if (mbResults.length === 0) mbError = 'No results found.';
    } catch {
      mbError = 'Search failed.';
    } finally {
      mbSearching = false;
    }
  }

  function applyMbResult(result: MBRecordingResult) {
    selectedMbid = result.mbid;
    if (result.release) formAlbum = result.release;
    mbResults = [];
  }

  async function handleSave() {
    if (!validateDuration(formDuration)) return;
    saveError = '';
    saving = true;

    const correction: Record<string, string | number | null> = {};
    if (formArtist !== entry.artist) correction.artist = formArtist;
    if (formTitle !== entry.title) correction.title = formTitle;
    if ((formAlbum || null) !== (entry.album ?? null)) correction.album = formAlbum || null;

    const newDurSecs = durationToSecs(formDuration);
    if (newDurSecs !== (entry.duration_secs ?? null)) correction.duration_secs = newDurSecs;

    if (selectedMbid !== (entry.recording_mbid ?? '')) {
      correction.recording_mbid = selectedMbid || null;
    }

    const newArt = formArtUrl.trim() || null;
    const currentArt = entry.cover_art_url ?? null;
    if (newArt !== currentArt) correction.cover_art_url = newArt;

    if (Object.keys(correction).length === 0) {
      onClose();
      return;
    }

    try {
      const updated = await submitListenCorrection(entry.id, correction);
      onSaved(updated);
    } catch (err) {
      saveError = err instanceof Error ? err.message : 'Save failed.';
    } finally {
      saving = false;
    }
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }
</script>

<div
  use:portal
  role="presentation"
  class="fixed inset-0 z-9998 bg-black/40 backdrop-blur-sm"
  transition:fade={{ duration: 180 }}
  onclick={handleBackdropClick}
  onkeydown={handleKeydown}
></div>

<div use:portal class="fixed inset-y-0 right-0 z-9999 flex items-stretch pointer-events-none">
  <div
    role="dialog"
    aria-modal="true"
    aria-label="Edit metadata"
    tabindex="-1"
    class="pointer-events-auto w-full max-w-sm flex flex-col memory-surface shadow-2xl"
    transition:fly={{ x: 360, duration: 260 }}
    onkeydown={handleKeydown}
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between px-5 py-4 border-b shrink-0"
      style="border-color: color-mix(in srgb, var(--text-primary) 10%, transparent);"
    >
      <div>
        <p class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">edit</p>
        <p class="text-sm font-medium text-theme-primary truncate max-w-52">{entry.title}</p>
      </div>
      <button
        type="button"
        class="btn-nav-icon text-base-content/50 hover:text-base-content transition-colors"
        onclick={onClose}
        aria-label="Close"
      >
        <Icon name="close" size="w-5 h-5" />
      </button>
    </div>

    <!-- Form body -->
    <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
      <!-- Artist -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">Artist</span>
        <input
          type="text"
          class="input input-sm w-full bg-base-200 border-base-content/10"
          bind:value={formArtist}
        />
      </label>

      <!-- Title -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">Title</span>
        <input
          type="text"
          class="input input-sm w-full bg-base-200 border-base-content/10"
          bind:value={formTitle}
        />
      </label>

      <!-- Album -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">Album</span>
        <input
          type="text"
          class="input input-sm w-full bg-base-200 border-base-content/10"
          bind:value={formAlbum}
        />
      </label>

      <!-- Duration -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase"
          >Duration</span
        >
        <input
          type="text"
          class="input input-sm w-32 bg-base-200 border-base-content/10"
          class:border-error={!!durationError}
          placeholder="3:42"
          bind:value={formDuration}
          oninput={() => validateDuration(formDuration)}
        />
        {#if durationError}
          <p class="text-xs text-error">{durationError}</p>
        {/if}
      </label>

      <!-- Cover art URL -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase"
          >Cover art URL</span
        >
        <input
          type="url"
          class="input input-sm w-full bg-base-200 border-base-content/10 font-mono text-xs"
          placeholder="https://..."
          bind:value={formArtUrl}
        />
        {#if formArtUrl}
          <img
            src={formArtUrl}
            alt="preview"
            class="w-10 h-10 rounded object-cover mt-1"
            onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
          />
        {/if}
      </label>

      <!-- MusicBrainz search -->
      <div class="space-y-2">
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase flex-1"
            >MusicBrainz</span
          >
          <button
            type="button"
            class="btn btn-xs btn-ghost border border-base-content/10 font-mono text-[10px] tracking-widest"
            onclick={handleMbSearch}
            disabled={mbSearching}
          >
            {mbSearching ? 'searching…' : 'search recordings'}
          </button>
        </div>

        {#if selectedMbid}
          <p class="text-[10px] font-mono text-theme-muted break-all">
            mbid: {selectedMbid}
          </p>
        {/if}

        {#if mbError}
          <p class="text-xs text-base-content/50">{mbError}</p>
        {/if}

        {#if mbResults.length > 0}
          <div class="space-y-1 memory-surface-nested p-2">
            {#each mbResults as result (result.mbid)}
              <button
                type="button"
                class="w-full text-left px-2 py-1.5 rounded hover:bg-base-content/5 transition-colors"
                onclick={() => applyMbResult(result)}
              >
                <p class="text-xs font-medium text-theme-primary truncate">{result.title}</p>
                <p class="text-[10px] text-theme-muted truncate">{result.artist_credit}</p>
                {#if result.release}
                  <p class="text-[10px] text-theme-muted/70 truncate">
                    {result.release}{result.release_date
                      ? ` · ${result.release_date.slice(0, 4)}`
                      : ''}
                  </p>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Footer -->
    <div
      class="px-5 py-4 border-t shrink-0 space-y-2"
      style="border-color: color-mix(in srgb, var(--text-primary) 10%, transparent);"
    >
      {#if saveError}
        <p class="text-xs text-error">{saveError}</p>
      {/if}
      <div class="flex gap-2 justify-end">
        <button type="button" class="btn btn-sm btn-ghost" onclick={onClose}>cancel</button>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          onclick={handleSave}
          disabled={saving || !!durationError}
        >
          {#if saving}
            <span class="loading loading-spinner loading-xs"></span>
          {:else}
            save
          {/if}
        </button>
      </div>
    </div>
  </div>
</div>
