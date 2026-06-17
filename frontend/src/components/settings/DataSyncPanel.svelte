<script lang="ts">
  import { appCache } from '../../services/store.svelte';
  import Icon from '../layout/Icon.svelte';
  import SelectDropdown from '../layout/SelectDropdown.svelte';

  let tokenInput = $state(appCache.syncToken);

  let exportFormat = $state<'csv' | 'json'>('csv');
  let exportRange = $state('all');

  const formatOptions: { value: 'csv' | 'json'; label: string }[] = [
    { value: 'csv', label: 'CSV' },
    { value: 'json', label: 'JSON' },
  ];

  const rangeOptions: { value: string; label: string }[] = [
    { value: 'all', label: 'All time' },
    { value: '365', label: '1 year' },
    { value: '90', label: '90 days' },
    { value: '30', label: '30 days' },
  ];

  const apiBase = import.meta.env.VITE_API_BASE || '';

  function triggerExport() {
    const url = `${apiBase}/api/export?format=${exportFormat}&range=${exportRange}`;
    const a = document.createElement('a');
    a.href = url;
    a.click();
  }

  function saveToken() {
    appCache.setSyncToken(tokenInput);
  }

  function clearToken() {
    tokenInput = '';
    appCache.setSyncToken('');
  }
</script>

<div class="space-y-8">
  <!-- Database Info Card -->
  <div class="memory-surface-nested">
    <h3 class="text-sm md:text-base font-mono tracking-widest uppercase text-theme-muted mb-6">
      Database Connection
    </h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-8">
      <div class="flex flex-col gap-1.5">
        <span class="text-sm font-mono text-theme-muted uppercase tracking-wider">Engine Type</span>
        <span class="text-xl font-light text-theme-text">
          {appCache.stats?.db_type || 'Resolving engine...'}
        </span>
      </div>
      <div class="flex flex-col gap-1.5">
        <span class="text-sm font-mono text-theme-muted uppercase tracking-wider"
          >Archived Plays</span
        >
        <span class="text-3xl font-mono font-normal text-theme-accent">
          {appCache.stats?.total_listens.toLocaleString() || 'Connecting...'}
        </span>
      </div>
    </div>
  </div>

  <!-- Sync Authentication Card -->
  <div class="memory-surface-nested">
    <h3 class="text-sm md:text-base font-mono tracking-widest uppercase text-theme-muted mb-6">
      Sync Authentication
    </h3>
    <p class="text-base font-light text-theme-muted mb-2 leading-relaxed">
      A private admin secret that authorizes triggering a sync from this browser. It must match the
      <code class="font-mono text-theme-accent">SYNC_TOKEN</code> set on the server.
    </p>
    <p class="text-sm font-light text-theme-muted mb-6 leading-relaxed">
      This is <span class="text-theme-text">not</span> your ListenBrainz token. It only exists so random
      visitors can't trigger syncs on the public deployment — without it, the dashboard is read-only.
    </p>
    <div class="flex flex-col sm:flex-row gap-3 items-start">
      <input
        type="password"
        class="input input-bordered w-full sm:max-w-sm font-mono text-sm"
        placeholder="Enter your SYNC_TOKEN..."
        bind:value={tokenInput}
        onkeydown={(e) => e.key === 'Enter' && saveToken()}
      />
      <div class="flex gap-2">
        <button
          class="btn btn-primary btn-md cursor-pointer focus:outline-none"
          onclick={saveToken}
        >
          Save
        </button>
        {#if appCache.syncToken}
          <button
            class="btn btn-ghost btn-md cursor-pointer focus:outline-none"
            onclick={clearToken}
          >
            Clear
          </button>
        {/if}
      </div>
    </div>
    {#if appCache.syncToken}
      <p class="text-xs text-success font-mono mt-3">
        Token saved in this browser — the server verifies it on each sync.
      </p>
    {/if}
  </div>

  <!-- Sync Controls Section -->
  <div class="space-y-6">
    <div>
      <h3 class="editorial-text-h2 pb-2 border-b">Archive Synchronization</h3>
      <p class="text-base font-light text-theme-muted mt-2 leading-relaxed">
        Two sync modes keep your local archive in sync with ListenBrainz.
        <strong class="text-theme-text font-normal">Incremental</strong> is fast and additive — use
        it daily. <strong class="text-theme-text font-normal">Mirror</strong> makes your local archive
        an exact copy of ListenBrainz, adding missing plays and removing any that no longer exist there.
      </p>
    </div>

    {#if appCache.syncToken}
      <div class="flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Incremental Sync Card -->
          <div class="memory-surface-nested flex flex-col justify-between gap-6 bg-transparent">
            <div class="space-y-3">
              <span class="text-sm font-mono tracking-widest text-theme-muted uppercase"
                >Incremental Sync</span
              >
              <h4 class="text-lg lg:text-xl font-light text-theme-text">Pull New Scrobbles</h4>
              <p class="text-base font-light text-theme-secondary leading-relaxed">
                Fetches plays added since your last sync, plus a backfill pass if your local count
                is behind. Always additive — only ever adds records. Recommended for daily use.
              </p>
            </div>
            <div>
              <button
                class="btn btn-primary btn-md shadow-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
                disabled={appCache.isSyncing}
                onclick={() => appCache.runSync('normal', false)}
              >
                {#if appCache.isSyncing && appCache.syncStatus?.mode === 'normal'}
                  <span class="loading loading-spinner loading-xs"></span>
                  Syncing...
                {:else}
                  <Icon name="sync" size="w-4 h-4" />
                  Sync New Plays
                {/if}
              </button>
            </div>
          </div>

          <!-- Mirror Sync Card -->
          <div
            class="memory-surface-nested flex flex-col justify-between gap-6 border-warning/40"
            style="background-color: color-mix(in srgb, oklch(var(--wa)) 4%, transparent);"
          >
            <div class="space-y-3">
              <span class="text-sm font-mono tracking-widest text-warning uppercase"
                >Mirror Sync</span
              >
              <h4 class="text-lg lg:text-xl font-light text-theme-text">
                Mirror from ListenBrainz
              </h4>
              <p class="text-base font-light text-theme-secondary leading-relaxed">
                Fetches your complete ListenBrainz history and makes the local archive an exact copy
                — adding any missing plays and permanently removing any that no longer exist on
                ListenBrainz. Takes 15–20 minutes.
              </p>
              <p class="text-xs font-mono text-warning/80">
                Permanently removes records not on ListenBrainz. Cannot be undone.
              </p>
            </div>
            <div>
              <button
                class="btn btn-warning btn-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
                disabled={appCache.isSyncing}
                onclick={() => appCache.runSync('mirror', false)}
              >
                {#if appCache.isSyncing && appCache.syncStatus?.mode === 'mirror'}
                  <span class="loading loading-spinner loading-xs"></span>
                  Mirroring Archive...
                {:else}
                  <Icon name="sync" size="w-4 h-4" />
                  Start Mirror Sync
                {/if}
              </button>
            </div>
          </div>
        </div>

        <!-- Sync Progress -->
        {#if appCache.isSyncing && appCache.syncStatus}
          <div
            class="p-4 rounded-xl border border-theme-border-soft bg-base-200/50 space-y-2 animate-fade-in"
          >
            {#if appCache.syncStatus.mode === 'mirror'}
              <div class="flex justify-between text-xs font-mono">
                <span class="text-warning font-semibold uppercase">Mirror Sync In Progress</span>
                <span class="text-theme-muted">
                  Page {Math.max(1, appCache.syncStatus.batches_fetched)} · {appCache.syncStatus
                    .synced_count}
                  added
                </span>
              </div>
              <div class="w-full bg-base-300 h-1.5 rounded-full overflow-hidden">
                <div
                  class="bg-warning h-full transition-all duration-300 animate-pulse"
                  style="width: {appCache.syncStatus.lb_total
                    ? Math.min(
                        100,
                        ((appCache.syncStatus.batches_fetched * 1000) /
                          appCache.syncStatus.lb_total) *
                          100,
                      )
                    : 30}%"
                ></div>
              </div>
              <div class="text-[10px] text-theme-muted font-mono flex justify-between">
                <span
                  >Fetching all {appCache.syncStatus.lb_total.toLocaleString()} ListenBrainz listens...</span
                >
              </div>
            {:else}
              <div class="flex justify-between text-xs font-mono">
                <span class="text-theme-text font-semibold uppercase">Sync In Progress</span>
                <span class="text-theme-accent font-semibold">
                  Batch {Math.max(1, appCache.syncStatus.batches_fetched)} · {appCache.syncStatus
                    .synced_count} new scrobbles
                </span>
              </div>
              <div class="w-full bg-base-300 h-1.5 rounded-full overflow-hidden">
                <div
                  class="bg-theme-accent h-full transition-all duration-300 animate-pulse"
                  style="width: {appCache.syncStatus.lb_total
                    ? Math.min(
                        100,
                        (appCache.syncStatus.local_total / appCache.syncStatus.lb_total) * 100,
                      )
                    : 50}%"
                ></div>
              </div>
              <div class="text-[10px] text-theme-muted font-mono flex justify-between">
                <span>Local total: {appCache.syncStatus.local_total.toLocaleString()}</span>
                <span>ListenBrainz total: {appCache.syncStatus.lb_total.toLocaleString()}</span>
              </div>
            {/if}
          </div>
        {/if}

        <!-- Sync Completion Message -->
        {#if !appCache.isSyncing && appCache.syncStatus?.finished && !appCache.syncError}
          <div class="text-xs font-semibold flex items-center gap-1.5 animate-fade-in">
            {#if appCache.syncStatus.mode === 'mirror'}
              {#if appCache.syncStatus.synced_count > 0 || appCache.syncStatus.deleted_count > 0}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  class="w-4 h-4 text-success"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                    clip-rule="evenodd"
                  />
                </svg>
                <span class="text-success">
                  Mirror complete — added {appCache.syncStatus.synced_count} play{appCache
                    .syncStatus.synced_count === 1
                    ? ''
                    : 's'}, removed {appCache.syncStatus.deleted_count} play{appCache.syncStatus
                    .deleted_count === 1
                    ? ''
                    : 's'}.
                </span>
              {:else}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  class="w-4 h-4 text-success"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                    clip-rule="evenodd"
                  />
                </svg>
                <span class="text-success">
                  Archive is already an exact mirror of ListenBrainz.
                </span>
              {/if}
            {:else}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="w-4 h-4 text-success"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                  clip-rule="evenodd"
                />
              </svg>
              <span class="text-success">
                Synced {appCache.syncStatus.synced_count} new play{appCache.syncStatus
                  .synced_count === 1
                  ? ''
                  : 's'} ({appCache.syncStatus.batches_fetched} batch{appCache.syncStatus
                  .batches_fetched === 1
                  ? ''
                  : 'es'}).
              </span>
            {/if}
          </div>
        {/if}

        <!-- Sync Error Message -->
        {#if appCache.syncError}
          <div
            class="text-xs text-error font-semibold flex items-start gap-1.5 max-w-125 animate-fade-in"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              class="w-4 h-4 shrink-0 mt-0.5"
            >
              <path
                fill-rule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
                clip-rule="evenodd"
              />
            </svg>
            <span>{appCache.syncError}</span>
          </div>
        {/if}
      </div>
    {:else}
      <p class="text-sm text-theme-muted font-light">
        Save a sync token above to enable archive synchronization controls.
      </p>
    {/if}
  </div>

  <!-- Export Section -->
  <div class="space-y-6">
    <div>
      <h3 class="editorial-text-h2 pb-2 border-b">Export Archive</h3>
      <p class="text-base font-light text-theme-muted mt-2 leading-relaxed">
        Download your full listening history as a CSV or JSON file for backup or offline analysis.
      </p>
    </div>

    <div class="memory-surface-nested">
      <div class="flex flex-wrap items-end gap-6">
        <div class="flex flex-col gap-2">
          <span class="text-xs font-mono uppercase tracking-widest text-theme-muted">Format</span>
          <SelectDropdown bind:value={exportFormat} options={formatOptions} />
        </div>

        <div class="flex flex-col gap-2">
          <span class="text-xs font-mono uppercase tracking-widest text-theme-muted">Range</span>
          <SelectDropdown bind:value={exportRange} options={rangeOptions} />
        </div>

        <button
          class="btn btn-primary btn-md shadow-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
          onclick={triggerExport}
        >
          <Icon name="download" size="w-4 h-4" />
          Download {exportFormat.toUpperCase()}
        </button>
      </div>
    </div>
  </div>
</div>
