<script lang="ts">
  import { inView } from '../../utils/inView';
  import type { StatsInfo } from '../../services/api';
  import StatsGrid from '../dashboard/StatsGrid.svelte';
  import LoadingSpinner from '../layout/LoadingSpinner.svelte';

  let {
    loading,
    stats,
    dimmed,
    onfocusenter,
    onfocusclear,
  }: {
    loading: boolean;
    stats: StatsInfo;
    dimmed: boolean;
    onfocusenter: () => void;
    onfocusclear: () => void;
  } = $props();
</script>

<div
  use:inView={{ once: true }}
  class="pt-30 space-y-8 transition-all duration-(--t-responsive) var(--ease-fluid) reveal-container"
  class:opacity-80={dimmed}
  role="region"
  onmouseenter={onfocusenter}
  onmouseleave={onfocusclear}
  id="telemetry-volumes"
>
  <div class="pb-2 border-b border-theme-border-soft reveal-label">
    <h2 class="editorial-text-h2">03 / Telemetry & Volumes</h2>
  </div>
  <div class="reveal-content">
    {#if loading}
      <LoadingSpinner py="py-10" />
    {:else}
      <StatsGrid {stats} />
    {/if}
  </div>
</div>
