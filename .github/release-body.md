# mdtx v3.0.0 · 全新桌面工作台 + Agent 流水线大版本

历时一个大的迭代周期，mdtx 从命令行工具进化为**开箱即用的跨平台桌面应用**，同时 AI Agent 翻译流水线完成全面升级。

## 🖥️ 全新桌面应用（本次最大更新）

无需 Python 环境，下载安装即可使用——Tauri 2 壳 + Vue3 前端 + 内置完整翻译管线的本地 sidecar，仅监听 `127.0.0.1`，数据不出本机。

- **任务创建**：访达拖拽 / 文件浏览器多选文件或整个目录（按 `*.md` 递归收集），语言标签多选，快速 / 平衡 / 严格三种模式，断点续传
- **实时进度**：任务 × 翻译对双层进度、bundle 级进度条、token 用量与前缀缓存命中率实时累计；**多文件 × 多语言任务自动并行执行**
- **结果对照与人工修订**：渲染视图 / 分段对照双视图；段落级人工修订，保存后自动同步整篇译文；一键复制译文、保存到文件、在访达中显示
- **任务历史**：所有任务持久化到本机（`~/.mdtx/history.sqlite3`），重启应用不丢；支持「再来一次」按原参数重新提交
- **可靠性**：输出文件写入失败时译文不丢失，可一键手动保存；任务在后台完成/失败时弹系统通知
- **配置中心**：表单化管理 `~/.mdtx/config.yaml`（API Key 掩码不回显）、一键测试模型端点连通性（延迟 + 模型列表）、翻译记忆统计与清空、深色模式

## 🤖 Agent 流水线升级

- **Structured Outputs 受限解码**：LLM 输出强制遵循 JSON Schema，端点不支持时自动降级，从根源消灭格式错误
- **反思式审校循环**：审校 Agent 先输出结构化批评意见（accuracy / fluency / terminology / style + 严重度分级），再只针对被标记段落改进
- **LLM-as-judge 质量评估**：按准确度 / 流畅度 / 术语 / 格式四维打分（CLI `--eval` / 桌面端评估开关）
- **翻译记忆**：相同段落（同源文、同语言、同模型、同风格）直接复用历史译文，零 LLM 调用
- **断点续传**：`--resume` 从上次中断处继续，已完成的翻译包不再重复翻译
- **异步并发与自动退避**：asyncio 单事件循环 + 全局并发信号量，限流 / 超时 / 5xx 指数退避并尊重 Retry-After
- 端到端集成测试覆盖完整任务生命周期

## 🔌 全新 MCP 集成：让 AI 客户端直接调用翻译能力

一条命令把 mdtx 变成 MCP 服务器，ZCode / Claude Desktop / Cursor 等支持 MCP 的 AI 客户端即可在对话中直接调用翻译：

```bash
pip install "mdtx[mcp]"
mdtx --serve
```

客户端配置示例：

```json
{
  "mcpServers": {
    "mdtx": {
      "command": "mdtx",
      "args": ["--serve"]
    }
  }
}
```

暴露两个 MCP 工具：

- `translate_markdown(path, target_langs, mode?, tone?, model?, write?)`：翻译 Markdown 文件，返回各语言译文、校验结果与 token 用量，翻译进度通过 MCP 进度通知实时上报
- `evaluate_translation(path, target_lang)`：翻译并用 LLM-as-judge 按四维打分

## 📦 下载

| 平台 | 文件 |
|------|------|
| macOS (Apple Silicon) | `mdtx_3.0.0_aarch64.dmg` |
| Windows x64 | `mdtx_3.0.0_x64-setup.exe` |
| Ubuntu / Debian | `mdtx_3.0.0_amd64.deb` |
| Linux 通用 | `mdtx_3.0.0_amd64.AppImage` |

CLI 用户依然可以 `pip install -e .` 后使用 `mdtx` 命令，桌面端与 CLI 共用 `~/.mdtx/config.yaml` 和翻译记忆库。

## ⚠️ 说明

- 安装包**未做代码签名**：macOS 首次打开请右键 → 打开；Windows 可能出现 SmartScreen 提示，选择「仍要运行」即可
- 首次启动后在「配置」页填入任意 OpenAI 兼容端点（OpenAI / OpenRouter / DeepSeek / Ollama / vLLM…）、密钥与模型，点「测试连接」验证后即可开始翻译

**Full Changelog**: https://github.com/CrazyMayfly/Free-Markdown-Translator/compare/2.0...v3.0
