<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type AppConfig, type GlossaryEntry } from "../api/client";

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

const glossaryLang = ref("zh-CN");
const glossaryEntries = ref<GlossaryEntry[]>([]);
const newTerm = ref("");
const newRendering = ref("");
const glossaryBusy = ref(false);

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
  await loadGlossary();
}

async function loadGlossary() {
  try {
    const data = await api.glossaryList(glossaryLang.value);
    glossaryEntries.value = data.entries[glossaryLang.value] ?? [];
  } catch {
    glossaryEntries.value = [];
  }
}

async function upsertGlossaryEntry() {
  const term = newTerm.value.trim();
  const rendering = newRendering.value.trim();
  if (!term || !rendering) return;
  glossaryBusy.value = true;
  try {
    await api.glossaryUpsert(glossaryLang.value, term, rendering);
    newTerm.value = "";
    newRendering.value = "";
    show(`术语「${term}」已保存`, "success");
    await loadGlossary();
  } catch (error) {
    show(String(error), "error");
  } finally {
    glossaryBusy.value = false;
  }
}

async function deleteGlossaryEntry(term: string) {
  glossaryBusy.value = true;
  try {
    await api.glossaryDelete(glossaryLang.value, term);
    show(`术语「${term}」已删除`, "success");
    await loadGlossary();
  } catch (error) {
    show(String(error), "error");
  } finally {
    glossaryBusy.value = false;
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
        <!-- 模型服务（基础） -->
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">模型服务</h2>
            <label class="form-control">
              <span class="label-text pb-1">接口地址</span>
              <input v-model="config.provider.base_url" class="input input-bordered input-sm font-mono" placeholder="https://api.openai.com/v1" />
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label class="form-control">
                <span class="label-text pb-1">模型名称</span>
                <input v-model="config.provider.model" class="input input-bordered input-sm font-mono" placeholder="gpt-5-mini" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">API Key</span>
                <input
                  v-model="apiKeyInput"
                  type="password"
                  class="input input-bordered input-sm font-mono"
                  :placeholder="API_KEY_MASK"
                />
              </label>
            </div>
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

        <!-- 翻译偏好（基础） -->
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">翻译设置</h2>
            <label class="form-control">
              <span class="label-text pb-1">质量与速度</span>
              <div class="join w-full">
                <button
                  v-for="option in [['fast', '快速'], ['balanced', '均衡'], ['strict', '严格']]"
                  :key="option[0]"
                  class="btn btn-sm join-item grow"
                  :class="config.pipeline.mode === option[0] ? 'btn-primary' : 'btn-ghost'"
                  @click="config.pipeline.mode = option[0]"
                >
                  {{ option[1] }}
                </button>
              </div>
            </label>
            <label class="form-control">
              <span class="label-text pb-1">目标语言（多个用逗号分隔）</span>
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

        <!-- 文风（基础，通俗） -->
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">文风</h2>
            <div class="grid grid-cols-2 gap-3">
              <label class="form-control">
                <span class="label-text pb-1">文风</span>
                <input v-model="config.style.tone" class="input input-bordered input-sm" placeholder="如：轻松、正式、technical" />
              </label>
              <label class="form-control">
                <span class="label-text pb-1">目标读者</span>
                <input v-model="config.style.audience" class="input input-bordered input-sm" placeholder="如：developers" />
              </label>
            </div>
            <label class="form-control">
              <span class="label-text pb-1">保留原文的术语（逗号分隔）</span>
              <input v-model="termsText" class="input input-bordered input-sm" placeholder="Markdown, OpenAI, Python" />
            </label>
          </div>
        </div>

        <!-- 记忆与译名（基础，可管理） -->
        <div class="card bg-base-100 shadow-sm">
          <div class="card-body gap-3">
            <h2 class="card-title text-base">翻译记忆</h2>
            <p class="text-xs text-base-content/60">相同的段落直接复用历史译文，节省时间与费用。</p>
            <div class="flex items-center gap-4">
              <div class="stat bg-base-200 rounded-box px-4 py-2">
                <div class="stat-title text-xs">记忆条目</div>
                <div class="stat-value text-xl">{{ memoryStats?.entries ?? "—" }}</div>
              </div>
              <div class="stat bg-base-200 rounded-box px-4 py-2">
                <div class="stat-title text-xs">命中次数</div>
                <div class="stat-value text-xl">{{ memoryStats?.hits ?? 0 }}</div>
              </div>
              <button class="btn btn-error btn-outline btn-sm" :disabled="!memoryStats?.entries" @click="clearMemory">
                清空记忆
              </button>
            </div>
            <h3 class="pt-1 text-sm font-semibold">术语表</h3>
            <p class="text-xs text-base-content/60">为术语指定统一译法，全文保持一致；手动条目优先于自动生成。</p>
            <div class="flex flex-wrap items-end gap-2">
              <label class="form-control w-28">
                <span class="label-text pb-1">目标语言</span>
                <input v-model="glossaryLang" class="input input-bordered input-sm font-mono" @change="loadGlossary" />
              </label>
              <label class="form-control grow">
                <span class="label-text pb-1">术语</span>
                <input v-model="newTerm" class="input input-bordered input-sm font-mono" placeholder="workspace" />
              </label>
              <label class="form-control grow">
                <span class="label-text pb-1">译法</span>
                <input v-model="newRendering" class="input input-bordered input-sm" placeholder="工作区" @keyup.enter="upsertGlossaryEntry" />
              </label>
              <button class="btn btn-primary btn-sm" :disabled="glossaryBusy || !newTerm.trim() || !newRendering.trim()" @click="upsertGlossaryEntry">
                添加
              </button>
            </div>
            <div v-if="glossaryEntries.length" class="overflow-x-auto">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>词</th>
                    <th>译法</th>
                    <th>来源</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in glossaryEntries" :key="entry.term">
                    <td class="font-mono">{{ entry.term }}</td>
                    <td>{{ entry.rendering }}</td>
                    <td>
                      <span class="badge badge-sm" :class="entry.origin === 'user' ? 'badge-primary' : 'badge-ghost'">
                        {{ entry.origin === "user" ? "手动" : "自动" }}
                      </span>
                    </td>
                    <td class="text-right">
                      <button class="btn btn-ghost btn-xs text-error" :disabled="glossaryBusy" @click="deleteGlossaryEntry(entry.term)">
                        删除
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="text-sm text-base-content/50">还没有固定译名，直接在上方添加即可。</p>
          </div>
        </div>

        <!-- 高级设置（默认收起） -->
        <details class="collapse collapse-arrow bg-base-100 shadow-sm lg:col-span-2">
          <summary class="collapse-title text-base font-semibold">
            高级设置
          </summary>
          <div class="collapse-content flex flex-col gap-5">
            <!-- 质量保障开关 -->
            <section class="flex flex-col gap-2">
              <h3 class="text-sm font-semibold">翻译质量保障</h3>
              <div class="grid gap-2 md:grid-cols-2">
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_glossary" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">统一术语译法<span class="ml-1 text-xs text-base-content/50">全文保持一致</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_sentinels" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">漏译检查<span class="ml-1 text-xs text-base-content/50">检测遗漏的数字与内容</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_anchor_scheduling" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">上下文衔接<span class="ml-1 text-xs text-base-content/50">参考已译内容保持连贯</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_context_pull" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">自动补充上下文<span class="ml-1 text-xs text-base-content/50">检索相似的历史译文</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_final_edit" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">全文最终校对<span class="ml-1 text-xs text-base-content/50">仅严格模式生效</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.memory.fuzzy_examples" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">复用相似翻译<span class="ml-1 text-xs text-base-content/50">相似段落复用历史译文</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.memory.enabled" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">启用翻译记忆<span class="ml-1 text-xs text-base-content/50">关闭后每次重新翻译</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_review" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">强制审校<span class="ml-1 text-xs text-base-content/50">对所有文本包执行审校</span></span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.enable_format_guard" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">强制格式修复</span>
                </label>
                <label class="label cursor-pointer justify-start gap-3">
                  <input v-model="config.pipeline.fail_on_validation_error" type="checkbox" class="toggle toggle-sm" />
                  <span class="label-text">格式校验失败时中止</span>
                </label>
              </div>
            </section>

            <!-- 模型进阶 -->
            <section class="flex flex-col gap-3">
              <h3 class="text-sm font-semibold">模型进阶</h3>
              <div class="grid gap-3 md:grid-cols-2">
                <label class="form-control">
                  <span class="label-text pb-1">审校模型（留空与翻译一致）</span>
                  <input v-model="config.pipeline.reviewer_model" class="input input-bordered input-sm font-mono" placeholder="gpt-5-mini" />
                </label>
                <label class="form-control">
                  <span class="label-text pb-1">评分模型（留空与翻译一致）</span>
                  <input v-model="config.pipeline.judge_model" class="input input-bordered input-sm font-mono" placeholder="gpt-5" />
                </label>
                <label class="form-control">
                  <span class="label-text pb-1">密钥环境变量名</span>
                  <input v-model="config.provider.api_key_env" class="input input-bordered input-sm font-mono" />
                </label>
                <label class="form-control">
                  <span class="label-text pb-1">结构化输出</span>
                  <select v-model="config.provider.structured_outputs" class="select select-bordered select-sm">
                    <option value="auto">auto（推荐，自动适配）</option>
                    <option value="on">on（强制 json_schema）</option>
                    <option value="off">off（始终 json_object）</option>
                  </select>
                </label>
              </div>
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
            </section>

            <!-- 性能与分包 -->
            <section class="flex flex-col gap-3">
              <h3 class="text-sm font-semibold">性能与分包</h3>
              <div class="grid grid-cols-2 gap-3 md:grid-cols-3">
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
                <label class="form-control">
                  <span class="label-text pb-1">章节对齐字符数</span>
                  <input v-model.number="config.segmentation.section_align_min_chars" type="number" min="0" class="input input-bordered input-sm" />
                </label>
                <label class="form-control">
                  <span class="label-text pb-1">审校轮数</span>
                  <input v-model.number="config.pipeline.review_max_rounds" type="number" min="1" max="5" class="input input-bordered input-sm" />
                </label>
                <label class="form-control">
                  <span class="label-text pb-1">记忆复用范围</span>
                  <select v-model="config.memory.scope" class="select select-bordered select-sm">
                    <option value="document">同一文档（推荐）</option>
                    <option value="global">跨文档</option>
                  </select>
                </label>
              </div>
            </section>

            <!-- 附加指令 -->
            <section class="flex flex-col gap-3">
              <h3 class="text-sm font-semibold">附加指令（每行一条）</h3>
              <textarea v-model="instructionsText" class="textarea textarea-bordered textarea-sm" rows="3"></textarea>
            </section>
          </div>
        </details>
      </div>
    </template>
  </div>
</template>
