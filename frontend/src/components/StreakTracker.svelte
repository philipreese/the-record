<script lang="ts">
  import Icon from './layout/Icon.svelte';

  interface StreakInfo {
    current_streak: number;
    longest_streak: number;
  }

  let { streakData = { current_streak: 0, longest_streak: 0 } }: { streakData?: StreakInfo } = $props();
  
  let current = $derived(streakData.current_streak || 0);
  let longest = $derived(streakData.longest_streak || 0);
  
  // Motivational messages depending on active streak
  let message = $derived(getMotivationalMessage(current));
  
  function getMotivationalMessage(streak: number): string {
    if (streak === 0) {
      return "Start listening today to kick off a new daily music streak!";
    } else if (streak <= 2) {
      return "Streak started! Listen again tomorrow to keep the flame alive.";
    } else if (streak <= 5) {
      return "Nice job! You've listened to music multiple days in a row.";
    } else if (streak <= 10) {
      return "On fire! You're building an incredible daily music habit.";
    } else {
      return "Legendary! Your music connection is unstoppable. Keep rocking!";
    }
  }
</script>

<div class="memory-surface flex flex-col justify-between h-full">
  <div>
    <h3 class="text-sm font-semibold mb-4 text-base-content opacity-80 uppercase tracking-wider">
      Listening Streaks
    </h3>
    
    <div class="grid grid-cols-2 gap-4 mt-2">
      <!-- Current Streak Card -->
      <div class="memory-surface-nested flex flex-col items-center justify-center relative overflow-hidden group">
        <!-- Glow backing -->
        <div class="absolute -right-4 -bottom-4 w-12 h-12 bg-primary/20 rounded-full blur-xl transition-all duration-500 group-hover:scale-150"></div>
        
        <Icon name="flame" size="w-10 h-10" class="stroke-primary fill-primary/20 animate-pulse transition-transform duration-300 group-hover:scale-110" />
        
        <span class="text-display-medium mt-2 text-base-content">{current}</span>
        <span class="text-caps mt-0.5">Current Streak</span>
        <span class="text-detail mt-1">days in a row</span>
      </div>
      
      <!-- Longest Streak Card -->
      <div class="memory-surface-nested flex flex-col items-center justify-center relative overflow-hidden group">
        <!-- Glow backing -->
        <div class="absolute -right-4 -bottom-4 w-12 h-12 bg-secondary/20 rounded-full blur-xl transition-all duration-500 group-hover:scale-150"></div>
        
        <Icon name="crown" size="w-10 h-10" class="stroke-secondary fill-secondary/10 transition-transform duration-300 group-hover:scale-110" />
        
        <span class="text-display-medium mt-2 text-base-content">{longest}</span>
        <span class="text-caps mt-0.5">Longest Record</span>
        <span class="text-detail mt-1">days active</span>
      </div>
    </div>
  </div>
  
  <p class="text-xs opacity-70 mt-6 bg-base-300/20 border border-base-content/5 rounded-lg p-3 text-center leading-relaxed">
    {message}
  </p>
</div>
