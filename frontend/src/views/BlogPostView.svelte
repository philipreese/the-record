<script lang="ts">
  import { marked } from 'marked';
  import { router } from '../services/router.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';

  interface Props {
    slug: string;
  }

  let { slug }: Props = $props();

  const rawFiles = import.meta.glob('../content/blog/*.md', {
    query: '?raw',
    import: 'default',
    eager: true,
  }) as Record<string, string>;

  function parseFrontmatter(raw: string): { meta: Record<string, string>; body: string } {
    const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) return { meta: {}, body: raw };
    const meta: Record<string, string> = {};
    for (const line of match[1].split('\n')) {
      const colon = line.indexOf(':');
      if (colon > 0) {
        meta[line.slice(0, colon).trim()] = line.slice(colon + 1).trim();
      }
    }
    return { meta, body: match[2] };
  }

  const allPosts = Object.entries(rawFiles).map(([path, raw]) => {
    const { meta, body } = parseFrontmatter(raw);
    const filename = path.split('/').pop()!.replace(/\.md$/, '');
    return { slug: meta.slug || filename, meta, body };
  });

  const entry = $derived(allPosts.find((p) => p.slug === slug));
  const html = $derived(entry ? (marked.parse(entry.body) as string) : '');
  const title = $derived(entry?.meta.title ?? slug);
  const date = $derived(entry?.meta.date ?? '');
</script>

<PageHeader title="writing">
  {#snippet actions(_isShrunk)}
    <button
      class="btn-nav-text text-xs uppercase tracking-widest font-mono text-theme-accent hover:text-theme-accent/80 transition-colors"
      onclick={() => router.navigate('/blog')}
    >
      ← all posts
    </button>
  {/snippet}
</PageHeader>

<div class="max-w-2xl mx-auto py-8">
  {#if entry}
    <article>
      <header class="mb-10">
        {#if date}
          <time class="text-xs font-mono text-theme-muted tracking-widest uppercase">{date}</time>
        {/if}
        <h1 class="mt-2 text-3xl font-serif italic tracking-tight text-theme-text leading-snug">
          {title}
        </h1>
      </header>

      <div class="prose-blog">
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        {@html html}
      </div>
    </article>
  {:else}
    <p class="font-mono text-sm text-theme-muted">Post not found.</p>
  {/if}
</div>

<style>
  .prose-blog :global(h2) {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 1.5rem;
    font-style: italic;
    color: var(--color-text);
    margin-top: 2.5rem;
    margin-bottom: 0.75rem;
    line-height: 1.3;
  }

  .prose-blog :global(h3) {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 1.15rem;
    font-style: italic;
    color: var(--color-text);
    margin-top: 2rem;
    margin-bottom: 0.5rem;
  }

  .prose-blog :global(p) {
    color: var(--color-secondary);
    line-height: 1.75;
    margin-bottom: 1.25rem;
    font-size: 0.9375rem;
  }

  .prose-blog :global(strong) {
    color: var(--color-text);
    font-weight: 600;
  }

  .prose-blog :global(em) {
    font-style: italic;
  }

  .prose-blog :global(a) {
    color: var(--color-accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .prose-blog :global(ul),
  .prose-blog :global(ol) {
    color: var(--color-secondary);
    padding-left: 1.5rem;
    margin-bottom: 1.25rem;
    font-size: 0.9375rem;
    line-height: 1.75;
  }

  .prose-blog :global(li) {
    margin-bottom: 0.25rem;
  }

  .prose-blog :global(code) {
    font-family: var(--font-mono, monospace);
    font-size: 0.85em;
    color: var(--color-accent);
    background: var(--bg-sidebar);
    padding: 0.1em 0.35em;
    border-radius: 3px;
  }

  .prose-blog :global(pre) {
    font-family: monospace;
    font-size: 14px;
    line-height: 1.5;
    white-space: pre;
    background: var(--bg-sidebar);
    border: 1px solid var(--color-border-soft);
    border-radius: 6px;
    padding: 1rem 1.25rem;
    overflow-x: auto;
    margin-bottom: 1.5rem;
    color: var(--color-secondary);
  }

  .prose-blog :global(pre code) {
    background: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
  }

  .prose-blog :global(hr) {
    border: none;
    border-top: 1px solid var(--color-border-soft);
    margin: 2.5rem 0;
  }

  .prose-blog :global(blockquote) {
    border-left: 3px solid var(--color-accent);
    padding-left: 1rem;
    margin-left: 0;
    color: var(--color-muted);
    font-style: italic;
  }
</style>
