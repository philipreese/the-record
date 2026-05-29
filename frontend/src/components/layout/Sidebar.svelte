<script lang="ts">
  import { themeManager } from '../../services/theme.svelte';
  import Icon from './Icon.svelte';

  // Svelte 5 bindable props
  let { 
    activeTab = $bindable() 
  }: { 
    activeTab: 'dashboard' | 'charts' | 'wrapped' | 'settings';
  } = $props();
</script>

<div class="drawer-side border-r border-base-content/10 bg-base-200">
  <label for="sidebar-drawer" class="drawer-overlay" aria-label="Close sidebar"></label> 
  
  <div class="menu p-4 w-64 min-h-screen text-base-content flex flex-col justify-between">
    
    <!-- Top Section -->
    <div>
      <!-- Logo Branding -->
      <div class="flex items-center gap-3 px-2 py-4 mb-6">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-8 h-8 text-primary">
          <circle cx="12" cy="12" r="10" stroke-width="1.5" class="stroke-current" />
          <circle cx="12" cy="12" r="7" stroke-width="0.5" stroke-dasharray="2 1" class="stroke-current opacity-80" />
          <circle cx="12" cy="12" r="4" stroke-width="0.5" stroke-dasharray="1 1" class="stroke-current opacity-60" />
          <circle cx="12" cy="12" r="2.5" class="fill-secondary stroke-none" />
          <circle cx="12" cy="12" r="0.8" class="fill-base-100 stroke-none" />
        </svg>
        <span class="text-xl font-black tracking-widest uppercase bg-clip-text bg-gradient-to-r from-primary to-secondary text-transparent">
          The Record
        </span>
      </div>

      <!-- Navigation Tabs -->
      <ul class="flex flex-col gap-2">
        <li>
          <button 
            class="flex items-center gap-3 px-4 py-3 rounded-xl font-extrabold text-sm w-full text-left transition-all duration-300"
            class:bg-primary={activeTab === 'dashboard'}
            class:text-primary-content={activeTab === 'dashboard'}
            class:bg-transparent={activeTab !== 'dashboard'}
            onclick={() => activeTab = 'dashboard'}
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
            onclick={() => activeTab = 'charts'}
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
            onclick={() => activeTab = 'wrapped'}
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
            onclick={() => activeTab = 'settings'}
          >
            <span class="flex items-center gap-3">
              <Icon name="settings" />
              Settings
            </span>
            <span class="text-[9px] px-2 py-0.5 rounded bg-primary-content/20 text-current uppercase font-black tracking-wider">
              {themeManager.currentTheme.replace('-', ' ')}
            </span>
          </button>
        </li>
      </ul>
    </div>

  </div>
</div>
