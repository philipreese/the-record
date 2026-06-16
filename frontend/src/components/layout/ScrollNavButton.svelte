<script lang="ts">
  import { fade } from 'svelte/transition';

  let {
    target,
    onclick,
  }: {
    target: { id: string; label: string };
    onclick: () => void;
  } = $props();
</script>

<div
  class="fixed bottom-12 left-1/2 -translate-x-1/2 lg:left-[calc(50%+128px)] z-40 flex justify-center"
>
  <button
    {onclick}
    class="group flex flex-col items-center gap-2 cursor-pointer focus:outline-none bg-base-200/60 hover:bg-base-200/90 backdrop-blur-md px-5 py-2 rounded-full border border-theme-border-soft shadow-xl transition-all"
    aria-label="Scroll Navigation"
  >
    <div class="flex items-center gap-2">
      {#key target.label}
        <span
          in:fade={{ duration: 150 }}
          class="font-mono text-theme-muted uppercase tracking-widest group-hover:text-theme-accent transition-colors select-none"
        >
          {target.id === 'top' ? 'return to top' : `scroll to ${target.label}`}
        </span>
      {/key}

      {#if target.id === 'top'}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          class="w-4 h-4 text-theme-muted group-hover:text-theme-accent group-hover:-translate-y-0.5 transition-all duration-300"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
        </svg>
      {:else}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          class="w-4 h-4 text-theme-muted group-hover:text-theme-accent group-hover:translate-y-0.5 transition-all duration-300 animate-bounce"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      {/if}
    </div>
  </button>
</div>
