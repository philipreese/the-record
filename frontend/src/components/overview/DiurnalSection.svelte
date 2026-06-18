<script lang="ts">
  import { inView } from '../../utils/inView';
  import HourlyHeatClock from '../HourlyHeatClock.svelte';
  import PunchcardChart from '../PunchcardChart.svelte';
  import { appCache } from '../../services/store.svelte';

  let {
    hourlyData,
    punchcardData,
  }: {
    hourlyData: Record<string, number>;
    punchcardData: Record<string, number>;
  } = $props();
</script>

<div id="diurnal-patterns" class="mt-30 space-y-16">
  <!-- 02A / Diurnal Intensity -->
  <div use:inView={{ once: true }} class="space-y-4 reveal-container" role="region">
    <div class="pb-2 border-b border-theme-border-soft reveal-label">
      <h3 class="editorial-text-h2">
        02A / {@html appCache.narrative['overview.insight.patterns_diurnal'] || 'Diurnal Intensity'}
      </h3>
    </div>
    <div class="reveal-content">
      <HourlyHeatClock {hourlyData} />
    </div>
  </div>

  <!-- 02B / Weekly Cadence -->
  <div use:inView={{ once: true }} class="space-y-4 reveal-container" role="region">
    <div class="pb-2 border-b border-theme-border-soft reveal-label">
      <h3 class="editorial-text-h2">
        02B / {@html appCache.narrative['overview.insight.patterns_weekly'] || 'Weekly Cadence'}
      </h3>
    </div>
    <div class="reveal-content">
      <PunchcardChart data={punchcardData} />
    </div>
  </div>
</div>
