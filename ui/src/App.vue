<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <div class="min-h-screen bg-base-200">
    <header class="navbar bg-base-100 shadow-sm">
      <div class="navbar-start">
        <RouterLink to="/" class="btn btn-ghost text-lg font-bold">
          <span class="text-primary">mdtx</span>
          <span class="hidden sm:inline">翻译工作台</span>
        </RouterLink>
      </div>
      <nav class="navbar-center">
        <ul class="menu menu-horizontal gap-1">
          <li><RouterLink to="/submit">提交任务</RouterLink></li>
          <li><RouterLink to="/config">配置</RouterLink></li>
        </ul>
      </nav>
      <div class="navbar-end">
        <span class="badge badge-ghost badge-sm mr-2">Tauri + Vue3</span>
      </div>
    </header>
    <main class="mx-auto w-full max-w-6xl p-4">
      <RouterView />
    </main>
  </div>
</template>
