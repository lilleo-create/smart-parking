import type { Point } from './map-view'

export interface Address {
  label: string
  point: Point
}

interface GeocodeItem {
  full_address_name?: string
  full_name?: string
  name?: string
  point?: { lon: number; lat: number }
}

export async function findAddresses(query: string, signal: AbortSignal): Promise<Address[]> {
  const key = import.meta.env.VITE_2GIS_MAP_KEY?.trim()
  if (!key) throw new Error('Для поиска адресов нужен ключ 2ГИС с доступом к геокодеру.')
  const params = new URLSearchParams({
    q: query,
    fields: 'items.point,items.full_address_name',
    key,
    locale: 'ru_RU',
    page_size: '5',
  })
  const response = await fetch('https://catalog.api.2gis.com/3.0/items/geocode?' + params, {
    signal,
  })
  if (!response.ok) throw new Error('Поиск адресов временно недоступен. Попробуйте ещё раз.')
  const body: { meta: { code: number }; result?: { items: GeocodeItem[] } } = await response.json()
  if (body.meta.code === 404) return []
  if (body.meta.code !== 200)
    throw new Error('Сервис 2ГИС не смог выполнить поиск. Попробуйте позже.')
  const matches: Address[] = []
  for (const item of body.result?.items ?? []) {
    const label = item.full_address_name || item.full_name || item.name
    if (label && item.point && Number.isFinite(item.point.lon) && Number.isFinite(item.point.lat))
      matches.push({ label, point: [item.point.lon, item.point.lat] })
  }
  return matches
}
