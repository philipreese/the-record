<script lang="ts">
  import { untrack } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { portal } from '../../utils/portal';
  import { fetchListen, submitListenCorrection, submitTrackCorrection } from '../../services/api';
  import type { ListenEntry } from '../../services/api';
  import CorrectionForm from './correction/CorrectionForm.svelte';
  import CoverArtSearch from './correction/CoverArtSearch.svelte';
  import MusicBrainzSearch from './correction/MusicBrainzSearch.svelte';
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
  let durationError = $state('');

  // Save state
  let savingListen = $state(false);
  let savingTrack = $state(false);
  let saveError = $state('');

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

  function buildCorrections(): Record<string, string | number | null> | null {
    if (durationError) return null;
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
      <MusicBrainzSearch
        artist={formArtist}
        title={formTitle}
        bind:selectedMbid
        bind:album={formAlbum}
        bind:duration={formDuration}
        bind:artUrl={formArtUrl}
      />

      <CorrectionForm
        {entry}
        bind:artist={formArtist}
        bind:title={formTitle}
        bind:album={formAlbum}
        bind:duration={formDuration}
        bind:durationError
      />

      <CoverArtSearch
        artist={formArtist}
        album={formAlbum}
        mbid={selectedMbid}
        bind:artUrl={formArtUrl}
        originalArtUrl={entry.original_cover_art_url ?? undefined}
      />
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
