<script lang="ts">
  import type { ListenEntry } from '../../../services/api';
  import Icon from '../../layout/Icon.svelte';

  let {
    entry,
    artist = $bindable(),
    title = $bindable(),
    album = $bindable(),
    duration = $bindable(),
    durationError = $bindable(),
  }: {
    entry: ListenEntry;
    artist: string;
    title: string;
    album: string;
    duration: string;
    durationError: string;
  } = $props();

  function secsToDuration(secs: number | null | undefined): string {
    if (!secs) return '';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function validateDuration(val: string): void {
    if (!val.trim() || val.match(/^\d+:\d{2}$/)) {
      durationError = '';
    } else {
      durationError = 'Format must be m:ss (e.g. 3:42)';
    }
  }
</script>

<div class="space-y-3">
  <h3
    class="text-[11px] font-mono text-theme-muted tracking-widest uppercase border-b border-base-content/10 pb-1"
  >
    Track Details
  </h3>

  <!-- Artist -->
  <label class="block space-y-1">
    <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Artist</span>
    <input
      type="text"
      class="input input-sm w-full bg-base-200 border-base-content/10"
      class:border-warning={entry.original_artist != null && entry.original_artist !== artist}
      bind:value={artist}
    />
    {#if entry.original_artist != null && entry.original_artist !== artist}
      <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
        <span class="truncate flex-1">original: {entry.original_artist}</span>
        <button
          type="button"
          class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
          onclick={() => (artist = entry.original_artist ?? '')}
        >
          <Icon name="undo" size="w-3 h-3" /> revert
        </button>
      </div>
    {/if}
  </label>

  <!-- Title -->
  <label class="block space-y-1">
    <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Title</span>
    <input
      type="text"
      class="input input-sm w-full bg-base-200 border-base-content/10"
      class:border-warning={entry.original_title != null && entry.original_title !== title}
      bind:value={title}
    />
    {#if entry.original_title != null && entry.original_title !== title}
      <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
        <span class="truncate flex-1">original: {entry.original_title}</span>
        <button
          type="button"
          class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
          onclick={() => (title = entry.original_title ?? '')}
        >
          <Icon name="undo" size="w-3 h-3" /> revert
        </button>
      </div>
    {/if}
  </label>

  <!-- Album -->
  <label class="block space-y-1">
    <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Album</span>
    <input
      type="text"
      class="input input-sm w-full bg-base-200 border-base-content/10"
      class:border-warning={entry.original_album != null && entry.original_album !== album}
      bind:value={album}
    />
    {#if entry.original_album != null && entry.original_album !== album}
      <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
        <span class="truncate flex-1">original: {entry.original_album}</span>
        <button
          type="button"
          class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
          onclick={() => (album = entry.original_album ?? '')}
        >
          <Icon name="undo" size="w-3 h-3" /> revert
        </button>
      </div>
    {/if}
  </label>

  <!-- Duration -->
  <label class="block space-y-1">
    <span class="text-[11px] font-mono text-theme-muted tracking-widest uppercase">Duration</span>
    <input
      type="text"
      class="input input-sm w-32 bg-base-200 border-base-content/10 block"
      class:border-error={!!durationError}
      class:border-warning={entry.original_duration_secs != null &&
        duration !== secsToDuration(entry.original_duration_secs) &&
        !durationError}
      placeholder="3:42"
      bind:value={duration}
      oninput={() => validateDuration(duration)}
    />
    {#if durationError}
      <p class="text-xs text-error mt-1">{durationError}</p>
    {/if}
    {#if entry.original_duration_secs != null && duration !== secsToDuration(entry.original_duration_secs)}
      <div class="flex items-center gap-1.5 text-[10px] text-warning mt-1">
        <span class="truncate flex-1">original: {secsToDuration(entry.original_duration_secs)}</span
        >
        <button
          type="button"
          class="btn btn-xs btn-ghost p-0 min-h-0 h-auto font-mono text-[10px] tracking-widest flex items-center gap-1 shrink-0"
          onclick={() => {
            duration = secsToDuration(entry.original_duration_secs);
            validateDuration(duration);
          }}
        >
          <Icon name="undo" size="w-3 h-3" /> revert
        </button>
      </div>
    {/if}
  </label>
</div>
