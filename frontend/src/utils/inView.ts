export interface InViewOptions {
  threshold?: number;
  rootMargin?: string;
  once?: boolean;
  callback?: (inView: boolean) => void;
}

/**
 * A Svelte action that adds the class 'in-view' when an element enters the viewport.
 * Useful for triggering CSS-driven transitions and keyframe animations.
 */
export function inView(node: HTMLElement, options: InViewOptions = {}) {
  const threshold = options.threshold ?? 0.1;
  const rootMargin = options.rootMargin ?? '0px 0px -50px 0px';
  const once = options.once ?? true;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          node.classList.add('in-view');
          options.callback?.(true);
          if (once) {
            observer.unobserve(node);
          }
        } else if (!once) {
          node.classList.remove('in-view');
          options.callback?.(false);
        }
      });
    },
    { threshold, rootMargin },
  );

  observer.observe(node);

  return {
    destroy() {
      observer.disconnect();
    },
  };
}
