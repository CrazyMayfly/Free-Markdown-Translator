<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import MarkdownIt from "markdown-it";
import { api, type JobDetail, type JobResult } from "../api/client";

const md = new MarkdownIt({ html: false, linkify: true });
const route = useRoute();
const jobId = String(route.params.id ?? "");

const detail = ref<JobDetail | null>(null);
const activeIndex = ref(0);
const viewMode = ref<"render" | "segments">("render");
const errorMessage = ref("");

const result = computed<JobResult | null>(() => detail.value?.results[activeIndex.value] ?? null);

const rendered = computed(() => (result.value ? md.render(result.value.translated_markdown) : ""));

const judgeScoreColor = (score: number | undefined) => {
  if (score === undefined) return "badge-ghost";
  if (score >= 4.5) return "badge-success";
  if (score >= 3.5) return "badge-info";
  if (score >= 2.5) return "badge-warning";
  return "badge-error";
};

const fileName = (path: string) => path.split("/").pop() ?? path;

onMounted(async () => {
  try {
    detail.value = await api.getJob(jobId);
  } catch (error) {
    errorMessage.value = String(error);
  }
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <h1 class="text-lg font-bold">翻译结果</h1>
      <span class="badge" :class="detail?.status === 'completed' ? 'badge-success' : 'badge-warning'">
        {{ detail?.status ?? "loading" }}
      </span>
    </div>

    <div v-if="errorMessage" role="alert" class="alert alert-error text-sm">{{ errorMessage }}</div>

    <div v-if="detail && detail.results.length > 1" role="tablist" class="tabs tabs-box w-fit">
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
      <div class="grid gap-4 md:grid-cols-4">
        <div class="stats stats-vertical bg-base-100 shadow-sm md:col-span-3 md:stats-horizontal">
          <div class="stat py-3">
            <div class="stat-title text-xs">格式校验</div>
            <div class="stat-value text-2xl">
              <span class="badge" :class="result.validation.passed ? 'badge-success' : 'badge-error'">
                {{ result.validation.passed ? "通过" : "失败" }}
              </span>
            </div>
            <div v-if="result.validation.errors.length" class="stat-desc text-xs text-error">
              {{ result.validation.errors.join("; ") }}
            </div>
          </div>
          <div class="stat py-3">
            <div class="stat-title text-xs">分段</div>
            <div class="stat-value text-2xl">{{ result.segments.length }}</div>
            <div class="stat-desc text-xs">Token {{ result.usage.total.toLocaleString() }}（缓存 {{ result.usage.cached.toLocaleString() }}）</div>
          </div>
          <div v-if="result.judge && !result.judge.error" class="stat py-3">
            <div class="stat-title text-xs">质量评估 overall</div>
            <div class="stat-value text-2xl" :class="result.judge.overall! >= 3 ? 'text-success' : 'text-error'">
              {{ result.judge.overall?.toFixed(1) }}
            </div>
            <div class="stat-desc text-xs">
              <span v-for="(score, key) in result.judge.scores" :key="key" class="mr-2">
                {{ key }} {{ Number(score).toFixed(1) }}
              </span>
            </div>
          </div>
          <div v-else-if="result.judge?.error" class="stat py-3">
            <div class="stat-title text-xs">质量评估</div>
            <div class="stat-value text-sm text-warning">未执行</div>
            <div class="stat-desc text-xs">{{ result.judge.error }}</div>
          </div>
        </div>
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-2 py-4">
            <div role="tablist" class="tabs tabs-sm tabs-box">
              <button role="tab" class="tab" :class="{ 'tab-active': viewMode === 'render' }" @click="viewMode = 'render'">渲染视图</button>
              <button role="tab" class="tab" :class="{ 'tab-active': viewMode === 'segments' }" @click="viewMode = 'segments'">分段对照</button>
            </div>
            <p v-if="result.output_path" class="font-mono text-xs text-base-content/60 break-all">
              {{ result.output_path }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="result.judge?.comments?.length" class="alert alert-info text-sm">
        <div>
          <p v-for="comment in result.judge.comments" :key="comment">{{ comment }}</p>
        </div>
      </div>

      <!-- 渲染视图 -->
      <article
        v-if="viewMode === 'render'"
        class="card bg-base-100 shadow-sm prose prose-sm max-w-none"
        v-html="rendered"
      ></article>

      <!-- 分段对照 -->
      <div v-else class="card bg-base-100 shadow-sm">
        <div class="card-body gap-0 p-0">
          <div class="grid grid-cols-2 border-b border-base-300 bg-base-200 text-sm font-semibold">
            <div class="p-3">原文</div>
            <div class="border-l border-base-300 p-3">译文（{{ result.target_lang }}）</div>
          </div>
          <div
            v-for="segment in result.segments"
            :key="segment.segment_id"
            class="grid grid-cols-2 border-b border-base-200 text-sm"
          >
            <div class="whitespace-pre-wrap p-3 text-base-content/70">{{ segment.source }}</div>
            <div class="whitespace-pre-wrap border-l border-base-200 p-3">
              {{ segment.translated }}
              <div class="mt-1 text-xs text-base-content/40">
                {{ segment.segment_id }} · 置信度 {{ segment.confidence.toFixed(2) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
