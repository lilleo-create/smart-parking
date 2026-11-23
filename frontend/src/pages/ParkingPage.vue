<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Icon from '../components/Icon.vue'
import ParkingGrid from '../components/ParkingGrid.vue'
import { parkings, snapshots, now, pending, dataError } from '../data/state'
import { areaCenter, areaName } from '../data/location'
import { savedSpot, updateSavedSpot } from '../data/saved-spot'
import { fresh, summary, type Spot } from '../data/parking'
const route = useRoute()
const id = computed(() => String(route.params.id))
const parking = computed(() => parkings.value.find((p) => p.id === id.value))
const snap = computed(() => snapshots[id.value])
const currentSnapshot = computed(() => (fresh(snap.value, now.value) ? snap.value : undefined))
const counts = computed(() =>
  parking.value ? summary(parking.value, snap.value, now.value) : undefined,
)
const savedHere = computed(() => {
  const saved = savedSpot.value
  const [lon, lat] = areaCenter.value
  return saved?.parkingId === id.value && saved.area.point[0] === lon && saved.area.point[1] === lat
    ? saved
    : undefined
})
const saveError = ref('')
watch([id, areaCenter], () => {
  saveError.value = ''
})
function save(spot: Spot) {
  const lot = parking.value
  if (!lot) return
  try {
    updateSavedSpot({
      parkingId: lot.id,
      parkingName: lot.name,
      spotId: spot.id,
      spotLabel: spot.label,
      area: { label: areaName.value, point: areaCenter.value },
    })
    saveError.value = ''
  } catch {
    saveError.value = 'Не удалось сохранить место в этом браузере.'
  }
}
function forget() {
  try {
    updateSavedSpot()
    saveError.value = ''
  } catch {
    saveError.value = 'Не удалось удалить отметку.'
  }
}
</script>
<template>
  <section class="page spot-page">
    <template v-if="parking && counts">
      <div class="page-title">
        <div>
          <h1>{{ parking.name }}</h1>
          <p class="subtitle"><Icon name="pin" />{{ parking.address }}</p>
        </div>
      </div>
      <div class="card plan-card">
        <div class="card-head">
          <h2>Схема мест</h2>
          <strong v-if="parking.spots.length" class="spot-count">{{ counts.label }}</strong>
        </div>
        <p v-if="parking.live && !parking.spots.length" role="status">Ожидаем разметку с камеры.</p>
        <p v-if="saveError" role="alert">{{ saveError }}</p>
        <ParkingGrid
          v-if="parking.spots.length"
          @remember="save"
          :parking="parking"
          :snapshot="currentSnapshot"
          :saved-id="savedHere?.spotId"
        >
          <template #legend>
            <div class="legend" role="group" aria-label="Обозначения на схеме">
              <span><i class="free-key"></i>Свободно</span
              ><span><i class="busy-key"></i>Занято</span>
              <span v-if="counts.unknown"><i class="unknown-key"></i>Нет данных</span>
            </div>
          </template>
          <template #status="{ routeHint }">
            <div class="spot-action">
              <p role="status">
                {{
                  routeHint ||
                  (savedHere
                    ? 'Моя машина · ' + savedHere.spotLabel
                    : 'Отметьте на схеме место, где вы припарковались.')
                }}
              </p>
              <button v-if="savedHere" type="button" class="textlink" @click="forget">
                Я уехал
              </button>
            </div>
          </template>
        </ParkingGrid>
      </div>
    </template>
    <p v-else-if="pending">Загружаем парковку…</p>
    <h1 v-else-if="!dataError">Парковка не найдена</h1>
  </section>
</template>
