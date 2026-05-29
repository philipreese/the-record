<script lang="ts">
  import { themeManager, themeMetadata } from '../../services/theme.svelte';
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

<div class="drawer-side border-r border-base-content/10 bg-base-200">
  <label for="sidebar-drawer" class="drawer-overlay" aria-label="Close sidebar"></label> 
  
  <div class="menu p-4 w-64 min-h-screen text-base-content flex flex-col justify-between">
    
    <!-- Top Section -->
    <div>
      <!-- Logo Branding -->
       <button
          class="button cursor-pointer"
          onclick={() => { activeTab = 'dashboard'; closeSidebar(); }}>
      <div class="flex items-center gap-3 px-2 py-4 mb-6">
        <Icon name="logo" size="w-8 h-8" class="text-primary" />
        <span class="text-xl font-black tracking-widest uppercase bg-clip-text bg-gradient-to-r from-primary to-secondary text-transparent">
          The Record
        </span>
      </div>
      </button>

      <!-- Navigation Tabs -->
      <ul class="flex flex-col gap-2">
        <li>
          <button 
            class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm w-full text-left transition-all duration-300"
            class:bg-primary={activeTab === 'dashboard'}
            class:text-primary-content={activeTab === 'dashboard'}
            class:bg-transparent={activeTab !== 'dashboard'}
            onclick={() => { activeTab = 'dashboard'; closeSidebar(); }}
          >
            <Icon name="home" />
            Overview
          </button>
        </li>
        
        <li>
          <button 
            class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm w-full text-left transition-all duration-300"
            class:bg-primary={activeTab === 'charts'}
            class:text-primary-content={activeTab === 'charts'}
            class:bg-transparent={activeTab !== 'charts'}
            onclick={() => { activeTab = 'charts'; closeSidebar(); }}
          >
            <Icon name="charts" />
            Top Charts
          </button>
        </li>

        <li>
          <button 
            class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm w-full text-left transition-all duration-300"
            class:bg-primary={activeTab === 'wrapped'}
            class:text-primary-content={activeTab === 'wrapped'}
            class:bg-transparent={activeTab !== 'wrapped'}
            onclick={() => { activeTab = 'wrapped'; closeSidebar(); }}
          >
            <Icon name="book" />
            Reviews
          </button>
        </li>
      </ul>
    </div>
    
    <!-- Bottom Settings Tab Section (Styled identically for consistency) -->
    <div class="border-t border-base-content/10 pt-4">
      <ul class="flex flex-col gap-2">
        <li>
          <button 
            class="flex items-center justify-between px-4 py-3 rounded-xl font-extrabold text-sm w-full text-left transition-all duration-300"
            class:bg-primary={activeTab === 'settings'}
            class:text-primary-content={activeTab === 'settings'}
            class:bg-transparent={activeTab !== 'settings'}
            onclick={() => { activeTab = 'settings'; closeSidebar(); }}
          >
            <span class="flex items-center gap-3">
              <Icon name="settings" />
              Settings
            </span>
            <span 
              class="chip-primary transition-all duration-300">
              <span>{themeManager.currentTheme.replace('-', ' ')}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</div>
