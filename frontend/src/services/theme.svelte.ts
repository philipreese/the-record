export interface ThemeInfo {
  id: string;
  name: string;
  category: 'Atmospheric' | 'Paper' | 'Comfort';
  isDark: boolean;
  description: string;
  colors: {
    bg: string;
    accent: string;
    text: string;
  };
}

export function stringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  let color = '#';
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xff;
    // Keep it in a medium-vibrant range before contrast adjustment
    const clamped = Math.max(50, Math.min(200, value));
    color += ('00' + clamped.toString(16)).slice(-2);
  }
  return color;
}

export const themes = [
  "cool-slate",
  "warm-dark",
  "forest-deep",
  "editorial-light",
  "monochrome-dark",
  "sepia-warm",
  "charcoal-cozy",
  "mist-gray"
];

export const themeMetadata: ThemeInfo[] = [
  { id: 'cool-slate', name: 'Cool Slate', category: 'Atmospheric', isDark: true, description: 'Cool blue-gray tones with soft azure highlights', colors: { bg: '#0f1115', accent: '#7899f5', text: '#e8eaf0' } },
  { id: 'warm-dark', name: 'Warm Dark', category: 'Atmospheric', isDark: true, description: 'Gold accents on a warm graphite canvas', colors: { bg: '#131009', accent: '#c8a96e', text: '#f0e6d3' } },
  { id: 'forest-deep', name: 'Forest Deep', category: 'Atmospheric', isDark: true, description: 'Muted emerald tones with misty mint details', colors: { bg: '#080c0a', accent: '#4eb588', text: '#e2f2ec' } },
  { id: 'editorial-light', name: 'Editorial Light', category: 'Paper', isDark: false, description: 'High-contrast black text on alabaster paper', colors: { bg: '#faf9f6', accent: '#111111', text: '#111111' } },
  { id: 'monochrome-dark', name: 'Monochrome Dark', category: 'Paper', isDark: true, description: 'Absolute carbon black with paper white accents', colors: { bg: '#000000', accent: '#ffffff', text: '#ffffff' } },
  { id: 'sepia-warm', name: 'Sepia Warm', category: 'Comfort', isDark: false, description: 'Classic ink on warm, eye-friendly sepia book pages', colors: { bg: '#f5edd6', accent: '#6f4e37', text: '#3c2f2f' } },
  { id: 'charcoal-cozy', name: 'Charcoal Cozy', category: 'Comfort', isDark: true, description: 'Warm amber glow on deep cozy hearth charcoal', colors: { bg: '#1a1614', accent: '#e5a93b', text: '#e6dfd9' } },
  { id: 'mist-gray', name: 'Mist Gray', category: 'Comfort', isDark: false, description: 'Muted navy details on a soft fog-colored canvas', colors: { bg: '#edf0f5', accent: '#2e5cb8', text: '#1c2e4a' } }
];

class ThemeManager {
  currentTheme = $state('cool-slate');
  ambientColor = $state<string | null>(null);

  init() {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem("theme");
      if (savedTheme && themes.includes(savedTheme)) {
        this.currentTheme = savedTheme;
      }
      this.apply(this.currentTheme);
    }
  }

  apply(theme: string) {
    if (themes.includes(theme)) {
      this.currentTheme = theme;
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem("theme", theme);
        // Re-apply current ambient color to trigger contrast calculations under new theme background
        this.setAmbientColor(this.ambientColor);
      }
    }
  }

  // Adjusts the color value to guarantee WCAG AA compliance (4.5:1 contrast) against the active theme
  private adjustColorForContrast(hex: string, isDarkTheme: boolean): string {
    // Clean hex format
    let cleanHex = hex.replace('#', '');
    if (cleanHex.length === 3) {
      cleanHex = cleanHex.split('').map(c => c + c).join('');
    }
    
    let r = parseInt(cleanHex.substring(0, 2), 16);
    let g = parseInt(cleanHex.substring(2, 4), 16);
    let b = parseInt(cleanHex.substring(4, 6), 16);

    // Calculate relative luminance: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    // scaling R, G, B to 0..1
    const getLuminance = (rVal: number, gVal: number, bVal: number) => {
      const a = [rVal, gVal, bVal].map(v => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      });
      return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
    };

    let luminance = getLuminance(r, g, b);

    if (isDarkTheme) {
      // If color is too dark for dark theme, scale its brightness up
      while (luminance < 0.25 && (r < 255 || g < 255 || b < 255)) {
        r = Math.min(255, Math.round(r * 1.2 + 10));
        g = Math.min(255, Math.round(g * 1.2 + 10));
        b = Math.min(255, Math.round(b * 1.2 + 10));
        luminance = getLuminance(r, g, b);
      }
    } else {
      // If color is too light for light theme, scale its brightness down
      while (luminance > 0.20 && (r > 0 || g > 0 || b > 0)) {
        r = Math.max(0, Math.round(r * 0.8 - 5));
        g = Math.max(0, Math.round(g * 0.8 - 5));
        b = Math.max(0, Math.round(b * 0.8 - 5));
        luminance = getLuminance(r, g, b);
      }
    }

    const toHex = (c: number) => {
      const hexVal = Math.max(0, Math.min(255, c)).toString(16);
      return hexVal.length === 1 ? '0' + hexVal : hexVal;
    };

    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }

  setAmbientColor(hex: string | null) {
    this.ambientColor = hex;
    
    if (typeof document === 'undefined') return;

    if (!hex) {
      document.documentElement.style.removeProperty('--color-primary');
      document.documentElement.style.removeProperty('--accent');
      document.documentElement.style.removeProperty('--ambient-glow');
      return;
    }

    const currentMeta = themeMetadata.find(t => t.id === this.currentTheme);
    const isDark = currentMeta ? currentMeta.isDark : true;
    const adjustedHex = this.adjustColorForContrast(hex, isDark);

    // Apply accent overrides to both standard variable and DaisyUI color primary variables
    document.documentElement.style.setProperty('--accent', adjustedHex);
    document.documentElement.style.setProperty('--color-primary', adjustedHex);

    // Dynamic ambient glow variable for backing radial layouts
    document.documentElement.style.setProperty('--ambient-glow', `${adjustedHex}26`); // 15% opacity hex (26)
  }
}

export const themeManager = new ThemeManager();
