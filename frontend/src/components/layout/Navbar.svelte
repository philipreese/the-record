<script lang="ts">
  import { fade } from 'svelte/transition';
  import { router } from '../../services/router.svelte';
  import Icon from './Icon.svelte';

  let scrollY = $state(0);

  let activePageLabel = $derived.by(() => {
    switch (router.route.type) {
      case 'dashboard':
        return 'overview';
      case 'charts':
        return 'charts';
      case 'wrapped':
        return 'reviews';
      case 'settings':
        return 'settings';
      case 'recent':
        return 'journal';
      default:
        return '';
    }
  });
</script>

<svelte:window bind:scrollY />

<div
  class="navbar sticky top-0 left-0 right-0 z-40 border-b border-theme-border-soft lg:hidden flex justify-between px-4 text-theme-text"
  style="background-color: color-mix(in srgb, var(--bg-sidebar) 88%, transparent); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);"
>
  <div class="flex items-center gap-2">
    <label for="sidebar-drawer" class="btn btn-ghost btn-square drawer-button cursor-pointer">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        class="inline-block w-5 h-5 stroke-current"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M4 6h16M4 12h16M4 18h16"
        ></path>
      </svg>
    </label>

    <!-- Branding: matches the Sidebar logo block exactly -->
    <div class="flex items-center gap-2">
      <Icon name="logo" size="w-6 h-6 text-theme-accent" />
      <span
        class="text-xl font-serif italic lowercase tracking-tight text-theme-text flex items-baseline gap-2"
      >
        the record
        {#if scrollY > 80}
          <span transition:fade={{ duration: 150 }} class="text-theme-accent select-none">|</span>
          <span
            transition:fade={{ duration: 150 }}
            class="text-md font-mono text-theme-muted font-normal lowercase select-none"
          >
            {activePageLabel}
          </span>
        {/if}
      </span>
    </div>
  </div>
</div>
