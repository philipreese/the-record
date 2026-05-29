export const themes = ["cool-slate", "warm-dark", "editorial-light", "forest-deep"];

class ThemeManager {
  currentTheme = $state('cool-slate');

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
