<script lang="ts">
  import { appCache } from '../../services/store.svelte';

  let { py = 'py-20' }: { py?: string } = $props();
</script>

<div class="flex flex-col justify-center items-center gap-3 {py}">
  <span class="loading loading-spinner loading-md text-primary"></span>
  {#if appCache.isWakingUp}
    <span class="text-xs font-mono tracking-widest uppercase text-theme-muted animate-pulse">
      Waking up the server…
    </span>
  {/if}
</div>
