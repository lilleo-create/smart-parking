<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { statusOf, labels, type Parking, type Snapshot, type Spot } from '../data/parking'
import Icon from './Icon.vue'
import { routeFromEntrance } from '../data/plan-route'
const props = defineProps<{
  parking: Parking
  snapshot?: Snapshot
  savedId?: string
}>()
const emit = defineEmits<{ remember: [spot: Spot] }>()
const cameraPlan = computed(() => props.parking.spots.some((spot) => spot.planRow !== undefined))
const sections = computed(() => {
  const groups = new Map<string, Map<string, Parking['spots']>>()
  for (const spot of props.parking.spots) {
    const section = spot.section ?? ''
    const rows = groups.get(section) ?? new Map<string, Parking['spots']>()
    groups.set(section, rows)
    const row = rows.get(spot.row) ?? []
    row.push(spot)
    rows.set(spot.row, row)
  }
  return Array.from(groups, ([id, rows]) => ({
    id,
    rows: Array.from(rows, ([id, spots]) => ({
      id,
      spots: spots.sort((a, b) => a.position - b.position),
    })),
  }))
})
const viewport = ref<HTMLElement>()

const plan = ref<HTMLElement>()
const entrance = ref<HTMLElement>()
const routeButton = ref<HTMLButtonElement>()
const routing = ref(false)
const selected = ref<Spot>()
const message = ref('')
const path = ref<ReturnType<typeof routeFromEntrance>>()
function bayStatus(id: string) {
  return props.snapshot?.statuses[id] ?? 'unknown'
}
const selectedStatus = computed(() => selected.value && bayStatus(selected.value.id))
function resetChoice() {
  selected.value = undefined
  routing.value = false
  message.value = ''
}
async function activate(spot: Spot, event: MouseEvent) {
  const status = statusOf(props.snapshot, spot.id, Date.now())
  if (status === 'unknown') return
  resetChoice()
  if (status === 'free') {
    selected.value = spot
    if (event.detail === 0) {
      await nextTick()
      routeButton.value?.focus()
    }
  } else emit('remember', spot)
}
watch(selectedStatus, (status) => {
  if (!selected.value || status === 'free') return
  const label = selected.value.label
  resetChoice()
  message.value =
    status === 'occupied'
      ? 'Место ' + label + ' уже занято.'
      : 'Нет свежих данных о месте ' + label + '.'
})
function refreshRoute() {
  const bay =
    selected.value &&
    plan.value?.querySelector<HTMLButtonElement>(
      '[data-spot="' + CSS.escape(selected.value.id) + '"]',
    )
  path.value =
    routing.value && selectedStatus.value === 'free' && bay && plan.value && entrance.value
      ? routeFromEntrance(plan.value, entrance.value, bay)
      : undefined
}
watch([routing, selected, sections, selectedStatus], refreshRoute, { flush: 'post' })
let observer: ResizeObserver | undefined
onMounted(() => {
  observer = new ResizeObserver(refreshRoute)
  if (plan.value) observer.observe(plan.value)
})
onBeforeUnmount(() => observer?.disconnect())
watch(() => props.parking.id, resetChoice)

function reveal(element?: HTMLElement | null, alignStart = false) {
  const panel = viewport.value
  if (!panel || !element) return
  const bounds = panel.getBoundingClientRect()
  const target = element.getBoundingClientRect()
  const left = target.left - bounds.left - 4
  const top = target.top - bounds.top - 4
  panel.scrollBy({
    left:
      alignStart || left < 0
        ? left
        : Math.max(0, target.right - bounds.left - panel.clientWidth + 4),
    top:
      alignStart || top < 0
        ? top
        : Math.max(0, target.bottom - bounds.top - panel.clientHeight + 4),
  })
}

function showSaved() {
  const saved = viewport.value?.querySelector<HTMLElement>('.remembered')
  if (saved) reveal(saved)
  else viewport.value?.scrollTo(0, 0)
}
onMounted(showSaved)
watch(() => props.parking.id, showSaved, { flush: 'post' })

function jump(event: Event) {
  const select = event.target as HTMLSelectElement
  const section = viewport.value?.querySelector<HTMLElement>(
    '[data-section="' + CSS.escape(select.value) + '"]',
  )
  reveal(section, true)
  select.value = ''
  section?.focus({ preventScroll: true })
}
</script>
<template>
  <div class="lot" role="group" aria-label="Схема парковки">
    <slot name="legend" />
    <div class="plan-route-tools">
      <button
        v-if="selected"
        ref="routeButton"
        class="route-toggle"
        type="button"
        :aria-pressed="routing"
        @click="routing = !routing"
      >
        <Icon name="route" />{{
          routing ? 'Скрыть путь до ' + selected.label : 'Проложить путь до ' + selected.label
        }}
      </button>
    </div>
    <select
      v-if="sections.length > 4"
      class="section-jump"
      aria-label="Перейти к секции"
      @change="jump"
    >
      <option value="" disabled selected>Перейти к секции…</option>
      <option v-for="section in sections" :key="section.id" :value="section.id">
        {{ section.id ? 'Секция ' + section.id : 'Без секции' }}
      </option>
    </select>
    <div
      ref="viewport"
      class="lot-scroll"
      tabindex="0"
      role="region"
      :aria-label="cameraPlan ? 'Парковочные места на схеме' : 'Парковочные места по секциям'"
    >
      <div ref="plan" class="lot-plan">
        <svg v-if="path" class="plan-path" aria-hidden="true">
          <polyline :points="path.map((p) => p.join(',')).join(' ')" />
        </svg>
        <div
          class="lot-sections"
          :style="{
            gridTemplateColumns:
              'repeat(' +
              Math.min(parking.sectionColumns ?? 2, sections.length || 1) +
              ', max-content)',
          }"
        >
          <section
            class="lot-inner"
            :class="{ 'lot-inner--camera': cameraPlan }"
            v-for="section in sections"
            :key="section.id"
            :data-section="section.id"
            tabindex="-1"
          >
            <h3 v-if="section.id">Секция {{ section.id }}</h3>
            <div v-for="row in section.rows" :key="row.id" class="spot-row">
              <div class="bays">
                <button
                  type="button"
                  @click="activate(spot, $event)"
                  :disabled="bayStatus(spot.id) === 'unknown'"
                  :aria-pressed="savedId === spot.id || selected?.id === spot.id"
                  v-for="spot in row.spots"
                  :key="spot.id"
                  class="bay"
                  :data-spot="spot.id"
                  :data-label="spot.label"
                  :style="{ gridColumn: spot.position, gridRow: spot.planRow }"
                  :class="[
                    bayStatus(spot.id),
                    { remembered: savedId === spot.id, destination: selected?.id === spot.id },
                  ]"
                  :aria-label="
                    'Место ' +
                    spot.label +
                    ' — ' +
                    labels[bayStatus(spot.id)] +
                    (savedId === spot.id ? ', моя машина' : '') +
                    (bayStatus(spot.id) === 'free'
                      ? ', выбрать для маршрута'
                      : bayStatus(spot.id) === 'occupied'
                        ? ', запомнить место'
                        : '')
                  "
                >
                  <Icon v-if="savedId === spot.id" name="pin" /><Icon
                    v-else-if="bayStatus(spot.id) === 'occupied'"
                    name="car"
                  /><span v-else aria-hidden="true">{{
                    bayStatus(spot.id) === 'unknown' ? '?' : 'Р'
                  }}</span
                  ><b>{{ spot.label }}</b>
                </button>
              </div>
            </div>
          </section>
        </div>
        <div ref="entrance" class="entrance"><span>↑</span> Въезд</div>
      </div>
    </div>
    <slot name="status" :route-hint="message" />
  </div>
</template>
