<script lang="ts">
  interface Props {
    name: 'home' | 'charts' | 'book' | 'sync' | 'flame' | 'crown' | 'clock' | 'calendar' | 'settings' | 'close' | 'logo';
    size?: string; // e.g. "w-5 h-5" or custom
    class?: string;
    style?: string;
  }

  let { 
    name, 
    size = "w-5 h-5", 
    class: className = "",
    style = ""
  }: Props = $props();
</script>

{#if name === 'logo'}
  <!-- Record logo: renders its own SVG because inner circles need mixed fill colors -->
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    class="{size} {className}"
    style={style}
  >
    <circle cx="12" cy="12" r="10" stroke-width="1.5" class="stroke-current" />
    <circle cx="12" cy="12" r="7" stroke-width="0.5" stroke-dasharray="2 1" class="stroke-current opacity-80" />
    <circle cx="12" cy="12" r="4" stroke-width="0.5" stroke-dasharray="1 1" class="stroke-current opacity-60" />
    <circle cx="12" cy="12" r="2.5" class="fill-secondary stroke-none" />
    <circle cx="12" cy="12" r="0.8" class="fill-base-100 stroke-none" />
  </svg>
{:else}
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke-width="1.5"
    stroke="currentColor"
    class="{size} {className}"
    style={style}
  >
    {#if name === 'home'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v4.875h4.875c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    {:else if name === 'charts'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v16.5M21 19.5H3.75M6.75 15v-4.5m3.75 4.5V8.25m3.75 11.25v-8.25m3.75 8.25V6" />
    {:else if name === 'book'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    {:else if name === 'sync'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
    {:else if name === 'flame'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1A3.75 3.75 0 0012 18z" />
    {:else if name === 'crown'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A2.25 2.25 0 006 18.727h12a2.25 2.25 0 002.23-2.233 60.49 60.49 0 00-.492-6.347m-15.42 0L9 15.541l3-8.541 3 8.541 3.86-5.394c.868.19 1.753.29 2.656.29m-17.02 0a20.822 20.822 0 00-2.656.29M12 18.727v-1.5m4.125 1.5v-1.5m-8.25 1.5v-1.5M3 10.147a.75.75 0 110-1.5.75.75 0 010 1.5zm9.75-3.07a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm9 3.07a.75.75 0 110-1.5.75.75 0 010 1.5z" />
    {:else if name === 'clock'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    {:else if name === 'calendar'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
    {:else if name === 'settings'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.43l-1.003.828c-.293.241-.438.613-.43.992a7.723 7.723 0 010 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.954.26 1.43l-1.297 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.43l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.991l-1.004-.827a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.645-.869l.214-1.28z" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    {:else if name === 'close'}
      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
    {/if}
  </svg>
{/if}
