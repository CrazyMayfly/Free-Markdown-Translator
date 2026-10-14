<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type AppConfig } from "../api/client";

const API_KEY_MASK = "********";

const config = ref<AppConfig | null>(null);
const configPath = ref("");
const apiKeyInput = ref("");
const saving = ref(false);
const message = ref("");
const messageKind = ref<"success" | "error">("success");
const memoryStats = ref<{ hits: number; misses: number; entries: number } | null>(null);
const testing = ref(false);
const testResult = ref<{ ok: boolean; text: string } | null>(null);

const termsText = ref("");
const instructionsText = ref("");

async function load() {
  try {
    const data = await api.getConfig();
    config.value = data.config;
    configPath.value = data.config_path;
    apiKeyInput.value = data.config.provider.api_key || "";
    termsText.value = data.config.style.preserve_terms.join(", ");
    instructionsText.value = data.config.style.instructions.join("\n");
  } catch (error) {
    show(String(error), "error");
  }
  try {
    memoryStats.value = await api.memoryStats();
  } catch {
    memoryStats.value = null;
  }
}

function show(text: string, kind: "success" | "error") {
  message.value = text;
  messageKind.value = kind;
  setTimeout(() => {
    message.value = "";
  }, 4000);
}

async function save() {
  if (!config.value) return;
  saving.value = true;
  try {
    const patch = {
      target_languages: config.value.target_languages,
      provider: {
        ...config.value.provider,
        api_key: apiKeyInput.value || API_KEY_MASK,
      },
      pipeline: config.value.pipeline,
      segmentation: config.value.segmentation,
      input: config.value.input,
      style: {
        ...config.value.style,
        preserve_terms: termsText.value
          .split(/[,,，]/)
          .map((item) => item.trim())
          .filter(Boolean),
        instructions: instructionsText.value
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      },
      output: config.value.output,
      execution: config.value.execution,
      memory: config.value.memory,
    };
    const data = await api.patchConfig(patch as Partial<AppConfig>);
    config.value = data.config;
    apiKeyInput.value = data.config.provider.api_key || "";
    show(`已保存到 ${data.config_path}`, "success");
  } catch (error) {
    show(String(error), "error");
  } finally {
    saving.value = false;
  }
}

async function testConnection() {
  if (!config.value) return;
  testing.value = true;
  testResult.value = null;
  try {
    const result = await api.testConfig({
      base_url: config.value.provider.base_url,
      api_key: apiKeyInput.value || undefined,
      model: config.value.provider.model,
    });
    if (result.ok) {
      const models = result.models?.length ? `，网关模型 ${result.models.length} 个` : "";
      if (result.model_warning) {
        testResult.value = { ok: false, text: `连接成功（${result.latency_ms}ms${models}）；${result.model_warning}` };
      } else {
        testResult.value = { ok: true, text: `连接成功（${result.latency_ms}ms${models}），模型 ${config.value.provider.model} 可用` };
      }
    } else {
      testResult.value = { ok: false, text: result.error ?? "连接失败" };
    }
  } catch (error) {
    testResult.value = { ok: false, text: String(error) };
  } finally {
    testing.value = false;
  }
}

async function clearMemory() {
  const removed = await api.clearMemory();
  show(`已清除 ${removed.removed} 条翻译记忆`, "success");
  memoryStats.value = await api.memoryStats();
}

onMounted(load);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <h1 class="text-lg font-bold">配置</h1>
      <span class="font-mono text-xs text-base-content/50">{{ configPath }}</span>
      <div class="grow"></div>
      <button class="btn btn-primary btn-sm" :disabled="saving || !config" @click="save">
        <span v-if="saving" class="loading loading-spinner loading-xs"></span>
        保存
      </button>
    </div>

    <div v-if="message" role="alert" class="alert alert-sm py-2 text-sm" :class="messageKind === 'success' ? 'alert-success' : 'alert-error'">
      {{ message }}
    </div>

    <template v-if="config">
      <div class="grid gap-4 lg:grid-cols-2">
        <!-- Provider -->
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">模型服务</h2>
            <label class="form-control">
              <span class="label-text pb-1">Base URL（OpenAI 兼容端点）</span>
              <input v-model="config.provider.base_url" class="input input-bordered input-sm font-mono" />
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label class="form-control">
                <span class="label-text pb-1">模型</span>
                <input v-model="config.provider.model" class="input input-bordered input-sm font-mono" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">API Key 环境变量名</span>
                <input v-model="config.provider.api_key_env" class="input input-bordered input-sm font-mono" />
              </label>
            </div>
            <label class="form-control">
              <span class="label-text pb-1">
                API Key
                <span class="text-xs text-base-content/50">（留空或保持掩码 = 不修改已存密钥）</span>
              </span>
              <input
                v-model="apiKeyInput"
                type="password"
                class="input input-bordered input-sm font-mono"
                :placeholder="API_KEY_MASK"
              />
            </label>
            <div class="grid grid-cols-3 gap-3">
              <label class="form-control">
                <span class="label-text pb-1">温度</span>
                <input v-model.number="config.provider.temperature" type="number" step="0.1" min="0" max="2" class="input input-bordered input-sm" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">max_tokens</span>
                <input v-model.number="config.provider.max_tokens" type="number" class="input input-bordered input-sm" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">重试次数</span>
                <input v-model.number="config.provider.max_retries" type="number" min="0" max="10" class="input input-bordered input-sm" />
              </label>
            </div>
            <label class="form-control">
              <span class="label-text pb-1">结构化输出</span>
              <select v-model="config.provider.structured_outputs" class="select select-bordered select-sm">
                <option value="auto">auto（不支持时自动降级）</option>
                <option value="on">on（强制 json_schema）</option>
                <option value="off">off（始终 json_object）</option>
              </select>
            </label>
            <div class="flex items-center gap-3">
              <button class="btn btn-outline btn-sm" :disabled="testing" @click="testConnection">
                <span v-if="testing" class="loading loading-spinner loading-xs"></span>
                测试连接
              </button>
              <span v-if="testResult" class="text-xs" :class="testResult.ok ? 'text-success' : 'text-error'">
                {{ testResult.text }}
              </span>
            </div>
          </div>
        </div>

        <!-- Pipeline & execution -->
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">流程与执行</h2>
            <label class="form-control">
              <span class="label-text pb-1">翻译模式</span>
              <div class="join w-full">
                <button
                  v-for="option in [['fast', '快速'], ['balanced', '平衡'], ['strict', '严格']]"
                  :key="option[0]"
                  class="btn btn-sm join-item grow"
                  :class="config.pipeline.mode === option[0] ? 'btn-primary' : 'btn-ghost'"
                  @click="config.pipeline.mode = option[0]"
                >
                  {{ option[1] }}
                </button>
              </div>
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label class="label cursor-pointer justify-start gap-3">
                <input v-model="config.pipeline.enable_review" type="checkbox" class="toggle toggle-sm" />
                <span class="label-text">强制审校 Agent</span>
              </label>
              <label class="label cursor-pointer justify-start gap-3">
                <input v-model="config.pipeline.enable_format_guard" type="checkbox" class="toggle toggle-sm" />
                <span class="label-text">强制格式修复</span>
              </label>
              <label class="label cursor-pointer justify-start gap-3">
                <input v-model="config.pipeline.fail_on_validation_error" type="checkbox" class="toggle toggle-sm" />
                <span class="label-text">校验失败即报错</span>
              </label>
              <label class="label cursor-pointer justify-start gap-3">
                <input v-model="config.memory.enabled" type="checkbox" class="toggle toggle-sm" />
                <span class="label-text">翻译记忆</span>
              </label>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <label class="form-control">
                <span class="label-text pb-1">并行数</span>
                <input v-model.number="config.execution.max_parallel_translations" type="number" min="1" max="32" class="input input-bordered input-sm" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">包字符上限</span>
                <input v-model.number="config.segmentation.max_bundle_chars" type="number" class="input input-bordered input-sm" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">包段落上限</span>
                <input v-model.number="config.segmentation.max_bundle_segments" type="number" class="input input-bordered input-sm" />
              </label>
            </div>
            <label class="form-control">
              <span class="label-text pb-1">默认目标语言（逗号分隔）</span>
              <input
                class="input input-bordered input-sm"
                :value="config.target_languages.join(', ')"
                @change="config.target_languages = ($event.target as HTMLInputElement).value.split(/[,,，]/).map(s => s.trim()).filter(Boolean)"
              />
            </label>
            <label class="form-control">
              <span class="label-text pb-1">输出目录</span>
              <input v-model="config.output.directory" class="input input-bordered input-sm font-mono" />
            </label>
          </div>
        </div>

        <!-- Style -->
        <div class="card bg-base-100 shadow-sm lg:col-span-2">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">文风与术语</h2>
            <div class="grid gap-3 md:grid-cols-2">
              <label class="form-control">
                <span class="label-text pb-1">语气（tone）</span>
                <input v-model="config.style.tone" class="input input-bordered input-sm" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">受众（audience）</span>
                <input v-model="config.style.audience" class="input input-bordered input-sm" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">保留术语（逗号分隔，注入上下文保护）</span>
                <input v-model="termsText" class="input input-bordered input-sm" placeholder="Markdown, OpenAI, Python" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">附加指令（每行一条）</span>
                <textarea v-model="instructionsText" class="textarea textarea-bordered textarea-sm" rows="3"></textarea>
              </label>
            </div>
          </div>
        </div>

        <!-- Memory management -->
        <div class="card bg-base-100 shadow-sm lg:col-span-2">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">翻译记忆</h2>
            <div class="flex items-center gap-4">
              <div class="stat bg-base-200 rounded-box px-4 py-2">
                <div class="stat-title text-xs">记忆条目</div>
                <div class="stat-value text-xl">{{ memoryStats?.entries ?? "—" }}</div>
              </div>
              <div class="stat bg-base-200 rounded-box px-4 py-2">
                <div class="stat-title text-xs">命中 / 未命中</div>
                <div class="stat-value text-xl">{{ memoryStats?.hits ?? 0 }} / {{ memoryStats?.misses ?? 0 }}</div>
              </div>
              <button class="btn btn-error btn-outline btn-sm" :disabled="!memoryStats?.entries" @click="clearMemory">
                清空记忆库
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
