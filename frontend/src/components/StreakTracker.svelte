<script lang="ts">
  import Icon from './layout/Icon.svelte';
  import { appCache } from '../services/store.svelte';

  interface StreakInfo {
    current_streak: number;
    longest_streak: number;
  }

  let { streakData = { current_streak: 0, longest_streak: 0 } }: { streakData?: StreakInfo } =
    $props();

  let current = $derived(streakData.current_streak || 0);
  let longest = $derived(streakData.longest_streak || 0);

  // Motivational messages depending on active streak
  let message = $derived(
    appCache.narrative.plain['streak.message'] ||
      'Start listening today to kick off a new daily music streak!',
  );
</script>

<div class="memory-surface flex flex-col justify-between h-full space-y-6">
  <div class="space-y-4">
    <div class="grid grid-cols-2 gap-4 divide-x divide-theme-border-soft">
      <!-- Current Streak Card -->
      <div
        class="flex flex-col items-center justify-center py-4 relative overflow-hidden group text-center"
      >
        <div
          class="p-2.5 rounded-full mb-1 transition-transform duration-300 group-hover:scale-105 bg-theme-accent-soft"
        >
          <Icon name="flame" size="w-7 h-7" class="text-theme-accent" />
        </div>
        <span class="text-display-large mt-3 text-theme-text">{current}</span>
        <span class="text-caps mt-2 text-xs text-theme-muted">Current Streak</span>
        <span class="text-detail mt-1 text-xs text-theme-faint">consecutive days</span>
      </div>

      <!-- Longest Streak Card -->
      <div
        class="flex flex-col items-center justify-center py-4 relative overflow-hidden group text-center pl-4"
      >
        <div
          class="p-2.5 rounded-full mb-1 transition-transform duration-300 group-hover:scale-105 bg-theme-secondary-soft"
        >
          <Icon name="crown" size="w-7 h-7" class="text-theme-secondary" />
        </div>
        <span class="text-display-large mt-3 text-theme-text">{longest}</span>
        <span class="text-caps mt-2 text-xs text-theme-muted">Longest Record</span>
        <span class="text-detail mt-1 text-xs text-theme-faint">all-time peak</span>
      </div>
    </div>
  </div>

  <p
    class="text-sm font-light italic leading-relaxed text-center px-5 py-4 rounded-xl text-theme-secondary bg-theme-neutral-soft border border-theme-border-soft"
  >
    {message}
  </p>
</div>
