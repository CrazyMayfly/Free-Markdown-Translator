<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, ApiError, type FsEntry } from "../api/client";
import { isTauri, onNativeFileDrop } from "../tauri";

const router = useRouter();

// ── 选择状态 ──────────────────────────────────────────────
const selected = ref<{ path: string; is_dir: boolean }[]>([]);
const LANG_PRESETS = ["Chinese", "English", "Japanese", "Korean", "German", "French", "Spanish", "Russian"];
const selectedLangs = ref<string[]>(["Chinese"]);
const customLang = ref("");
const mode = ref("balanced");
const evaluate = ref(false);
const resume = ref(false);
const outputDir = ref("");
const submitting = ref(false);
const errorMessage = ref("");

const MODES = [
  { value: "fast", title: "快速", desc: "跳过反思审校，速度最快", icon: "⚡" },
  { value: "balanced", title: "平衡", desc: "按置信度自动触发反思审校", icon: "⚖️" },
  { value: "strict", title: "严格", desc: "全量反思审校 + 格式修复", icon: "🎯" },
];

function toggleLang(lang: string) {
  const index = selectedLangs.value.indexOf(lang);
  if (index >= 0) {
    if (selectedLangs.value.length > 1) selectedLangs.value.splice(index, 1);
  } else {
    selectedLangs.value.push(lang);
  }
}

function addCustomLang() {
  const value = customLang.value.trim();
  if (value && !selectedLangs.value.includes(value)) {
    selectedLangs.value.push(value);
  }
  customLang.value = "";
}

function addPaths(paths: { path: string; is_dir: boolean }[]) {
  for (const item of paths) {
    if (!selected.value.some((s) => s.path === item.path)) {
      selected.value.push(item);
    }
  }
}

function removePath(path: string) {
  selected.value = selected.value.filter((item) => item.path !== path);
}

const summaryText = computed(() => {
  const items = selected.value.length === 1 ? "1 个文件/目录" : `${selected.value.length} 个文件/目录`;
  const langs = selectedLangs.value.join(" / ");
  return `${items} → ${langs}`;
});

// ── 拖拽（Tauri 原生路径 / 浏览器提示）────────────────────
const dragging = ref(false);
let unlistenDrop: (() => void) | null = null;

function isMarkdownish(path: string) {
  return /\.(md|markdown)$/i.test(path) || !path.split("/").pop()!.includes(".");
}

async function setupNativeDrop() {
  if (!isTauri()) return;
  unlistenDrop = await onNativeFileDrop((paths) => {
    dragging.value = false;
    addPaths(paths.filter(isMarkdownish).map((p) => ({ path: p, is_dir: !p.includes(".") || /\.(md|markdown)$/i.test(p) === false && !p.split("/").pop()!.includes(".") })));
  });
}

function onBrowserDrop(event: DragEvent) {
  dragging.value = false;
  if (isTauri()) return; // native handler owns it
  errorMessage.value = "浏览器模式无法获取拖入文件的路径，请点击下方“浏览文件”选择，或使用桌面版直接拖入。";
}

// ── 文件浏览器弹窗 ────────────────────────────────────────
const browserOpen = ref(false);
const dir = ref("");
const parentDir = ref<string | null>(null);
const entries = ref<FsEntry[]>([]);
const browserLoading = ref(false);

async function browse(path: string) {
  browserLoading.value = true;
  try {
    const data = await api.listDir(path);
    dir.value = data.path;
    parentDir.value = data.parent;
    entries.value = data.entries;
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    browserLoading.value = false;
  }
}

function openBrowser() {
  browserOpen.value = true;
  if (!dir.value) void browse("~");
}

function pickEntry(entry: FsEntry) {
  if (entry.is_dir) {
    void browse(entry.path);
    return;
  }
  if (!entry.is_markdown) return;
  addPaths([{ path: entry.path, is_dir: false }]);
}

function addCurrentDir() {
  addPaths([{ path: dir.value, is_dir: true }]);
  browserOpen.value = false;
}

function pickAndClose() {
  browserOpen.value = false;
}

// ── 提交 ─────────────────────────────────────────────────
async function submit() {
  errorMessage.value = "";
  if (!selected.value.length) {
    errorMessage.value = "请先添加要翻译的文件或目录";
    return;
  }
  if (!selectedLangs.value.length) {
    errorMessage.value = "请至少选择一个目标语言";
    return;
  }
  submitting.value = true;
  try {
    const job = await api.createJob({
      paths: selected.value.map((item) => item.path),
      target_langs: [...selectedLangs.value],
      mode: mode.value,
      evaluate: evaluate.value,
      resume: resume.value,
      output_dir: outputDir.value || null,
    });
    void router.push(`/run/${job.id}`);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  try {
    const data = await api.getConfig();
    outputDir.value = data.config.output.directory;
    const defaults = data.config.target_languages.filter(Boolean);
    if (defaults.length) {
      // Match config values to preset casing (english -> English); keep
      // unknown languages as custom chips.
      selectedLangs.value = defaults
        .map((lang) => LANG_PRESETS.find((p) => p.toLowerCase() === lang.toLowerCase()) ?? lang)
        .slice(0, 4);
    }
  } catch {
    /* 连接状态由全局横幅呈现 */
  }
  await setupNativeDrop();
});
onUnmounted(() => unlistenDrop?.());
</script>

<template>
  <div class="flex flex-col gap-5 pb-24">
    <div>
      <h1 class="text-xl font-bold">新建翻译任务</h1>
      <p class="mt-1 text-sm text-base-content/60">添加 Markdown 文件或整个目录，选择目标语言后开始。</p>
    </div>

    <!-- 拖拽区 -->
    <div
      class="rounded-2xl border-2 border-dashed p-8 text-center transition-colors"
      :class="dragging ? 'border-primary bg-primary/5' : 'border-base-300 bg-base-100'"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="onBrowserDrop"
    >
      <div class="text-3xl">📄</div>
      <p class="mt-2 text-sm font-medium">
        {{ isTauri() ? "把 Markdown 文件或文件夹拖到这里" : "点击下方按钮选择要翻译的内容" }}
      </p>
      <p class="mt-1 text-xs text-base-content/50">
        {{ isTauri() ? "支持多选；目录会按 *.md 递归收集" : "桌面版支持从访达直接拖入" }}
      </p>
      <button class="btn btn-primary btn-sm mt-4" @click="openBrowser">
        浏览文件…
      </button>
    </div>

    <!-- 已选清单 -->
    <div v-if="selected.length" class="card bg-base-100 shadow-sm">
      <div class="card-body gap-2 p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold">已添加（{{ selected.length }}）</h2>
          <button class="btn btn-ghost btn-xs text-error" @click="selected = []">全部移除</button>
        </div>
        <ul class="flex flex-col gap-1">
          <li
            v-for="item in selected"
            :key="item.path"
            class="flex items-center gap-2 rounded-lg bg-base-200 px-3 py-2 text-sm"
          >
            <span>{{ item.is_dir ? "📁" : "📝" }}</span>
            <span class="min-w-0 flex-1 truncate font-mono text-xs" :title="item.path">{{ item.path }}</span>
            <button class="btn btn-ghost btn-xs" @click="removePath(item.path)">✕</button>
          </li>
        </ul>
      </div>
    </div>

    <!-- 目标语言 -->
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body gap-3 p-5">
        <h2 class="text-sm font-semibold">目标语言</h2>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="lang in LANG_PRESETS"
            :key="lang"
            class="btn btn-sm rounded-full"
            :class="selectedLangs.includes(lang) ? 'btn-primary' : 'btn-outline'"
            @click="toggleLang(lang)"
          >
            {{ lang }}
          </button>
          <span
            v-for="lang in selectedLangs.filter((l) => !LANG_PRESETS.includes(l))"
            :key="lang"
            class="btn btn-sm btn-primary rounded-full"
            @click="toggleLang(lang)"
          >
            {{ lang }} ✕
          </span>
        </div>
        <div class="flex items-center gap-2">
          <input
            v-model="customLang"
            class="input input-sm input-bordered w-44"
            placeholder="自定义语言或代码…"
            @keydown.enter="addCustomLang"
          />
          <button class="btn btn-sm btn-ghost" :disabled="!customLang.trim()" @click="addCustomLang">添加</button>
        </div>
      </div>
    </div>

    <!-- 翻译模式 -->
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body gap-3 p-5">
        <h2 class="text-sm font-semibold">翻译模式</h2>
        <div class="grid gap-3 sm:grid-cols-3">
          <button
            v-for="item in MODES"
            :key="item.value"
            class="rounded-xl border-2 p-4 text-left transition-all"
            :class="mode === item.value ? 'border-primary bg-primary/5 shadow-sm' : 'border-base-300 hover:border-base-400'"
            @click="mode = item.value"
          >
            <div class="flex items-center justify-between">
              <span class="text-sm font-bold">{{ item.title }}</span>
              <span class="text-lg">{{ item.icon }}</span>
            </div>
            <p class="mt-1 text-xs text-base-content/60">{{ item.desc }}</p>
          </button>
        </div>
      </div>
    </div>

    <!-- 高级选项 -->
    <div class="collapse collapse-arrow rounded-2xl bg-base-100 shadow-sm">
      <input type="checkbox" />
      <div class="collapse-title text-sm font-semibold">高级选项</div>
      <div class="collapse-content flex flex-col gap-3">
        <label class="form-control">
          <span class="label-text pb-1">输出目录</span>
          <input v-model="outputDir" class="input input-bordered input-sm font-mono" placeholder="output" />
          <span class="label-text mt-1 text-xs text-base-content/50">相对路径将解析到用户主目录（如 ~/output）</span>
        </label>
        <label class="label cursor-pointer justify-start gap-3">
          <input v-model="evaluate" type="checkbox" class="toggle toggle-sm" />
          <span class="label-text text-sm">完成后运行 LLM 质量评估（会额外消耗 token）</span>
        </label>
        <label class="label cursor-pointer justify-start gap-3">
          <input v-model="resume" type="checkbox" class="toggle toggle-sm" />
          <span class="label-text text-sm">断点续传（复用上次未完成任务的已译内容）</span>
        </label>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" role="alert" class="alert alert-error text-sm">
      <span>{{ errorMessage }}</span>
      <button class="btn btn-ghost btn-xs" @click="errorMessage = ''">✕</button>
    </div>

    <!-- 粘性动作栏 -->
    <div class="fixed bottom-0 left-56 right-0 z-10 border-t border-base-300 bg-base-100/90 backdrop-blur">
      <div class="mx-auto flex w-full max-w-6xl items-center gap-4 px-6 py-3">
        <div class="min-w-0 flex-1 text-sm">
          <p class="truncate font-medium" :class="selected.length ? '' : 'text-base-content/40'">
            {{ summaryText }}
          </p>
          <p class="text-xs text-base-content/50">
            模式：{{ MODES.find((m) => m.value === mode)?.title }}
            <template v-if="evaluate"> · 含质量评估</template>
          </p>
        </div>
        <button class="btn btn-primary" :disabled="submitting || !selected.length" @click="submit">
          <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
          开始翻译
        </button>
      </div>
    </div>

    <!-- 文件浏览器弹窗 -->
    <dialog class="modal" :class="{ 'modal-open': browserOpen }">
      <div class="modal-box max-w-2xl">
        <div class="flex items-center justify-between">
          <h3 class="font-bold">选择 Markdown 文件</h3>
          <button class="btn btn-circle btn-ghost btn-sm" @click="browserOpen = false">✕</button>
        </div>
        <div class="mt-3 flex items-center gap-2">
          <input class="input input-sm input-bordered grow font-mono text-xs" :value="dir" readonly />
          <button class="btn btn-sm" :disabled="!parentDir || browserLoading" @click="parentDir && browse(parentDir)">
            上一级
          </button>
          <button class="btn btn-sm btn-outline" @click="addCurrentDir">翻译整个目录</button>
        </div>
        <div v-if="browserLoading" class="mt-4 flex justify-center py-8">
          <span class="loading loading-spinner"></span>
        </div>
        <ul v-else class="menu mt-3 max-h-96 w-full overflow-y-auto rounded-xl border border-base-300 p-1">
          <li v-for="entry in entries" :key="entry.path">
            <button @click="pickEntry(entry)">
              <span>{{ entry.is_dir ? "📁" : entry.is_markdown ? "📝" : "📄" }}</span>
              <span class="flex-1 truncate text-left">{{ entry.name }}</span>
              <span
                v-if="entry.is_markdown"
                class="badge badge-xs"
                :class="selected.some((s) => s.path === entry.path) ? 'badge-primary' : 'badge-ghost'"
              >
                {{ selected.some((s) => s.path === entry.path) ? "已选" : "选" }}
              </span>
            </button>
          </li>
        </ul>
        <div class="modal-action">
          <button class="btn btn-primary btn-sm" @click="pickAndClose">完成（{{ selected.length }} 项）</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="browserOpen = false"></div>
    </dialog>
  </div>
</template>
