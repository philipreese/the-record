import { beforeEach, describe, expect, it } from 'vitest';
import { appCache } from './store.svelte';

describe('AppCache sync token', () => {
  beforeEach(() => {
    localStorage.clear();
    appCache.setSyncToken('');
  });

  it('persists the token to localStorage and trims whitespace', () => {
    appCache.setSyncToken('  my-secret  ');
    expect(appCache.syncToken).toBe('my-secret');
    expect(localStorage.getItem('syncToken')).toBe('my-secret');
  });

  it('clears the token when set to empty', () => {
    appCache.setSyncToken('something');
    appCache.setSyncToken('');
    expect(appCache.syncToken).toBe('');
    expect(localStorage.getItem('syncToken')).toBe('');
  });
});
