<script lang="ts">
  import { inView } from '../../utils/inView';
  import HourlyHeatClock from '../HourlyHeatClock.svelte';
  import StreakTracker from '../StreakTracker.svelte';
  import PunchcardChart from '../PunchcardChart.svelte';

  let {
    hourlyData,
    punchcardData,
    streakData,
    clockDimmed,
    streakDimmed,
    punchcardDimmed,
    onClockFocusEnter,
    onClockFocusClear,
    onStreakFocusEnter,
    onStreakFocusClear,
    onPunchcardFocusEnter,
    onPunchcardFocusClear,
  }: {
    hourlyData: Record<string, number>;
    punchcardData: Record<string, number>;
    streakData: { current_streak: number; longest_streak: number };
    clockDimmed: boolean;
    streakDimmed: boolean;
    punchcardDimmed: boolean;
    onClockFocusEnter: () => void;
    onClockFocusClear: () => void;
    onStreakFocusEnter: () => void;
    onStreakFocusClear: () => void;
    onPunchcardFocusEnter: () => void;
    onPunchcardFocusClear: () => void;
  } = $props();
</script>

<div
  class="grid grid-cols-1 xl:grid-cols-2 gap-16 lg:gap-20 pt-30 items-start"
  id="diurnal-patterns"
>
  <!-- Hourly clock -->
  <div
    use:inView={{ once: true }}
    class="space-y-4 transition-all duration-(--t-responsive) var(--ease-fluid) reveal-container"
    class:opacity-80={clockDimmed}
    role="region"
    onmouseenter={onClockFocusEnter}
    onmouseleave={onClockFocusClear}
  >
    <div class="pb-2 border-b border-theme-border-soft reveal-label">
      <h3 class="editorial-text-h2">02A / Diurnal Intensity</h3>
    </div>
    <div class="reveal-content">
      <HourlyHeatClock {hourlyData} />
    </div>
  </div>

  <!-- Streak tracker -->
  <div
    use:inView={{ once: true }}
    class="space-y-4 transition-all duration-(--t-responsive) var(--ease-fluid) reveal-container"
    class:opacity-80={streakDimmed}
    role="region"
    onmouseenter={onStreakFocusEnter}
    onmouseleave={onStreakFocusClear}
  >
    <div class="pb-2 border-b border-theme-border-soft reveal-label">
      <h3 class="editorial-text-h2">02B / Recollection Continuous</h3>
    </div>
    <div class="reveal-content">
      <StreakTracker {streakData} />
    </div>
  </div>
</div>

<!-- Punchcard — full-width below the two-column grid -->
<div
  use:inView={{ once: true }}
  class="pt-16 space-y-4 transition-all duration-(--t-responsive) var(--ease-fluid) reveal-container"
  class:opacity-80={punchcardDimmed}
  role="region"
  onmouseenter={onPunchcardFocusEnter}
  onmouseleave={onPunchcardFocusClear}
>
  <div class="pb-2 border-b border-theme-border-soft reveal-label">
    <h3 class="editorial-text-h2">02C / Weekly Cadence</h3>
  </div>
  <div class="reveal-content">
    <PunchcardChart data={punchcardData} />
  </div>
</div>
