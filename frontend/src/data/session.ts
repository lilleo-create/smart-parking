import { readTabItem, writeTabItem } from './tab-storage'
const key = 'smart-parking.demo-session'
export const demoLogin = 'driver'
export const demoPassword = 'parking123'
export function hasSession() {
  return readTabItem(key) === 'active'
}
export function signIn(login: string, password: string) {
  if (login.trim() !== demoLogin || password !== demoPassword) return false
  writeTabItem(key, 'active')
  return true
}
export function demoRegister() {
  writeTabItem(key, 'active')
}
export function signOut() {
  writeTabItem(key, null)
}
