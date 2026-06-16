<script lang="ts">
  import { inView } from '../../utils/inView';
  import { timeOnly, sourceLabel } from '../../utils/listens';
  import type { OnThisDayGroup } from '../../services/api';

  let {
    groups,
    dimmed,
    onfocusenter,
    onfocusclear,
  }: {
    groups: OnThisDayGroup[];
    dimmed: boolean;
    onfocusenter: () => void;
    onfocusclear: () => void;
  } = $props();

  const currentYear = new Date().getFullYear();

  const todayLabel = $derived(() => {
    const now = new Date();
    return now.toLocaleDateString('en-US', { month: 'long', day: 'numeric' });
  });

  function yearsAgo(year: number): string {
    const n = currentYear - year;
    return n === 1 ? '1 year ago' : `${n} years ago`;
  }
</script>

<div
  use:inView={{ once: true }}
  class="space-y-8 transition-all duration-(--t-responsive) var(--ease-fluid) reveal-container"
  class:opacity-80={dimmed}
  role="region"
  onmouseenter={onfocusenter}
  onmouseleave={onfocusclear}
  id="on-this-day"
>
  <div class="pb-2 border-b border-theme-border-soft reveal-label">
    <h2 class="editorial-text-h2">04 / On This Day &mdash; {todayLabel()}</h2>
  </div>

  <div class="reveal-content space-y-8">
    {#each groups as group (group.year)}
      <div class="space-y-1">
        <p class="text-xs font-mono text-theme-muted uppercase tracking-widest">
          {group.year} &bull; {yearsAgo(group.year)}
        </p>
        <div class="space-y-0">
          {#each group.listens as entry (entry.id)}
            <div
              class="flex items-center gap-3 py-2 px-2 rounded hover:bg-base-200/40 transition-colors"
            >
              <span class="text-xs font-mono text-theme-muted w-12 shrink-0 tabular-nums">
                {timeOnly(entry.unix_ts)}
              </span>
              <span class="text-sm text-theme-secondary font-medium truncate">
                {entry.artist}
              </span>
              <span class="text-theme-muted/50 text-xs shrink-0">&mdash;</span>
              <span class="text-sm text-theme-secondary/70 truncate">
                {entry.title}
              </span>
              <span
                class="ml-auto text-[10px] font-mono text-theme-muted/60 uppercase tracking-wider shrink-0"
              >
                {sourceLabel(entry.source)}
              </span>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </div>
</div>
