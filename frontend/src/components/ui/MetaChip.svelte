<script lang="ts">
  let {
    value,
    variant = 'neutral',
  }: {
    value: string;
    variant?: 'primary' | 'neutral';
  } = $props();
</script>

<span class="chip-{variant}">{value}</span>
