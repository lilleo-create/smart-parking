import assert from 'node:assert/strict'
import { after, before, beforeEach, test } from 'node:test'
import { createServer } from 'vite'

let vite, state, source, listings

before(async () => {
  vite = await createServer({
    configFile: false,
    server: { middlewareMode: true, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true },
  })
  state = await vite.ssrLoadModule('/src/data/state.ts')
  const demo = await vite.ssrLoadModule('/src/data/demo.ts')
  source = demo.source
  listings = await source.listParkings()
})
beforeEach(() => state.resetParkings())
after(() => vite?.close())

test('a repeated poll waits for the current request', async (t) => {
  const request = Promise.withResolvers()
  const list = t.mock.method(source, 'listParkings', () => request.promise)
  const first = state.refresh()
  const second = state.refresh()
  assert.equal(list.mock.callCount(), 1)
  request.resolve(listings)
  await Promise.all([first, second])
  assert.equal(state.parkings.value.length, listings.length)
  assert.equal(state.pending.value, false)
})

test('a late map response cannot replace the active parking', async (t) => {
  const request = Promise.withResolvers()
  t.mock.method(source, 'listParkings', () => request.promise)
  const previous = state.refresh()
  const { id } = listings[0].parking
  await state.refresh(id)
  request.resolve(listings)
  await previous
  assert.deepEqual(
    state.parkings.value.map((parking) => parking.id),
    [id],
  )
})

test('a missing parking clears the cached plan and occupancy', async (t) => {
  await state.refresh()
  const { id } = listings[0].parking
  t.mock.method(source, 'getParking', async () => undefined)
  await state.refresh(id)
  assert.ok(!state.parkings.value.some((parking) => parking.id === id))
  assert.equal(state.snapshots[id], undefined)
  assert.equal(state.dataError.value, '')
})

test('a failed refresh can be retried', async (t) => {
  const list = t.mock.method(source, 'listParkings', async () => {
    throw new Error('Unavailable')
  })
  await state.refresh()
  assert.ok(state.dataError.value)
  assert.equal(state.pending.value, false)
  list.mock.restore()
  await state.refresh()
  assert.equal(state.parkings.value.length, listings.length)
  assert.equal(state.dataError.value, '')
})

test('a response with an older observation keeps the newer occupancy', async (t) => {
  await state.refresh()
  const { parking, snapshot } = listings[0]
  const current = state.snapshots[parking.id]
  t.mock.method(source, 'getOccupancy', async () => ({
    ...snapshot,
    observedAt: new Date(Date.parse(current.observedAt) - 1).toISOString(),
    statuses: {},
  }))
  await state.refresh(parking.id)
  assert.equal(state.snapshots[parking.id], current)
})

test('missing observations and expired snapshots do not count as available', async () => {
  const { summary } = await vite.ssrLoadModule('/src/data/parking.ts')
  const { parking, snapshot } = listings[0]
  const expires = Date.parse(snapshot.validUntil)
  const partial = { ...snapshot, statuses: { [parking.spots[0].id]: 'free' } }
  assert.deepEqual(summary(parking, partial, expires - 1), {
    free: 1,
    unknown: parking.spots.length - 1,
    label: '1 свободно',
  })
  assert.deepEqual(summary(parking, partial, expires), {
    free: 0,
    unknown: parking.spots.length,
    label: 'Нет актуальных данных',
  })
})
