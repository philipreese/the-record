<script lang="ts">
  import { themeManager, themes } from '../../services/theme.svelte';
  import Icon from './Icon.svelte';

  let { activeTab = $bindable() }: { activeTab: 'dashboard' | 'charts' | 'wrapped' | 'settings' } = $props();

  function goHome() {
    activeTab = 'dashboard';
    // Close the mobile drawer after navigating
    const drawerToggle = document.getElementById('sidebar-drawer') as HTMLInputElement | null;
    if (drawerToggle) drawerToggle.checked = false;
  }
</script>

<div class="navbar bg-base-200 border-b border-base-content/10 lg:hidden flex justify-between px-4">
  <div class="flex items-center gap-2">
    <label for="sidebar-drawer" class="btn btn-ghost btn-square drawer-button">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
      </svg>
    </label>

    <!-- Branding: matches the Sidebar logo block exactly -->
      <button class="flex items-center gap-2 cursor-pointer" onclick={goHome}>
        <Icon name="logo" size="w-6 h-6" class="text-primary" />
        <span class="text-lg font-black tracking-widest uppercase bg-clip-text bg-gradient-to-r from-primary to-secondary text-transparent">
          The Record
        </span>
      </button>
  </div>
</div>
