<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, type AppConfig, type FsEntry } from "../api/client";

const router = useRouter();

const dir = ref<string>("");
const parent = ref<string | null>(null);
const entries = ref<FsEntry[]>([]);
const selected = ref<string[]>([]);
const langs = ref("chinese, japanese");
const mode = ref("balanced");
const evaluate = ref(false);
const resume = ref(false);
const outputDir = ref("");
const submitting = ref(false);
const errorMessage = ref("");

async function browse(path: string) {
  try {
    const data = await api.listDir(path);
    dir.value = data.path;
    parent.value = data.parent;
    entries.value = data.entries;
  } catch (error) {
    errorMessage.value = String(error);
  }
}

function toggleSelect(entry: FsEntry) {
  if (entry.is_dir) {
    void browse(entry.path);
    return;
  }
  if (!entry.is_markdown) return;
  const index = selected.value.indexOf(entry.path);
  if (index >= 0) {
    selected.value.splice(index, 1);
  } else {
    selected.value.push(entry.path);
  }
}

function isSelected(path: string) {
  return selected.value.includes(path);
}

function addCurrentDir() {
  if (!selected.value.includes(dir.value)) {
    selected.value.push(dir.value);
  }
}

function removeSelected(path: string) {
  selected.value = selected.value.filter((item) => item !== path);
}

async function loadConfigDefaults() {
  try {
    const data = await api.getConfig();
    outputDir.value = data.config.output.directory;
    if (data.config.target_languages.length) {
      langs.value = data.config.target_languages.join(", ");
    }
    mode.value = data.config.pipeline.mode;
  } catch {
    /* API offline; fields stay editable */
  }
}

async function submit() {
  errorMessage.value = "";
  const targetLangs = langs.value
    .split(/[,,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (!selected.value.length || !targetLangs.length) {
    errorMessage.value = "请至少选择一个文件/目录和一个目标语言";
    return;
  }
  submitting.value = true;
  try {
    const job = await api.createJob({
      paths: [...selected.value],
      target_langs: targetLangs,
      mode: mode.value,
      evaluate: evaluate.value,
      resume: resume.value,
      output_dir: outputDir.value || null,
    });
    void router.push(`/run/${job.id}`);
  } catch (error) {
    errorMessage.value = String(error);
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  void browse("~");
  void loadConfigDefaults();
});
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-5">
    <!-- 文件选择 -->
    <div class="card bg-base-100 shadow-sm lg:col-span-3">
      <div class="card-body gap-3">
        <h2 class="card-title text-base">选择要翻译的 Markdown</h2>
        <div class="flex items-center gap-2">
          <input class="input input-sm input-bordered grow font-mono" :value="dir" readonly />
          <button class="btn btn-sm" :disabled="!parent" @click="parent && browse(parent)">上一级</button>
          <button class="btn btn-sm btn-outline" @click="addCurrentDir">添加整个目录</button>
        </div>
        <ul class="menu w-full rounded-box border border-base-300 max-h-80 overflow-y-auto p-1">
          <li v-for="entry in entries" :key="entry.path">
            <button
              :class="{ 'menu-active': isSelected(entry.path) }"
              @click="toggleSelect(entry)"
            >
              <span>{{ entry.is_dir ? "📁" : entry.is_markdown ? "📝" : "📄" }}</span>
              <span class="truncate">{{ entry.name }}</span>
              <span
                v-if="entry.is_markdown"
                class="badge badge-xs"
                :class="isSelected(entry.path) ? 'badge-primary' : 'badge-ghost'"
              >
                {{ isSelected(entry.path) ? "已选" : "选" }}
              </span>
            </button>
          </li>
        </ul>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="path in selected"
            :key="path"
            class="badge badge-outline gap-1 font-mono text-xs"
          >
            {{ path.split("/").pop() }}
            <button class="cursor-pointer" @click="removeSelected(path)">✕</button>
          </span>
        </div>
      </div>
    </div>

    <!-- 任务参数 -->
    <div class="card bg-base-100 shadow-sm lg:col-span-2">
      <div class="card-body gap-3">
        <h2 class="card-title text-base">任务参数</h2>

        <label class="form-control">
          <span class="label-text pb-1">目标语言（逗号分隔）</span>
          <input v-model="langs" class="input input-bordered input-sm" placeholder="chinese, japanese" />
        </label>

        <fieldset class="fieldset">
          <legend class="fieldset-legend text-sm">翻译模式</legend>
          <div class="join w-full">
            <button
              v-for="option in [
                ['fast', '快速'],
                ['balanced', '平衡'],
                ['strict', '严格'],
              ]"
              :key="option[0]"
              class="btn btn-sm join-item grow"
              :class="mode === option[0] ? 'btn-primary' : 'btn-ghost'"
              @click="mode = option[0]"
            >
              {{ option[1] }}
            </button>
          </div>
        </fieldset>

        <label class="label cursor-pointer justify-start gap-3">
          <input v-model="evaluate" type="checkbox" class="toggle toggle-sm" />
          <span class="label-text">完成后 LLM 质量评估（--eval）</span>
        </label>
        <label class="label cursor-pointer justify-start gap-3">
          <input v-model="resume" type="checkbox" class="toggle toggle-sm" />
          <span class="label-text">断点续传（--resume）</span>
        </label>

        <label class="form-control">
          <span class="label-text pb-1">输出目录</span>
          <input v-model="outputDir" class="input input-bordered input-sm font-mono" placeholder="output" />
        </label>

        <div v-if="errorMessage" role="alert" class="alert alert-error alert-sm py-2 text-sm">
          {{ errorMessage }}
        </div>

        <button class="btn btn-primary mt-1" :disabled="submitting" @click="submit">
          <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
          开始翻译
        </button>
      </div>
    </div>
  </div>
</template>
