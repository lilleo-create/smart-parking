import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { loadMaps } from './yandex'

export type Point = [longitude: number, latitude: number]
export type Pose = { center: Point; zoom: number }
export interface MapView {
  move(view: Pose): void
  view(): Pose
  pin(point: Point, element: HTMLElement): () => void
  resize(): void
  destroy(): void
}
const latLng = ([lon, lat]: Point): L.LatLngTuple => [lat, lon]

// Project before measuring. Padding leaves room for labels, controls and attribution.
export function fitted(points: Point[], width: number, height: number): Pose {
  const crs = L.CRS.EPSG3857
  const box = L.bounds(points.map((p) => crs.latLngToPoint(L.latLng(...latLng(p)), 0)))
  const size = box.getSize()
  // Allow half a label at either edge, plus the zoom buttons on the right.
  const left = 62,
    right = left + 56
  const top = 94,
    bottom = 42
  const scale = Math.min(
    Math.max(32, width - left - right) / Math.max(size.x, 0.001),
    Math.max(32, height - top - bottom) / Math.max(size.y, 0.001),
  )
  const zoom = Math.min(16, Math.max(2, Math.floor(Math.log2(scale))))
  const midpoint = box.getCenter().multiplyBy(2 ** zoom)
  const offset = L.point((right - left) / 2, (bottom - top) / 2)
  const center = crs.pointToLatLng(midpoint.add(offset), zoom)
  return { center: [center.lng, center.lat], zoom }
}

export function rasterMap(
  host: HTMLElement,
  initial: Pose,
  tileError: (failed: boolean) => void,
  twoGisKey?: string,
): MapView {
  const map = L.map(host, {
    zoomControl: false,
    minZoom: 2,
    maxZoom: 19,
    attributionControl: true,
  }).setView(latLng(initial.center), initial.zoom)
  map.attributionControl.setPrefix(false)
  const url = twoGisKey
    ? 'https://tile0.maps.2gis.com/v2/tiles/online_sd/{z}/{x}/{y}.png?key=' +
      encodeURIComponent(twoGisKey)
    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
  const tiles = L.tileLayer(url, {
    maxZoom: 19,
    maxNativeZoom: twoGisKey ? 18 : 19,
    attribution: twoGisKey
      ? '© <a href="https://2gis.ru/">2ГИС</a>'
      : '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map)
  const failedTiles = new Set<HTMLElement>()
  tiles.on('tileerror', ({ tile }) => {
    failedTiles.add(tile)
    tileError(true)
  })
  function clearTileFailure({ tile }: L.TileEvent) {
    if (failedTiles.delete(tile)) tileError(failedTiles.size > 0)
  }
  tiles.on('tileload', clearTileFailure)
  tiles.on('tileunload', clearTileFailure)
  return {
    move: (v) => {
      map.setView(latLng(v.center), v.zoom, { animate: false })
    },
    view: () => ({ center: [map.getCenter().lng, map.getCenter().lat], zoom: map.getZoom() }),
    pin(point, element) {
      L.DomEvent.disableClickPropagation(element)
      const marker = L.marker(latLng(point), {
        keyboard: false,
        interactive: false,
        icon: L.divIcon({
          html: element,
          className: 'parking-anchor',
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
      }).addTo(map)
      return () => marker.remove()
    },
    resize: () => {
      map.invalidateSize({ pan: false })
    },
    destroy: () => map.remove(),
  }
}

export async function yandexMap(
  host: HTMLElement,
  key: string,
  initial: Pose,
  active: () => boolean,
): Promise<MapView | undefined> {
  const api = await loadMaps(key)
  if (!active()) return
  const map = new api.YMap(host, { location: initial })
  try {
    map.addChild(new api.YMapDefaultSchemeLayer({})).addChild(new api.YMapDefaultFeaturesLayer({}))
  } catch (error) {
    map.destroy()
    throw error
  }
  return {
    move: (v) => map.setLocation(v),
    view: () => ({ center: map.center, zoom: map.zoom }),
    pin(point, element) {
      const pin = new api.YMapMarker({ coordinates: point }, element)
      map.addChild(pin)
      return () => map.removeChild(pin)
    },
    resize() {},
    destroy: () => map.destroy(),
  }
}
