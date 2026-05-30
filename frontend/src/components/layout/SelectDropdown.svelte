<script lang="ts">
  // Svelte 5 Custom Themed Dropdown Component with Slide Transition & Exact Sizing
  import { slide } from 'svelte/transition';
  
  let { 
    value = $bindable(), 
    options = [] 
  }: { 
    value: any, 
    options: { value: any, label: string }[] 
  } = $props();

  let isOpen = $state(false);
  let containerRef = $state<HTMLElement | null>(null);

  // Close dropdown when clicking outside
  function handleDocumentClick(e: MouseEvent) {
    if (containerRef && !containerRef.contains(e.target as Node)) {
      isOpen = false;
    }
  }

  $effect(() => {
    document.addEventListener("click", handleDocumentClick);
    return () => document.removeEventListener("click", handleDocumentClick);
  });

  // Selected option
  let selectedOption = $derived(options.find(o => o.value === value) || options[0] || { value: '', label: '' });

  // Find the option with the longest label to size the button stably
  let longestOption = $derived(
    options.reduce((longest, current) => 
      current.label.length > longest.label.length ? current : longest, 
      options[0] || { value: '', label: '' }
    )
  );
</script>

<div class="relative inline-block" bind:this={containerRef}>
  <!-- Dropdown Trigger Button (Uses select-premium for border and bottom line padding) -->
  <button 
    type="button"
    class="select-premium relative w-full flex items-center focus:outline-none cursor-pointer select-none font-mono" 
    onclick={() => isOpen = !isOpen}
  >
    <!-- Hidden layout spacer (preserves height & width, with padding offsets respected via inline-block) -->
    <span class="invisible pointer-events-none select-none font-mono tracking-wide inline-block" style="font-size: 1rem; padding: 0.25rem;">
      {longestOption.label}
    </span>
    <!-- Actual Selected Label (Positioned at the left padding offset 0.25rem) -->
    <span class="pl-1 absolute left-[0.25rem] right-6 font-mono text-left truncate" style="font-size: 1rem;">
      {selectedOption.label}
    </span>
    <!-- Arrow indicator (Positioned at the right padding offset 0.25rem) -->
    <span class="pr-1 text-xs opacity-60 absolute right-[0.25rem] transition-transform duration-200" style="transform: rotate({isOpen ? 180 : 0}deg);">↓</span>
  </button>
  
  <!-- Floating Menu Panel (Seamless downward extension, slides open smoothly) -->
  {#if isOpen}
    <div 
      transition:slide={{ duration: 180 }}
      class="absolute left-0 mt-0 w-full rounded-b-xl border-l border-r border-b shadow-2xl backdrop-blur-xl z-50 py-1 overflow-hidden"
      style="
        background-color: color-mix(in srgb, var(--bg-base) 96%, transparent);
        border-color: color-mix(in srgb, var(--text-primary) 12%, transparent);
        opacity: 0.98;
      "
    >
      {#each options as option}
        <button
          type="button"
          // Align option text exactly underneath the trigger button text
          class="w-full text-left pl-2 pr-[1.5rem] py-2.5 font-mono tracking-wide transition-colors duration-150 cursor-pointer block select-none truncate"
          style="
            font-size: 1rem;
            color: {option.value === value ? 'var(--accent)' : 'var(--text-secondary)'};
            background-color: {option.value === value ? 'color-mix(in srgb, var(--accent) 8%, transparent)' : 'transparent'};
          "
          onclick={() => {
            value = option.value;
            isOpen = false;
          }}
          onmouseenter={(e) => {
            if (option.value !== value) {
              e.currentTarget.style.backgroundColor = 'color-mix(in srgb, var(--text-primary) 4%, transparent)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }
          }}
          onmouseleave={(e) => {
            if (option.value !== value) {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }
          }}
          title={option.label}
        >
          {option.label}
        </button>
      {/each}
    </div>
  {/if}
</div>
