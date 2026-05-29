<script lang="ts">
  import { themeManager, themes } from '../../services/theme.svelte';
</script>

<div class="navbar bg-base-200 border-b border-base-content/10 lg:hidden flex justify-between px-4">
  <div class="flex items-center gap-2">
    <label for="sidebar-drawer" class="btn btn-ghost btn-square drawer-button">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
      </svg>
    </label>
    <span class="text-lg font-extrabold tracking-wider text-base-content">The Record</span>
  </div>
  
  <!-- Quick Theme Switcher -->
  <select 
    class="select select-sm select-bordered max-w-xs text-base-content" 
    value={themeManager.currentTheme} 
    onchange={(e) => themeManager.apply(e.currentTarget.value)}
  >
    {#each themes as theme}
      <option value={theme}>{theme}</option>
    {/each}
  </select>
</div>
