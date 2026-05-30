<script lang="ts">
  import { themeManager, themeMetadata } from '../../services/theme.svelte';
  import { appCache } from '../../services/store.svelte';
  import Icon from './Icon.svelte';

  // Svelte 5 bindable props
  let { 
    activeTab = $bindable() 
  }: { 
    activeTab: 'dashboard' | 'charts' | 'wrapped' | 'settings';
  } = $props();

  let activeThemeMeta = $derived(themeMetadata.find(t => t.id === themeManager.currentTheme));

  function closeSidebar() {
    // On mobile the sidebar is a DaisyUI drawer controlled by a checkbox input.
    // Programmatically unchecking it dismisses the overlay after navigation.
    const drawerToggle = document.getElementById('sidebar-drawer') as HTMLInputElement | null;
    if (drawerToggle) drawerToggle.checked = false;
  }
</script>

<div class="drawer-side border-r border-theme-border-soft" style="background-color: var(--bg-sidebar);">
  <label for="sidebar-drawer" class="drawer-overlay" aria-label="Close sidebar"></label> 
  
  <div class="p-6 w-64 min-h-screen flex flex-col justify-between text-theme-text">
    
    <!-- Top Section -->
    <div>
      <!-- Logo Branding -->
      <button
        class="cursor-pointer text-left block w-full focus:outline-none"
        onclick={() => { activeTab = 'dashboard'; closeSidebar(); }}
      >
        <div class="flex items-center gap-3.5 py-4 mb-8">
          <Icon name="logo" size="w-8 h-8 text-theme-accent" />
          <span class="text-3xl font-serif italic tracking-tight lowercase text-theme-text">
            the record
          </span>
        </div>
      </button>

      <!-- Navigation Tabs (Journal Index) -->
      <ul class="flex flex-col gap-5 font-sans text-base mt-6">
        <li>
          <button 
            class="flex items-center gap-3.5 py-1.5 px-2 text-base w-full text-left transition-all duration-[var(--t-responsive)] var(--ease-fluid) relative group cursor-pointer focus:outline-none"
            class:text-theme-accent={activeTab === 'dashboard'}
            class:text-theme-secondary={activeTab !== 'dashboard'}
            onclick={() => { activeTab = 'dashboard'; closeSidebar(); }}
          >
            <Icon 
              name="home" 
              size="w-6 h-6" 
              class="transition-transform duration-300 group-hover:scale-105 {activeTab === 'dashboard' ? 'text-theme-accent' : 'text-theme-muted'}"
            />
            <span class="transition-transform duration-300 group-hover:translate-x-1" class:translate-x-1={activeTab === 'dashboard'}>
              Overview
            </span>
          </button>
        </li>
        
        <li>
          <button 
            class="flex items-center gap-3.5 py-1.5 px-2 text-base w-full text-left transition-all duration-[var(--t-responsive)] var(--ease-fluid) relative group cursor-pointer focus:outline-none"
            class:text-theme-accent={activeTab === 'charts'}
            class:text-theme-secondary={activeTab !== 'charts'}
            onclick={() => { activeTab = 'charts'; closeSidebar(); }}
          >
            <Icon 
              name="charts" 
              size="w-6 h-6" 
              class="transition-transform duration-300 group-hover:scale-105 {activeTab === 'charts' ? 'text-theme-accent' : 'text-theme-muted'}"
            />
            <span class="transition-transform duration-300 group-hover:translate-x-1" class:translate-x-1={activeTab === 'charts'}>
              Top Charts
            </span>
          </button>
        </li>

        <li>
          <button 
            class="flex items-center gap-3.5 py-1.5 px-2 text-base w-full text-left transition-all duration-[var(--t-responsive)] var(--ease-fluid) relative group cursor-pointer focus:outline-none"
            class:text-theme-accent={activeTab === 'wrapped'}
            class:text-theme-secondary={activeTab !== 'wrapped'}
            onclick={() => { activeTab = 'wrapped'; closeSidebar(); }}
          >
            <Icon 
              name="book" 
              size="w-6 h-6" 
              class="transition-transform duration-300 group-hover:scale-105 {activeTab === 'wrapped' ? 'text-theme-accent' : 'text-theme-muted'}"
            />
            <span class="transition-transform duration-300 group-hover:translate-x-1" class:translate-x-1={activeTab === 'wrapped'}>
              Reviews
            </span>
          </button>
        </li>

        <li>
          <button 
            class="flex items-center gap-3.5 py-1.5 px-2 text-base w-full text-left transition-all duration-[var(--t-responsive)] var(--ease-fluid) relative group cursor-pointer focus:outline-none"
            class:text-theme-accent={activeTab === 'settings'}
            class:text-theme-secondary={activeTab !== 'settings'}
            onclick={() => { activeTab = 'settings'; closeSidebar(); }}
          >
            <Icon 
              name="settings" 
              size="w-6 h-6" 
              class="transition-transform duration-300 group-hover:scale-105 {activeTab === 'settings' ? 'text-theme-accent' : 'text-theme-muted'}"
            />
            <span class="transition-transform duration-300 group-hover:translate-x-1" class:translate-x-1={activeTab === 'settings'}>
              Settings
            </span>
          </button>
        </li>
      </ul>
    </div>
    
    <!-- Bottom Stable Memory Anchor -->
    <div class="border-t border-theme-border-soft pt-6">
      <div class="space-y-2">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <div class="w-1.5 h-1.5 rounded-full bg-theme-accent animate-pulse"></div>
            <span class="text-xs font-mono tracking-widest uppercase text-theme-muted">
              Memory Surface
            </span>
          </div>
          {#if appCache.isSyncing}
            <span class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-theme-accent opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-theme-accent"></span>
            </span>
          {/if}
        </div>
        {#if appCache.isSyncing}
          <div class="space-y-0.5">
            <div class="text-xs font-light leading-relaxed text-theme-accent animate-pulse">
              Syncing latest plays...
            </div>
            {#if appCache.stats}
              <div class="text-[10px] font-mono text-theme-muted">
                Current count: {appCache.stats.total_listens.toLocaleString()}
              </div>
            {/if}
          </div>
        {:else if appCache.stats}
          <div class="space-y-0.5">
            <div class="text-xs font-light leading-relaxed text-theme-secondary">
              Archived <span class="font-mono">{appCache.stats.total_listens.toLocaleString()}</span> plays
            </div>
            <div class="text-xs font-mono text-theme-muted">
              Active habit: {appCache.stats.avg_per_day}/day
            </div>
          </div>
        {:else}
          <div class="text-xs font-mono text-theme-muted">
            Connecting to archive...
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
