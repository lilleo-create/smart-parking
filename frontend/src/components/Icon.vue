<script setup lang="ts">
const paths = {
  arrow: 'M4 12h15m-6-6 6 6-6 6',
  back: 'M20 12H5m6-6-6 6 6 6',
  pin: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  car: 'm4 10 2-6h12l2 6 M3 11h18v7H3z M5 18v2m14-2v2 M6 14h2m8 0h2',
  exit: 'M9 4H4v16h5 M9 12H18 M14 8l4 4-4 4',
  route: 'm21 3-7 18-3-8-8-3 18-7z',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
}
defineProps<{ name: keyof typeof paths }>()
</script>
<template>
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name]" />
  </svg>
</template>
