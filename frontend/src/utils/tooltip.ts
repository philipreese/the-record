/**
 * Svelte Action directive to show a theme-styled floating tooltip when text is truncated.
 * Detects truncation automatically by checking scrollWidth > clientWidth on hover.
 */
export function tooltip(node: HTMLElement, customText?: string) {
  let tooltipEl: HTMLDivElement | null = null;

  function handleMouseEnter(e: MouseEvent) {
    // Only show tooltip if text is actually truncated with an ellipsis
    if (node.scrollWidth <= node.clientWidth) {
      return;
    }

    const content = customText || node.textContent || '';
    if (!content.trim()) return;

    // Create custom tooltip div matching the design of the heatmap popovers
    tooltipEl = document.createElement('div');
    tooltipEl.className =
      'fixed z-50 pointer-events-none p-2.5 rounded-lg text-[11px] leading-normal shadow-xl border backdrop-blur-md transition-opacity duration-150';

    // Style coordinates and colors using active CSS variables
    tooltipEl.style.backgroundColor = 'var(--bg-base)';
    tooltipEl.style.borderColor = 'color-mix(in srgb, var(--text-primary) 12%, transparent)';
    tooltipEl.style.color = 'var(--text-primary)';
    tooltipEl.style.fontFamily = 'var(--font-mono)';
    tooltipEl.style.opacity = '0';
    tooltipEl.textContent = content;

    document.body.appendChild(tooltipEl);

    // Subtle fade in
    setTimeout(() => {
      if (tooltipEl) tooltipEl.style.opacity = '0.97';
    }, 20);

    positionTooltip(e);
  }

  function handleMouseMove(e: MouseEvent) {
    if (!tooltipEl) return;
    positionTooltip(e);
  }

  function handleMouseLeave() {
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
  }

  function positionTooltip(e: MouseEvent) {
    if (!tooltipEl) return;

    // Position offset from the mouse pointer
    const offsetX = 14;
    const offsetY = 14;

    const x = e.clientX + offsetX;
    const y = e.clientY + offsetY;

    const rect = tooltipEl.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = x;
    let top = y;

    // Colission detection to keep tooltip inside the viewport boundaries
    if (x + rect.width > viewportWidth) {
      left = e.clientX - rect.width - offsetX;
    }
    if (y + rect.height > viewportHeight) {
      top = e.clientY - rect.height - offsetY;
    }

    tooltipEl.style.left = `${left}px`;
    tooltipEl.style.top = `${top}px`;
  }

  node.addEventListener('mouseenter', handleMouseEnter);
  node.addEventListener('mousemove', handleMouseMove);
  node.addEventListener('mouseleave', handleMouseLeave);

  return {
    update(newText?: string) {
      customText = newText;
    },
    destroy() {
      node.removeEventListener('mouseenter', handleMouseEnter);
      node.removeEventListener('mousemove', handleMouseMove);
      node.removeEventListener('mouseleave', handleMouseLeave);
      if (tooltipEl) {
        tooltipEl.remove();
      }
    },
  };
}
