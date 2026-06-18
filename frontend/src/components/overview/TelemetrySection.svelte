<script lang="ts">
  import { inView } from '../../utils/inView';
  import { slide } from 'svelte/transition';
  import type { StatsInfo } from '../../services/api';
  import StatsGrid from '../dashboard/StatsGrid.svelte';
  import LoadingSpinner from '../layout/LoadingSpinner.svelte';
  import { appCache } from '../../services/store.svelte';

  let {
    loading,
    stats,
    sectionNumber = '05',
  }: {
    loading: boolean;
    stats: StatsInfo;
    sectionNumber?: string;
  } = $props();
</script>

<div
  use:inView={{ once: true }}
  class="mt-30 reveal-container"
  role="region"
  id="telemetry-volumes"
>
  <h2 class="editorial-text-h2">
    {sectionNumber} / {appCache.narrative['overview.insight.telemetry_volumes_header'] ||
      'Telemetry & Volumes'}
  </h2>
  <div class="mt-8 reveal-content" transition:slide={{ duration: 250 }}>
    {#if loading}
      <LoadingSpinner py="py-10" />
    {:else}
      <div class="pb-30">
        <StatsGrid {stats} />
      </div>
    {/if}
  </div>
</div>
