<script lang="ts" generics="T extends string | number">
  // Svelte 5 Custom Themed Dropdown Component with Slide Transition & Exact Sizing
  import { slide } from 'svelte/transition';

  let {
    value = $bindable(),
    options = [],
  }: {
    value: T;
    options: { value: T; label: string }[];
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
    document.addEventListener('click', handleDocumentClick);
    return () => document.removeEventListener('click', handleDocumentClick);
  });

  // Selected option
  let selectedOption = $derived(
    options.find((o) => o.value === value) || options[0] || { value: '', label: '' },
  );

  // Find the option with the longest label to size the button stably
  let longestOption = $derived(
    options.reduce(
      (longest, current) => (current.label.length > longest.label.length ? current : longest),
      options[0] || { value: '', label: '' },
    ),
  );
</script>

<div class="relative inline-block" bind:this={containerRef}>
  <!-- Dropdown Trigger Button (Uses select-premium for border and bottom line padding) -->
  <button
    type="button"
    class="select-premium relative w-full flex items-center focus:outline-none cursor-pointer select-none font-mono"
    onclick={() => (isOpen = !isOpen)}
  >
    <!-- Hidden layout spacer (preserves height & width, with padding offsets respected via inline-block) -->
    <span
      class="invisible pointer-events-none select-none font-mono tracking-wide inline-block text-base p-1"
    >
      {longestOption.label}
    </span>
    <!-- Actual Selected Label (Positioned at the left padding offset 0.25rem) -->
    <span class="pl-1 absolute left-1 right-6 font-mono text-left truncate text-base">
      {selectedOption.label}
    </span>
    <!-- Arrow indicator (Positioned at the right padding offset 0.25rem) -->
    <span
      class="pr-1 text-xs opacity-60 absolute right-1 transition-transform duration-200 {isOpen
        ? 'rotate-180'
        : 'rotate-0'}"
    >
      ↓
    </span>
  </button>

  <!-- Floating Menu Panel (Seamless downward extension, slides open smoothly) -->
  {#if isOpen}
    <div
      transition:slide={{ duration: 180 }}
      class="absolute left-0 mt-0 w-full rounded-b-xl border-l border-r border-b shadow-2xl popover-premium py-1 overflow-hidden"
    >
      {#each options as option}
        <button
          type="button"
          class="w-full text-left pl-2 pr-6 py-2.5 font-mono text-base tracking-wide transition-colors duration-150 cursor-pointer block select-none truncate {option.value ===
          value
            ? 'text-theme-accent bg-theme-accent-soft'
            : 'text-theme-secondary bg-transparent hover:text-theme-text hover:bg-theme-neutral-soft'}"
          onclick={() => {
            value = option.value;
            isOpen = false;
          }}
          title={option.label}
        >
          {option.label}
        </button>
      {/each}
    </div>
  {/if}
</div>
