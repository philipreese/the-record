<script lang="ts">
  import { themeManager, themes } from '../../services/theme.svelte';

  // Svelte 5 bindable prop
  let { activeTab = $bindable() }: { activeTab: 'dashboard' | 'charts' | 'wrapped' } = $props();
</script>

<div class="drawer-side border-r border-base-content/10">
  <label for="sidebar-drawer" class="drawer-overlay"></label> 
  
  <div class="menu p-4 w-64 min-h-screen bg-base-200 text-base-content flex flex-col justify-between">
    
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
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v4.875h4.875c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
            </svg>
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
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v16.5M21 19.5H3.75M6.75 15v-4.5m3.75 4.5V8.25m3.75 11.25v-8.25m3.75 8.25V6" />
            </svg>
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
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
            Reviews
          </button>
        </li>
      </ul>
    </div>
    
    <!-- Bottom Theme Switcher Section (Desktop only) -->
    <div class="border-t border-base-content/10 pt-4 flex flex-col gap-2">
      <span class="text-[10px] font-bold uppercase opacity-50 px-2 tracking-wider">Select Theme</span>
      <select 
        class="select select-sm select-bordered w-full text-base-content" 
        value={themeManager.currentTheme} 
        onchange={(e) => themeManager.apply(e.currentTarget.value)}
      >
        {#each themes as theme}
          <option value={theme}>
            {theme.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
          </option>
        {/each}
      </select>
    </div>

  </div>
</div>
