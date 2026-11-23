import { computed, reactive, ref } from 'vue'
import { apiSource, useParkingApi } from './api'
import { source as demoSource } from './demo'
import { summary, type Parking, type Snapshot } from './parking'

const source = useParkingApi ? apiSource : demoSource

export const parkings = ref<Parking[]>([])
export const snapshots = reactive<Record<string, Snapshot | undefined>>({})
export const now = ref(Date.now())
export const dataError = ref('')
export const pending = ref(false)
export const availability = computed(() =>
  Object.fromEntries(parkings.value.map((p) => [p.id, summary(p, snapshots[p.id], now.value)])),
)
let generation = 0
let inFlight: { id?: string; done: Promise<void> } | undefined

export function tick() {
  now.value = Date.now()
}
function accept(s: Snapshot) {
  const prev = snapshots[s.parkingId]
  if (!prev || Date.parse(s.observedAt) >= Date.parse(prev.observedAt)) snapshots[s.parkingId] = s
}
export function refresh(activeId?: string): Promise<void> {
  if (inFlight && inFlight.id === activeId) return inFlight.done
  const version = ++generation
  const done = load(version, activeId).finally(() => {
    if (generation === version) {
      inFlight = undefined
      pending.value = false
    }
  })
  inFlight = { id: activeId, done }
  return done
}

async function load(version: number, activeId?: string) {
  pending.value = true
  try {
    if (activeId) {
      const p = await source.getParking(activeId)
      if (version !== generation) return
      if (!p) {
        parkings.value = parkings.value.filter((parking) => parking.id !== activeId)
        delete snapshots[activeId]
        dataError.value = ''
        return
      }
      const index = parkings.value.findIndex((item) => item.id === p.id)
      if (index < 0) parkings.value.push(p)
      else if (parkings.value[index] !== p) parkings.value[index] = p
      const s = await source.getOccupancy(activeId)
      if (version !== generation) return
      accept(s)
    } else {
      const listings = await source.listParkings()
      if (version !== generation) return
      parkings.value = listings.map((l) => l.parking)
      const ids = new Set(listings.map((item) => item.parking.id))
      for (const id of Object.keys(snapshots)) if (!ids.has(id)) delete snapshots[id]
      listings.forEach((l) => accept(l.snapshot))
    }
    dataError.value = ''
  } catch {
    if (version === generation) dataError.value = 'Не удалось обновить данные парковки.'
  }
  tick()
}
export function resetParkings() {
  generation++
  inFlight = undefined
  pending.value = false
  for (const id of Object.keys(snapshots)) delete snapshots[id]
  parkings.value = []
  dataError.value = ''
}
