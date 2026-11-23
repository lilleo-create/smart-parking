import type { Listing, Parking, ParkingSource, Snapshot } from './parking'

export const useParkingApi = import.meta.env.VITE_PARKING_API === '1'

async function get(path: string) {
  return fetch(`/api/parkings${path}`, {
    cache: 'no-store',
    signal: AbortSignal.timeout(5000),
  })
}

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Ошибка API (${response.status})`)
  return response.json()
}

export const apiSource: ParkingSource = {
  async listParkings() {
    return read<Listing[]>(await get(''))
  },
  async getParking(id) {
    const response = await get(`/${encodeURIComponent(id)}`)
    if (response.status === 404) return undefined
    return read<Parking>(response)
  },
  async getOccupancy(id) {
    return read<Snapshot>(await get(`/${encodeURIComponent(id)}/occupancy`))
  },
}
