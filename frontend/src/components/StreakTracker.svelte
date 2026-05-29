<script lang="ts">
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

<div class="card bg-base-200/50 backdrop-blur-md border border-base-content/10 p-6 flex flex-col justify-between h-full">
  <div>
    <h3 class="text-sm font-semibold mb-4 text-base-content opacity-80 uppercase tracking-wider">
      Listening Streaks
    </h3>
    
    <div class="grid grid-cols-2 gap-4 mt-2">
      <!-- Current Streak Card -->
      <div class="bg-base-300/40 rounded-xl p-4 flex flex-col items-center justify-center border border-base-content/5 relative overflow-hidden group">
        <!-- Glow backing -->
        <div class="absolute -right-4 -bottom-4 w-12 h-12 bg-primary/20 rounded-full blur-xl transition-all duration-500 group-hover:scale-150"></div>
        
        <!-- Flame Icon -->
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-10 h-10 stroke-primary fill-primary/20 animate-pulse transition-transform duration-300 group-hover:scale-110">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        
        <span class="text-2xl font-extrabold mt-2 text-base-content">{current}</span>
        <span class="text-[10px] font-bold uppercase opacity-60 mt-0.5">Current Streak</span>
        <span class="text-[9px] opacity-40 mt-1">days in a row</span>
      </div>
      
      <!-- Longest Streak Card -->
      <div class="bg-base-300/40 rounded-xl p-4 flex flex-col items-center justify-center border border-base-content/5 relative overflow-hidden group">
        <!-- Glow backing -->
        <div class="absolute -right-4 -bottom-4 w-12 h-12 bg-secondary/20 rounded-full blur-xl transition-all duration-500 group-hover:scale-150"></div>
        
        <!-- Crown/Trophy Icon -->
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-10 h-10 stroke-secondary fill-secondary/10 transition-transform duration-300 group-hover:scale-110">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
        </svg>
        
        <span class="text-2xl font-extrabold mt-2 text-base-content">{longest}</span>
        <span class="text-[10px] font-bold uppercase opacity-60 mt-0.5">Longest Record</span>
        <span class="text-[9px] opacity-40 mt-1">days active</span>
      </div>
    </div>
  </div>
  
  <p class="text-xs opacity-70 mt-6 bg-base-300/20 border border-base-content/5 rounded-lg p-3 text-center leading-relaxed">
    {message}
  </p>
</div>
