<script lang="ts">
  import type { WrappedQuarter, WrappedMonth } from '../../services/api';
  import SelectDropdown from './SelectDropdown.svelte';

  let {
    period = $bindable(),
    year = $bindable(),
    quarter = $bindable(),
    month = $bindable(),
    yearOptions,
    quarterOptions,
    monthOptions,
  }: {
    period: 'year' | 'quarter' | 'month';
    year: number;
    quarter: WrappedQuarter;
    month: WrappedMonth;
    yearOptions: { value: number; label: string }[];
    quarterOptions: { value: WrappedQuarter; label: string }[];
    monthOptions: { value: WrappedMonth; label: string }[];
  } = $props();
</script>

<!-- Mobile Sticky Controls -->
<div class="sticky-sub-header lg:hidden flex flex-col gap-3">
  <div class="nav-selector w-full justify-between gap-1">
    {#each [['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']] as [p, label]}
      <button
        class="nav-selector-item flex-1 text-center justify-center py-1 text-xs"
        class:active={period === p}
        onclick={() => {
          period = p as 'year' | 'quarter' | 'month';
        }}
      >
        {label}
      </button>
    {/each}
  </div>

  <div class="flex flex-wrap gap-4 items-center justify-start px-1 text-xs">
    <div class="flex items-center gap-2">
      <span class="text-caps text-[10px] text-theme-muted uppercase tracking-wider">Year</span>
      <SelectDropdown bind:value={year} options={yearOptions} />
    </div>

    {#if period === 'quarter'}
      <div class="flex items-center gap-2">
        <span class="text-caps text-[10px] text-theme-muted uppercase tracking-wider">Quarter</span>
        <SelectDropdown bind:value={quarter} options={quarterOptions} />
      </div>
    {/if}

    {#if period === 'month'}
      <div class="flex items-center gap-2">
        <span class="text-caps text-[10px] text-theme-muted uppercase tracking-wider">Month</span>
        <SelectDropdown bind:value={month} options={monthOptions} />
      </div>
    {/if}
  </div>
</div>

<!-- Desktop Controls -->
<div class="hidden lg:flex flex-wrap gap-8 items-center px-2">
  <div class="flex items-center gap-3">
    <span class="text-caps text-xs text-theme-muted">Year</span>
    <SelectDropdown bind:value={year} options={yearOptions} />
  </div>

  {#if period === 'quarter'}
    <div class="flex items-center gap-3">
      <span class="text-caps text-xs text-theme-muted">Quarter</span>
      <SelectDropdown bind:value={quarter} options={quarterOptions} />
    </div>
  {/if}

  {#if period === 'month'}
    <div class="flex items-center gap-3">
      <span class="text-caps text-xs text-theme-muted">Month</span>
      <SelectDropdown bind:value={month} options={monthOptions} />
    </div>
  {/if}
</div>
