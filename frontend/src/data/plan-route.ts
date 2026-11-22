// The demo plan has a cross aisle at the entrance, side aisles beside each
// section and a transverse aisle immediately below every row of spaces.
type PlanPoint = [x: number, y: number]

export function routeFromEntrance(
  plan: HTMLElement,
  entrance: HTMLElement,
  bay: HTMLButtonElement,
): PlanPoint[] {
  const origin = plan.getBoundingClientRect()
  const gate = entrance.getBoundingClientRect()
  const section = bay.closest('.lot-inner')!.getBoundingClientRect()
  const box = bay.getBoundingClientRect()
  const halfLane = parseFloat(getComputedStyle(plan).getPropertyValue('--lane-half-width'))
  const startX = gate.left + gate.width / 2 - origin.left
  const startY = gate.top - origin.top
  const x = box.left + box.width / 2 - origin.left
  const y = box.bottom - origin.top
  const aisleY = y + 7
  const left = section.left - origin.left - halfLane
  const right = section.right - origin.left + halfLane
  const distanceVia = (side: number) => Math.abs(startX - side) + Math.abs(side - x)
  const side = distanceVia(left) <= distanceVia(right) ? left : right
  return [
    [startX, startY],
    [side, startY],
    [side, aisleY],
    [x, aisleY],
    [x, y],
  ]
}
