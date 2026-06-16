<script lang="ts">
  import { inView } from '../../utils/inView';
  import HourlyHeatClock from '../HourlyHeatClock.svelte';
  import StreakTracker from '../StreakTracker.svelte';

  let {
    hourlyData,
    streakData,
    clockDimmed,
    streakDimmed,
    onClockFocusEnter,
    onClockFocusClear,
    onStreakFocusEnter,
    onStreakFocusClear,
  }: {
    hourlyData: Record<string, number>;
    streakData: { current_streak: number; longest_streak: number };
    clockDimmed: boolean;
    streakDimmed: boolean;
    onClockFocusEnter: () => void;
    onClockFocusClear: () => void;
    onStreakFocusEnter: () => void;
    onStreakFocusClear: () => void;
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
