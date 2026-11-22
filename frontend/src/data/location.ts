import { readTabItem, writeTabItem } from './tab-storage'
import { computed, shallowRef } from 'vue'
import type { Point } from './map-view'
import type { Address } from './address'

const storageKey = 'smart-parking.search-address'
function readAddress(): Address | undefined {
  try {
    const value = JSON.parse(readTabItem(storageKey) ?? 'null')
    if (
      value &&
      typeof value.label === 'string' &&
      Array.isArray(value.point) &&
      value.point.length === 2 &&
      value.point.every(Number.isFinite) &&
      Math.abs(value.point[0]) <= 180 &&
      Math.abs(value.point[1]) <= 90
    )
      return value
  } catch {
    /* A new tab starts with the Moscow overview. */
  }
}
export const searchAddress = shallowRef<Address | undefined>(readAddress())
const moscow: Point = [37.6, 55.765]
export const areaCenter = computed(() => searchAddress.value?.point ?? moscow)
export const areaName = computed(() => searchAddress.value?.label ?? 'Москва')
export function selectAddress(address?: Address) {
  searchAddress.value = address
  writeTabItem(storageKey, address ? JSON.stringify(address) : null)
}

// Keep the layout of the three entrances stable when the driver returns in another tab.
const seedKey = 'smart-parking.demo-layout'
function layoutSeed() {
  const previous = Number(readTabItem(seedKey))
  const fallback = previous || crypto.getRandomValues(new Uint32Array(1))[0] || 1
  try {
    const stored = Number(localStorage.getItem(seedKey))
    if (stored) return stored
    localStorage.setItem(seedKey, String(fallback))
  } catch {
    writeTabItem(seedKey, String(fallback))
  }
  return fallback
}
const seed = layoutSeed()
export const nearbyEntrances = computed(() => {
  const [lng, lat] = areaCenter.value
  let state = (seed ^ Math.round(lat * 1000) ^ (Math.round(lng * 1000) << 12)) >>> 0
  function random() {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0
    return state / 4294967296
  }
  const rotation = random() * 2 * Math.PI
  return Array.from({ length: 3 }, (_, i) => {
    const angle = rotation + ((i + random() * 0.3) * Math.PI * 2) / 3
    const meters = 450 + random() * 800
    const offsetLat = (meters * Math.cos(angle)) / 111320
    const offsetLng =
      (meters * Math.sin(angle)) / (111320 * Math.max(0.01, Math.cos((lat * Math.PI) / 180)))
    return { lat: lat + offsetLat, lon: ((lng + offsetLng + 540) % 360) - 180 }
  })
})
