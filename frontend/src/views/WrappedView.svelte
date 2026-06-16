<script lang="ts">
  import { untrack } from 'svelte';
  import {
    generateWrapped,
    type WrappedQuarter,
    type WrappedMonth,
    type WrappedDataInfo,
  } from '../services/api';
  import { appCache } from '../services/store.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';
  import LoadingSpinner from '../components/layout/LoadingSpinner.svelte';
  import PeriodSelector from '../components/layout/PeriodSelector.svelte';
  import WrappedCard from '../components/dashboard/WrappedCard.svelte';

  const yearOptions = [
    { value: 2026, label: '2026' },
    { value: 2025, label: '2025' },
    { value: 2024, label: '2024' },
    { value: 2023, label: '2023' },
    { value: 2022, label: '2022' },
    { value: 2021, label: '2021' },
    { value: 2020, label: '2020' },
  ];

  const quarterOptions = [
    { value: 'Q1' as WrappedQuarter, label: 'Q1 (Jan-Mar)' },
    { value: 'Q2' as WrappedQuarter, label: 'Q2 (Apr-Jun)' },
    { value: 'Q3' as WrappedQuarter, label: 'Q3 (Jul-Sep)' },
    { value: 'Q4' as WrappedQuarter, label: 'Q4 (Oct-Dec)' },
  ];

  const monthOptions = [
    { value: 'M1' as WrappedMonth, label: 'January' },
    { value: 'M2' as WrappedMonth, label: 'February' },
    { value: 'M3' as WrappedMonth, label: 'March' },
    { value: 'M4' as WrappedMonth, label: 'April' },
    { value: 'M5' as WrappedMonth, label: 'May' },
    { value: 'M6' as WrappedMonth, label: 'June' },
    { value: 'M7' as WrappedMonth, label: 'July' },
    { value: 'M8' as WrappedMonth, label: 'August' },
    { value: 'M9' as WrappedMonth, label: 'September' },
    { value: 'M10' as WrappedMonth, label: 'October' },
    { value: 'M11' as WrappedMonth, label: 'November' },
    { value: 'M12' as WrappedMonth, label: 'December' },
  ];

  let wrappedPeriod = $state<'year' | 'quarter' | 'month'>('year');
  let wrappedYear = $state(2026);
  let wrappedQuarter = $state<WrappedQuarter>('Q1');
  let wrappedMonth = $state<WrappedMonth>('M1');
  let loadingWrapped = $state(false);
  let wrappedError = $state<string | null>(null);

  let cacheKey = $derived(`${wrappedPeriod}-${wrappedYear}-${wrappedQuarter}-${wrappedMonth}`);

  // Auto trigger Wrapped when controls change. Reading the cache entry here keeps the
  // effect reactive to invalidation: a sync clears appCache.wrapped and this refetches.
  $effect(() => {
    const period = wrappedPeriod;
    const year = wrappedYear;
    const quarter = wrappedQuarter;
    const month = wrappedMonth;
    const key = cacheKey;

    if (appCache.wrapped[key]) {
      wrappedError = null;
      loadingWrapped = false;
      return;
    }
    untrack(() => {
      runGenerateWrapped(period, year, quarter, month, key);
    });
  });

  // Tracks pending fetches per cache key so rapid period switching (A->B->A)
  // reuses the in-flight request for A instead of firing a second, racing one.
  const inFlight = new Map<string, Promise<WrappedDataInfo>>();

  async function runGenerateWrapped(
    period: 'year' | 'quarter' | 'month',
    year: number,
    quarter: WrappedQuarter,
    month: WrappedMonth,
    key: string,
  ) {
    loadingWrapped = true;
    wrappedError = null;
    try {
      let request = inFlight.get(key);
      if (!request) {
        request = generateWrapped(period, year, quarter, month).finally(() => {
          inFlight.delete(key);
        });
        inFlight.set(key, request);
      }
      const data = await request;
      appCache.wrapped[key] = data;
    } catch (e) {
      wrappedError = e instanceof Error ? e.message : String(e);
    } finally {
      if (key === cacheKey) loadingWrapped = false;
    }
  }

  let currentWrappedData = $derived(appCache.wrapped[cacheKey] || null);
</script>

<PageHeader
  title="periodic reviews"
  subtitle="Spotify Wrapped style summaries for custom time ranges."
>
  {#snippet actions(isShrunk)}
    <div class="hidden lg:block">
      <div
        class="nav-selector transition-all duration-300"
        class:text-xs={isShrunk}
        class:text-sm={!isShrunk}
      >
        {#each [['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']] as [period, label]}
          <button
            class="nav-selector-item"
            class:active={wrappedPeriod === period}
            onclick={() => {
              wrappedPeriod = period as 'year' | 'quarter' | 'month';
            }}
          >
            {label}
          </button>
        {/each}
      </div>
    </div>
  {/snippet}
</PageHeader>

<PeriodSelector
  bind:period={wrappedPeriod}
  bind:year={wrappedYear}
  bind:quarter={wrappedQuarter}
  bind:month={wrappedMonth}
  {yearOptions}
  {quarterOptions}
  {monthOptions}
/>

<div class="flex flex-col gap-12 text-base-content">
  {#if loadingWrapped}
    <LoadingSpinner />
  {:else if wrappedError}
    <div
      class="max-w-4xl mx-auto w-full p-4 rounded-xl text-center text-sm font-mono text-theme-secondary bg-theme-neutral-soft border border-dashed border-theme-border-heavy"
    >
      {wrappedError}
    </div>
  {:else if currentWrappedData}
    <WrappedCard
      data={currentWrappedData}
      period={wrappedPeriod}
      year={wrappedYear}
      quarter={wrappedQuarter}
      month={wrappedMonth}
    />
  {/if}
</div>
