<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { fetchDayListens } from '../services/api';
  import type { ListenEntry } from '../services/api';
  import ListenRow from './dashboard/ListenRow.svelte';
  import { portal } from '../utils/portal';

  let { date = $bindable(null) }: { date: string | null } = $props();

  let tracks = $state<ListenEntry[]>([]);
  let loading = $state(false);
  let fetchError = $state<string | null>(null);
  let closeButton = $state<HTMLButtonElement | null>(null);

  $effect(() => {
    if (date) {
      loadTracks(date);
    } else {
      tracks = [];
      fetchError = null;
    }
  });

  $effect(() => {
    if (date && closeButton) {
      closeButton.focus({ preventScroll: true });
    }
  });

  async function loadTracks(d: string) {
    loading = true;
    fetchError = null;
    try {
      tracks = await fetchDayListens(d);
    } catch {
      fetchError = 'Failed to load tracks.';
    } finally {
      loading = false;
    }
  }

  function close() {
    date = null;
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  function formatOverlayDate(dateStr: string): string {
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
</script>

{#if date}
  <!-- Backdrop — portaled to body so fixed positioning is relative to the viewport,
       not the transformed .memory-surface ancestor -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    use:portal
    class="fixed inset-0 z-9998 bg-black/40 backdrop-blur-sm"
    transition:fade={{ duration: 200 }}
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  ></div>

  <!-- Panel -->
  <div
    use:portal
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    aria-label="Tracks played on {formatOverlayDate(date)}"
    class="fixed bottom-0 left-0 right-0 z-9999 max-h-[80vh] flex flex-col memory-surface rounded-t-2xl shadow-2xl"
    transition:fly={{ y: 400, duration: 300, opacity: 1 }}
    onkeydown={handleKeydown}
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between px-6 py-4 border-b shrink-0"
      style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);"
    >
      <div>
        <div class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">
          Daily Journal
        </div>
        <div class="font-light text-lg text-theme-text mt-0.5">{formatOverlayDate(date)}</div>
      </div>
      <button
        bind:this={closeButton}
        onclick={close}
        class="p-2 rounded-lg transition-colors text-theme-muted hover:text-theme-text"
        style="background-color: transparent;"
        aria-label="Close daily journal"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M3 3l10 10M13 3L3 13"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          />
        </svg>
      </button>
    </div>

    <!-- Track list -->
    <div class="overflow-y-auto grow px-2 py-2">
      {#if loading}
        <div class="flex items-center justify-center py-12 text-theme-muted text-sm font-mono">
          Loading…
        </div>
      {:else if fetchError}
        <div class="flex items-center justify-center py-12 text-sm font-mono opacity-60">
          {fetchError}
        </div>
      {:else if tracks.length === 0}
        <div class="flex items-center justify-center py-12 text-theme-muted text-sm font-mono">
          No tracks recorded this day.
        </div>
      {:else}
        <div class="text-[10px] font-mono text-theme-muted px-4 py-2 uppercase tracking-widest">
          {tracks.length} play{tracks.length === 1 ? '' : 's'}
        </div>
        {#each tracks as entry}
          <ListenRow {entry} showAbsoluteTime={true} showRelativeTime={false} />
        {/each}
      {/if}
    </div>
  </div>
{/if}
