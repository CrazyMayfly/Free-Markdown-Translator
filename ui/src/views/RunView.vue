<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, type JobDetail, type JobSummary } from "../api/client";
import { useJobEvents, type JobEvent } from "../composables/useSSE";
import { ensureNotifyPermission, notifyApp } from "../notify";

const route = useRoute();
const router = useRouter();
const jobId = String(route.params.id ?? "");

const summary = ref<JobSummary | null>(null);
const detail = ref<JobDetail | null>(null);
const events = ref<JobEvent[]>([]);
const finished = ref(false);
const notified = ref(false);
const currentPair = ref("");
const pairProgress = ref({ done: 0, total: 0 });
const pairLog = ref<{ key: string; input: string; lang: string; done: number; total: number }[]>([]);
const writeErrors = ref<string[]>([]);
const usage = ref({ prompt: 0, completion: 0, total: 0, cached: 0, calls: 0 });
const sseConnected = ref(false);
const eventBox = ref<HTMLDivElement | null>(null);
let pollTimer: number | null = null;

const statusMeta = computed(() => {
  const status = summary.value?.status ?? "queued";
  const map: Record<string, { label: string; badge: string }> = {
    queued: { label: "排队中", badge: "badge-ghost" },
    running: { label: "进行中", badge: "badge-info" },
    completed: { label: "已完成", badge: "badge-success" },
    failed: { label: "失败", badge: "badge-error" },
    cancelled: { label: "已取消", badge: "badge-warning" },
  };
  return map[status] ?? { label: status, badge: "badge-ghost" };
});

const percent = computed(() => {
  if (finished.value && summary.value?.status === "completed") return 100;
  const totalPairs = summary.value?.pairs.length ?? 0;
  if (!pairLog.value.length || !totalPairs) return 0;
  // Pairs run in parallel: sum each pair's own bundle ratio instead of
  // counting completed pairs.
  const sum = pairLog.value.reduce((acc, pair) => acc + (pair.total ? Math.min(1, pair.done / pair.total) : 0), 0);
  return Math.min(99, Math.round((sum / totalPairs) * 100));
});

const donePairs = computed(() => pairLog.value.filter((pair) => pair.total && pair.done >= pair.total).length);
const inFlightPairs = computed(() => pairLog.value.length - donePairs.value);

const cacheShare = computed(() => {
  if (!usage.value.prompt) return 0;
  return Math.round((usage.value.cached / usage.value.prompt) * 100);
});

function fileName(path: string) {
  return path.split("/").pop() ?? path;
}

function statusLabel(status: string) {
  return { completed: "已完成", failed: "失败", cancelled: "已取消" }[status] ?? status;
}

async function maybeNotify(status: string) {
  if (notified.value) return;
  notified.value = true;
  if (document.hidden || !document.hasFocus()) {
    await ensureNotifyPermission();
    const writeNote = writeErrors.value.length ? `（${writeErrors.value.length} 个结果写文件失败，译文已在结果页保留）` : "";
    void notifyApp(`翻译任务${statusLabel(status)}`, `任务 ${jobId.slice(0, 8)} · ${summary.value?.pairs.length ?? 0} 个翻译对${writeNote}`);
  }
}

function onEvent(event: JobEvent) {
  events.value.push(event);
  if (events.value.length > 300) events.value.splice(0, events.value.length - 300);
  if (event.usage) {
    // Backend sends cumulative snapshots; just adopt them (no double count).
    const incoming = event.usage;
    usage.value = {
      prompt: incoming.prompt ?? 0,
      completion: incoming.completion ?? 0,
      total: incoming.total ?? 0,
      cached: incoming.cached ?? 0,
      calls: incoming.calls ?? 0,
    };
  }
  if (event.type === "pair_start") {
    // A pair is known the moment it starts (bundles = total count), so show its
    // progress row immediately instead of waiting for the first bundle to
    // finish — that first update used to lag a full bundle translation.
    const key = `${event.input}|${event.lang}`;
    if (!pairLog.value.some((p) => p.key === key)) {
      pairLog.value.push({
        key,
        input: fileName(event.input ?? ""),
        lang: event.lang ?? "",
        done: 0,
        total: event.bundles ?? event.total ?? 0,
      });
    }
    currentPair.value = `${fileName(event.input ?? "")} → ${event.lang}`;
  }
  if (event.type === "progress") {
    currentPair.value = `${fileName(event.input ?? "")} → ${event.lang}`;
    pairProgress.value = { done: event.done ?? 0, total: event.total ?? 0 };
    const key = `${event.input}|${event.lang}`;
    const last = pairLog.value[pairLog.value.length - 1];
    if (last && last.key === key) {
      last.done = event.done ?? 0;
      last.total = event.total ?? 0;
    } else {
      pairLog.value.push({
        key,
        input: fileName(event.input ?? ""),
        lang: event.lang ?? "",
        done: event.done ?? 0,
        total: event.total ?? 0,
      });
    }
  }
  if (event.type === "pair_done" && event.write_error) {
    writeErrors.value.push(`${fileName(event.input ?? "")} → ${event.lang}`);
  }
  if (event.type === "status") {
    if (summary.value) summary.value.status = event.status ?? summary.value.status;
    if (["completed", "failed", "cancelled"].includes(event.status ?? "")) {
      finished.value = true;
      void maybeNotify(event.status ?? "");
    }
  }
}

async function refresh() {
  try {
    detail.value = await api.getJob(jobId);
    summary.value = detail.value;
    usage.value = { ...summary.value.usage };
    for (const result of detail.value.results ?? []) {
      if (result.write_error) {
        const label = `${fileName(result.input_path)} → ${result.target_lang}`;
        if (!writeErrors.value.includes(label)) writeErrors.value.push(label);
      }
    }
    const wasFinished = finished.value;
    finished.value = ["completed", "failed", "cancelled"].includes(summary.value.status);
    if (finished.value && !wasFinished) void maybeNotify(summary.value.status);
  } catch {
    /* job may not exist yet */
  }
}

const cancelling = ref(false);

async function cancel() {
  cancelling.value = true;
  try {
    await api.cancelJob(jobId);
  } finally {
    // Status will flip to "cancelled" via SSE/polling; keep the button muted.
  }
}

onMounted(() => {
  void refresh();
  void ensureNotifyPermission();
  const { connect, connected } = useJobEvents(jobId, onEvent, () => {
    void refresh();
  });
  // Reflect the live stream state so a silent drop isn't mistaken for a hang.
  watch(connected, (value) => (sseConnected.value = value), { immediate: true });
  connect();
  // Keep the event log pinned to the newest entry.
  watch(
    () => events.value.length,
    () => {
      const box = eventBox.value;
      if (box) box.scrollTop = box.scrollHeight;
    },
  );
  // Safety net: if SSE dies silently (sleep, network hiccup), keep polling.
  pollTimer = window.setInterval(() => {
    if (!finished.value) void refresh();
  }, 5000);
});

onBeforeUnmount(() => {
  if (pollTimer !== null) window.clearInterval(pollTimer);
});
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="flex items-center gap-3">
      <button class="btn btn-ghost btn-sm btn-circle" @click="router.push('/jobs')">←</button>
      <h1 class="text-lg font-bold">任务 {{ jobId.slice(0, 8) }}</h1>
      <span class="badge" :class="statusMeta.badge">{{ statusMeta.label }}</span>
      <div class="grow"></div>
      <button v-if="!finished" class="btn btn-sm btn-error btn-outline" :disabled="cancelling" @click="cancel">
        {{ cancelling ? "正在取消…" : "取消任务" }}
      </button>
      <button
        v-if="finished && summary?.result_count"
        class="btn btn-sm btn-primary"
        @click="router.push(`/result/${jobId}`)"
      >
        查看结果 →
      </button>
    </div>

    <div v-if="summary?.error" role="alert" class="alert alert-error text-sm">{{ summary.error }}</div>

    <div v-if="writeErrors.length" role="alert" class="alert alert-warning text-sm">
      <span>
        {{ writeErrors.length }} 个结果写入文件失败（{{ writeErrors.join("、") }}），译文已保留，
        可在结果页手动保存。
      </span>
    </div>

    <div class="grid gap-4 lg:grid-cols-3">
      <!-- 总进度卡 -->
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body items-center gap-2 p-6">
          <div
            class="radial-progress text-primary"
            :style="{ '--value': percent, '--size': '8rem', '--thickness': '0.6rem' }"
            role="progressbar"
            :aria-valuenow="percent"
          >
            <span class="text-xl font-bold">{{ percent }}%</span>
          </div>
          <p class="text-sm text-base-content/70">{{ currentPair || "等待开始…" }}</p>
          <p class="text-xs text-base-content/50">
            {{ donePairs }}/{{ summary?.pairs.length ?? "?" }} 对完成 · {{ inFlightPairs }} 对进行中 ·
            bundle {{ pairProgress.done }}/{{ pairProgress.total || "?" }}
          </p>
          <p v-if="!finished && !sseConnected" class="text-xs text-warning">
            实时连接已断开，正在降级为轮询刷新…
          </p>
        </div>
      </div>

      <!-- Token 统计 -->
      <div class="card bg-base-100 shadow-sm lg:col-span-2">
        <div class="card-body p-5">
          <h2 class="text-sm font-semibold">Token 用量</h2>
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-xl bg-base-200 p-3">
              <div class="text-xs text-base-content/60">总计</div>
              <div class="text-xl font-bold">{{ usage.total.toLocaleString() }}</div>
            </div>
            <div class="rounded-xl bg-base-200 p-3">
              <div class="text-xs text-base-content/60">提示 / 生成</div>
              <div class="text-xl font-bold">{{ usage.prompt.toLocaleString() }} <span class="text-sm font-normal text-base-content/50">/ {{ usage.completion.toLocaleString() }}</span></div>
            </div>
            <div class="rounded-xl bg-base-200 p-3">
              <div class="text-xs text-base-content/60">前缀缓存命中</div>
              <div class="text-xl font-bold text-primary">
                {{ cacheShare }}%
                <span class="text-sm font-normal text-base-content/50">{{ usage.cached.toLocaleString() }}</span>
              </div>
            </div>
            <div class="rounded-xl bg-base-200 p-3">
              <div class="text-xs text-base-content/60">LLM 调用</div>
              <div class="text-xl font-bold">{{ usage.calls }}</div>
            </div>
          </div>
          <!-- 每翻译对进度 -->
          <ul v-if="pairLog.length" class="mt-2 flex flex-col gap-2">
            <li v-for="(pair, index) in pairLog" :key="`${pair.input}-${pair.lang}-${index}`" class="text-xs">
              <div class="mb-1 flex justify-between text-base-content/70">
                <span class="font-mono">{{ pair.input }} → {{ pair.lang }}</span>
                <span>{{ pair.done }}/{{ pair.total }}</span>
              </div>
              <progress
                class="progress progress-primary h-1.5 w-full"
                :value="pair.done"
                :max="pair.total || 1"
              ></progress>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 事件流 -->
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body p-5">
        <h2 class="text-sm font-semibold">实时事件</h2>
        <div ref="eventBox" class="max-h-60 overflow-y-auto rounded-xl bg-base-200 p-3 font-mono text-xs leading-5">
          <p v-for="event in events" :key="event.seq" class="text-base-content/70">
            <span class="text-base-content/40">{{ new Date(event.ts * 1000).toLocaleTimeString() }}</span>
            <template v-if="event.type === 'progress'"> · {{ event.input?.split("/").pop() }} → {{ event.lang }}（{{ event.done }}/{{ event.total }}）</template>
            <template v-else-if="event.type === 'status'"> · {{ event.status }}</template>
            <template v-else-if="event.type === 'pair_start'"> · 开始 {{ event.input?.split("/").pop() }} → {{ event.lang }}</template>
            <template v-else-if="event.type === 'pair_done'"> · 完成 {{ event.input?.split("/").pop() }} → {{ event.lang }}</template>
            <template v-else> · {{ event.type }}</template>
          </p>
          <p v-if="!events.length" class="text-base-content/40">等待事件…</p>
        </div>
      </div>
    </div>
  </div>
</template>
