export type Status = 'free' | 'occupied' | 'unknown'
export interface Spot {
  id: string
  label: string
  section?: string
  row: string
  position: number
}
export interface Parking {
  id: string
  name: string
  kind: string
  address: string
  entrance: { lat: number; lon: number }
  sectionColumns?: number
  spots: Spot[]
}
export interface Snapshot {
  parkingId: string
  observedAt: string
  validUntil: string
  statuses: Record<string, Status>
}
export interface Listing {
  parking: Parking
  snapshot: Snapshot
}
export interface ParkingSource {
  listParkings(): Promise<Listing[]>
  getParking(id: string): Promise<Parking | undefined>
  getOccupancy(id: string): Promise<Snapshot>
}
export const labels: Record<Status, string> = {
  free: 'Свободно',
  occupied: 'Занято',
  unknown: 'Нет данных',
}
export function fresh(snapshot: Snapshot | undefined, now: number): snapshot is Snapshot {
  return !!snapshot && now < Date.parse(snapshot.validUntil)
}
export function statusOf(snapshot: Snapshot | undefined, id: string, now: number): Status {
  return fresh(snapshot, now) ? (snapshot.statuses[id] ?? 'unknown') : 'unknown'
}
export function summary(parking: Parking, snapshot: Snapshot | undefined, now: number) {
  if (!fresh(snapshot, now)) {
    return { free: 0, unknown: parking.spots.length, label: 'Нет актуальных данных' }
  }
  let free = 0
  let unknown = 0
  for (const spot of parking.spots) {
    const status = snapshot.statuses[spot.id] ?? 'unknown'
    if (status === 'free') free++
    else if (status === 'unknown') unknown++
  }
  let label = free + ' свободно'
  if (!free) label = unknown ? 'Нет точных данных' : 'Мест нет'
  return { free, unknown, label }
}
