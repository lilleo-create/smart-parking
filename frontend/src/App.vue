<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from './components/Icon.vue'
import BrandLogo from './components/BrandLogo.vue'
import { useParkingApi } from './data/api'
import { refresh, tick, resetParkings, dataError } from './data/state'
import { areaCenter, selectAddress } from './data/location'
import { savedSpot } from './data/saved-spot'
import { signOut } from './data/session'
const route = useRoute(),
  router = useRouter()
const privatePage = computed(() => !!route.meta.auth)
const offline = ref(!navigator.onLine)
function connection() {
  offline.value = !navigator.onLine
}
function reload() {
  if (privatePage.value)
    void refresh(typeof route.params.id === 'string' ? route.params.id : undefined)
}
watch(() => route.fullPath, reload, { immediate: true })
watch(areaCenter, () => {
  if (privatePage.value && !useParkingApi) {
    resetParkings()
    reload()
  }
})
let polling: number, clock: number
onMounted(() => {
  polling = window.setInterval(reload, useParkingApi ? 1000 : 5000)
  clock = window.setInterval(tick, 1000)
  window.addEventListener('online', connection)
  window.addEventListener('offline', connection)
})
onUnmounted(() => {
  clearInterval(polling)
  clearInterval(clock)
  window.removeEventListener('online', connection)
  window.removeEventListener('offline', connection)
})
function showCar() {
  const car = savedSpot.value
  if (!car) return
  selectAddress(car.area)
  router.push({ name: 'parking', params: { id: car.parkingId } })
}
function logout() {
  signOut()
  selectAddress()
  resetParkings()
  router.replace('/')
}
</script>
<template>
  <div class="shell" :class="{ inside: privatePage }">
    <header class="top">
      <div class="top-inner">
        <RouterLink v-if="route.name === 'parking'" to="/map" class="quiet"
          ><Icon name="back" />К карте</RouterLink
        >
        <RouterLink v-else :to="privatePage ? '/map' : '/'" aria-label="Smart Parking — на главную"
          ><BrandLogo aria-hidden="true" class="brand"
        /></RouterLink>
        <div class="header-end">
          <RouterLink
            v-if="route.name === 'login' || route.name === 'register'"
            class="quiet"
            to="/"
          >
            <Icon name="back" />На главную
          </RouterLink>
          <button
            v-if="route.name === 'map' && savedSpot"
            type="button"
            class="quiet find-car"
            :aria-label="'Моя машина · ' + savedSpot.spotLabel + ' · ' + savedSpot.parkingName"
            :title="savedSpot.parkingName"
            @click="showCar"
          >
            <Icon name="car" /><span>Моя машина · {{ savedSpot.spotLabel }}</span>
          </button>
          <button v-if="privatePage" class="quiet" @click="logout">
            <Icon name="exit" /><span>Выйти</span>
          </button>
        </div>
      </div>
    </header>
    <p v-if="offline" class="warning" role="status">
      Нет сети. Список парковок и схемы мест доступны, загрузка карты требует подключения.
    </p>
    <p v-if="dataError && privatePage" class="warning" role="status">{{ dataError }}</p>
    <main><RouterView /></main>
  </div>
</template>
