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
  let hasAnimated = $state(false);

  // Trigger the animation when the element is in viewport AND the target value is loaded (> 0)
  $effect(() => {
    if (isElementInView && !hasAnimated && value > 0) {
      hasAnimated = true;
      animate();
    }
  });

  function handleVisibility(visible: boolean) {
    if (visible) {
      isElementInView = true;
    }
  }

  function animate() {
    const startTime = performance.now();
    const startVal = displayValue;
    const endVal = value;

    function update(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Cubic ease-out curve
      const ease = 1 - Math.pow(1 - progress, 3);

      displayValue = Math.floor(startVal + (endVal - startVal) * ease);

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        displayValue = endVal;
      }
    }

    requestAnimationFrame(update);
  }
</script>

<span use:inView={{ once: true, callback: handleVisibility }} class={className}>
  {displayValue.toLocaleString()}
</span>
