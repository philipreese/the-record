export type Route =
  | { type: 'dashboard' | 'charts' | 'wrapped' | 'recent' | 'settings' | 'blog' | 'not-found' }
  | { type: 'artist'; name: string }
  | { type: 'blog-post'; slug: string };

const VALID_TABS = ['dashboard', 'charts', 'wrapped', 'recent', 'settings', 'blog'] as const;
type ValidTab = (typeof VALID_TABS)[number];

class Router {
  #hash = $state('');

  init(): void {
    const h = window.location.hash;
    if (!h || h === '#') {
      history.replaceState(null, '', '#/');
      this.#hash = '#/';
    } else {
      this.#hash = h;
    }
  }

  sync(): void {
    this.#hash = window.location.hash;
  }

  get route(): Route {
    const raw = this.#hash.startsWith('#') ? this.#hash.slice(1) : '/';
    const [pathPart] = raw.split('?');
    const segments = pathPart.split('/').filter(Boolean);
    const first = segments[0] || 'dashboard';
    if (first === 'artist' && segments[1]) {
      return { type: 'artist', name: decodeURIComponent(segments[1]) };
    }
    if (first === 'blog' && segments[1]) {
      return { type: 'blog-post', slug: decodeURIComponent(segments[1]) };
    }
    return VALID_TABS.includes(first as ValidTab)
      ? { type: first as ValidTab }
      : { type: 'not-found' };
  }

  get params(): URLSearchParams {
    const raw = this.#hash.startsWith('#') ? this.#hash.slice(1) : '';
    const idx = raw.indexOf('?');
    return new URLSearchParams(idx >= 0 ? raw.slice(idx + 1) : '');
  }

  navigate(path: string, replace = false): void {
    const hash = path.startsWith('/') ? path : '/' + path;
    if (replace) {
      history.replaceState(null, '', '#' + hash);
      this.#hash = '#' + hash;
    } else {
      window.location.hash = hash;
    }
  }
}

export const router = new Router();
