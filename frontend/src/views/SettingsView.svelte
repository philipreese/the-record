<script lang="ts">
  import { themeManager, themeMetadata } from '../services/theme.svelte';

  const categories = ['Atmospheric', 'Paper', 'Comfort'] as const;

  function getThemesByCategory(category: typeof categories[number]) {
    return themeMetadata.filter(t => t.category === category);
  }
</script>

<div class="flex flex-col gap-10 text-base-content p-2 md:p-4">
  
  <!-- Header Card (Spacious with standard padding classes) -->
  <div class="memory-surface p-6 sm:p-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
    <div>
      <h1 class="editorial-text-h1">Interface Settings</h1>
      <p class="editorial-text-muted mt-1.5">Tailor the visual atmosphere of your music memory space.</p>
    </div>
  </div>

  <!-- Main Settings Panel (Ensured padding directly via tailwind to prevent overrides) -->
  <div class="memory-surface p-6 sm:p-8 space-y-10">
    {#each categories as category}
      <div class="space-y-5">
        <h3 class="text-xs font-black uppercase tracking-widest text-base-content/30 border-b border-base-content/5 pb-3">
          {category} Presets
        </h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          {#each getThemesByCategory(category) as theme}
            <button 
              class="flex flex-row items-center justify-between gap-4 p-5 rounded-2xl border text-left transition-all duration-300 w-full relative overflow-hidden group cursor-pointer {themeManager.currentTheme === theme.id ? 'border-primary bg-base-200/50 ring-2 ring-primary/10' : 'border-base-content/10 bg-base-200/20 hover:bg-base-200/40'}"
              onclick={() => themeManager.apply(theme.id)}
            >
              <!-- Selector Active Line -->
              {#if themeManager.currentTheme === theme.id}
                <div class="absolute left-0 top-0 bottom-0 w-1.5 bg-primary"></div>
              {/if}

              <!-- Left Side: Details & Badges -->
              <div class="flex flex-col gap-2.5 pl-1.5 flex-grow pr-4">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-extrabold text-base-content">
                    {theme.name}
                  </span>
                  
                  {#if themeManager.currentTheme === theme.id}
                    <span class="text-[9px] font-black px-2 py-0.5 rounded bg-primary text-primary-content uppercase tracking-wider">
                      Active
                    </span>
                  {/if}
                  
                  <span class="text-[9px] font-bold px-2 py-0.5 rounded bg-base-300 text-base-content/75 border border-base-content/5 uppercase tracking-wider">
                    {theme.isDark ? 'dark' : 'light'}
                  </span>
                </div>
                
                <span class="text-[11px] leading-relaxed text-base-content/60 font-medium max-w-[280px]">
                  {theme.description}
                </span>
              </div>

              <!-- Right Side: Clean Connected Color Swatch Pill -->
              <div class="flex h-10 rounded overflow-hidden border border-base-content/10 flex-shrink-0 shadow-sm">
                <!-- Background Block -->
                <div class="w-10 flex-grow h-full" style="background-color: {theme.colors.bg}" title="Background"></div>
                <!-- Accent Block -->
                <div class="w-10 h-full" style="background-color: {theme.colors.accent}" title="Accent"></div>
              </div>
            </button>
          {/each}
        </div>
      </div>
    {/each}
  </div>

  <!-- Information Footer (Clean & simple) -->
  <div class="memory-surface-nested p-5 flex flex-col sm:flex-row justify-between items-center text-xs text-base-content/40 gap-3">
    <div class="flex items-center gap-2.5">
      <div class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
      <span>Tonal overlays automatically shift atmospheric temperature based on your historical music trends.</span>
    </div>
    <span>All themes verified for contrast comfort.</span>
  </div>

</div>
