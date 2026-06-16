<script lang="ts">
  import { inView } from '../../utils/inView';
  import { slide } from 'svelte/transition';
  import type { StatsInfo } from '../../services/api';
  import StatsGrid from '../dashboard/StatsGrid.svelte';
  import LoadingSpinner from '../layout/LoadingSpinner.svelte';

  let {
    loading,
    stats,
  }: {
    loading: boolean;
    stats: StatsInfo;
  } = $props();

  let expanded = $state(true);
</script>

<div
  use:inView={{ once: true }}
  class="mt-30 reveal-container"
  role="region"
  id="telemetry-volumes"
>
  <button
    class="w-full pb-2 border-b border-theme-border-soft flex items-center justify-between group cursor-pointer reveal-label"
    onclick={() => (expanded = !expanded)}
  >
    <h2 class="editorial-text-h2">Telemetry & Volumes</h2>
    <span
      class="text-xs font-mono tracking-wider transition-opacity opacity-40 group-hover:opacity-70"
      style="color: var(--text-muted);"
    >
      {expanded ? '− collapse' : '+ expand'}
    </span>
  </button>

  {#if expanded}
    <div class="mt-8 reveal-content" transition:slide={{ duration: 250 }}>
      {#if loading}
        <LoadingSpinner py="py-10" />
      {:else}
        <StatsGrid {stats} />
      {/if}
    </div>
  {/if}
</div>
