<script lang="ts">
  import { slide } from 'svelte/transition';
  import type { MonthlyTrendInfo } from '../../services/api';

  let {
    value = $bindable(),
    monthlyTrends = [],
    class: className = '',
  }: {
    value: string;
    monthlyTrends: MonthlyTrendInfo[];
    class?: string;
  } = $props();

  let isPopoverOpen = $state(false);
  let viewingDaysFor = $state('');
  let containerRef = $state<HTMLElement | null>(null);

  const MONTH_NAMES = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  // format trends grouped by year
  let groupedTrends = $derived.by(() => {
    const yearsMap = new Map<number, { monthStr: string; monthNum: number; count: number }[]>();
    for (const t of monthlyTrends) {
      const [yearStr, monthStr] = t.month.split('-');
      const year = parseInt(yearStr);
      const monthNum = parseInt(monthStr);
      if (!yearsMap.has(year)) {
        yearsMap.set(year, []);
      }
      yearsMap.get(year)!.push({
        monthStr: t.month,
        monthNum,
        count: t.count,
      });
    }

    const result = Array.from(yearsMap.entries()).map(([year, months]) => {
      months.sort((a, b) => a.monthNum - b.monthNum);
      return { year, months };
    });
    result.sort((a, b) => b.year - a.year);
    return result;
  });

  let trendsLookup = $derived(new Map(monthlyTrends.map((t) => [t.month, t.count])));

  function formatSelectedDateLabel(dateStr: string): string {
    if (!dateStr) return 'Jump to Date';
    const parts = dateStr.split('-');
    if (parts.length === 2) {
      const year = parseInt(parts[0]);
      const month = parseInt(parts[1]);
      const date = new Date(year, month - 1, 1);
      return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
    } else if (parts.length === 3) {
      const year = parseInt(parts[0]);
      const month = parseInt(parts[1]);
      const day = parseInt(parts[2]);
      const date = new Date(year, month - 1, day);
      return date.toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    }
    return 'Jump to Date';
  }

  function getMonthKey(year: number, monthIndex: number): string {
    return `${year}-${String(monthIndex + 1).padStart(2, '0')}`;
  }

  function hasData(year: number, monthIndex: number): boolean {
    const key = getMonthKey(year, monthIndex);
    return (trendsLookup.get(key) ?? 0) > 0;
  }

  function getDaysInMonth(year: number, monthNum: number): number {
    return new Date(year, monthNum, 0).getDate();
  }

  function getMonthName(monthStr: string): string {
    if (!monthStr) return '';
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1, 1);
    return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }

  let viewingDaysList = $derived.by(() => {
    if (!viewingDaysFor) return [];
    const [yearStr, monthStr] = viewingDaysFor.split('-');
    const year = parseInt(yearStr);
    const month = parseInt(monthStr);
    const numDays = getDaysInMonth(year, month);
    return Array.from({ length: numDays }, (_, i) => i + 1);
  });

  let firstDayOfWeek = $derived.by(() => {
    if (!viewingDaysFor) return 0;
    const [yearStr, monthStr] = viewingDaysFor.split('-');
    const year = parseInt(yearStr);
    const month = parseInt(monthStr);
    return new Date(year, month - 1, 1).getDay();
  });

  function handleDocumentClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target || !document.body.contains(target)) {
      return;
    }
    if (isPopoverOpen && containerRef && !containerRef.contains(target)) {
      isPopoverOpen = false;
    }
  }

  $effect(() => {
    document.addEventListener('click', handleDocumentClick);
    return () => document.removeEventListener('click', handleDocumentClick);
  });

  $effect(() => {
    if (!isPopoverOpen) {
      viewingDaysFor = '';
    }
  });
</script>

<div
  class="relative inline-block text-left date-popover-container {className}"
  bind:this={containerRef}
>
  <button
    type="button"
    class="select-premium relative w-full flex items-center focus:outline-none cursor-pointer select-none font-mono text-sm"
    onclick={() => (isPopoverOpen = !isPopoverOpen)}
  >
    <span class="pl-1 pr-6 font-mono text-left truncate">
      {value ? formatSelectedDateLabel(value) : 'Jump to Date'}
    </span>
    <span
      class="pr-1 text-xs opacity-60 absolute right-1 transition-transform duration-200 {isPopoverOpen
        ? 'rotate-180'
        : 'rotate-0'}"
    >
      ↓
    </span>
  </button>

  {#if isPopoverOpen}
    <div
      transition:slide={{ duration: 180 }}
      class="datepicker-popover absolute mt-2 left-0 lg:left-auto lg:right-0"
    >
      {#if viewingDaysFor}
        <!-- Day picker grid view -->
        <div>
          <div class="flex items-center gap-2 mb-4">
            <button
              type="button"
              class="btn-nav-text text-xs tracking-wider"
              onclick={() => (viewingDaysFor = '')}
            >
              ← Back
            </button>
            <span class="text-xs font-mono font-bold grow text-right truncate">
              {getMonthName(viewingDaysFor)}
            </span>
          </div>

          <button
            type="button"
            class="datepicker-btn w-full mb-3 py-2"
            class:active={value === viewingDaysFor}
            onclick={() => {
              value = viewingDaysFor;
              isPopoverOpen = false;
            }}
          >
            Jump to End of Month
          </button>

          <!-- Weekday Initials Header -->
          <div
            class="grid grid-cols-7 gap-1 mb-2 text-center text-[9px] font-mono text-theme-muted uppercase tracking-wider"
          >
            {#each ['S', 'M', 'T', 'W', 'T', 'F', 'S'] as d}
              <div>{d}</div>
            {/each}
          </div>

          <div class="grid grid-cols-7 gap-1">
            {#each Array.from({ length: firstDayOfWeek }) as _}
              <div></div>
            {/each}
            {#each viewingDaysList as day}
              {@const key = `${viewingDaysFor}-${String(day).padStart(2, '0')}`}
              {@const active = value === key}
              <button
                type="button"
                class="datepicker-btn datepicker-day-btn"
                class:active
                onclick={() => {
                  value = key;
                  isPopoverOpen = false;
                }}
              >
                {day}
              </button>
            {/each}
          </div>
        </div>
      {:else}
        <!-- Year/Month picker main view -->
        <div class="space-y-6">
          {#each groupedTrends as yearGroup}
            <div>
              <div
                class="text-caps text-[10px] text-theme-muted uppercase tracking-wider mb-2 border-b border-theme-border-soft pb-1"
              >
                {yearGroup.year}
              </div>
              <div class="grid grid-cols-4 gap-1.5">
                {#each MONTH_NAMES as name, idx}
                  {@const key = getMonthKey(yearGroup.year, idx)}
                  {@const available = hasData(yearGroup.year, idx)}
                  {@const active = value === key || value.startsWith(key + '-')}
                  <button
                    type="button"
                    disabled={!available}
                    class="datepicker-btn"
                    class:active
                    onclick={() => {
                      viewingDaysFor = key;
                    }}
                  >
                    {name}
                  </button>
                {/each}
              </div>
            </div>
          {:else}
            <div class="text-xs font-mono text-theme-muted text-center py-4">
              No history months found.
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
