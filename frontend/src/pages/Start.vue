<script setup lang="ts">
import Icon from '../components/Icon.vue'
import arrival from '../assets/arrival.png'
</script>
<template>
  <section class="welcome">
    <div class="welcome-copy">
      <h1>Где <span>припарковаться?</span></h1>
      <p>Выберите парковку на карте и посмотрите, какие места свободны.</p>
      <div class="actions">
        <RouterLink class="button primary" to="/login">Войти <Icon name="arrow" /></RouterLink
        ><RouterLink class="button secondary" to="/register">Создать аккаунт</RouterLink>
      </div>
    </div>
    <figure class="hero-art">
      <div class="art-grid"></div>
      <img :src="arrival" alt="Автомобиль и маршрут до парковки на экране телефона" />
    </figure>
  </section>
</template>
