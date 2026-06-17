<script lang="ts">
  import { appCache } from '../../services/store.svelte';
  import Icon from '../layout/Icon.svelte';
  import SelectDropdown from '../layout/SelectDropdown.svelte';

  let tokenInput = $state(appCache.syncToken);

  let exportFormat = $state<'csv' | 'json'>('csv');
  let exportRange = $state('all');
  let reconcileDays = $state(30);

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

  const reconcileDaysOptions: { value: number; label: string }[] = [
    { value: 30, label: 'Last 30 days' },
    { value: 90, label: 'Last 90 days' },
    { value: 365, label: 'Last 365 days' },
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
        Three modes let you keep your local archive in sync with ListenBrainz. <strong
          class="text-theme-text font-normal">Incremental</strong
        >
        and
        <strong class="text-theme-text font-normal">Full Reconstruction</strong> are always additive
        — they only ever add records, never remove them.
        <strong class="text-theme-text font-normal">Deletion Sync</strong> compares your local archive
        against ListenBrainz within a time window and permanently removes records that no longer exist
        there.
      </p>
    </div>

    {#if appCache.syncToken}
      <div class="flex flex-col gap-6">
        <!-- Additive sync cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Incremental Sync Card -->
          <div class="memory-surface-nested flex flex-col justify-between gap-6 bg-transparent">
            <div class="space-y-3">
              <span class="text-sm font-mono tracking-widest text-theme-muted uppercase"
                >Incremental Sync</span
              >
              <h4 class="text-lg lg:text-xl font-light text-theme-text">Pull New Scrobbles</h4>
              <p class="text-base font-light text-theme-secondary leading-relaxed">
                Fetches plays added since your last sync, plus a quick backfill pass if your local
                count is behind. Safe and fast — only adds records. Recommended for daily updates.
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
                  Syncing New...
                {:else}
                  <Icon name="sync" size="w-4 h-4" />
                  Sync New Plays
                {/if}
              </button>
            </div>
          </div>

          <!-- Full Reconstruction Sync Card -->
          <div class="memory-surface-nested flex flex-col justify-between gap-6 bg-transparent">
            <div class="space-y-3">
              <span class="text-sm font-mono tracking-widest text-theme-muted uppercase"
                >Deep Sync</span
              >
              <h4 class="text-lg lg:text-xl font-light text-theme-text">Reconstruct Archive</h4>
              <p class="text-base font-light text-theme-secondary leading-relaxed">
                Re-scans your entire ListenBrainz history from the beginning and backfills any gaps.
                Always additive — never deletes. Use for recovery or after a fresh install.
              </p>
            </div>
            <div>
              <button
                class="btn btn-outline btn-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
                disabled={appCache.isSyncing}
                onclick={() => appCache.runSync('full', false)}
              >
                {#if appCache.isSyncing && appCache.syncStatus?.mode === 'full'}
                  <span class="loading loading-spinner loading-xs"></span>
                  Syncing Entire Archive...
                {:else}
                  <Icon name="download" size="w-4 h-4" />
                  Full Reconstruction
                {/if}
              </button>
            </div>
          </div>
        </div>

        <!-- Deletion Sync Card (full width, warning-styled) -->
        <div
          class="memory-surface-nested flex flex-col gap-6 border-warning/40"
          style="background-color: color-mix(in srgb, oklch(var(--wa)) 4%, transparent);"
        >
          <div class="space-y-3">
            <span class="text-sm font-mono tracking-widest text-warning uppercase"
              >Deletion Sync</span
            >
            <h4 class="text-lg lg:text-xl font-light text-theme-text">Remove Deleted Plays</h4>
            <p class="text-base font-light text-theme-secondary leading-relaxed">
              Fetches all ListenBrainz listens within the selected time window and compares them
              against your local archive. Any local records that no longer exist on ListenBrainz are
              permanently deleted. <strong class="text-theme-text font-normal"
                >Only ListenBrainz-sourced records are affected</strong
              > — imported data (YouTube Music, Google Takeout) is never touched.
            </p>
            <p class="text-xs font-mono text-warning/80 mt-1">
              This permanently deletes local records and cannot be undone.
            </p>
          </div>
          <div class="flex flex-wrap items-end gap-6">
            <div class="flex flex-col gap-1.5">
              <span class="text-xs font-mono uppercase tracking-widest text-theme-muted"
                >Time Window</span
              >
              <SelectDropdown bind:value={reconcileDays} options={reconcileDaysOptions} />
            </div>
            <button
              class="btn btn-warning btn-md flex items-center gap-2.5 cursor-pointer focus:outline-none"
              disabled={appCache.isSyncing}
              onclick={() => appCache.runSync('reconcile', false, reconcileDays)}
            >
              {#if appCache.isSyncing && appCache.syncStatus?.mode === 'reconcile'}
                <span class="loading loading-spinner loading-xs"></span>
                Comparing Archive...
              {:else}
                <Icon name="trash" size="w-4 h-4" />
                Sync Deletions
              {/if}
            </button>
          </div>
        </div>

        <!-- Sync Progress -->
        {#if appCache.isSyncing && appCache.syncStatus}
          <div
            class="p-4 rounded-xl border border-theme-border-soft bg-base-200/50 space-y-2 animate-fade-in"
          >
            {#if appCache.syncStatus.mode === 'reconcile'}
              <div class="flex justify-between text-xs font-mono">
                <span class="text-warning font-semibold uppercase">Deletion Sync In Progress</span>
                <span class="text-theme-muted">
                  {appCache.syncStatus.batches_fetched} page{appCache.syncStatus.batches_fetched ===
                  1
                    ? ''
                    : 's'} fetched from ListenBrainz
                </span>
              </div>
              <div class="w-full bg-base-300 h-1.5 rounded-full overflow-hidden">
                <div class="bg-warning h-full animate-pulse" style="width: 60%"></div>
              </div>
              <div class="text-[10px] text-theme-muted font-mono">
                Comparing {appCache.syncStatus.local_total.toLocaleString()} local records in window against
                ListenBrainz…
              </div>
            {:else}
              <div class="flex justify-between text-xs font-mono">
                <span class="text-theme-text font-semibold uppercase"
                  >Sync in Progress ({appCache.syncStatus.mode} mode)</span
                >
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
            {#if appCache.syncStatus.mode === 'reconcile'}
              {#if appCache.syncStatus.deleted_count > 0}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  class="w-4 h-4 text-warning"
                >
                  <path
                    fill-rule="evenodd"
                    d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                    clip-rule="evenodd"
                  />
                </svg>
                <span class="text-warning">
                  Removed {appCache.syncStatus.deleted_count} record{appCache.syncStatus
                    .deleted_count === 1
                    ? ''
                    : 's'} that no longer exist on ListenBrainz.
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
                <span class="text-success">Archive is up to date — no records were removed.</span>
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
                  : 's'} successfully ({appCache.syncStatus.batches_fetched} batch{appCache
                  .syncStatus.batches_fetched === 1
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
