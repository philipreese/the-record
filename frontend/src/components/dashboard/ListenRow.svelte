<script lang="ts">
  import type { ListenEntry, TrackStatsInfo } from '../../services/api';
  import {
    sourceLabel,
    sourceLabelFull,
    timeOnly,
    relativeTimeShort,
    absoluteTime,
  } from '../../utils/listens';

  let {
    entry,
    showAbsoluteTime = false,
    expanded = false,
    stats = undefined,
    onToggle,
  }: {
    entry: ListenEntry;
    showAbsoluteTime?: boolean;
    expanded?: boolean;
    stats?: TrackStatsInfo | null | undefined;
    onToggle?: () => void;
  } = $props();

  const label = $derived(sourceLabel(entry.source));

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
    class="flex items-center gap-4 py-2 px-2 rounded cursor-pointer hover:bg-base-200/50 transition-colors group"
    class:hover:bg-transparent={expanded}
    onclick={onToggle}
    onkeydown={handleKeydown}
  >
    <div
      class="w-36 shrink-0 text-right"
      title={showAbsoluteTime ? absoluteTime(entry.unix_ts) : undefined}
    >
      <span
        class="text-xs font-mono tabular-nums text-base-content/55 group-hover:text-base-content/70 transition-colors"
      >
        {timeOnly(entry.unix_ts)}
        {#if relativeTimeShort(entry.unix_ts)}
          <span class="text-base-content/35"> · {relativeTimeShort(entry.unix_ts)}</span>
        {/if}
      </span>
    </div>

    <div class="flex-1 min-w-0">
      <span class="text-sm font-medium truncate block text-base-content">{entry.title}</span>
      <span class="text-xs text-base-content/65 truncate block">{entry.artist}</span>
    </div>

    {#if label}
      <span class="badge badge-ghost badge-xs text-base-content/45 font-mono shrink-0">{label}</span
      >
    {/if}
  </div>

  {#if expanded}
    <div class="px-2 pb-2 pt-0.5 flex gap-6 text-xs font-mono text-base-content/50">
      <span>source: <span class="text-base-content/70">{sourceLabelFull(entry.source)}</span></span>
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
    </div>
  {/if}
</div>
