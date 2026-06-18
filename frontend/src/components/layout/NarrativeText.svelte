<script lang="ts">
  let {
    text = '',
    accentClass = 'text-theme-accent',
  }: {
    text?: string;
    accentClass?: string;
  } = $props();

  let parts = $derived(text.split('*'));
</script>

{#each parts as part, index}
  {#if index % 2 === 1}
    <span class={accentClass}>{part}</span>
  {:else}
    {part}
  {/if}
{/each}
