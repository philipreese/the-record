<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import Sidebar from './components/layout/Sidebar.svelte';
  import Navbar from './components/layout/Navbar.svelte';
  
  import OverviewView from './views/OverviewView.svelte';
  import ChartsView from './views/ChartsView.svelte';
  import WrappedView from './views/WrappedView.svelte';
  import SettingsView from './views/SettingsView.svelte';

  import { themeManager } from './services/theme.svelte';
  import { appCache } from './services/store.svelte';

  // Navigation state using Svelte 5 state rune
  let activeTab = $state<'dashboard' | 'charts' | 'wrapped' | 'settings'>('dashboard');

  onMount(() => {
    themeManager.init();
  });
</script>

<div class="drawer lg:drawer-open min-h-screen bg-base-100 text-base-content relative z-10 transition-colors duration-300">
  
  <!-- Dynamic Ambient Backing Glow -->
  <div class="fixed inset-0 pointer-events-none -z-10 overflow-hidden opacity-25 blur-[120px] transition-all duration-1000">
    <div class="absolute -top-[20%] -right-[20%] w-[70%] h-[70%] rounded-full bg-[var(--ambient-glow,rgba(0,0,0,0))] transition-all duration-1000"></div>
    <div class="absolute -bottom-[20%] -left-[20%] w-[60%] h-[60%] rounded-full bg-[var(--ambient-glow,rgba(0,0,0,0))] opacity-60 transition-all duration-1000"></div>
  </div>

  <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" />
  
  <!-- Drawer content (Main Screen) -->
  <div class="drawer-content flex flex-col bg-transparent min-h-screen">
    
    <!-- Navbar (Mobile only) -->
    <Navbar bind:activeTab />
 
    <!-- Main Content Area -->
    <main class="flex-grow p-4 lg:p-8 max-w-[1400px] w-full mx-auto relative z-10">
      
      <!-- Views conditional rendering with dissolve-reconfigure transition -->
      {#key activeTab}
        <div in:fade={{ duration: 160, delay: 120 }} out:fade={{ duration: 120 }} class="w-full">
          {#if activeTab === 'dashboard'}
            <OverviewView />
          {:else if activeTab === 'charts'}
            <ChartsView />
          {:else if activeTab === 'wrapped'}
            <WrappedView />
          {:else if activeTab === 'settings'}
            <SettingsView />
          {/if}
        </div>
      {/key}
      
    </main>
  </div> 

  <!-- Sidebar Container -->
  <Sidebar bind:activeTab />
</div>
