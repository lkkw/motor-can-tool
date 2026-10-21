<script setup lang="ts">
import { ref } from 'vue'

type Theme = 'light' | 'dark'

const THEME_KEY = 'motorcan.theme' // also read by the pre-paint script in index.html

// index.html has already set data-theme before the app mounted
const theme = ref<Theme>(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark')

function toggle() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  // Switch every color at once: without this, elements with transition-colors fade
  // while the rest snap, which looks like a half-applied theme for a moment
  const root = document.documentElement
  root.classList.add('theme-switching')
  root.dataset.theme = theme.value
  void getComputedStyle(root).color // force style recalc with transitions off
  root.classList.remove('theme-switching')
  try {
    localStorage.setItem(THEME_KEY, theme.value)
  } catch {
    // Not persisted; theme still applies for this session
  }
}
</script>

<template>
  <button
    class="w-7 h-7 flex items-center justify-center rounded border border-border text-fg-secondary hover:text-accent-fg hover:bg-bg-hover transition-colors"
    :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
    :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
    @click="toggle"
  >
    <!-- Sun: shown in dark theme (click for light) -->
    <svg v-if="theme === 'dark'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
    <!-- Moon: shown in light theme (click for dark) -->
    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  </button>
</template>
