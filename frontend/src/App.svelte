<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import Sidebar from './components/layout/Sidebar.svelte';
  import Navbar from './components/layout/Navbar.svelte';
  import Footer from './components/layout/Footer.svelte';

  import OverviewView from './views/OverviewView.svelte';
  import ChartsView from './views/ChartsView.svelte';
  import WrappedView from './views/WrappedView.svelte';
  import SettingsView from './views/SettingsView.svelte';
  import RecentView from './views/RecentView.svelte';
  import BlogView from './views/BlogView.svelte';
  import BlogPostView from './views/BlogPostView.svelte';
  import ArtistView from './views/ArtistView.svelte';
  import NotFoundView from './views/NotFoundView.svelte';

  import { themeManager } from './services/theme.svelte';
  import { appCache } from './services/store.svelte';
  import { router } from './services/router.svelte';

  onMount(() => {
    router.init();
    themeManager.init();
    appCache.startPlayingNowPolling();

    const onHashChange = () => router.sync();
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  });
</script>

<div
  class="drawer lg:drawer-open min-h-screen bg-base-100 text-base-content relative z-10 transition-colors duration-300"
>
  <!-- Dynamic Ambient Backing Glow -->
  <div
    class="fixed inset-0 pointer-events-none -z-10 overflow-hidden opacity-25 blur-[120px] transition-all duration-1000"
  >
    <div
      class="absolute top-[-20%] right-[-20%] w-[70%] h-[70%] rounded-full bg-(--ambient-glow,rgba(0,0,0,0)) transition-all duration-1000"
    ></div>
    <div
      class="absolute bottom-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-(--ambient-glow,rgba(0,0,0,0)) opacity-60 transition-all duration-1000"
    ></div>
  </div>

  <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" />

  <!-- Drawer content (Main Screen) -->
  <div class="drawer-content flex flex-col bg-transparent min-h-screen">
    <!-- Navbar (Mobile only) -->
    <Navbar />

    <!-- Main Content Area -->
    <main class="grow p-4 lg:p-8 max-w-350 w-full mx-auto relative z-10">
      <!-- Views conditional rendering with dissolve-reconfigure transition -->
      {#key router.route.type}
        <div in:fade={{ duration: 160, delay: 120 }} out:fade={{ duration: 120 }} class="w-full">
          {#if router.route.type === 'dashboard'}
            <OverviewView />
          {:else if router.route.type === 'charts'}
            <ChartsView />
          {:else if router.route.type === 'wrapped'}
            <WrappedView />
          {:else if router.route.type === 'settings'}
            <SettingsView />
          {:else if router.route.type === 'recent'}
            <RecentView />
          {:else if router.route.type === 'blog'}
            <BlogView />
          {:else if router.route.type === 'blog-post'}
            <BlogPostView slug={router.route.slug} />
          {:else if router.route.type === 'artist'}
            <ArtistView />
          {:else if router.route.type === 'not-found'}
            <NotFoundView />
          {/if}
        </div>
      {/key}

      {#if router.route.type !== 'recent'}
        <Footer />
      {/if}
    </main>
  </div>

  <!-- Fixed footer for the journal tab (infinite scroll pushes the normal footer out of reach) -->
  {#if router.route.type === 'recent'}
    <div
      class="fixed bottom-0 left-0 lg:left-64 right-0 z-20 bg-base-100/95 backdrop-blur-sm [&>div>footer]:mt-0 [&>div>footer]:pt-3 [&>div>footer]:pb-3"
    >
      <div class="max-w-350 w-full mx-auto px-4 lg:px-8">
        <Footer />
      </div>
    </div>
  {/if}

  <!-- Sidebar Container -->
  <Sidebar />
</div>
