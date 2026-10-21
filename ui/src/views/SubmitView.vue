<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, ApiError, type FsEntry } from "../api/client";
import { confirmAction } from "../confirm";
import { isTauri, onNativeFileDrop } from "../tauri";

const router = useRouter();

// ── 选择状态 ──────────────────────────────────────────────
const selected = ref<{ path: string; is_dir: boolean }[]>([]);
const LANG_PRESETS = ["Chinese", "English", "Japanese", "Korean", "German", "French", "Spanish", "Russian"];
const selectedLangs = ref<string[]>(["Chinese"]);
const customLang = ref("");
const mode = ref("balanced");
const evaluate = computed(() => mode.value === "quality"); // 质量评估跟随模式，不由用户指定
const resume = ref(true); // 断点续传默认开启
const outputDir = ref("");
const outputDirTouched = ref(false); // 用户手动改过输出目录后，不再随选择自动联动
const submitting = ref(false);
const errorMessage = ref("");
const reusedNotice = ref(false);
// 文风固定为「保持原文」：后端把它映射成提示词措辞（document_context.TONE_PROMPTS）。
const TONE = "preserve";

// 语言代码 ↔ 预设名互查：配置里存的是代码（zh-CN），按钮显示英文名（Chinese），
// 两者都映射到同一 code，避免“配置默认语言显示成普通 chip”的错位。
const LANG_CODES: Record<string, string> = {
  chinese: "zh-CN",
  english: "en",
  japanese: "ja",
  korean: "ko",
  german: "de",
  french: "fr",
  spanish: "es",
  russian: "ru",
};
const langCodeOf = (name: string) => LANG_CODES[name.toLowerCase()] ?? name;
const langNameOf = (code: string) => {
  const hit = Object.entries(LANG_CODES).find(([, c]) => c.toLowerCase() === code.toLowerCase());
  return hit ? hit[0][0].toUpperCase() + hit[0].slice(1) : code;
};
const selectedLangsCoded = computed(() => selectedLangs.value.map(langCodeOf));

const MODES = [
  { value: "fast", title: "快速", desc: "仅术语与语气 + 最小上下文，省 token 提速", icon: "⚡" },
  { value: "balanced", title: "平衡", desc: "文档摘要 + 只审可疑段落", icon: "⚖️" },
  { value: "quality", title: "质量", desc: "完整上下文 + 全量审校 + 文档级终审", icon: "🎯" },
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
  syncDefaultOutputDir();
}

function removePath(path: string) {
  selected.value = selected.value.filter((item) => item.path !== path);
  syncDefaultOutputDir();
}

async function clearAll() {
  if (!selected.value.length) return;
  const ok = await confirmAction("确定要移除全部已添加的文件/目录吗？", { confirmLabel: "移除" });
  if (!ok) return;
  selected.value = [];
  syncDefaultOutputDir();
}

// 输出目录默认规则：取第一个所选文件/目录的父目录下的 output/ 文件夹；
// 一旦用户手动改过输出目录，就不再自动联动。
function syncDefaultOutputDir() {
  if (outputDirTouched.value || !selected.value.length) return;
  const first = selected.value[0].path;
  const base = first.endsWith("/") ? first.slice(0, -1) : first;
  const parent = base.slice(0, base.lastIndexOf("/")) || base;
  outputDir.value = `${parent}/output`;
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
  return /\.(md|markdown)$/i.test(path);
}

async function setupNativeDrop() {
  if (!isTauri()) return;
  unlistenDrop = await onNativeFileDrop((paths) => {
    dragging.value = false;
    // Only real markdown files are accepted on drop; directories with a dot
    // in their name (docs.v2/) are no longer silently dropped — the native
    // handler already filters, and here we just normalise what got through.
    addPaths(
      paths
        .filter(isMarkdownish)
        .map((p) => ({ path: p, is_dir: false })),
    );
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

// ── 输出目录选择弹窗（复用 listDir 浏览能力）──────────────
const dirPickerOpen = ref(false);
const pickerDir = ref("");
const pickerParent = ref<string | null>(null);
const pickerEntries = ref<FsEntry[]>([]);
const pickerLoading = ref(false);

async function pickerBrowse(path: string) {
  pickerLoading.value = true;
  try {
    const data = await api.listDir(path);
    pickerDir.value = data.path;
    pickerParent.value = data.parent;
    pickerEntries.value = data.entries.filter((e) => e.is_dir);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    pickerLoading.value = false;
  }
}

function openDirPicker() {
  dirPickerOpen.value = true;
  if (!pickerDir.value) void pickerBrowse(outputDir.value || "~");
}

function pickOutputDir(path: string) {
  outputDir.value = path;
  outputDirTouched.value = true;
  dirPickerOpen.value = false;
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
      target_langs: selectedLangsCoded.value,
      mode: mode.value,
      tone: TONE,
      evaluate: evaluate.value,
      resume: resume.value,
      output_dir: outputDir.value || null,
    });
    // 记住本次选择的目标语言，下次新建任务时预填。
    localStorage.setItem("mdtx-last-langs", JSON.stringify(selectedLangsCoded.value));
    void router.push(`/run/${job.id}`);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : String(error);
  } finally {
    submitting.value = false;
  }
}

/** "再来一次"预填：JobsView 会把上次任务的参数存进 sessionStorage。 */
interface ReuseParams {
  paths: string[];
  target_langs: string[];
  output_dir: string | null;
  mode: string | null;
  tone: string | null;
  model: string | null;
  evaluate: boolean;
}

function applyReuse() {
  const raw = sessionStorage.getItem("mdtx-reuse");
  if (!raw) return;
  sessionStorage.removeItem("mdtx-reuse");
  try {
    const reuse = JSON.parse(raw) as Partial<ReuseParams>;
    if (reuse.paths?.length) {
      selected.value = reuse.paths.map((path) => ({
        path,
        is_dir: !/\.(md|markdown)$/i.test(path),
      }));
    }
    if (reuse.target_langs?.length) {
      selectedLangs.value = reuse.target_langs.map(langNameOf).slice(0, 6);
    }
    // Old jobs recorded the deprecated "strict" alias; map it before matching.
    const reuseMode = reuse.mode === "strict" ? "quality" : reuse.mode;
    if (reuseMode && MODES.some((m) => m.value === reuseMode)) mode.value = reuseMode;
    if (reuse.output_dir) {
      outputDir.value = reuse.output_dir;
      outputDirTouched.value = true;
    }
    reusedNotice.value = true;
  } catch {
    /* ignore malformed reuse payload */
  }
}

onMounted(async () => {
  // 目标语言优先取「上次提交」的记忆，其次才是配置默认值。
  let hasRemembered = false;
  const remembered = localStorage.getItem("mdtx-last-langs");
  if (remembered) {
    try {
      const langs = JSON.parse(remembered) as string[];
      if (Array.isArray(langs) && langs.length) {
        selectedLangs.value = langs.map(langNameOf);
        hasRemembered = true;
      }
    } catch {
      /* fall through to config defaults */
    }
  }
  try {
    const data = await api.getConfig();
    outputDir.value = data.config.output.directory;
    outputDirTouched.value = true; // 初始值来自配置，不随选择联动
    if (!hasRemembered) {
      const defaults = data.config.target_languages.filter(Boolean);
      if (defaults.length) {
        selectedLangs.value = defaults.map(langNameOf).slice(0, 4);
      }
    }
  } catch {
    /* 连接状态由全局横幅呈现 */
  }
  applyReuse();
  await expandOutputDir();
  await setupNativeDrop();
});

// 相对路径的输出目录按用户主目录展开成绝对路径显示（后端同样按主目录解析）。
async function expandOutputDir() {
  if (!outputDir.value || outputDir.value.startsWith("/") || outputDir.value.startsWith("~")) return;
  try {
    const data = await api.listDir("~");
    outputDir.value = `${data.path.replace(/\/$/, "")}/${outputDir.value}`;
    outputDirTouched.value = true;
  } catch {
    /* 无法取得主目录时保持原样 */
  }
}
onUnmounted(() => unlistenDrop?.());
</script>

<template>
  <div class="flex flex-col gap-5 pb-24">
    <div>
      <h1 class="text-xl font-bold">新建翻译任务</h1>
      <p class="mt-1 text-sm text-base-content/60">添加 Markdown 文件或整个目录，选择目标语言后开始。</p>
    </div>

    <!-- 复用提示 -->
    <div v-if="reusedNotice" role="status" class="alert alert-info py-2 text-sm">
      <span>已按上次任务的设置预填，可调整后再次开始。</span>
      <button class="btn btn-ghost btn-xs" @click="reusedNotice = false">✕</button>
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
          <button class="btn btn-ghost btn-xs text-error" @click="clearAll">全部移除</button>
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
            :aria-pressed="selectedLangs.includes(lang)"
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
            :aria-pressed="mode === item.value"
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

    <!-- 输出目录 -->
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body gap-3 p-5">
        <h2 class="text-sm font-semibold">输出目录</h2>
        <div class="join w-full">
          <input
            v-model="outputDir"
            class="input input-bordered input-sm join-item grow font-mono"
            placeholder="output"
            @input="outputDirTouched = true"
          />
          <button
            type="button"
            class="btn btn-sm join-item"
            :disabled="pickerLoading"
            @click="openDirPicker"
          >
            浏览…
          </button>
        </div>
        <p class="text-xs text-base-content/50">默认随所选文档生成同目录下的 output/ 文件夹；手动修改后不再联动</p>
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
    <div class="fixed bottom-0 left-0 right-0 z-10 border-t border-base-300 bg-base-100/90 backdrop-blur lg:left-56">
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

    <!-- 输出目录选择弹窗 -->
    <dialog class="modal" :class="{ 'modal-open': dirPickerOpen }">
      <div class="modal-box max-w-2xl">
        <div class="flex items-center justify-between">
          <h3 class="font-bold">选择输出目录</h3>
          <button class="btn btn-circle btn-ghost btn-sm" aria-label="关闭" @click="dirPickerOpen = false">✕</button>
        </div>
        <div class="mt-3 flex items-center gap-2">
          <input class="input input-sm input-bordered grow font-mono text-xs" :value="pickerDir" readonly />
          <button class="btn btn-sm" :disabled="!pickerParent || pickerLoading" @click="pickerParent && pickerBrowse(pickerParent)">
            上一级
          </button>
        </div>
        <div v-if="pickerLoading" class="mt-4 flex justify-center py-8">
          <span class="loading loading-spinner"></span>
        </div>
        <ul v-else class="menu mt-3 max-h-96 w-full overflow-y-auto rounded-xl border border-base-300 p-1">
          <li v-for="entry in pickerEntries" :key="entry.path">
            <button @click="pickerDir === entry.path ? pickOutputDir(entry.path) : pickerBrowse(entry.path)">
              <span>📁</span>
              <span class="flex-1 truncate text-left">{{ entry.name }}</span>
              <span v-if="pickerDir === entry.path" class="badge badge-xs badge-primary">选中</span>
            </button>
          </li>
          <li v-if="!pickerEntries.length" class="p-3 text-center text-xs text-base-content/50">此目录下没有子文件夹</li>
        </ul>
        <div class="modal-action">
          <button class="btn btn-primary btn-sm" @click="pickOutputDir(pickerDir)">选择当前目录</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="dirPickerOpen = false"></div>
    </dialog>
  </div>
</template>
