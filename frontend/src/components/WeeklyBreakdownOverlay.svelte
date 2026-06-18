<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { fetchWeeklyBreakdown } from '../services/api';
  import type { WeeklyBreakdownItem } from '../services/api';

  let { monthKey = $bindable(null) }: { monthKey: string | null } = $props();

  let weeks = $state<WeeklyBreakdownItem[]>([]);
  let loading = $state(false);
  let fetchError = $state<string | null>(null);
  let closeButton = $state<HTMLButtonElement | null>(null);

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
      closeButton.focus();
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
</script>

{#if monthKey}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
    transition:fade={{ duration: 200 }}
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  ></div>

  <!-- Panel -->
  <div
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    aria-label="Weekly breakdown for {formatMonthTitle(monthKey)}"
    class="fixed bottom-0 left-0 right-0 z-50 flex flex-col memory-surface rounded-t-2xl shadow-2xl"
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
          Weekly Breakdown
        </div>
        <div class="font-light text-lg text-theme-text mt-0.5">{formatMonthTitle(monthKey)}</div>
      </div>
      <button
        bind:this={closeButton}
        onclick={close}
        class="p-2 rounded-lg transition-colors text-theme-muted hover:text-theme-text"
        style="background-color: transparent;"
        aria-label="Close weekly breakdown"
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
                  <span class="text-theme-accent font-semibold">{week.count.toLocaleString()}</span>
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
                style="height: {ratio * 100}%; background-color: var(--accent); opacity: {opacity};"
              ></div>
              <!-- Label -->
              <span class="text-[10px] font-mono text-theme-muted mt-2 uppercase select-none">
                {monthKey ? weekLabel(week.week, monthKey) : ''}
              </span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}
