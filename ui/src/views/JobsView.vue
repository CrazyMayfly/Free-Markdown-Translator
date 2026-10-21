<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, ApiError, type JobSummary } from "../api/client";
import { confirmAction } from "../confirm";

const router = useRouter();
const jobs = ref<JobSummary[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const deletingId = ref("");
let pollTimer: number | null = null;

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
  const diff = (Date.now() - ts * 1000) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`;
  return new Date(ts * 1000).toLocaleString();
}

function open(job: JobSummary) {
  if (job.status === "completed" && job.result_count > 0) {
    void router.push(`/result/${job.id}`);
  } else {
    void router.push(`/run/${job.id}`);
  }
}

/** Re-run the same submission: stash params for SubmitView to prefill. */
async function reuse(job: JobSummary) {
  try {
    const detail = await api.getJob(job.id);
    if (detail.params) {
      sessionStorage.setItem(
        "mdtx-reuse",
        JSON.stringify({
          paths: detail.params.paths ?? [],
          target_langs: detail.params.target_langs ?? [],
          output_dir: detail.params.output_dir ?? null,
          mode: detail.params.mode ?? null,
          tone: detail.params.tone ?? null,
          model: detail.params.model ?? null,
          evaluate: Boolean(detail.params.evaluate),
        }),
      );
    }
  } catch {
    /* fall through: prefill simply won't happen */
  }
  void router.push("/submit");
}

async function remove(job: JobSummary) {
  const ok = await confirmAction("确定要从历史记录中删除该任务吗？（不会删除已产出的译文文件）", {
    confirmLabel: "删除",
  });
  if (!ok) return;
  deletingId.value = job.id;
  try {
    await api.deleteHistory(job.id);
    jobs.value = jobs.value.filter((item) => item.id !== job.id);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    deletingId.value = "";
  }
}

async function refresh() {
  try {
    const live = await api.listJobs();
    const history = await api.listHistory();
    const byId = new Map<string, JobSummary>();
    // History first, live records win (they carry params for reuse).
    for (const job of history) byId.set(job.id, job);
    for (const job of live) byId.set(job.id, job);
    jobs.value = [...byId.values()].sort((a, b) => (b.finished_at ?? b.created_at) - (a.finished_at ?? a.created_at));
    errorMessage.value = "";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void refresh();
  pollTimer = window.setInterval(() => {
    if (document.hidden) return; // 后台标签页不刷，省电
    void refresh();
  }, 5000);
});

onBeforeUnmount(() => {
  if (pollTimer !== null) window.clearInterval(pollTimer);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <h1 class="text-xl font-bold">任务记录</h1>
      <p class="mt-1 text-sm text-base-content/60">历史任务保存在本机（~/.mdtx），重启应用后仍在；点击可查看结果、修订译文。</p>
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
        <div class="card w-full bg-base-100 shadow-sm transition-shadow hover:shadow-md">
          <div class="card-body flex-row items-center gap-4 p-4">
            <button class="flex min-w-0 flex-1 items-center gap-4 text-left" @click="open(job)">
              <span class="badge shrink-0" :class="meta(job.status).badge">{{ meta(job.status).label }}</span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ job.pairs.join("、") || "—" }}</p>
                <p class="mt-0.5 text-xs text-base-content/50">
                  {{ formatTime(job.created_at) }}
                  <template v-if="job.usage?.calls"> · {{ job.usage.calls }} 次 LLM 调用 · {{ job.usage.total.toLocaleString() }} tokens</template>
                  <template v-if="job.error"> · <span class="text-error">{{ job.error }}</span></template>
                </p>
              </div>
              <span v-if="job.result_count" class="badge badge-ghost badge-sm shrink-0">{{ job.result_count }} 份结果</span>
              <svg class="h-4 w-4 shrink-0 text-base-content/30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6" /></svg>
            </button>
            <div class="flex shrink-0 items-center gap-1">
              <button class="btn btn-ghost btn-xs" title="用同样的设置再跑一次" @click.stop="reuse(job)">再来一次</button>
              <button
                class="btn btn-ghost btn-xs text-error"
                :disabled="deletingId === job.id"
                title="从历史中删除（不删除已产出的文件）"
                @click.stop="remove(job)"
              >
                {{ deletingId === job.id ? "删除中…" : "删除" }}
              </button>
            </div>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
