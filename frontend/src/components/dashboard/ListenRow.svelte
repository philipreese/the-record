<script lang="ts">
  import type { ListenEntry } from '../../services/api';
  import { sourceLabel, timeOnly, relativeTimeShort, absoluteTime } from '../../utils/listens';

  let {
    entry,
    showAbsoluteTime = false,
  }: {
    entry: ListenEntry;
    showAbsoluteTime?: boolean;
  } = $props();

  const label = $derived(sourceLabel(entry.source));
</script>

<div class="flex items-center gap-4 py-2 px-2 rounded hover:bg-base-200/50 transition-colors group">
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
    <span class="badge badge-ghost badge-xs text-base-content/45 font-mono shrink-0">{label}</span>
  {/if}
</div>
