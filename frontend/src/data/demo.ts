import { computed } from 'vue'
import { areaName, nearbyEntrances } from './location'
import type { Parking, ParkingSource, Snapshot, Status } from './parking'

// Row codes are unique within a parking lot and form the camera spot IDs (A1, A2, …).
type Layout = { section: string; rows: Record<string, number> }[]
const defaultLayout: Layout = [
  { section: '1', rows: { A: 3, B: 3 } },
  { section: '2', rows: { C: 3, D: 3 } },
  { section: '3', rows: { E: 3, F: 3 } },
  { section: '4', rows: { G: 3, H: 3 } },
]

function buildSpots(layout: Layout) {
  return layout.flatMap(({ section, rows }) =>
    Object.entries(rows).flatMap(([row, count]) =>
      Array.from({ length: count }, (_, index) => {
        const position = index + 1
        const id = row + position
        return { id, label: id, section, row, position }
      }),
    ),
  )
}

const sites = [
  {
    id: 'open-lot',
    name: 'Открытая стоянка',
    kind: 'Частная парковка',
    layout: defaultLayout,
    sectionColumns: 2,
    free: ['A2', 'A3', 'B1', 'C1', 'D3', 'E2', 'F1', 'G2', 'H3'],
  },
  {
    id: 'courtyard',
    name: 'Двор жилого комплекса',
    kind: 'Придомовая парковка',
    layout: defaultLayout,
    sectionColumns: 2,
    free: ['A2', 'B2', 'D1', 'F3', 'G2'],
  },
  {
    id: 'business',
    name: 'Парковка бизнес-центра',
    kind: 'Корпоративная парковка',
    layout: defaultLayout,
    sectionColumns: 2,
    free: ['A1', 'A2', 'A3', 'B3', 'C2', 'D1', 'D3', 'E1', 'F2', 'G1', 'G3', 'H2'],
  },
]
const lots = computed<Parking[]>(() =>
  sites.map((site, i) => ({
    id: site.id,
    name: site.name,
    kind: site.kind,
    address: areaName.value,
    entrance: nearbyEntrances.value[i],
    sectionColumns: site.sectionColumns,
    spots: buildSpots(site.layout),
  })),
)
function sample(parking: Parking): Snapshot {
  const now = Date.now()
  const free = sites.find((site) => site.id === parking.id)!.free
  const statuses: Record<string, Status> = Object.fromEntries(
    parking.spots.map((spot) => [spot.id, free.includes(spot.id) ? 'free' : 'occupied']),
  )
  return {
    parkingId: parking.id,
    observedAt: new Date(now).toISOString(),
    validUntil: new Date(now + 15000).toISOString(),
    statuses,
  }
}
export const source: ParkingSource = {
  async listParkings() {
    return lots.value.map((parking) => ({ parking, snapshot: sample(parking) }))
  },
  async getParking(id) {
    return lots.value.find((p) => p.id === id)
  },
  async getOccupancy(id) {
    const parking = lots.value.find((p) => p.id === id)
    if (!parking) throw new Error('Парковка не найдена')
    return sample(parking)
  },
}
