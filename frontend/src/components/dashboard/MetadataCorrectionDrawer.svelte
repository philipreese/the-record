<script lang="ts">
  import { untrack } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { portal } from '../../utils/portal';
  import {
    fetchListen,
    submitListenCorrection,
    submitTrackCorrection,
    searchMusicBrainz,
    searchCoverArt,
  } from '../../services/api';
  import type { ListenEntry, MBRecordingResult, CoverArtResult } from '../../services/api';
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
  let saveError = $state('');
  let mbSearching = $state(false);
  let mbResults = $state<MBRecordingResult[]>([]);
  let mbError = $state('');
  let artSearching = $state(false);
  let artResults = $state<CoverArtResult[]>([]);
  let artError = $state('');
  let artLoadFailures = $state(0);
  let durationError = $state('');

  // Lock body scroll when drawer is open
  $effect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  });

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

  async function handleArtSearch() {
    artError = '';
    artResults = [];
    artLoadFailures = 0;
    artSearching = true;
    try {
      artResults = await searchCoverArt(formArtist, formAlbum, selectedMbid || undefined);
      if (artResults.length === 0) artError = 'No releases found.';
    } catch {
      artError = 'Search failed.';
    } finally {
      artSearching = false;
    }
  }

  function applyArtResult(result: CoverArtResult) {
    formArtUrl = `https://coverartarchive.org/release/${result.release_mbid}/front-250`;
    artResults = [];
  }

  function buildCorrections(): Record<string, string | number | null> | null {
    if (!validateDuration(formDuration)) return null;
    const c: Record<string, string | number | null> = {};
    if (formArtist !== entry.artist) c.artist = formArtist;
    if (formTitle !== entry.title) c.title = formTitle;
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

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }

  let fetchedTrackCount = $state<number | null>(null);
  $effect(() => {
    if (trackPlayCount == null && entry.track_play_count == null) {
      fetchListen(entry.id)
        .then((full) => {
          fetchedTrackCount = full.track_play_count ?? null;
        })
        .catch(() => {});
    }
  });

  let resolvedTrackCount = $derived(trackPlayCount ?? entry.track_play_count ?? fetchedTrackCount);
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
    class="pointer-events-auto w-full sm:w-md flex flex-col memory-surface p-3! rounded-none! shadow-2xl"
    transition:fly={{ x: 480, duration: 260 }}
    onkeydown={handleKeydown}
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between px-3 py-2.5 border-b shrink-0"
      style="border-color: color-mix(in srgb, var(--text-primary) 10%, transparent);"
    >
      <div>
        <p class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">edit</p>
        <p class="text-sm font-medium text-theme-primary truncate max-w-82">{entry.title}</p>
      </div>
      <button
        type="button"
        class="btn-nav-icon text-base-content/50 hover:text-base-content cursor-pointer transition-colors"
        onclick={onClose}
        aria-label="Close"
      >
        <Icon name="close" size="w-5 h-5" />
      </button>
    </div>

    <!-- Form body -->
    <div class="flex-1 overflow-y-auto px-3 py-4 space-y-6">
      <!-- MusicBrainz search (Magic Auto-Fix) -->
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
              {@const artUrl = result.release_mbid
                ? `https://coverartarchive.org/release/${result.release_mbid}/front-250`
                : null}
              <button
                type="button"
                class="w-full text-left px-2 py-2 hover:bg-base-content/5 transition-colors flex gap-2.5 items-start"
                onclick={() => applyMbResult(result)}
              >
                <!-- Thumbnail -->
                <div
                  class="w-9 h-9 shrink-0 rounded bg-base-200 overflow-hidden flex items-center justify-center mt-0.5"
                >
                  {#if artUrl}
                    <img
                      src={artUrl}
                      alt=""
                      class="w-full h-full object-cover"
                      loading="lazy"
                      onerror={(e) =>
                        ((e.currentTarget as HTMLImageElement).style.display = 'none')}
                    />
                  {/if}
                  <span class="text-[9px] font-mono text-theme-muted/30">{i + 1}</span>
                </div>
                <!-- Text -->
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-medium text-theme-primary truncate">{result.title}</p>
                  <p class="text-[11px] text-theme-muted truncate">{result.artist_credit}</p>
                  {#if result.release}
                    <p class="text-[11px] text-theme-muted/70 truncate">{result.release}</p>
                  {/if}
                  {#if result.release_date || result.length_ms}
                    <p class="text-[11px] text-theme-muted/40">
                      {#if result.release_date}{result.release_date.slice(
                          0,
                          4,
                        )}{/if}{result.length_ms
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

      <!-- Track Details Section -->
      <div class="space-y-3">
        <h3
          class="text-[11px] font-mono text-theme-muted tracking-widest uppercase border-b border-base-content/10 pb-1"
        >
          Track Details
        </h3>

        <!-- Artist -->
        <label class="block space-y-1">
          <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase"
            >Artist</span
          >
          <input
            type="text"
            class="input input-sm w-full bg-base-200 border-base-content/10"
            class:border-warning={entry.original_artist != null &&
              entry.original_artist !== formArtist}
            bind:value={formArtist}
          />
          {#if entry.original_artist != null && entry.original_artist !== formArtist}
            <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
              <span class="truncate flex-1">original: {entry.original_artist}</span>
              <button
                type="button"
                class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
                onclick={() => (formArtist = entry.original_artist ?? '')}
              >
                <Icon name="undo" size="w-3 h-3" /> revert
              </button>
            </div>
          {/if}
        </label>

        <!-- Title -->
        <label class="block space-y-1">
          <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Title</span
          >
          <input
            type="text"
            class="input input-sm w-full bg-base-200 border-base-content/10"
            class:border-warning={entry.original_title != null &&
              entry.original_title !== formTitle}
            bind:value={formTitle}
          />
          {#if entry.original_title != null && entry.original_title !== formTitle}
            <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
              <span class="truncate flex-1">original: {entry.original_title}</span>
              <button
                type="button"
                class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
                onclick={() => (formTitle = entry.original_title ?? '')}
              >
                <Icon name="undo" size="w-3 h-3" /> revert
              </button>
            </div>
          {/if}
        </label>

        <!-- Album -->
        <label class="block space-y-1">
          <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Album</span
          >
          <input
            type="text"
            class="input input-sm w-full bg-base-200 border-base-content/10"
            class:border-warning={entry.original_album != null &&
              entry.original_album !== formAlbum}
            bind:value={formAlbum}
          />
          {#if entry.original_album != null && entry.original_album !== formAlbum}
            <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
              <span class="truncate flex-1">original: {entry.original_album}</span>
              <button
                type="button"
                class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
                onclick={() => (formAlbum = entry.original_album ?? '')}
              >
                <Icon name="undo" size="w-3 h-3" /> revert
              </button>
            </div>
          {/if}
        </label>

        <!-- Duration -->
        <label class="block space-y-1">
          <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase"
            >Duration</span
          >
          <input
            type="text"
            class="input input-sm w-32 bg-base-200 border-base-content/10 block"
            class:border-error={!!durationError}
            class:border-warning={entry.original_duration_secs != null &&
              formDuration !== secsToDuration(entry.original_duration_secs) &&
              !durationError}
            placeholder="3:42"
            bind:value={formDuration}
            oninput={() => validateDuration(formDuration)}
          />
          {#if durationError}
            <p class="text-xs text-error mt-1">{durationError}</p>
          {/if}
          {#if entry.original_duration_secs != null && formDuration !== secsToDuration(entry.original_duration_secs)}
            <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
              <span class="truncate flex-1"
                >original: {secsToDuration(entry.original_duration_secs)}</span
              >
              <button
                type="button"
                class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
                onclick={() => {
                  formDuration = secsToDuration(entry.original_duration_secs);
                  validateDuration(formDuration);
                }}
              >
                <Icon name="undo" size="w-3 h-3" /> revert
              </button>
            </div>
          {/if}
        </label>
      </div>

      <!-- Cover Art Section -->
      <div class="space-y-3">
        <h3
          class="text-[11px] font-mono text-theme-muted tracking-widest uppercase border-b border-base-content/10 pb-1"
        >
          Cover Art
        </h3>

        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase"
              >Image URL</span
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
            bind:value={formArtUrl}
          />

          {#if formArtUrl}
            <img
              src={formArtUrl}
              alt="preview"
              class="w-16 h-16 rounded object-cover mt-2 shadow"
              onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
            />
          {/if}

          {#if entry.original_cover_art_url && entry.original_cover_art_url !== formArtUrl}
            <div class="flex items-center gap-3 mt-2 p-2 rounded-lg bg-base-200">
              <img
                src={entry.original_cover_art_url}
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
                  onclick={() => (formArtUrl = entry.original_cover_art_url!)}
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
              <p class="text-xs text-theme-muted mt-2 italic">
                No artwork found for these releases.
              </p>
            {:else}
              <div class="grid grid-cols-4 gap-1.5 pt-2">
                {#each artResults as result (result.release_mbid)}
                  {@const caaUrl = `https://coverartarchive.org/release/${result.release_mbid}/front-250`}
                  <button
                    type="button"
                    class="relative aspect-square rounded overflow-hidden bg-base-200 hover:ring-2 hover:ring-theme-accent transition-all group"
                    title="{result.release_title}{result.date
                      ? ` (${result.date.slice(0, 4)})`
                      : ''}"
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
    </div>

    <!-- Footer -->
    <div
      class="px-3 py-2.5 border-t shrink-0 space-y-2"
      style="border-color: color-mix(in srgb, var(--text-primary) 10%, transparent);"
    >
      {#if saveError}
        <p class="text-xs text-error">{saveError}</p>
      {/if}
      <!--
        flex-col-reverse: DOM order cancel→listen→track renders visually as track→listen→cancel.
        Drawer is fixed max-w-sm at all breakpoints so flex-row would truncate button text.
      -->
      <div class="flex flex-col-reverse gap-2">
        <button type="button" class="btn btn-sm btn-ghost" onclick={onClose}>cancel</button>
        {#if forcedScope !== 'track'}
          <button
            type="button"
            class="btn btn-sm btn-primary"
            onclick={handleSaveListen}
            disabled={savingListen || savingTrack || !!durationError}
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
          disabled={savingListen || savingTrack || !!durationError}
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
