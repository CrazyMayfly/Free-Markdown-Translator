<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, jobEventsUrl, type JobDetail, type JobSummary } from "../api/client";
import { useJobEvents, type JobEvent } from "../composables/useSSE";

const route = useRoute();
const router = useRouter();
const jobId = String(route.params.id ?? "");

const summary = ref<JobSummary | null>(null);
const events = ref<JobEvent[]>([]);
const connected = ref(false);
const finished = ref(false);
const currentPair = ref("");
const pairProgress = ref({ done: 0, total: 0 });
const usage = ref({ prompt: 0, completion: 0, total: 0, cached: 0, calls: 0 });

const statusBadge = computed(() => {
  const status = summary.value?.status ?? "queued";
  const map: Record<string, string> = {
    queued: "badge-ghost",
    running: "badge-info",
    completed: "badge-success",
    failed: "badge-error",
    cancelled: "badge-warning",
  };
  return map[status] ?? "badge-ghost";
});

const percent = computed(() => {
  if (!pairProgress.value.total) return 0;
  return Math.round((pairProgress.value.done / pairProgress.value.total) * 100);
});

function onEvent(event: JobEvent) {
  events.value.push(event);
  if (events.value.length > 300) {
    events.value.splice(0, events.value.length - 300);
  }
  if (event.type === "progress") {
    currentPair.value = `${fileName(event.input ?? "")} → ${event.lang}`;
    pairProgress.value = { done: event.done ?? 0, total: event.total ?? 0 };
  }
  if (event.type === "pair_done" && event.usage) {
    usage.value.prompt += event.usage.prompt ?? 0;
    usage.value.completion += event.usage.completion ?? 0;
    usage.value.total += event.usage.total ?? 0;
    usage.value.cached += event.usage.cached ?? 0;
    usage.value.calls += 1;
  }
  if (event.type === "status") {
    if (summary.value) summary.value.status = event.status ?? summary.value.status;
    if (["completed", "failed", "cancelled"].includes(event.status ?? "")) {
      finished.value = true;
    }
  }
}

function fileName(path: string) {
  return path.split("/").pop() ?? path;
}

async function refreshSummary() {
  try {
    summary.value = await api.getJob(jobId);
    usage.value = { ...summary.value.usage };
    finished.value = ["completed", "failed", "cancelled"].includes(summary.value.status);
  } catch {
    /* job may not exist yet */
  }
}

async function cancel() {
  await api.cancelJob(jobId);
}

onMounted(() => {
  void refreshSummary();
  const { connected: conn, connect } = useJobEvents(jobId, onEvent, () => {
    void refreshSummary();
  });
  connected.value = conn.value;
  connect();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <h1 class="text-lg font-bold">任务 {{ jobId }}</h1>
      <span class="badge" :class="statusBadge">{{ summary?.status ?? "loading" }}</span>
      <span v-if="connected && !finished" class="badge badge-outline badge-sm">
        <span class="status status-success status-sm"></span> 实时
      </span>
      <div class="grow"></div>
      <button v-if="!finished" class="btn btn-sm btn-error btn-outline" @click="cancel">取消</button>
      <button
        v-if="finished && summary?.status === 'completed'"
        class="btn btn-sm btn-primary"
        @click="router.push(`/result/${jobId}`)"
      >
        查看结果
      </button>
    </div>

    <div v-if="summary?.error" role="alert" class="alert alert-error text-sm">{{ summary.error }}</div>

    <div class="grid gap-4 md:grid-cols-3">
      <div class="card bg-base-100 shadow-sm md:col-span-2">
        <div class="card-body gap-3">
          <h2 class="card-title text-base">进度</h2>
          <p class="text-sm text-base-content/70">{{ currentPair || "等待翻译事件…" }}</p>
          <progress
            v-if="!finished"
            class="progress progress-primary w-full"
            :value="pairProgress.done"
            :max="pairProgress.total || 1"
          ></progress>
          <div v-else class="w-full">
            <progress class="progress progress-success w-full" value="1" max="1"></progress>
          </div>
          <p class="text-xs text-base-content/60">
            bundle {{ pairProgress.done }}/{{ pairProgress.total || "?" }}
            <span v-if="summary?.pairs?.length"> · {{ summary.pairs.length }} 个翻译对</span>
          </p>
        </div>
      </div>

      <div class="stats stats-vertical bg-base-100 shadow-sm">
        <div class="stat py-3">
          <div class="stat-title text-xs">Token 用量</div>
          <div class="stat-value text-2xl">{{ usage.total.toLocaleString() }}</div>
          <div class="stat-desc text-xs">
            提示 {{ usage.prompt.toLocaleString() }} · 生成 {{ usage.completion.toLocaleString() }}
          </div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">缓存命中</div>
          <div class="stat-value text-2xl text-primary">{{ usage.cached.toLocaleString() }}</div>
          <div class="stat-desc text-xs">调用 {{ usage.calls }} 次</div>
        </div>
      </div>
    </div>

    <div class="card bg-base-100 shadow-sm">
      <div class="card-body">
        <h2 class="card-title text-base">事件流</h2>
        <div class="mockup-code max-h-72 overflow-y-auto bg-base-200 text-xs">
          <pre
            v-for="event in events"
            :key="event.seq"
            data-prefix="·"
          ><code>[{{ new Date(event.ts * 1000).toLocaleTimeString() }}] {{ event.type }}
    <template v-if="event.type === 'progress'">{{ fileName(event.input ?? '') }} → {{ event.lang }} ({{ event.done }}/{{ event.total }})</template>
    <template v-else-if="event.type === 'status'">{{ event.status }}</template>
    <template v-else-if="event.type === 'pair_start'">{{ fileName(event.input ?? '') }} → {{ event.lang }}，共 {{ event.bundles }} 包</template>
    <template v-else-if="event.type === 'pair_done'">{{ fileName(event.input ?? '') }} → {{ event.lang }} 完成</template></code></pre>
          <pre v-if="!events.length" data-prefix="…"><code>等待事件</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>
