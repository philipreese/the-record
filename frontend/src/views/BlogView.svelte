<script lang="ts">
  import { router } from '../services/router.svelte';
  import PageHeader from '../components/layout/PageHeader.svelte';

  interface PostMeta {
    slug: string;
    title: string;
    date: string;
    blurb: string;
  }

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

  const posts: PostMeta[] = Object.entries(rawFiles)
    .map(([path, raw]) => {
      const { meta } = parseFrontmatter(raw);
      const filename = path.split('/').pop()!.replace(/\.md$/, '');
      return {
        slug: meta.slug || filename,
        title: meta.title || filename,
        date: meta.date || '',
        blurb: meta.blurb || '',
      };
    })
    .sort((a, b) => b.date.localeCompare(a.date));
</script>

<PageHeader title="writing" subtitle="Long-form notes on the project and the data behind it." />

<div class="max-w-4xl mx-auto py-8 space-y-12">
  <ul class="space-y-8">
    {#each posts as post}
      <li>
        <button
          class="text-left group w-full focus:outline-none cursor-pointer"
          onclick={() => router.navigate(`/blog/${post.slug}`)}
        >
          <time class="text-xs font-mono text-theme-muted tracking-widest uppercase"
            >{post.date}</time
          >
          <h2
            class="mt-1 text-2xl font-serif text-theme-text group-hover:text-theme-accent transition-colors duration-200 leading-snug"
          >
            {post.title}
          </h2>
          {#if post.blurb}
            <p class="mt-2 text-theme-secondary leading-relaxed">{post.blurb}</p>
          {/if}
          <span
            class="mt-3 inline-block text-xs font-mono text-theme-accent opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          >
            Read →
          </span>
        </button>
      </li>
    {/each}
  </ul>
</div>
