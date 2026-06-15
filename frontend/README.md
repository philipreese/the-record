# The Record - Frontend Application ⚡

This directory contains the Svelte 5 single-page application built with Vite, TypeScript, Tailwind CSS, and DaisyUI.

---

## 🏗 Key Concepts & Design Patterns

### 1. Svelte 5 Runes

The application is built on Svelte 5's reactivity system. We use `$state` and `$derived` for reactive layouts, and `$effect` paired with `untrack()` to coordinate backend API syncs without triggering tracking loops.

### 2. Global Caching Store

To ensure instantaneous tab switching, API responses are saved to a global store cache. When a tab is clicked, the UI instantly renders the cached data while refreshing the state in the background.

### 3. Generated TypeScript Models

TypeScript interfaces for API data are synchronized directly from backend Pydantic models via OpenAPI. This ensures compile-time safety and prevents structural drift.

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🛠 Available Scripts

- `npm run dev` — Run local Vite dev server.
- `npm run build` — Build production bundle to `/dist`.
- `npm run lint` — Runs `svelte-check` to type-check Svelte and TypeScript files.
