<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink, RouterView, useRouter } from "vue-router";
import { getApiBase } from "./api/client";
import { checkConnection, connection } from "./connection";
import { isTauri } from "./tauri";

const router = useRouter();
const theme = ref<"corporate" | "dim">(
  (localStorage.getItem("mdtx-theme") as "corporate" | "dim") ?? "corporate",
);

function applyTheme(value: "corporate" | "dim") {
  theme.value = value;
  localStorage.setItem("mdtx-theme", value);
  document.documentElement.setAttribute("data-theme", value);
}

onMounted(() => applyTheme(theme.value));

function retryConnection() {
  // In the Tauri shell a missed handshake can only be recovered by re-running
  // the bootstrap (the sidecar may already be listening by now).
  if (isTauri() && !getApiBase()) {
    window.location.reload();
    return;
  }
  void checkConnection();
}

const navItems = [
  { to: "/submit", label: "新建任务", icon: "M12 5v14m-7-7h14" },
  { to: "/jobs", label: "任务记录", icon: "M4 6h16M4 12h16M4 18h10" },
  { to: "/config", label: "配置", icon: "M10.325 4.317a1.724 1.724 0 013.35 0 1.724 1.724 0 002.573 1.066 1.724 1.724 0 012.421 2.421 1.724 1.724 0 001.066 2.573 1.724 1.724 0 010 3.35 1.724 1.724 0 00-1.066 2.573 1.724 1.724 0 01-2.421 2.421 1.724 1.724 0 00-2.573 1.066 1.724 1.724 0 01-3.35 0 1.724 1.724 0 00-2.573-1.066 1.724 1.724 0 01-2.421-2.421A1.724 1.724 0 004.317 13.675a1.724 1.724 0 010-3.35 1.724 1.724 0 001.066-2.573 1.724 1.724 0 012.421-2.421c.577.234 1.223.23 1.621-.114z" },
];
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-base-200">
    <!-- 侧边栏 -->
    <aside class="flex w-56 shrink-0 flex-col border-r border-base-300 bg-base-100">
      <div class="flex items-center gap-2 px-5 pt-5 pb-4">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary font-black text-primary-content">m</div>
        <div>
          <div class="text-sm font-bold leading-tight">mdtx</div>
          <div class="text-[10px] leading-tight text-base-content/50">翻译工作台</div>
        </div>
      </div>

      <nav class="px-3">
        <ul class="menu w-full gap-1 p-0">
          <li v-for="item in navItems" :key="item.to">
            <RouterLink :to="item.to" class="gap-3 rounded-lg" active-class="menu-active">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="item.icon" />
              </svg>
              {{ item.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>

      <div class="mt-auto flex flex-col gap-2 p-3">
        <button
          class="flex items-center justify-between rounded-lg px-2 py-1.5 text-xs text-base-content/60 hover:bg-base-200"
          title="点击重新检测连接"
          @click="retryConnection()"
        >
          <span class="flex items-center gap-2">
            <span
              class="inline-block h-2 w-2 rounded-full"
              :class="connection.checking ? 'bg-warning animate-pulse' : connection.online ? 'bg-success' : 'bg-error'"
            ></span>
            {{ connection.checking ? "检测中…" : connection.online ? "后端已连接" : "后端未连接" }}
          </span>
        </button>
        <label class="label cursor-pointer justify-between rounded-lg px-2 py-1.5 text-xs text-base-content/60 hover:bg-base-200">
          <span>深色模式</span>
          <input
            type="checkbox"
            class="toggle toggle-sm"
            :checked="theme === 'dim'"
            @change="applyTheme(($event.target as HTMLInputElement).checked ? 'dim' : 'corporate')"
          />
        </label>
      </div>
    </aside>

    <!-- 内容区 -->
    <div class="flex min-w-0 flex-1 flex-col">
      <div
        v-if="!connection.online && !connection.checking"
        role="alert"
        class="alert alert-warning rounded-none py-2 text-sm"
      >
        <span class="truncate">{{ connection.error ?? "无法连接后端服务" }}</span>
        <button class="btn btn-xs btn-outline" @click="retryConnection()">重试</button>
      </div>
      <main class="min-h-0 flex-1 overflow-y-auto">
        <div class="mx-auto w-full max-w-6xl p-6">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>
