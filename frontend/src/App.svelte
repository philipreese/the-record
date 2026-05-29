<script lang="ts">
  import { onMount } from 'svelte';
  import Sidebar from './components/layout/Sidebar.svelte';
  import Navbar from './components/layout/Navbar.svelte';
  
  import OverviewView from './views/OverviewView.svelte';
  import ChartsView from './views/ChartsView.svelte';
  import WrappedView from './views/WrappedView.svelte';

  import { themeManager } from './services/theme.svelte';

  // Navigation state using Svelte 5 state rune
  let activeTab = $state<'dashboard' | 'charts' | 'wrapped'>('dashboard');

  onMount(() => {
    themeManager.init();
  });
</script>

<div class="drawer lg:drawer-open min-h-screen bg-base-100">
  <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" />
  
  <!-- Drawer content (Main Screen) -->
  <div class="drawer-content flex flex-col bg-base-100 text-base-content min-h-screen">
    
    <!-- Navbar (Mobile only) -->
    <Navbar />

    <!-- Main Content Area -->
    <main class="flex-grow p-4 lg:p-8 max-w-[1400px] w-full mx-auto">
      
      <!-- Views conditional rendering -->
      {#if activeTab === 'dashboard'}
        <OverviewView />
      {:else if activeTab === 'charts'}
        <ChartsView />
      {:else if activeTab === 'wrapped'}
        <WrappedView />
      {/if}
      
    </main>
  </div> 

  <!-- Sidebar Container -->
  <Sidebar bind:activeTab />
</div>
