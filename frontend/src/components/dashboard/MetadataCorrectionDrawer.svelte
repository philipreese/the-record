<script lang="ts">
  import { untrack } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { portal } from '../../utils/portal';
  import {
    submitListenCorrection,
    submitTrackCorrection,
    revertListenCorrection,
    revertTrackCorrection,
    searchMusicBrainz,
  } from '../../services/api';
  import type { ListenEntry, MBRecordingResult } from '../../services/api';
  import Icon from '../layout/Icon.svelte';

  let {
    entry,
    forcedScope = undefined,
    trackPlayCount = undefined,
    onClose,
    onSaved,
  }: {
    entry: ListenEntry;
    forcedScope?: 'track';
    trackPlayCount?: number;
    onClose: () => void;
    onSaved: (updated: ListenEntry) => void;
  } = $props();

  // Form fields — pre-filled from entry (untrack: capturing initial value only)
  let formArtist = $state(untrack(() => entry.artist));
  let formTitle = $state(untrack(() => entry.title));
  let formAlbum = $state(untrack(() => entry.album ?? ''));
  let formDuration = $state(untrack(() => secsToDuration(entry.duration_secs)));
  let formArtUrl = $state(untrack(() => entry.cover_art_url ?? ''));
  let selectedMbid = $state(untrack(() => entry.recording_mbid ?? ''));

  // UI state
  let savingListen = $state(false);
  let savingTrack = $state(false);
  let reverting = $state(false);
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

  function msToMmSs(ms: number | null | undefined): string {
    if (!ms) return '';
    const s = Math.round(ms / 1000);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }

  function applyMbResult(result: MBRecordingResult) {
    selectedMbid = result.mbid;
    if (result.release) formAlbum = result.release;
    if (result.length_ms) formDuration = msToMmSs(result.length_ms);
    if (result.release_mbid) {
      formArtUrl = `https://coverartarchive.org/release/${result.release_mbid}/front-250`;
    }
    mbResults = [];
  }

  function buildCorrections(): Record<string, string | number | null> | null {
    if (!validateDuration(formDuration)) return null;
    const c: Record<string, string | number | null> = {};
    if (formArtist !== entry.artist) c.artist = formArtist;
    if (formTitle !== entry.title) c.title = formTitle;
    // Pass "" as-is — COALESCE("", x) returns "" which clears the field in the view
    if (formAlbum !== (entry.album ?? '')) c.album = formAlbum;
    const newDurSecs = durationToSecs(formDuration);
    if (newDurSecs !== (entry.duration_secs ?? null)) c.duration_secs = newDurSecs;
    if (selectedMbid !== (entry.recording_mbid ?? '')) c.recording_mbid = selectedMbid || null;
    const newArt = formArtUrl.trim() || null;
    if (newArt !== (entry.cover_art_url ?? null)) c.cover_art_url = newArt;
    return c;
  }

  async function handleSaveListen() {
    const correction = buildCorrections();
    if (correction === null) return;
    if (Object.keys(correction).length === 0) {
      onClose();
      return;
    }
    saveError = '';
    savingListen = true;
    try {
      const updated = await submitListenCorrection(entry.id, correction);
      onSaved(updated);
    } catch (err) {
      saveError = err instanceof Error ? err.message : 'Save failed.';
    } finally {
      savingListen = false;
    }
  }

  async function handleSaveTrack() {
    const correction = buildCorrections();
    if (correction === null) return;
    if (Object.keys(correction).length === 0) {
      onClose();
      return;
    }
    saveError = '';
    savingTrack = true;
    try {
      const updated = await submitTrackCorrection({
        corrected_artist: entry.artist,
        corrected_title: entry.title,
        track_id: entry.track_id,
        corrections: correction,
      });
      onSaved(updated);
    } catch (err) {
      saveError = err instanceof Error ? err.message : 'Save failed.';
    } finally {
      savingTrack = false;
    }
  }

  async function handleRevertListen() {
    saveError = '';
    reverting = true;
    try {
      const updated = await revertListenCorrection(entry.id);
      onSaved(updated);
    } catch (err) {
      saveError = err instanceof Error ? err.message : 'Revert failed.';
    } finally {
      reverting = false;
    }
  }

  async function handleRevertTrack() {
    saveError = '';
    reverting = true;
    try {
      const updated = await revertTrackCorrection({
        corrected_artist: entry.artist,
        corrected_title: entry.title,
        track_id: entry.track_id,
      });
      onSaved(updated);
    } catch (err) {
      saveError = err instanceof Error ? err.message : 'Revert failed.';
    } finally {
      reverting = false;
    }
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }

  let resolvedTrackCount = $derived(trackPlayCount ?? entry.track_play_count ?? null);
  let trackCountLabel = $derived(
    resolvedTrackCount != null ? resolvedTrackCount.toLocaleString() : '?',
  );
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
    <div class="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      <!-- Existing corrections / revert section -->
      {#if entry.has_listen_correction || entry.has_track_correction}
        <div
          class="rounded border border-base-content/10 p-3 space-y-1.5"
          style="background: color-mix(in srgb, var(--base-content) 3%, transparent);"
        >
          <p class="text-[10px] font-mono text-theme-muted tracking-widest uppercase mb-2">
            existing corrections
          </p>
          {#if entry.has_listen_correction && forcedScope !== 'track'}
            <button
              type="button"
              class="btn btn-xs btn-ghost w-full justify-start text-left font-mono text-[10px] tracking-widest"
              onclick={handleRevertListen}
              disabled={reverting}
            >
              {reverting ? '…' : 'Revert this listen → original'}
            </button>
          {/if}
          {#if entry.has_track_correction}
            <button
              type="button"
              class="btn btn-xs btn-ghost w-full justify-start text-left font-mono text-[10px] tracking-widest text-warning"
              onclick={handleRevertTrack}
              disabled={reverting}
            >
              {reverting ? '…' : `Revert all ${trackCountLabel} listens → original`}
            </button>
          {/if}
        </div>
      {/if}

      <!-- Artist -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">Artist</span>
        <input
          type="text"
          class="input input-sm w-full bg-base-200 border-base-content/10"
          bind:value={formArtist}
        />
        {#if entry.original_artist != null && entry.original_artist !== entry.artist}
          <p class="text-[10px] font-mono text-theme-muted/50">
            original: {entry.original_artist}
          </p>
        {/if}
      </label>

      <!-- Title -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">Title</span>
        <input
          type="text"
          class="input input-sm w-full bg-base-200 border-base-content/10"
          bind:value={formTitle}
        />
        {#if entry.original_title != null && entry.original_title !== entry.title}
          <p class="text-[10px] font-mono text-theme-muted/50">
            original: {entry.original_title}
          </p>
        {/if}
      </label>

      <!-- Album -->
      <label class="block space-y-1">
        <span class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">Album</span>
        <input
          type="text"
          class="input input-sm w-full bg-base-200 border-base-content/10"
          bind:value={formAlbum}
        />
        {#if entry.original_album != null && entry.original_album !== entry.album}
          <p class="text-[10px] font-mono text-theme-muted/50">
            original: {entry.original_album}
          </p>
        {/if}
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
          <div class="space-y-0.5 memory-surface-nested p-1.5">
            {#each mbResults as result, i (result.mbid)}
              <button
                type="button"
                class="w-full text-left px-2 py-2 rounded hover:bg-base-content/5 transition-colors"
                onclick={() => applyMbResult(result)}
              >
                <div class="flex items-baseline gap-1.5">
                  <span class="text-[9px] font-mono text-theme-muted/40 shrink-0">{i + 1}</span>
                  <p class="text-xs font-medium text-theme-primary truncate">{result.title}</p>
                </div>
                <p class="text-[10px] text-theme-muted truncate pl-4">{result.artist_credit}</p>
                <p class="text-[10px] text-theme-muted/60 truncate pl-4">
                  {#if result.release}{result.release}{/if}{result.release_date
                    ? ` · ${result.release_date.slice(0, 4)}`
                    : ''}{result.length_ms ? ` · ${msToMmSs(result.length_ms)}` : ''}
                </p>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Footer -->
    <div
      class="px-4 py-3 border-t shrink-0 space-y-2"
      style="border-color: color-mix(in srgb, var(--text-primary) 10%, transparent);"
    >
      {#if saveError}
        <p class="text-xs text-error">{saveError}</p>
      {/if}
      <!--
        flex-col-reverse on mobile: DOM order is cancel → listen → track,
        visual order top-to-bottom is track (most important) → listen → cancel.
        sm:flex-row: left-to-right cancel | listen | track.
      -->
      <div class="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end">
        <button type="button" class="btn btn-sm btn-ghost" onclick={onClose}>cancel</button>
        {#if forcedScope !== 'track'}
          <button
            type="button"
            class="btn btn-sm btn-primary"
            onclick={handleSaveListen}
            disabled={savingListen || savingTrack || reverting || !!durationError}
          >
            {#if savingListen}
              <span class="loading loading-spinner loading-xs"></span>
            {:else}
              Save for this listen
            {/if}
          </button>
        {/if}
        <button
          type="button"
          class="btn btn-sm btn-warning"
          onclick={handleSaveTrack}
          disabled={savingListen || savingTrack || reverting || !!durationError}
        >
          {#if savingTrack}
            <span class="loading loading-spinner loading-xs"></span>
          {:else}
            Save for all {trackCountLabel} listens
          {/if}
        </button>
      </div>
    </div>
  </div>
</div>
