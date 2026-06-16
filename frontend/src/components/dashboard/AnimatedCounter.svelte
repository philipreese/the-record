<script lang="ts">
  import { inView } from '../../utils/inView';

  let {
    value,
    duration = 800,
    class: className = '',
  }: {
    value: number;
    duration?: number;
    class?: string;
  } = $props();

  let displayValue = $state(0);
  let isElementInView = $state(false);
  let pendingFrame: number | null = null;

  // Re-trigger animation whenever value changes while in view (handles cached data switches)
  $effect(() => {
    if (isElementInView && value > 0) {
      animate();
    }
  });

  function handleVisibility(visible: boolean) {
    if (visible) {
      isElementInView = true;
    }
  }

  function animate() {
    if (pendingFrame !== null) {
      cancelAnimationFrame(pendingFrame);
      pendingFrame = null;
    }
    const startTime = performance.now();
    const startVal = displayValue;
    const endVal = value;
    // Preserve the target's decimal precision during animation so the counter
    // never shows a floored integer that then jumps to a decimal at the end.
    const decimals = (String(endVal).split('.')[1] ?? '').length;

    function update(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const raw = startVal + (endVal - startVal) * ease;
      displayValue = progress < 1 ? parseFloat(raw.toFixed(decimals)) : endVal;
      if (progress < 1) {
        pendingFrame = requestAnimationFrame(update);
      } else {
        pendingFrame = null;
      }
    }

    pendingFrame = requestAnimationFrame(update);
  }
</script>

<span use:inView={{ once: true, callback: handleVisibility }} class={className}>
  {displayValue.toLocaleString()}
</span>
