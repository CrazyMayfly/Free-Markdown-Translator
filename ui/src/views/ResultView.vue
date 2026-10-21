<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import MarkdownIt from "markdown-it";
import { api, ApiError, type JobDetail, type JobResult, type SegmentPair } from "../api/client";

const md = new MarkdownIt({ html: false, linkify: true });
// Links in the rendered translation must not navigate the whole app away (in
// the Tauri webview that replaces the app with the external site).
const defaultLinkOpen =
  md.renderer.rules.link_open ??
  ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options));
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet("target", "_blank");
  tokens[idx].attrSet("rel", "noopener noreferrer");
  return defaultLinkOpen(tokens, idx, options, env, self);
};
const route = useRoute();
const router = useRouter();
const jobId = String(route.params.id ?? "");

const detail = ref<JobDetail | null>(null);
const activeIndex = ref(0);
const viewMode = ref<"render" | "segments">("render");
const errorMessage = ref("");
const loading = ref(true);

const editingId = ref("");
const editText = ref("");
const savingEdit = ref(false);
const savingFile = ref(false);
const toast = ref<{ kind: "success" | "error"; message: string } | null>(null);
let toastTimer: number | null = null;

const result = computed<JobResult | null>(() => detail.value?.results[activeIndex.value] ?? null);
const rendered = computed(() => (result.value ? md.render(result.value.translated_markdown) : ""));

function fileName(path: string) {
  return path.split("/").pop() ?? path;
}

const revealLabel =
  typeof navigator !== "undefined" && /Mac/i.test(navigator.platform ?? "")
    ? "在访达中显示"
    : "在资源管理器中显示";

function scoreBadge(score: number | undefined) {
  if (score === undefined) return "badge-ghost";
  if (score >= 4.5) return "badge-success";
  if (score >= 3.5) return "badge-info";
  if (score >= 2.5) return "badge-warning";
  return "badge-error";
}

function confidenceClass(conf: number) {
  if (conf >= 0.85) return "text-success";
  if (conf >= 0.6) return "text-warning";
  return "text-error";
}

function scoreBarColor(score: number) {
  if (score >= 4.5) return "progress-success";
  if (score >= 3.5) return "progress-info";
  if (score >= 2.5) return "progress-warning";
  return "progress-error";
}

function showToast(kind: "success" | "error", message: string) {
  toast.value = { kind, message };
  if (toastTimer !== null) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (toast.value = null), 2600);
}

async function copyMarkdown() {
  if (!result.value?.translated_markdown) return;
  try {
    await navigator.clipboard.writeText(result.value.translated_markdown);
    showToast("success", "译文已复制到剪贴板");
  } catch {
    showToast("error", "复制失败：浏览器拒绝了剪贴板访问");
  }
}

async function revealOutput() {
  const target = result.value?.output_path ?? result.value?.input_path;
  if (!target) return;
  try {
    await api.revealPath(target);
  } catch (error) {
    showToast("error", error instanceof ApiError ? error.message : String(error));
  }
}

async function saveToFile() {
  if (!result.value) return;
  savingFile.value = true;
  try {
    const saved = await api.saveResult(jobId, activeIndex.value);
    result.value.output_path = saved.path;
    showToast("success", `已保存：${saved.path}`);
  } catch (error) {
    showToast("error", error instanceof ApiError ? error.message : String(error));
  } finally {
    savingFile.value = false;
  }
}

function startEdit(segment: SegmentPair) {
  editingId.value = segment.segment_id;
  editText.value = segment.translated;
  // Auto-grow the textarea after it renders.
  void nextTick(() => {
    const el = document.querySelector<HTMLTextAreaElement>("textarea[data-editing]");
    if (el) {
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }
  });
}

function cancelEdit() {
  editingId.value = "";
  editText.value = "";
}

async function saveEdit(segment: SegmentPair) {
  if (!result.value) return;
  savingEdit.value = true;
  try {
    const updated = await api.updateSegment(jobId, activeIndex.value, segment.segment_id, editText.value);
    detail.value!.results[activeIndex.value] = updated.result;
    editingId.value = "";
    showToast("success", "段落已更新，译文文档已同步修订");
  } catch (error) {
    showToast("error", error instanceof ApiError ? error.message : String(error));
  } finally {
    savingEdit.value = false;
  }
}

onMounted(async () => {
  try {
    detail.value = await api.getJob(jobId);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="flex items-center gap-3">
      <button class="btn btn-ghost btn-sm btn-circle" @click="router.push('/jobs')">←</button>
      <h1 class="text-lg font-bold">翻译结果</h1>
      <span class="badge" :class="detail?.status === 'completed' ? 'badge-success' : 'badge-warning'">
        {{ detail?.status ?? "…" }}
      </span>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg"></span>
    </div>
    <div v-else-if="errorMessage" role="alert" class="alert alert-error text-sm">{{ errorMessage }}</div>
    <div v-else-if="!detail?.results.length" class="rounded-2xl border-2 border-dashed border-base-300 bg-base-100 p-12 text-center text-sm text-base-content/60">
      该任务还没有可用结果。
    </div>

    <template v-else>
      <!-- 结果切换 -->
      <div v-if="detail.results.length > 1" role="tablist" class="tabs tabs-box w-fit max-w-full overflow-x-auto">
        <button
          v-for="(item, index) in detail.results"
          :key="`${item.input_path}-${item.target_lang}`"
          role="tab"
          class="tab"
          :class="{ 'tab-active': index === activeIndex }"
          @click="activeIndex = index; editingId = ''; editText = ''"
        >
          {{ fileName(item.input_path) }} → {{ item.target_lang }}
        </button>
      </div>

      <template v-if="result">
        <!-- 写文件失败警示：译文仍在，可手动保存 -->
        <div v-if="result.write_error" role="alert" class="alert alert-warning text-sm">
          <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
          <div class="grow">
            <p class="font-medium">输出文件写入失败，译文已保留</p>
            <p class="mt-0.5 text-xs opacity-80">{{ result.write_error }}</p>
          </div>
          <button class="btn btn-sm" :disabled="savingFile" @click="saveToFile">保存到文件…</button>
        </div>

        <!-- 操作条 -->
        <div class="flex flex-wrap items-center gap-2">
          <button class="btn btn-primary btn-sm" @click="copyMarkdown">复制译文</button>
          <button class="btn btn-sm" :disabled="savingFile" @click="saveToFile">
            {{ savingFile ? "保存中…" : result.output_path ? "重新保存到文件" : "保存到文件" }}
          </button>
          <button class="btn btn-ghost btn-sm" @click="revealOutput">
            {{ revealLabel }}
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17L17 7M17 7H8m9 0v9"/></svg>
          </button>
        </div>

        <!-- 指标条 -->
        <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div class="rounded-xl bg-base-100 p-4 shadow-sm">
            <div class="text-xs text-base-content/60">格式校验</div>
            <div class="mt-1">
              <span class="badge" :class="result.validation.passed ? 'badge-success' : 'badge-error'">
                {{ result.validation.passed ? "通过" : "失败" }}
              </span>
            </div>
            <p v-if="result.validation.errors.length" class="mt-1 text-xs text-error">
              {{ result.validation.errors[0] }}
              <template v-if="result.validation.errors.length > 1"> 等 {{ result.validation.errors.length }} 项</template>
            </p>
          </div>
          <div class="rounded-xl bg-base-100 p-4 shadow-sm">
            <div class="text-xs text-base-content/60">分段 / Token</div>
            <div class="mt-1 text-xl font-bold">
              {{ result.segments.length }}
              <span class="text-sm font-normal text-base-content/50">/ {{ result.usage.total.toLocaleString() }}</span>
            </div>
            <p class="mt-1 text-xs text-base-content/50">缓存命中 {{ result.usage.cached.toLocaleString() }}</p>
          </div>
          <div class="rounded-xl bg-base-100 p-4 shadow-sm">
            <div class="text-xs text-base-content/60">质量评估</div>
            <div v-if="result.judge && !result.judge.error" class="mt-1 flex items-baseline gap-2">
              <span class="text-xl font-bold" :class="(result.judge.overall ?? 0) >= 3 ? 'text-success' : 'text-error'">
                {{ result.judge.overall?.toFixed(1) }}
              </span>
              <span class="text-xs text-base-content/50">/ 5.0</span>
            </div>
            <div v-else class="mt-1 text-sm text-base-content/40">{{ result.judge?.error ? "未执行" : "—" }}</div>
          </div>
          <div class="rounded-xl bg-base-100 p-4 shadow-sm">
            <div class="text-xs text-base-content/60">输出文件</div>
            <p class="mt-1 truncate font-mono text-xs" :title="result.output_path ?? ''">
              {{ result.output_path ?? "未写入" }}
            </p>
          </div>
        </div>

        <!-- 格式校验错误详情（可展开） -->
        <details v-if="result.validation.errors.length > 1" class="collapse collapse-arrow bg-base-100 shadow-sm">
          <summary class="collapse-title text-sm font-semibold">
            格式校验发现 {{ result.validation.errors.length }} 个问题
          </summary>
          <div class="collapse-content flex flex-col gap-1">
            <p v-for="(err, i) in result.validation.errors" :key="i" class="text-xs text-error">· {{ err }}</p>
          </div>
        </details>

        <!-- 评估分维度条 -->
        <div v-if="result.judge?.scores && !result.judge.error" class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3 p-5">
            <h2 class="text-sm font-semibold">质量评估 · {{ result.judge.target_lang ?? result.target_lang }}</h2>
            <div class="grid gap-x-8 gap-y-2 sm:grid-cols-2">
              <div v-for="(score, key) in result.judge.scores" :key="key">
                <div class="mb-1 flex items-center justify-between text-xs">
                  <span class="text-base-content/70">{{ key }}</span>
                  <span class="font-mono" :class="Number(score) >= 3 ? 'text-success' : 'text-error'">{{ Number(score).toFixed(1) }}/5</span>
                </div>
                <progress
                  class="progress h-1.5 w-full"
                  :class="scoreBarColor(Number(score))"
                  :value="Number(score)"
                  max="5"
                ></progress>
              </div>
            </div>
            <div v-if="result.judge.comments?.length" class="mt-1 flex flex-col gap-1 rounded-xl bg-base-200 p-3 text-xs leading-5 text-base-content/70">
              <p v-for="comment in result.judge.comments" :key="comment">· {{ comment }}</p>
            </div>
          </div>
        </div>

        <!-- 视图切换 -->
        <div class="flex items-center justify-between">
          <div role="tablist" class="tabs tabs-sm tabs-box">
            <button role="tab" class="tab" :class="{ 'tab-active': viewMode === 'render' }" @click="viewMode = 'render'">渲染视图</button>
            <button role="tab" class="tab" :class="{ 'tab-active': viewMode === 'segments' }" @click="viewMode = 'segments'">分段对照</button>
          </div>
          <p v-if="viewMode === 'segments'" class="text-xs text-base-content/50">点击译文可直接修订，保存后同步更新全文</p>
        </div>

        <!-- 渲染视图 -->
        <article
          v-if="viewMode === 'render'"
          class="card bg-base-100 shadow-sm prose prose-sm max-w-none p-6"
          :lang="result.target_lang"
          v-html="rendered"
        ></article>

        <!-- 分段对照（译文可修订） -->
        <div v-else class="card overflow-hidden bg-base-100 shadow-sm">
          <div class="grid grid-cols-2 border-b border-base-300 bg-base-200 text-sm font-semibold">
            <div class="p-3">原文</div>
            <div class="border-l border-base-300 p-3">译文（{{ result.target_lang }}）</div>
          </div>
          <div class="max-h-[60vh] overflow-y-auto">
            <div
              v-for="segment in result.segments"
              :key="segment.segment_id"
              class="grid grid-cols-2 border-b border-base-200 text-sm"
              :class="{ 'bg-base-200/50': editingId === segment.segment_id }"
            >
              <div class="whitespace-pre-wrap p-3 text-base-content/70">{{ segment.source }}</div>
              <div class="border-l border-base-200 p-3">
                <textarea
                  v-if="editingId === segment.segment_id"
                  v-model="editText"
                  data-editing
                  class="textarea textarea-bordered w-full font-mono text-xs leading-5"
                  rows="3"
                  @keydown.meta.enter.prevent="saveEdit(segment)"
                  @keydown.ctrl.enter.prevent="saveEdit(segment)"
                ></textarea>
                <div v-else class="whitespace-pre-wrap">{{ segment.translated }}</div>
                <div class="mt-1 flex items-center gap-2">
                  <span class="text-xs text-base-content/40">{{ segment.segment_id }}</span>
                  <span class="text-xs" :class="confidenceClass(segment.confidence)" :title="`置信度低于 0.85 会触发审校`">
                    置信度 {{ segment.confidence.toFixed(2) }}
                  </span>
                  <span v-if="segment.notes?.length" class="badge badge-ghost badge-xs" :title="segment.notes.join('；')">
                    {{ segment.notes[0] }}
                  </span>
                  <template v-if="editingId === segment.segment_id">
                    <button class="btn btn-primary btn-xs ml-auto" :disabled="savingEdit" @click="saveEdit(segment)">
                      {{ savingEdit ? "保存中…" : "保存" }}
                    </button>
                    <button class="btn btn-ghost btn-xs" @click="cancelEdit">取消</button>
                  </template>
                  <button v-else class="btn btn-ghost btn-xs ml-auto opacity-60 hover:opacity-100" @click="startEdit(segment)">修订</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- 全局提示 -->
    <div v-if="toast" class="toast toast-end toast-bottom z-50">
      <div class="alert py-2 text-sm" :class="toast.kind === 'success' ? 'alert-success' : 'alert-error'">
        <span>{{ toast.message }}</span>
      </div>
    </div>
  </div>
</template>
