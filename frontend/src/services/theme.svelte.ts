export const themes = ["dark", "synthwave", "dracula", "luxury", "night", "cyberpunk", "dim", "coffee"];

class ThemeManager {
  currentTheme = $state('dark');

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
      }
    }
  }
}

export const themeManager = new ThemeManager();
