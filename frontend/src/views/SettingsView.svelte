<script lang="ts">
  import { themeManager, themeMetadata } from '../services/theme.svelte';
  import { appCache } from '../services/store.svelte';
  import { fetchStats } from '../services/api';
  import Icon from '../components/layout/Icon.svelte';

  let activeSettingsTab = $state<'interface' | 'data'>('interface');

  const categories = ['Atmospheric', 'Paper', 'Comfort'] as const;

  function getThemesByCategory(category: typeof categories[number]) {
    return themeMetadata.filter(t => t.category === category);
  }

  function handleSync(forceFull: boolean) {
    appCache.runSync(forceFull);
  }

  // Auto-fetch database stats if not loaded yet
  $effect(() => {
    if (!appCache.isSyncing && !appCache.stats) {
      fetchStats()
        .then(data => { appCache.stats = data; })
        .catch(err => console.error("Failed to load stats in settings:", err));
    }
  });
</script>

<div class="flex flex-col gap-8 text-base-content">
  
  <!-- Header Card (Spacious and lowercase italic) -->
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 pb-4 border-b">
    <div>
      <h1 class="editorial-text-h1 lowercase italic">settings</h1>
      <p class="editorial-subtitle">Configure system settings and personalize your interface.</p>
    </div>
  </div>

  <!-- Tab Switcher Navigation -->
  <div class="flex border-b border-theme-border-soft gap-6">
    <button 
      class="pb-3 text-sm font-mono tracking-wider uppercase transition-all relative cursor-pointer focus:outline-none"
      style="color: {activeSettingsTab === 'interface' ? 'var(--accent)' : 'var(--text-secondary)'};"
      onclick={() => activeSettingsTab = 'interface'}
    >
      Visual Interface
      {#if activeSettingsTab === 'interface'}
        <div class="absolute bottom-0 left-0 right-0 h-[2px]" style="background-color: var(--accent);"></div>
      {/if}
    </button>
    <button 
      class="pb-3 text-sm font-mono tracking-wider uppercase transition-all relative cursor-pointer focus:outline-none"
      style="color: {activeSettingsTab === 'data' ? 'var(--accent)' : 'var(--text-secondary)'};"
      onclick={() => activeSettingsTab = 'data'}
    >
      Database & Sync
      {#if activeSettingsTab === 'data'}
        <div class="absolute bottom-0 left-0 right-0 h-[2px]" style="background-color: var(--accent);"></div>
      {/if}
    </button>
  </div>

  <!-- Conditional Rendering -->
  {#if activeSettingsTab === 'interface'}
    <!-- Main Settings Panel (Themes Selector) -->
    <div class="space-y-12">
      {#each categories as category}
        <div class="space-y-6">
          <h3 class="editorial-text-h2 pb-2 border-b">
            {category} Presets
          </h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            {#each getThemesByCategory(category) as theme}
              <button 
                class="flex flex-row items-center justify-between gap-6 p-6 lg:p-8 rounded-2xl border text-left transition-all duration-300 w-full relative overflow-hidden group cursor-pointer focus:outline-none"
                style="
                  border-color: {themeManager.currentTheme === theme.id ? 'var(--accent)' : 'color-mix(in srgb, var(--text-primary) 8%, transparent)'};
                  background-color: {themeManager.currentTheme === theme.id ? 'color-mix(in srgb, var(--accent) 5%, transparent)' : 'transparent'};
                "
                onclick={() => themeManager.apply(theme.id)}
              >
                <!-- Selector Active Line -->
                {#if themeManager.currentTheme === theme.id}
                  <div class="absolute left-0 top-0 bottom-0 w-1.5" style="background-color: var(--accent);"></div>
                {/if}

                <!-- Left Side: Details & Badges -->
                <div class="flex flex-col gap-3 pl-1 flex-grow pr-4">
                  <div class="flex items-center gap-3 flex-wrap">
                    <span class="text-base lg:text-lg font-light" style="color: var(--text-primary);">
                      {theme.name}
                    </span>
                    
                    {#if themeManager.currentTheme === theme.id}
                      <span class="chip-primary">
                        Active
                      </span>
                    {/if}
                    
                    <span class="chip-neutral">
                      {theme.isDark ? 'dark' : 'light'}
                    </span>
                  </div>
                  
                  <span class="text-sm leading-relaxed font-light max-w-[360px]" style="color: var(--text-secondary);">
                    {theme.description}
                  </span>
                </div>

                <!-- Right Side: Clean Connected Color Swatch Pill -->
                <div class="flex h-12 w-20 rounded overflow-hidden border shrink-0 shadow-sm" style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);">
                  <!-- Background Block -->
                  <div class="w-1/2 h-full" style="background-color: {theme.colors.bg}" title="Background"></div>
                  <!-- Accent Block -->
                  <div class="w-1/2 h-full" style="background-color: {theme.colors.accent}" title="Accent"></div>
                </div>
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>

    <!-- Information Footer -->
    <div class="memory-surface-nested flex flex-col sm:flex-row justify-between items-center text-xs gap-3">
      <div class="flex items-center gap-2.5">
        <div class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--accent);"></div>
        <span style="color: var(--text-secondary);">Tonal overlays automatically shift atmospheric temperature based on your historical music trends.</span>
      </div>
      <span style="color: var(--text-muted);">All themes verified for contrast comfort.</span>
    </div>

  {:else if activeSettingsTab === 'data'}
    <!-- Data Settings Panel -->
    <div class="space-y-8">
      
      <!-- Database Info Card -->
      <div class="memory-surface-nested">
        <h3 class="text-sm md:text-base font-mono tracking-widest uppercase text-theme-muted mb-6">Database Connection</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-8">
          <div class="flex flex-col gap-1.5">
            <span class="text-sm font-mono text-theme-muted uppercase tracking-wider">Engine Type</span>
            <span class="text-xl font-light text-theme-text">
              {appCache.stats?.db_type || 'Resolving engine...'}
            </span>
          </div>
          <div class="flex flex-col gap-1.5">
            <span class="text-sm font-mono text-theme-muted uppercase tracking-wider">Archived Plays</span>
            <span class="text-3xl font-mono font-normal text-theme-accent">
              {appCache.stats?.total_listens.toLocaleString() || 'Connecting...'}
            </span>
          </div>
        </div>
      </div>

      <!-- Sync Controls Section -->
      <div class="space-y-6">
        <div>
          <h3 class="editorial-text-h2 pb-2 border-b">Archive Synchronization</h3>
          <p class="text-base font-light text-theme-muted mt-2 leading-relaxed">
            Synchronize your local playback records with your ListenBrainz account history. Note: The local database acts as a permanent, cumulative archive—deleting items on ListenBrainz will not delete them here.
          </p>
        </div>

        <div class="flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Incremental Sync Card -->
          <div class="memory-surface-nested flex flex-col justify-between gap-6 bg-transparent">
            <div class="space-y-3">
              <span class="text-sm font-mono tracking-widest text-theme-muted uppercase">Incremental Sync</span>
              <h4 class="text-lg lg:text-xl font-light text-theme-text">Pull New Scrobbles</h4>
              <p class="text-base font-light text-theme-secondary leading-relaxed">
                Scan for recent tracks since your last sync. Safe and fast. Recommended for daily updates.
              </p>
            </div>
            <div>
              <button 
                class="btn btn-primary btn-md shadow-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
                disabled={appCache.isSyncing}
                onclick={() => handleSync(false)}
              >
                {#if appCache.isSyncing && appCache.syncStatus && appCache.syncStatus.mode !== 'full'}
                  <span class="loading loading-spinner loading-xs"></span>
                  Syncing New...
                {:else}
                  <Icon name="sync" size="w-4 h-4" />
                  Sync New Plays
                {/if}
              </button>
            </div>
          </div>

          <!-- Full Reconstruction Sync Card -->
          <div class="memory-surface-nested flex flex-col justify-between gap-6 bg-transparent">
            <div class="space-y-3">
              <span class="text-sm font-mono tracking-widest text-theme-muted uppercase">Deep Sync</span>
              <h4 class="text-lg lg:text-xl font-light text-theme-text">Reconstruct Archive</h4>
              <p class="text-base font-light text-theme-secondary leading-relaxed">
                Re-scan your entire ListenBrainz history from the beginning. Rebuilds database records and backfills any gaps.
              </p>
            </div>
            <div>
              <button 
                class="btn btn-outline btn-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
                disabled={appCache.isSyncing}
                onclick={() => handleSync(true)}
              >
                {#if appCache.isSyncing && appCache.syncStatus && appCache.syncStatus.mode === 'full'}
                  <span class="loading loading-spinner loading-xs"></span>
                  Syncing Entire Archive...
                {:else}
                  <Icon name="download" size="w-4 h-4" />
                  Full Reconstruction
                {/if}
              </button>
            </div>
          </div>
        </div>

          <!-- Sync Progress and Details -->
          {#if appCache.isSyncing && appCache.syncStatus}
            <div class="p-4 rounded-xl border border-theme-border-soft bg-base-200/50 space-y-2 animate-fade-in">
              <div class="flex justify-between text-xs font-mono">
                <span class="text-theme-text font-semibold uppercase">Sync in Progress ({appCache.syncStatus.mode} mode)</span>
                <span class="text-theme-accent font-semibold">
                  Batch {Math.max(1, appCache.syncStatus.batches_fetched)} · {appCache.syncStatus.synced_count} new scrobbles
                </span>
              </div>
              <div class="w-full bg-base-300 h-1.5 rounded-full overflow-hidden">
                <div 
                  class="bg-theme-accent h-full transition-all duration-300 animate-pulse" 
                  style="width: {appCache.syncStatus.lb_total ? Math.min(100, (appCache.syncStatus.local_total / appCache.syncStatus.lb_total) * 100) : 50}%"
                ></div>
              </div>
              <div class="text-[10px] text-theme-muted font-mono flex justify-between">
                <span>Local total: {appCache.syncStatus.local_total.toLocaleString()}</span>
                <span>ListenBrainz total: {appCache.syncStatus.lb_total.toLocaleString()}</span>
              </div>
            </div>
          {/if}

          <!-- Sync Completion Message -->
          {#if !appCache.isSyncing && appCache.syncStatus?.finished && !appCache.syncError}
            <div class="text-xs text-success font-semibold flex items-center gap-1.5 animate-fade-in">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
              </svg>
              Synced {appCache.syncStatus.synced_count} new play{appCache.syncStatus.synced_count === 1 ? '' : 's'} successfully ({appCache.syncStatus.batches_fetched} batch{appCache.syncStatus.batches_fetched === 1 ? '' : 'es'}).
            </div>
          {/if}

          <!-- Sync Error Message -->
          {#if appCache.syncError}
            <div class="text-xs text-error font-semibold flex items-start gap-1.5 max-w-[500px] animate-fade-in">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 shrink-0 mt-0.5">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
              </svg>
              <span>{appCache.syncError}</span>
            </div>
          {/if}

        </div>
      </div>
    </div>
  {/if}
</div>
