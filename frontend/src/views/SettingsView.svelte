<script lang="ts">
  import { appCache } from '../services/store.svelte';
  import { fetchStats } from '../services/api';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import ThemeSelector from '../components/settings/ThemeSelector.svelte';
  import DataSyncPanel from '../components/settings/DataSyncPanel.svelte';

  let activeSettingsTab = $state<'interface' | 'data'>('interface');

  // Auto-fetch database stats if not loaded yet
  $effect(() => {
    if (!appCache.isSyncing && !appCache.stats) {
      fetchStats().then((data) => {
        appCache.stats = data;
      });
    }
  });
</script>

<PageHeader title="settings" subtitle="Configure system settings and personalize your interface." />

<div class="flex flex-col gap-8 text-base-content">
  <!-- Tab Switcher Navigation -->
  <div class="sticky-sub-header flex mt-6 gap-6">
    <button
      class="pb-3 text-sm font-mono tracking-wider uppercase transition-all relative cursor-pointer focus:outline-none"
      style="color: {activeSettingsTab === 'interface'
        ? 'var(--accent)'
        : 'var(--text-secondary)'};"
      onclick={() => (activeSettingsTab = 'interface')}
    >
      Visual Interface
      {#if activeSettingsTab === 'interface'}
        <div
          class="absolute bottom-0 left-0 right-0 h-0.5"
          style="background-color: var(--accent);"
        ></div>
      {/if}
    </button>
    <button
      class="pb-3 text-sm font-mono tracking-wider uppercase transition-all relative cursor-pointer focus:outline-none"
      style="color: {activeSettingsTab === 'data' ? 'var(--accent)' : 'var(--text-secondary)'};"
      onclick={() => (activeSettingsTab = 'data')}
    >
      Database & Sync
      {#if activeSettingsTab === 'data'}
        <div
          class="absolute bottom-0 left-0 right-0 h-0.5"
          style="background-color: var(--accent);"
        ></div>
      {/if}
    </button>
  </div>

  {#if activeSettingsTab === 'interface'}
    <ThemeSelector />
  {:else if activeSettingsTab === 'data'}
    <DataSyncPanel />
  {/if}
</div>
