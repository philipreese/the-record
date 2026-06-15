import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';

// https://vite.dev/config/
export default defineConfig({
  base: process.env.GITHUB_PAGES ? '/the-record/' : '/',
  plugins: [tailwindcss(), svelte()],
  // Svelte 5 needs the browser build resolved under Vitest so runes work in .svelte.ts modules.
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
  test: {
    environment: 'jsdom',
    globals: true,
  },
  server: {
    proxy: {
      '/api': {
        // Use 127.0.0.1 (not localhost): on Node 17+ localhost can resolve to
        // IPv6 ::1 first, but the backend binds IPv4 127.0.0.1 only.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
