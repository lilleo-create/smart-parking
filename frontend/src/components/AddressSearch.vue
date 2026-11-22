<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { findAddresses, type Address } from '../data/address'

const props = defineProps<{ label: string; initial?: string }>()
const emit = defineEmits<{ select: [address: Address] }>()
const form = ref<HTMLFormElement>()
const findButton = ref<HTMLButtonElement>()
const query = ref(props.initial ?? '')
const choices = ref<Address[]>([])
const message = ref('')
const busy = ref(false)
let active: AbortController | undefined

function reset() {
  active?.abort()
  active = undefined
  busy.value = false
  choices.value = []
  message.value = ''
}
function choose(address: Address) {
  const fromList = choices.value.length > 0
  reset()
  query.value = address.label
  emit('select', address)
  if (fromList) findButton.value?.focus({ preventScroll: true })
}
async function search() {
  reset()
  const text = query.value.trim()
  if (!text) return
  const controller = new AbortController()
  active = controller
  busy.value = true
  const timeout = window.setTimeout(() => controller.abort(), 12000)
  try {
    const results = await findAddresses(text, controller.signal)
    if (active !== controller) return
    if (results.length === 1) choose(results[0])
    else {
      choices.value = results
      message.value = results.length
        ? 'Выберите адрес'
        : 'Адрес не найден. Уточните город, улицу и номер дома.'
    }
  } catch (e) {
    if (active === controller)
      message.value =
        e instanceof Error && !controller.signal.aborted && !(e instanceof TypeError)
          ? e.message
          : 'Сервис поиска не ответил. Проверьте подключение и попробуйте ещё раз.'
  } finally {
    clearTimeout(timeout)
    if (active === controller) {
      busy.value = false
      active = undefined
    }
  }
}
function dismissOutside(event: PointerEvent | FocusEvent) {
  if (
    (choices.value.length || busy.value) &&
    event.target instanceof Node &&
    !form.value?.contains(event.target)
  )
    reset()
}
function dismiss() {
  if (!choices.value.length && !busy.value) return
  reset()
  findButton.value?.focus({ preventScroll: true })
}
onMounted(() => {
  document.addEventListener('pointerdown', dismissOutside)
  document.addEventListener('focusin', dismissOutside)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', dismissOutside)
  document.removeEventListener('focusin', dismissOutside)
  reset()
})
</script>
<template>
  <form ref="form" class="address-search" @submit.prevent="search" @keydown.esc="dismiss">
    <label>
      {{ label }}
      <input
        v-model="query"
        type="search"
        placeholder="Город, улица, дом"
        maxlength="500"
        required
        @input="reset"
      />
    </label>
    <button
      ref="findButton"
      type="submit"
      class="button secondary"
      :disabled="busy || !query.trim()"
    >
      Найти
    </button>
    <p v-if="busy || message" role="status">{{ busy ? 'Ищем адрес…' : message }}</p>
    <ul v-if="choices.length" aria-label="Найденные адреса">
      <li v-for="item in choices" :key="item.label + item.point.join(',')">
        <button type="button" class="textlink" @click="choose(item)">
          {{ item.label }}
        </button>
      </li>
    </ul>
  </form>
</template>
