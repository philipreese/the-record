export function portal(node: Element, target: Element = document.body) {
  target.appendChild(node);
  return {
    destroy() {
      node.remove();
    },
  };
}
