<script lang="ts">
  import { themeManager, themeMetadata } from '../../services/theme.svelte';

  const categories = ['Atmospheric', 'Paper', 'Comfort'] as const;

  function getThemesByCategory(category: (typeof categories)[number]) {
    return themeMetadata.filter((t) => t.category === category);
  }
</script>

<div class="space-y-12">
  {#each categories as category}
    <div class="space-y-6">
      <h3 class="editorial-text-h2 pb-2 border-b">
        {category} Presets
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        {#each getThemesByCategory(category) as theme}
          <button
            class="flex flex-row items-center justify-between gap-6 p-6 lg:p-8 rounded-2xl border text-left transition-all duration-300 w-full relative overflow-hidden group cursor-pointer focus:outline-none"
            style="
              border-color: {themeManager.currentTheme === theme.id
              ? 'var(--accent)'
              : 'color-mix(in srgb, var(--text-primary) 8%, transparent)'};
              background-color: {themeManager.currentTheme === theme.id
              ? 'color-mix(in srgb, var(--accent) 5%, transparent)'
              : 'transparent'};
            "
            onclick={() => themeManager.apply(theme.id)}
          >
            {#if themeManager.currentTheme === theme.id}
              <div
                class="absolute left-0 top-0 bottom-0 w-1.5"
                style="background-color: var(--accent);"
              ></div>
            {/if}

            <div class="flex flex-col gap-3 pl-1 grow pr-4">
              <div class="flex items-center gap-3 flex-wrap">
                <span class="text-base lg:text-lg font-light" style="color: var(--text-primary);">
                  {theme.name}
                </span>
                {#if themeManager.currentTheme === theme.id}
                  <span class="chip-primary"> Active </span>
                {/if}
                <span class="chip-neutral">
                  {theme.isDark ? 'dark' : 'light'}
                </span>
              </div>
              <span
                class="text-sm leading-relaxed font-light max-w-90"
                style="color: var(--text-secondary);"
              >
                {theme.description}
              </span>
            </div>

            <div
              class="flex h-12 w-20 rounded overflow-hidden border shrink-0 shadow-sm"
              style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);"
            >
              <div
                class="w-1/2 h-full"
                style="background-color: {theme.colors.bg}"
                title="Background"
              ></div>
              <div
                class="w-1/2 h-full"
                style="background-color: {theme.id === 'music-mood'
                  ? (themeManager.adjustedAmbientColor ?? '#7899f5')
                  : theme.colors.accent}"
                title="Accent"
              ></div>
            </div>
          </button>
        {/each}
      </div>
    </div>
  {/each}
</div>

<div
  class="memory-surface-nested flex flex-col sm:flex-row justify-between items-center text-xs gap-3"
>
  <div class="flex items-center gap-2.5">
    <div class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--accent);"></div>
    <span style="color: var(--text-secondary);"
      >Tonal overlays automatically shift atmospheric temperature based on your historical music
      trends.</span
    >
  </div>
  <span style="color: var(--text-muted);">All themes verified for contrast comfort.</span>
</div>
