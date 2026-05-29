<script lang="ts">
  import { onDestroy } from 'svelte';
  import { triggerSync, getSyncStatus, type SyncStatusInfo } from '../../services/api';

  // Svelte 5 props definition
  let { onSyncComplete }: { onSyncComplete: () => void } = $props();

  let syncing = $state(false);
  let syncStatus = $state<SyncStatusInfo | null>(null);
  let syncError = $state<string | null>(null);
  let forceFullSync = $state(false);
  let syncPollInterval: ReturnType<typeof setInterval> | null = null;

  onDestroy(() => {
    if (syncPollInterval) {
      clearInterval(syncPollInterval);
    }
  });

  async function runSync() {
    syncing = true;
    syncError = null;
    syncStatus = null;

    if (syncPollInterval) {
      clearInterval(syncPollInterval);
      syncPollInterval = null;
    }

    try {
      await triggerSync(forceFullSync);
      
      syncPollInterval = setInterval(async () => {
        try {
          const data = await getSyncStatus();
          syncStatus = data;
          if (data.finished) {
            if (syncPollInterval) clearInterval(syncPollInterval);
            syncPollInterval = null;
            syncing = false;
            const finalCount = data.synced_count;
            if (data.error) {
              syncError = data.error;
            } else {
              onSyncComplete();
            }
          }
        } catch (e) {
          if (syncPollInterval) clearInterval(syncPollInterval);
          syncPollInterval = null;
          syncing = false;
          syncError = e instanceof Error ? e.message : String(e);
        }
      }, 2000);
    } catch (e) {
      syncing = false;
      syncError = e instanceof Error ? e.message : String(e);
    }
  }
</script>

<div class="flex flex-col items-end gap-2 w-full sm:w-auto">
  <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
    <label class="label cursor-pointer gap-2 py-0">
      <span class="label-text text-detail">Force Full Sync</span>
      <input 
        type="checkbox" 
        bind:checked={forceFullSync} 
        class="checkbox checkbox-primary" 
        style={!forceFullSync ? "border: 2px solid var(--border);" : ""}
      />
    </label>
    <button 
      class="btn btn-primary btn-md w-full sm:w-auto shadow-lg" 
      disabled={syncing}
      onclick={runSync}
    >
      {#if syncing}
        <span class="loading loading-spinner loading-xs"></span>
        Syncing ListenBrainz...
      {:else}
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
        Sync Now
      {/if}
    </button>
  </div>
  
  {#if syncing && syncStatus}
    <span class="text-detail font-semibold text-base-content">
      Batch {Math.max(1, syncStatus.batches_fetched)}{syncStatus.mode === 'full' && syncStatus.lb_total ? ' of ' + Math.ceil(syncStatus.lb_total / 1000) : ''} · {syncStatus.synced_count} new
    </span>
  {/if}
  {#if !syncing && syncStatus?.finished && !syncStatus.error}
    <span class="text-xs text-success font-semibold">
      ✓ Synced {syncStatus.synced_count} new play{syncStatus.synced_count === 1 ? '' : 's'}
      ({syncStatus.batches_fetched} batch{syncStatus.batches_fetched === 1 ? '' : 'es'})
    </span>
  {/if}
  {#if syncError}
    <span class="text-xs text-error font-semibold max-w-[250px] text-right">
      {syncError}
    </span>
  {/if}
</div>
