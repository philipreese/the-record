<script lang="ts">
  import { fade } from 'svelte/transition';
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    subtitle?: string;
    actions?: Snippet<[boolean]>;
  }

  let { title, subtitle, actions }: Props = $props();

  let scrollY = $state(0);
  let isShrunk = $state(false);

  $effect(() => {
    if (scrollY > 80) {
      isShrunk = true;
    } else if (scrollY < 20) {
      isShrunk = false;
    }
  });
</script>

<svelte:window bind:scrollY />

<div
  class="sticky-header flex flex-row justify-between items-center gap-4 pb-4 transition-all duration-(--t-reflective) var(--ease-fluid)"
  class:lg:py-2={isShrunk}
  class:lg:py-4={!isShrunk}
>
  <div class="flex flex-col justify-center">
    <h1
      class="font-serif italic lowercase tracking-tight transition-all duration-(--t-responsive) var(--ease-fluid)"
      class:text-3xl={isShrunk}
      class:text-4xl={!isShrunk}
      class:lg:text-4xl={isShrunk}
      class:lg:text-7xl={!isShrunk}
    >
      {title}
    </h1>
    {#if subtitle && !isShrunk}
      <div transition:fade={{ duration: 120 }}>
        <p class="editorial-subtitle text-xs! mt-1">{subtitle}</p>
      </div>
    {/if}
  </div>

  {#if actions}
    {@render actions(isShrunk)}
  {/if}
</div>
