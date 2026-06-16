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

    function update(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      displayValue = Math.floor(startVal + (endVal - startVal) * ease);
      if (progress < 1) {
        pendingFrame = requestAnimationFrame(update);
      } else {
        displayValue = endVal;
        pendingFrame = null;
      }
    }

    pendingFrame = requestAnimationFrame(update);
  }
</script>

<span use:inView={{ once: true, callback: handleVisibility }} class={className}>
  {displayValue.toLocaleString()}
</span>
