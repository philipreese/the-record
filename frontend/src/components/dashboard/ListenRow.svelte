<script lang="ts">
  import type { ListenEntry, TrackStatsInfo } from '../../services/api';
  import { sourceLabelFull, timeOnly, relativeTimeShort, absoluteTime } from '../../utils/listens';
  import Icon from '../layout/Icon.svelte';
  import MetadataCorrectionDrawer from './MetadataCorrectionDrawer.svelte';

  let {
    entry,
    showAbsoluteTime = false,
    showRelativeTime = true,
    expanded = false,
    stats = undefined,
    coverArtUrl = undefined,
    onToggle,
    onCorrectionSaved,
  }: {
    entry: ListenEntry;
    showAbsoluteTime?: boolean;
    showRelativeTime?: boolean;
    expanded?: boolean;
    stats?: TrackStatsInfo | null | undefined;
    coverArtUrl?: string | null | undefined;
    onToggle?: () => void;
    onCorrectionSaved?: (updated: ListenEntry) => void;
  } = $props();

  let correctionOpen = $state(false);

  let imgLoaded = $state(false);
  let imgError = $state(false);
  $effect(() => {
    imgLoaded = false;
    imgError = false;
  });

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle?.();
    } else if (e.key === 'Escape' && expanded) {
      onToggle?.();
    }
  }
</script>

<div class="rounded transition-colors" class:bg-base-200={expanded}>
  <div
    role="button"
    tabindex="0"
    aria-expanded={expanded}
    class="flex items-center gap-4 py-2 rounded cursor-pointer hover:bg-base-200/50 transition-colors group"
    class:hover:bg-transparent={expanded}
    onclick={onToggle}
    onkeydown={handleKeydown}
  >
    <div
      class="shrink-0 sm:w-36 flex flex-col sm:flex-row sm:items-center sm:gap-1 ml-2"
      title={showAbsoluteTime ? absoluteTime(entry.unix_ts) : undefined}
    >
      <span
        class="text-xs font-mono tabular-nums text-base-content/55 group-hover:text-base-content/70 transition-colors"
      >
        {timeOnly(entry.unix_ts)}
      </span>
      {#if showRelativeTime && relativeTimeShort(entry.unix_ts)}
        <span class="text-xs font-mono text-base-content/35">
          <span class="hidden sm:inline">· </span>{relativeTimeShort(entry.unix_ts)}
        </span>
      {/if}
    </div>

    <div
      class="w-10 h-10 shrink-0 rounded overflow-hidden bg-base-200 flex items-center justify-center relative"
    >
      <Icon name="music-note" size="w-4 h-4" class="opacity-20" />
      {#if coverArtUrl && !imgError}
        <img
          src={coverArtUrl}
          alt=""
          class="absolute inset-0 w-full h-full object-cover transition-opacity duration-150"
          class:opacity-0={!imgLoaded}
          loading="lazy"
          onload={() => (imgLoaded = true)}
          onerror={() => (imgError = true)}
        />
      {/if}
      <button
        type="button"
        class="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity rounded"
        aria-label="Edit metadata"
        onclick={(e) => {
          e.stopPropagation();
          correctionOpen = true;
        }}
      >
        <Icon name="pencil" size="w-3.5 h-3.5" class="text-white" />
      </button>
    </div>

    <div class="flex-1 min-w-0">
      <span
        class="text-sm font-medium block text-base-content"
        class:truncate={!expanded}
        class:whitespace-normal={expanded}
        class:break-words={expanded}
      >
        {entry.title}
      </span>
      <span
        class="text-xs text-base-content/65 block"
        class:truncate={!expanded}
        class:whitespace-normal={expanded}
        class:break-words={expanded}
      >
        {entry.artist}
      </span>
    </div>

    {#if stats && stats.play_count !== undefined}
      <span
        class="text-xs font-mono text-base-content/35 shrink-0 mr-2"
        title={`${stats.play_count} ${stats.play_count === 1 ? 'play' : 'plays'}`}
      >
        {stats.play_count}
        {stats.play_count === 1 ? 'play' : 'plays'}
      </span>
    {/if}
  </div>

  {#if expanded}
    <div
      class="px-2 pb-2 pt-0.5 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs font-mono text-base-content/50"
    >
      <span>source: <span class="text-base-content/70">{sourceLabelFull(entry.source)}</span></span>
      {#if entry.album}
        <span class="truncate max-w-48"
          >album: <span class="text-base-content/70">{entry.album}</span></span
        >
      {/if}
      {#if stats === undefined}
        <span class="opacity-40">loading…</span>
      {:else if stats === null}
        <span class="opacity-40">—</span>
      {:else}
        <span
          >played <span class="text-base-content/70">{stats.play_count}</span>
          {stats.play_count === 1 ? 'time' : 'times'}</span
        >
        {#if stats.duration_secs}
          <span
            >duration: <span class="text-base-content/70"
              >{Math.floor(stats.duration_secs / 60)}:{String(stats.duration_secs % 60).padStart(
                2,
                '0',
              )}</span
            ></span
          >
        {/if}
      {/if}
      <button
        type="button"
        class="ml-auto text-theme-muted hover:text-theme-text transition-colors"
        onclick={(e) => {
          e.stopPropagation();
          correctionOpen = true;
        }}
      >
        edit
      </button>
    </div>
  {/if}
</div>

{#if correctionOpen}
  <MetadataCorrectionDrawer
    {entry}
    trackPlayCount={entry.track_play_count ?? undefined}
    onClose={() => (correctionOpen = false)}
    onSaved={(updated) => {
      onCorrectionSaved?.(updated);
      correctionOpen = false;
    }}
  />
{/if}
