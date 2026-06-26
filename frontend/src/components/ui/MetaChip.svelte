<script lang="ts">
  let {
    value,
    variant = 'neutral',
    class: extraClass = '',
  }: {
    value: string;
    variant?: 'primary' | 'neutral';
    class?: string;
  } = $props();
</script>

<span class="chip-{variant} {extraClass}">{value}</span>
