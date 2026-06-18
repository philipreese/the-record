<script lang="ts">
  import { scale, fade } from 'svelte/transition';
  import { fetchWeeklyBreakdown } from '../services/api';
  import type { WeeklyBreakdownItem } from '../services/api';
  import { portal } from '../utils/portal';
  import Icon from './layout/Icon.svelte';

  let { monthKey = $bindable(null) }: { monthKey: string | null } = $props();

  let weeks = $state<WeeklyBreakdownItem[]>([]);
  let loading = $state(false);
  let fetchError = $state<string | null>(null);
  let closeButton = $state<HTMLButtonElement | null>(null);

  $effect(() => {
    if (monthKey) {
      document.body.classList.add('overflow-hidden');
      document.documentElement.classList.add('overflow-hidden');
      return () => {
        document.body.classList.remove('overflow-hidden');
        document.documentElement.classList.remove('overflow-hidden');
      };
    }
  });

  $effect(() => {
    if (monthKey) {
      loadWeeks(monthKey);
    } else {
      weeks = [];
      fetchError = null;
    }
  });

  $effect(() => {
    if (monthKey && closeButton) {
      closeButton.focus({ preventScroll: true });
    }
  });

  async function loadWeeks(key: string) {
    loading = true;
    fetchError = null;
    const [year, month] = key.split('-').map(Number);
    try {
      weeks = await fetchWeeklyBreakdown(year, month);
    } catch {
      fetchError = 'Failed to load weekly data.';
    } finally {
      loading = false;
    }
  }

  // Rest of script functions unchanged
  function close() {
    monthKey = null;
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  function formatMonthTitle(key: string): string {
    const [year, month] = key.split('-').map(Number);
    return new Date(year, month - 1).toLocaleDateString(undefined, {
      month: 'long',
      year: 'numeric',
    });
  }

  function weekLabel(week: number, key: string): string {
    const [year, month] = key.split('-').map(Number);
    const startDay = (week - 1) * 7 + 1;
    const endDay = Math.min(week * 7, new Date(year, month, 0).getDate());
    return `${startDay}–${endDay}`;
  }

  let maxCount = $derived(Math.max(...weeks.map((w) => w.count), 1));
  let totalMonthPlays = $derived(weeks.reduce((sum, w) => sum + w.count, 0));
</script>

{#if monthKey}
  <!-- Backdrop — portaled to body so fixed positioning is relative to the viewport -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    use:portal
    class="fixed inset-0 z-9998 bg-black/40 backdrop-blur-sm"
    transition:fade={{ duration: 200 }}
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  ></div>

  <!-- Dialog wrapper to position centered on desktop and bottom on mobile -->
  <div
    use:portal
    class="fixed inset-0 z-9999 flex items-end justify-center pointer-events-none md:items-center p-0"
  >
    <!-- Panel -->
    <div
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      aria-label="Weekly breakdown for {formatMonthTitle(monthKey)}"
      class="pointer-events-auto w-full md:max-w-2xl flex flex-col memory-surface p-0! rounded-t-2xl md:rounded-2xl shadow-2xl"
      transition:scale={{ start: 0.93, duration: 220 }}
      onkeydown={handleKeydown}
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between px-6 py-4 border-b shrink-0"
        style="border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);"
      >
        <div>
          <div class="text-[10px] font-mono text-theme-muted tracking-widest uppercase">
            Weekly Breakdown
          </div>
          <div class="font-light text-lg text-theme-text mt-0.5">{formatMonthTitle(monthKey)}</div>
          {#if weeks.length > 0 && !loading}
            <div class="text-xs font-mono text-theme-muted mt-1">
              {totalMonthPlays.toLocaleString()} total play{totalMonthPlays === 1 ? '' : 's'}
            </div>
          {/if}
        </div>
        <button
          bind:this={closeButton}
          onclick={close}
          class="p-2 rounded-lg transition-colors text-theme-muted hover:text-theme-text cursor-pointer"
          style="background-color: transparent;"
          aria-label="Close weekly breakdown"
        >
          <Icon name="close" size="w-4 h-4" />
        </button>
      </div>

      <!-- Chart area -->
      <div class="px-6 py-6">
        {#if loading}
          <div class="flex items-center justify-center py-8 text-theme-muted text-sm font-mono">
            Loading…
          </div>
        {:else if fetchError}
          <div class="flex items-center justify-center py-8 text-sm font-mono opacity-60">
            {fetchError}
          </div>
        {:else if weeks.length === 0}
          <div class="flex items-center justify-center py-8 text-theme-muted text-sm font-mono">
            No data for this month.
          </div>
        {:else}
          <div class="flex items-end gap-3 h-40">
            {#each weeks as week}
              {@const ratio = week.count / maxCount}
              {@const opacity = 0.18 + ratio * 0.82}
              <div class="grow h-full flex flex-col justify-end items-center group relative">
                <!-- Tooltip -->
                <div
                  class="absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center z-20 pointer-events-none"
                >
                  <div
                    class="border px-2.5 py-1 rounded text-[12px] font-mono text-theme-text shadow-xl whitespace-nowrap"
                    style="
                      background-color: var(--bg-base);
                      border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);
                    "
                  >
                    <span class="text-theme-accent font-semibold"
                      >{week.count.toLocaleString()}</span
                    >
                    plays
                  </div>
                  <div
                    class="w-1.5 h-1.5 border-r border-b rotate-45 -mt-1"
                    style="
                      background-color: var(--bg-base);
                      border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);
                    "
                  ></div>
                </div>
                <!-- Bar -->
                <div
                  class="w-full rounded-t-sm transition-all duration-(--t-responsive) var(--ease-fluid) group-hover:brightness-110"
                  style="height: {ratio *
                    100}%; background-color: var(--accent); opacity: {opacity};"
                ></div>
                <!-- Label -->
                <span class="text-[10px] font-mono text-theme-muted mt-2 uppercase select-none">
                  {monthKey ? weekLabel(week.week, monthKey) : ''}
                </span>
                <!-- Plays count -->
                <span
                  class="text-[10px] font-mono text-theme-accent font-semibold mt-0.5 select-none"
                >
                  {week.count} play{week.count === 1 ? '' : 's'}
                </span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
