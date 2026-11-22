<script setup lang="ts">
import { computed, reactive, ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { demoLogin, demoPassword, demoRegister, signIn } from '../data/session'
const route = useRoute(),
  router = useRouter()
const register = computed(() => route.name === 'register')
const fields = reactive({ name: '', login: '', password: '', confirm: '' })
type Field = keyof typeof fields
const errors = ref<Partial<Record<Field, string>>>({})
const message = ref(''),
  visible = ref(false),
  sending = ref(false)
const fieldsShown = computed<Field[]>(() =>
  register.value ? ['name', 'login', 'password', 'confirm'] : ['login', 'password'],
)
const labels = { name: 'Имя', login: 'Логин', password: 'Пароль', confirm: 'Подтверждение пароля' }
watch(register, () => {
  message.value = ''
  errors.value = {}
  visible.value = false
  fields.password = ''
  fields.confirm = ''
})
function clearError(key: Field) {
  delete errors.value[key]
  message.value = ''
}
function demoFill() {
  if (register.value) {
    fields.name = 'Алексей'
    fields.confirm = demoPassword
  }
  fields.login = demoLogin
  fields.password = demoPassword
  errors.value = {}
  message.value = ''
}
async function submit() {
  if (sending.value) return
  message.value = ''
  const issues: Partial<Record<Field, string>> = {}
  for (const key of fieldsShown.value) if (!fields[key].trim()) issues[key] = 'Заполните поле'
  if (register.value && fields.password && fields.password.length < 8)
    issues.password = 'Введите минимум 8 символов'
  if (register.value && fields.confirm && fields.confirm !== fields.password)
    issues.confirm = 'Пароли должны совпадать'
  errors.value = issues
  if (Object.keys(issues).length) {
    await nextTick()
    document.getElementById('auth-' + Object.keys(issues)[0])?.focus()
    return
  }
  if (register.value) demoRegister()
  else if (!signIn(fields.login, fields.password)) {
    message.value =
      'Логин или пароль не подошли. Нажмите «Подставить демоданные» для быстрого входа.'
    return
  }
  const next = route.query.next
  const destination =
    typeof next === 'string' && /^\/(map|parkings\/[\w-]+(?:\/(?:drive|route))?)$/.test(next)
      ? next
      : '/map'
  sending.value = true
  try {
    await router.replace(destination)
  } finally {
    sending.value = false
  }
}
</script>
<template>
  <section class="form-page">
    <div class="form-card">
      <div class="auth-heading">
        <h1>{{ register ? 'Регистрация' : 'Вход в демоверсию' }}</h1>
        <button type="button" class="demo-fill" @click="demoFill">Подставить демоданные</button>
      </div>
      <form @submit.prevent="submit" novalidate>
        <label class="field" v-for="key in fieldsShown" :key="key" :for="'auth-' + key"
          >{{ labels[key] }}
          <span class="input-wrap"
            ><input
              v-model="fields[key]"
              :id="'auth-' + key"
              :autocomplete="'off'"
              :type="(key === 'password' || key === 'confirm') && !visible ? 'password' : 'text'"
              :aria-invalid="!!errors[key]"
              :aria-describedby="errors[key] ? 'err-' + key : undefined"
              @input="clearError(key)" />
            <button
              v-if="key === 'password'"
              type="button"
              class="eye"
              :aria-label="visible ? 'Скрыть пароль' : 'Показать пароль'"
              :aria-pressed="visible"
              @click="visible = !visible"
            >
              <Icon name="eye" /></button
          ></span>
          <small class="error" v-if="errors[key]" :id="'err-' + key">{{
            errors[key]
          }}</small></label
        >
        <p v-if="message" class="error" role="alert">{{ message }}</p>
        <button class="button primary" :disabled="sending">
          {{ register ? 'Зарегистрироваться' : 'Войти' }} <Icon name="arrow" />
        </button>
        <p class="auth-switch">
          {{ register ? 'Уже есть профиль?' : 'Впервые здесь?' }}
          <RouterLink :to="{ name: register ? 'login' : 'register', query: route.query }">{{
            register ? 'Войти' : 'Зарегистрироваться'
          }}</RouterLink>
        </p>
      </form>
    </div>
  </section>
</template>
