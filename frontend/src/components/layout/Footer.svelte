<script lang="ts">
  import { appCache } from '../../services/store.svelte';
</script>

<footer
  class="mt-20 pb-32 border-t border-theme-border-soft pt-8 flex flex-col md:flex-row justify-between items-center gap-6 text-xs text-theme-muted font-mono select-none"
>
  <div class="flex flex-col items-center md:items-start gap-1">
    <div class="flex items-center gap-2">
      <span class="text-sm font-serif italic lowercase tracking-tight text-theme-secondary"
        >the record</span
      >
      <span class="opacity-30">/</span>
      <span>{appCache.narrative['footer.title_tag'] || 'listening journal'}</span>
    </div>
    <span class="opacity-50 text-[10px]"
      >{appCache.narrative['footer.subtitle'] ||
        'Your personal music history, archived and analyzed.'}</span
    >
  </div>

  <div class="flex items-center gap-6">
    <span class="opacity-40"
      >{appCache.narrative['footer.copyright'] ||
        '© 2026 the record. all plays accounted for.'}</span
    >
  </div>
</footer>
