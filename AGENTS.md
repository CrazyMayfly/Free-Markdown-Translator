# AGENTS.md

给 AI 编码代理（ZCode / Claude Code / Cursor 等）在本仓库工作时的指引。

## 项目概览

mdtx 是基于 AI Agent 流水线的 Markdown 翻译工具，由三部分组成：

1. **Python 核心管线与 CLI**（`src/`）：解析 → 分段 → 翻译 → 审校 → 格式修复 → 校验 → 渲染，兼容任意 OpenAI 接口
2. **FastAPI 服务层**（`src/api/`）：任务管理、SSE 进度、配置/历史/记忆路由，供前端调用
3. **桌面应用**（`ui/`）：Tauri 2 壳 + Vue3 前端 + PyInstaller 打包的 `mdtx-api` sidecar

## 环境与工具链

- **Python 3.11**，虚拟环境在 `.venv`（一律用 `.venv/bin/python`，不要用系统 python）
- **Node** 通过 nvm 安装：`source ~/.nvm/nvm.sh && nvm use default`
- **Rust** 通过 rustup：`source "$HOME/.cargo/env"`
- npm 走 npmmirror 镜像；本机有系统代理，**curl 本地端口必须加 `--noproxy '*'`**

## 常用命令

```bash
# 后端测试（全量，提交前必须通过）
.venv/bin/python -m pytest src/test -q

# Lint（提交前必须通过）
.venv/bin/ruff check src

# 前端类型检查与构建
cd ui && npm run build

# Rust 壳检查
cd ui/src-tauri && cargo check

# 打包桌面应用（先 sidecar 后 Tauri，产物在 ui/src-tauri/target/release/bundle/）
.venv/bin/python -m src.buildtool.build_api
cd ui && npx tauri build

# 本地起 API（浏览器开发模式，配合 cd ui && npm run dev）
.venv/bin/mdtx --ui-port 8000 --ui-headless
# vite 代理目标不是 8000 时用 MDTX_API_TARGET=http://127.0.0.1:<port> 覆盖
```

## 架构速查

```
src/
├─ agents/      TranslatorAgent / ReviewerAgent / FormatGuardAgent / JudgeAgent
├─ api/         FastAPI：app.py(路由工厂) jobs.py(JobManager) history.py(SQLite 历史)
├─ cli/         命令行入口（mdtx）；--ui-port 复用 api.run_server
├─ core/        pipeline.py(管线编排) errors.py
├─ llm/         同步/异步 Provider，Structured Outputs 自动降级
├─ memory/      翻译记忆(SQLite) 与断点(JobCheckpointStore)
├─ parser/      解析/分段/AST 映射/渲染
└─ buildtool/   build_api.py（PyInstaller sidecar 打包）
ui/
├─ src/         Vue3 + daisyUI5：views/{Submit,Run,Result,Jobs,Config}View.vue
└─ src-tauri/   Rust 壳：sidecar 生命周期、api_ready_state 端口握手、通知插件
```

## 关键约定

- **提交纪律**：按功能分阶段提交，每个提交前测试 + ruff 通过；commit message 用英文 conventional 风格（feat/fix/docs/ci/perf + 范围）
- **测试**：API 层测试用 `FakeUiPipeline` + `patch("src.api.jobs.build_pipeline", ...)`，走 httpx ASGITransport；新功能必须带测试；fake 的字段要跟 `PipelineResult` 保持一致
- **UI 文案用中文**；README 主文档中文（`docs/README.*.md` 是各语言翻译版）
- **API Key 安全**：GET 永远返回掩码 `********`；PATCH 收到掩码或空值时保留已存密钥（见 `app.py` 的 `_strip_mask`）
- **任务执行**：`JobManager._execute` 用 TaskGroup 跨「文件×语言」对并行，一个全局 `asyncio.Semaphore(max_parallel_translations)` 限制 LLM 并发；用量统计必须是**增量累加**（并发下快照覆盖会互相冲掉）
- **译文不丢原则**：输出文件写失败时抛 `OutputWriteError`（携带译文/段落/校验），API 层转为 `write_error` 结果而不是失败
- **历史持久化**：任务终态写入 `~/.mdtx/history.sqlite3`；重存历史时必须带上 `params`（否则「再来一次」失效）；段落修订通过 `rerender_markdown` 按文档顺序重排全文
- **配置**：用户配置在 `~/.mdtx/config.yaml`；可写字段白名单见 `_CONFIG_WRITABLE_SECTIONS`

## 发布流程

1. 更新版本号：`pyproject.toml`、`ui/src-tauri/tauri.conf.json`、`ui/src-tauri/Cargo.toml`、`ui/package.json`、`src/api/app.py`（五处保持一致），跑 `cargo check` 同步 Cargo.lock
2. 更新 `.github/release-body.md`（发布文案）
3. 提交推送后打 `v*` 标签推送 → GitHub Actions 矩阵自动构建 macOS/Windows/Linux 产物并挂到 Release

## 已踩过的坑（勿重蹈）

- **Windows 下 `platform.machine()` 返回 `AMD64`**：任何 arch 判断先 `.lower()` 再比较，归一成 Rust triple 名（`x86_64`/`aarch64`），sidecar 文件名必须是 `mdtx-api-<triple>[.exe]`（Tauri externalBin 约定）
- **sidecar 生命周期**：dev 模式跑仓库 `.venv/bin/mdtx`；release 模式跑 exe 同目录的 `mdtx-api --parent-pid <pid>`（watchdog 轮询 `os.kill(pid, 0)`，不能用 getppid——PyInstaller bootloader 会隔一层）；sidecar 的 cwd 必须设为用户主目录（GUI 应用默认 cwd=/ 只读）
- **端口握手**：前端先 invoke `api_ready_state` 命令查询，`api-ready` 事件只作兜底（webview 启动早期事件会丢）
- **Vue 陷阱**：ref 嵌在普通对象里模板不会解包，需要 `reactive()`
- **Tauri webview 里 Playwright locator 点击会卡死**：自动化 UI 用 computer-use 元素索引或坐标
- **PyInstaller onefile 未签名 exe**：CI 上可能被 Windows Defender 误报隔离（workflow 已加排除），本地复现"文件莫名消失"时先想到这个
- **Actions 排障**：匿名读不到 Actions 日志，workflow 失败时会把错误尾部写进 check-run annotations（`::error::`），用公开 API 可读
