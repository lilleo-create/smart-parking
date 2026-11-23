<script setup lang="ts">
import { computed, ref } from 'vue'
import AddressSearch from '../components/AddressSearch.vue'
import { searchAddress, selectAddress } from '../data/location'
import CityMap from '../components/CityMap.vue'
import Icon from '../components/Icon.vue'
import { useParkingApi } from '../data/api'
import { parkings, availability, pending, dataError } from '../data/state'
const hovered = ref<string>()
const focused = ref<string>()
const highlighted = computed(() => hovered.value ?? focused.value)
const list = ref<HTMLElement>()

function focusParking(id?: string) {
  if (id) hovered.value = undefined
  focused.value = id
}
function hoverPin(id?: string) {
  hovered.value = id
  revealRow(id)
}
function focusPin(id?: string) {
  focusParking(id)
  revealRow(id)
}
function revealRow(id?: string) {
  const panel = list.value
  if (!id || !panel || panel.scrollHeight <= panel.clientHeight) return
  const row = panel.querySelector<HTMLElement>(`[data-parking-id="${CSS.escape(id)}"]`)
  if (!row) return
  const bounds = panel.getBoundingClientRect()
  const target = row.getBoundingClientRect()
  if (target.top < bounds.top) panel.scrollTop += target.top - bounds.top
  else if (target.bottom > bounds.bottom) panel.scrollTop += target.bottom - bounds.bottom
}
</script>
<template>
  <section class="page map-page" :class="{ 'fixed-catalog': useParkingApi }">
    <h1>Карта парковок</h1>
    <div class="map-layout">
      <AddressSearch
        v-if="!useParkingApi"
        label="Где ищем парковку?"
        :initial="searchAddress?.label"
        @select="selectAddress"
      />
      <template v-if="parkings.length">
        <CityMap :highlighted="highlighted" @hover="hoverPin" @focus-pin="focusPin" />
        <aside class="card list-card">
          <h2>{{ useParkingApi ? 'Демонстрационные парковки' : 'Парковки рядом' }}</h2>
          <p class="list-context">{{ useParkingApi ? 'Москва' : searchAddress?.label ?? 'Москва' }}</p>
          <div ref="list" class="parking-results">
            <RouterLink
              class="parking-link"
              v-for="p in parkings"
              :key="p.id"
              :data-parking-id="p.id"
              :class="{ highlighted: highlighted === p.id }"
              @mouseenter="hovered = p.id"
              @mouseleave="hovered = undefined"
              @focus="focusParking(p.id)"
              @blur="focused = undefined"
              :to="{ name: 'parking', params: { id: p.id } }"
            >
              <span class="parking-icon">P</span
              ><span
                ><strong>{{ p.name }}</strong
                ><small>{{ p.kind }}</small
                ><em>{{ availability[p.id].label }}</em></span
              ><Icon name="arrow"
            /></RouterLink>
          </div>
        </aside>
      </template>
      <p v-else-if="pending">Загружаем парковки…</p>
      <p v-else-if="!dataError">Список парковок пока пуст.</p>
    </div>
  </section>
</template>
