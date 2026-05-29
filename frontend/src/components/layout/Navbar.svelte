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

<div class="navbar border-b border-theme-border-soft lg:hidden flex justify-between px-4 text-theme-text" style="background-color: var(--bg-sidebar);">
  <div class="flex items-center gap-2">
    <label for="sidebar-drawer" class="btn btn-ghost btn-square drawer-button cursor-pointer">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
      </svg>
    </label>
 
    <!-- Branding: matches the Sidebar logo block exactly -->
    <button class="flex items-center gap-2 cursor-pointer focus:outline-none" onclick={goHome}>
      <Icon name="logo" size="w-6 h-6 text-theme-accent" />
      <span class="text-xl font-serif italic lowercase tracking-tight text-theme-text">
        the record
      </span>
    </button>
  </div>
</div>
