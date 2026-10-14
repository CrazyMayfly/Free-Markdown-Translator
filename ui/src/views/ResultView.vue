<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import MarkdownIt from "markdown-it";
import { api, ApiError, type JobDetail, type JobResult } from "../api/client";

const md = new MarkdownIt({ html: false, linkify: true });
const route = useRoute();
const router = useRouter();
const jobId = String(route.params.id ?? "");

const detail = ref<JobDetail | null>(null);
const activeIndex = ref(0);
const viewMode = ref<"render" | "segments">("render");
const errorMessage = ref("");
const loading = ref(true);

const result = computed<JobResult | null>(() => detail.value?.results[activeIndex.value] ?? null);
const rendered = computed(() => (result.value ? md.render(result.value.translated_markdown) : ""));

function fileName(path: string) {
  return path.split("/").pop() ?? path;
}

function scoreBadge(score: number | undefined) {
  if (score === undefined) return "badge-ghost";
  if (score >= 4.5) return "badge-success";
  if (score >= 3.5) return "badge-info";
  if (score >= 2.5) return "badge-warning";
  return "badge-error";
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
      <div v-if="detail.results.length > 1" role="tablist" class="tabs tabs-box w-fit">
        <button
          v-for="(item, index) in detail.results"
          :key="`${item.input_path}-${item.target_lang}`"
          role="tab"
          class="tab"
          :class="{ 'tab-active': index === activeIndex }"
          @click="activeIndex = index"
        >
          {{ fileName(item.input_path) }} → {{ item.target_lang }}
        </button>
      </div>

      <template v-if="result">
        <!-- 指标条 -->
        <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div class="rounded-xl bg-base-100 p-4 shadow-sm">
            <div class="text-xs text-base-content/60">格式校验</div>
            <div class="mt-1">
              <span class="badge" :class="result.validation.passed ? 'badge-success' : 'badge-error'">
                {{ result.validation.passed ? "通过" : "失败" }}
              </span>
            </div>
            <p v-if="result.validation.errors.length" class="mt-1 line-clamp-2 text-xs text-error">
              {{ result.validation.errors[0] }}
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

        <!-- 评估分维度 -->
        <div v-if="result.judge?.scores && !result.judge.error" class="flex flex-wrap items-center gap-2">
          <span
            v-for="(score, key) in result.judge.scores"
            :key="key"
            class="badge badge-lg badge-outline gap-1"
          >
            {{ key }}
            <span class="badge badge-sm" :class="scoreBadge(Number(score))">{{ Number(score).toFixed(1) }}</span>
          </span>
        </div>
        <div v-if="result.judge?.comments?.length" role="alert" class="alert alert-info py-2 text-sm">
          <div><p v-for="comment in result.judge.comments" :key="comment">{{ comment }}</p></div>
        </div>

        <!-- 视图切换 -->
        <div class="flex items-center justify-between">
          <div role="tablist" class="tabs tabs-sm tabs-box">
            <button role="tab" class="tab" :class="{ 'tab-active': viewMode === 'render' }" @click="viewMode = 'render'">渲染视图</button>
            <button role="tab" class="tab" :class="{ 'tab-active': viewMode === 'segments' }" @click="viewMode = 'segments'">分段对照</button>
          </div>
        </div>

        <!-- 渲染视图 -->
        <article
          v-if="viewMode === 'render'"
          class="card bg-base-100 shadow-sm prose prose-sm max-w-none p-6"
          v-html="rendered"
        ></article>

        <!-- 分段对照 -->
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
            >
              <div class="whitespace-pre-wrap p-3 text-base-content/70">{{ segment.source }}</div>
              <div class="whitespace-pre-wrap border-l border-base-200 p-3">
                {{ segment.translated }}
                <div class="mt-1 text-xs text-base-content/40">{{ segment.segment_id }} · 置信度 {{ segment.confidence.toFixed(2) }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
