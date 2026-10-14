<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, ApiError, type JobSummary } from "../api/client";

const router = useRouter();
const jobs = ref<JobSummary[]>([]);
const loading = ref(true);
const errorMessage = ref("");

const statusMeta: Record<string, { label: string; badge: string }> = {
  queued: { label: "排队中", badge: "badge-ghost" },
  running: { label: "进行中", badge: "badge-info" },
  completed: { label: "已完成", badge: "badge-success" },
  failed: { label: "失败", badge: "badge-error" },
  cancelled: { label: "已取消", badge: "badge-warning" },
};

function meta(status: string) {
  return statusMeta[status] ?? { label: status, badge: "badge-ghost" };
}

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleString();
}

function open(job: JobSummary) {
  if (job.status === "completed" && job.result_count > 0) {
    void router.push(`/result/${job.id}`);
  } else {
    void router.push(`/run/${job.id}`);
  }
}

onMounted(async () => {
  try {
    jobs.value = await api.listJobs();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <h1 class="text-xl font-bold">任务记录</h1>
      <p class="mt-1 text-sm text-base-content/60">本次会话内提交过的翻译任务（服务重启后清空，产出文件不受影响）。</p>
    </div>

    <div v-if="errorMessage" role="alert" class="alert alert-error text-sm">{{ errorMessage }}</div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="!jobs.length" class="rounded-2xl border-2 border-dashed border-base-300 bg-base-100 p-12 text-center">
      <div class="text-3xl">🗂️</div>
      <p class="mt-2 text-sm text-base-content/60">还没有任务，去「新建任务」开始第一次翻译吧。</p>
      <button class="btn btn-primary btn-sm mt-4" @click="router.push('/submit')">新建任务</button>
    </div>

    <ul v-else class="flex flex-col gap-2">
      <li v-for="job in jobs" :key="job.id">
        <button
          class="card w-full bg-base-100 text-left shadow-sm transition-shadow hover:shadow-md"
          @click="open(job)"
        >
          <div class="card-body flex-row items-center gap-4 p-4">
            <span class="badge shrink-0" :class="meta(job.status).badge">{{ meta(job.status).label }}</span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium">{{ job.pairs.join("、") || "—" }}</p>
              <p class="mt-0.5 text-xs text-base-content/50">
                {{ formatTime(job.created_at) }}
                <template v-if="job.usage.calls"> · {{ job.usage.calls }} 次 LLM 调用 · {{ job.usage.total.toLocaleString() }} tokens</template>
                <template v-if="job.error"> · <span class="text-error">{{ job.error }}</span></template>
              </p>
            </div>
            <span v-if="job.result_count" class="badge badge-ghost badge-sm shrink-0">{{ job.result_count }} 份结果</span>
            <svg class="h-4 w-4 shrink-0 text-base-content/30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6" /></svg>
          </div>
        </button>
      </li>
    </ul>
  </div>
</template>
