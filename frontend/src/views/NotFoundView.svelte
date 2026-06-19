<script lang="ts">
  import { router } from '../services/router.svelte';
  import { appCache } from '../services/store.svelte';
  import NarrativeText from '../components/layout/NarrativeText.svelte';
</script>

<div class="flex flex-col items-start justify-center min-h-[60vh] gap-8 py-16">
  <div class="space-y-4">
    <p class="text-[10px] font-mono tracking-widest uppercase text-theme-muted">404 / not found</p>
    <h1
      class="text-3xl md:text-4xl xl:text-5xl font-serif font-light leading-relaxed italic text-theme-secondary"
    >
      <NarrativeText
        text={appCache.narrative.rich['not_found.headline'] || 'The [[needle]] skipped.'}
        accentClass="font-sans font-normal not-italic text-theme-accent"
      />
    </h1>
  </div>

  <p class="text-sm font-mono text-theme-muted max-w-md leading-relaxed">
    {appCache.narrative.plain['not_found.body'] ||
      "This track doesn't exist in the archive. Maybe it was never recorded, or maybe it's just lost to time."}
  </p>

  <button
    class="font-mono text-sm tracking-wider text-theme-accent hover:translate-x-1 transition-transform duration-200 cursor-pointer focus:outline-none"
    onclick={() => router.navigate('/dashboard')}
  >
    ← back to the archive
  </button>
</div>
