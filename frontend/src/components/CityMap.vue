<script lang="ts">
let overview: { pose: Pose; locations: string; size: string; provider: string } | undefined
</script>
<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import demoMap from '../assets/moscow-demo.webp'
import { useParkingApi } from '../data/api'
import { availability, parkings } from '../data/state'
import type { Parking } from '../data/parking'
import { fitted, rasterMap, yandexMap, type MapImage, type MapView, type Point, type Pose } from '../data/map-view'

const props = defineProps<{ highlighted?: string }>()
const emit = defineEmits<{ hover: [id?: string]; focusPin: [id?: string] }>()
const host = ref<HTMLElement>()
const router = useRouter()
const coords = (p: Parking): Point => [p.entrance.lon, p.entrance.lat]
const demoBackground: MapImage = {
  src: demoMap,
  bounds: [[55.728, 37.526], [55.806, 37.674]],
}
function insideDemoMap([lon, lat]: Point) {
  const [[south, west], [north, east]] = demoBackground.bounds
  return south <= lat && lat <= north && west <= lon && lon <= east
}
const locations = computed(() => JSON.stringify(parkings.value.map((p) => [p.id, ...coords(p)])))
const tilesMissing = ref(false)
const ready = ref(false)
const provider = ref('')
let view: MapView | undefined,
  observer: ResizeObserver | undefined,
  alive = true
const pins = new Map<string, { el: HTMLButtonElement; remove: () => void }>()
function bounds() {
  return fitted(parkings.value.map(coords), host.value!.clientWidth, host.value!.clientHeight)
}
function size() {
  return host.value!.clientWidth + 'x' + host.value!.clientHeight
}
function fit() {
  if (!view || !parkings.value.length) return
  view.move(bounds())
}
function zoom(delta: number) {
  if (!view) return
  const pos = view.view()
  view.move({ ...pos, zoom: Math.max(2, Math.min(19, pos.zoom + delta)) })
}
function paintLabels() {
  parkings.value.forEach((p) => {
    const el = pins.get(p.id)?.el
    if (!el) return
    const info = availability.value[p.id]
    const label = info.label
    if (el.textContent !== label) el.textContent = label
    el.dataset.compact = 'P · ' + (!p.spots.length || (!info.free && info.unknown) ? '?' : info.free)
    el.title = p.name + ' — ' + info.label
    el.setAttribute('aria-label', el.title)
  })
}
function paintPins() {
  if (!view) return
  pins.forEach((pin) => pin.remove())
  pins.clear()
  for (const parking of parkings.value) {
    const el = document.createElement('button')
    el.type = 'button'
    el.className = 'geo-pin'
    el.classList.toggle('highlighted', props.highlighted === parking.id)
    el.onmouseenter = () => emit('hover', parking.id)
    el.onmouseleave = () => emit('hover')
    el.onfocus = () => emit('focusPin', parking.id)
    el.onblur = () => emit('focusPin')
    el.onclick = (e) => {
      e.stopPropagation()
      router.push({ name: 'parking', params: { id: parking.id } })
    }
    pins.set(parking.id, { el, remove: view.pin(coords(parking), el) })
  }
  paintLabels()
}
watch(locations, () => {
  paintPins()
  fit()
})
watch(availability, paintLabels)
watch(
  () => props.highlighted,
  (id) => {
    for (const [parkingId, pin] of pins) pin.el.classList.toggle('highlighted', parkingId === id)
  },
)
onMounted(async () => {
  const el = host.value!
  const initial =
    overview?.locations === locations.value && overview.size === size() ? overview.pose : bounds()
  const key = import.meta.env.VITE_YANDEX_MAPS_KEY?.trim()
  if (key) {
    try {
      view = await yandexMap(el, key, initial, () => alive)
      provider.value = 'Яндекс Карты'
    } catch {
      /* Ниже подключается резервная карта. */
    }
  }
  if (!alive) return
  if (!view) {
    const backupKey = import.meta.env.VITE_2GIS_MAP_KEY?.trim()
    const background =
      useParkingApi && !backupKey && parkings.value.every((p) => insideDemoMap(coords(p)))
        ? demoBackground
        : undefined
    view = rasterMap(el, initial, (failed) => (tilesMissing.value = failed), backupKey, background)
    provider.value = backupKey ? '2ГИС' : 'OpenStreetMap'
  }
  ready.value = true
  paintPins()
  if (
    !overview ||
    overview.locations !== locations.value ||
    overview.size !== size() ||
    overview.provider !== provider.value
  )
    fit()
  let lastSize = size()
  observer = new ResizeObserver(() => {
    if (lastSize === size()) return
    lastSize = size()
    view?.resize()
    fit()
  })
  observer.observe(el)
})
onBeforeUnmount(() => {
  alive = false
  observer?.disconnect()
  if (view && ready.value)
    overview = {
      pose: view.view(),
      locations: locations.value,
      size: size(),
      provider: provider.value,
    }
  view?.destroy()
})
</script>
<template>
  <div class="city-map" :data-provider="provider">
    <div ref="host" class="map-host" role="region" aria-label="Интерактивная карта парковок"></div>
    <div class="map-tools" v-if="ready">
      <button type="button" @click="fit">Все парковки</button>
      <div class="zoom-tools">
        <button aria-label="Приблизить" @click="zoom(1)">+</button
        ><button aria-label="Отдалить" @click="zoom(-1)">−</button>
      </div>
    </div>
    <span v-if="!ready || tilesMissing" class="map-notice" role="status">{{
      ready ? 'Подложка карты недоступна. Парковки можно выбрать в списке.' : 'Загружаем карту…'
    }}</span>
  </div>
</template>
