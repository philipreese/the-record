<script lang="ts">
  import { appCache } from '../services/store.svelte';
  import { themeManager } from '../services/theme.svelte';
  import { getDominantColor } from '../utils/dominantColor';

  let { compact = false }: { compact?: boolean } = $props();

  let imgLoaded = $state(false);
  let prevCoverUrl = $state<string | null>(null);

  $effect(() => {
    if (compact) return;
    const url = appCache.playingNow?.cover_art_url ?? null;
    if (url !== prevCoverUrl) {
      imgLoaded = false;
      prevCoverUrl = url;
    }
    if (!url) {
      themeManager.setAmbientColor(null);
      return;
    }
    getDominantColor(url).then((color) => {
      themeManager.setAmbientColor(color);
    });
  });

  const info = $derived(appCache.playingNow);
  const isPlaying = $derived(info?.is_playing ?? false);
  const artist = $derived(isPlaying ? info?.artist : info?.last_played?.artist);
  const title = $derived(isPlaying ? info?.title : info?.last_played?.title);
  const release = $derived(isPlaying ? (info?.release ?? null) : null);
  const coverUrl = $derived(isPlaying ? (info?.cover_art_url ?? null) : null);
  const hasContent = $derived(!!artist && !!title);
</script>

{#if hasContent}
  {#if compact}
    <!-- Compact sidebar version: dot + artist/title only -->
    <div class="border-t border-theme-border-soft pt-4 mt-2 mb-4">
      <div class="flex items-center gap-2 mb-1.5">
        {#if isPlaying}
          <span class="flex h-1.5 w-1.5 relative shrink-0">
            <span
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-theme-accent opacity-60"
            ></span>
            <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-theme-accent"></span>
          </span>
        {:else}
          <span class="inline-flex rounded-full h-1.5 w-1.5 bg-theme-muted shrink-0"></span>
        {/if}
        <span class="text-xs font-mono tracking-widest uppercase text-theme-muted">
          {isPlaying ? 'Now Playing' : 'Last Played'}
        </span>
      </div>
      <div class="flex items-center gap-2.5 pl-3.5">
        {#if isPlaying && coverUrl}
          <img
            src={coverUrl}
            alt="Album art"
            crossorigin="anonymous"
            class="w-8 h-8 rounded shrink-0 object-cover opacity-90"
          />
        {/if}
        <div class="min-w-0">
          <div class="text-xs font-medium text-theme-text truncate leading-snug">{title}</div>
          <div class="text-xs text-theme-muted truncate">{artist}</div>
        </div>
      </div>
    </div>
  {:else}
    <!-- Full overview version: album art, glow, release -->
    <div class="space-y-4">
      <div class="pb-2 border-b border-theme-border-soft reveal-label">
        <div class="flex items-center gap-2">
          {#if isPlaying}
            <span class="flex h-2 w-2 relative shrink-0">
              <span
                class="animate-ping absolute inline-flex h-full w-full rounded-full bg-theme-accent opacity-60"
              ></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-theme-accent"></span>
            </span>
          {:else}
            <span class="inline-flex rounded-full h-2 w-2 bg-theme-muted shrink-0"></span>
          {/if}
          <h2 class="editorial-text-h2">
            {isPlaying ? 'Now Playing' : 'Last Played'}
          </h2>
        </div>
      </div>

      <div class="reveal-content flex items-start gap-4">
        {#if coverUrl}
          <div
            class="w-16 h-16 shrink-0 rounded overflow-hidden border border-theme-border-soft"
            style={appCache.playingNow?.cover_art_url
              ? `box-shadow: 0 0 20px color-mix(in srgb, var(--accent) 30%, transparent)`
              : ''}
          >
            <img
              src={coverUrl}
              alt="Album art"
              crossorigin="anonymous"
              class="w-full h-full object-cover transition-opacity duration-300"
              class:opacity-0={!imgLoaded}
              class:opacity-100={imgLoaded}
              onload={() => (imgLoaded = true)}
              onerror={() => (imgLoaded = false)}
            />
          </div>
        {:else if isPlaying}
          <div
            class="w-16 h-16 shrink-0 rounded bg-base-200 border border-theme-border-soft flex items-center justify-center"
          >
            <span class="text-theme-muted text-2xl">♫</span>
          </div>
        {/if}

        <div class="flex-1 min-w-0 pt-1">
          <div class="text-base font-medium text-theme-text truncate leading-tight">{title}</div>
          <div class="text-sm text-theme-secondary truncate mt-0.5">{artist}</div>
          {#if release}
            <div class="text-xs text-theme-muted truncate mt-1 italic">{release}</div>
          {/if}
        </div>
      </div>
    </div>
  {/if}
{/if}
