type Coordinates = [number, number]
interface MapInstance {
  center: Coordinates
  zoom: number
  setLocation(view: { center?: Coordinates; zoom: number }): void
  addChild(child: unknown): MapInstance
  removeChild(child: unknown): MapInstance
  destroy(): void
}
interface YMaps {
  ready: Promise<void>
  YMap: new (
    host: HTMLElement,
    options: { location: { center: Coordinates; zoom: number } },
  ) => MapInstance
  YMapDefaultSchemeLayer: new (options: {}) => unknown
  YMapDefaultFeaturesLayer: new (options: {}) => unknown
  YMapMarker: new (options: { coordinates: Coordinates }, element: HTMLElement) => unknown
}
declare global {
  interface Window {
    ymaps3?: YMaps
  }
}
let loading: Promise<YMaps> | undefined
export function loadMaps(key: string): Promise<YMaps> {
  if (loading) return loading
  loading = new Promise<YMaps>((resolve, reject) => {
    const script = document.createElement('script')
    const timer = window.setTimeout(fail, 12000)
    function fail() {
      clearTimeout(timer)
      script.remove()
      loading = undefined
      reject(new Error('Карта недоступна'))
    }
    script.onload = async () => {
      try {
        const api = window.ymaps3
        if (!api) throw new Error()
        await api.ready
        clearTimeout(timer)
        resolve(api)
      } catch {
        fail()
      }
    }
    script.onerror = fail
    script.src =
      'https://api-maps.yandex.ru/v3/?' + new URLSearchParams({ apikey: key, lang: 'ru_RU' })
    document.head.append(script)
  })
  return loading
}
export type { MapInstance }
