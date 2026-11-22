import { shallowRef } from 'vue'
import type { Address } from './address'

type SavedSpot = {
  parkingId: string
  parkingName: string
  spotId: string
  spotLabel: string
  area: Address
}

const key = 'smart-parking.saved-spot'

function read(): SavedSpot | undefined {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? 'null')
    if (
      value &&
      [value.parkingId, value.parkingName, value.spotId, value.spotLabel, value.area?.label].every(
        (field) => typeof field === 'string' && field.length > 0,
      ) &&
      Array.isArray(value.area.point) &&
      value.area.point.length === 2 &&
      value.area.point.every(Number.isFinite)
    )
      return value
  } catch {
    /* Storage may be unavailable. */
  }
}
export const savedSpot = shallowRef(read())

export function updateSavedSpot(value?: SavedSpot) {
  if (value) localStorage.setItem(key, JSON.stringify(value))
  else localStorage.removeItem(key)
  savedSpot.value = value
}

window.addEventListener('storage', (event) => {
  if (event.key === key || event.key === null) savedSpot.value = read()
})
