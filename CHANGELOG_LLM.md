# LLM 翻译器功能更新日志

## 新增功能

### 1. LLM 翻译器核心模块

**文件**: `src/llm_translator.py`

新增了基于大语言模型的翻译器，支持多种 LLM 提供商：

- ✅ OpenAI (GPT-3.5, GPT-4)
- ✅ Anthropic Claude (Claude-3)
- ✅ 通义千问 (Qwen)
- ✅ 智谱 AI (GLM)
- ✅ DeepSeek

**核心特性**:
- 完全兼容现有的翻译器接口
- 自动重试机制（最多5次）
- 指数退避策略
- 支持自定义 API 端点
- 智能的翻译提示词构建
- 完整的错误处理

### 2. 配置文件更新

**文件**: `src/config.yaml`

新增了 LLM 配置部分：
```yaml
translator: llm  # 设置为 llm 启用 LLM 翻译

llm_config:
  provider: openai
  api_key: 'your-api-key'
  api_base: ''
  model: gpt-3.5-turbo
  temperature: 0.3
  max_tokens: 2000
```

**文件**: `src/config.py`

- 在 `Configration` 数据类中新增 `llm_config` 字段
- 在 `SUPPORTED_TRANSLATORS` 中添加 `'llm'` 支持
- 更新默认配置函数以支持 LLM 配置

### 3. 主程序集成

**文件**: `src/MarkdownTranslator.py`

修改了 `MdTranslater` 类的初始化方法：
- 根据配置自动选择使用传统翻译器或 LLM 翻译器
- 无缝集成，不影响现有功能

### 4. 依赖管理

**文件**: `requirements.txt`

添加了 LLM 相关的可选依赖说明：
```
# LLM 翻译器依赖（可选）
# openai>=1.0.0
# anthropic>=0.18.0
```

### 5. 文档和示例

新增了以下文件：

1. **LLM_TRANSLATOR_README.md** - 详细的使用文档
   - 功能介绍和优势
   - 支持的 LLM 提供商
   - 详细的配置步骤
   - 配置示例
   - 成本对比
   - 常见问题解答

2. **src/config.yaml** 中的 **llm_config**（可选）
   - 在 `config.yaml` 中配置 `llm_config`（api_base、model、api_key 等）优先于 .env
   - 不配置时从项目根目录 `.env` 读取 LLM_MODEL_URL / LLM_MODEL_NAME / LLM_MODEL_API_KEY

3. **test_llm_translator.py** - 测试脚本
   - 快速测试 LLM 翻译器是否正常工作
   - 配置验证
   - 简单的翻译测试

4. **CHANGELOG_LLM.md** - 本文件
   - 详细的变更记录

## 技术实现细节

### 接口兼容性

`LLMTranslator` 类实现了与 `Translator` 类完全相同的接口：

```python
class LLMTranslator:
    def translate(self, source_text: str, src_lang: str, target_lang: str, retries: int = 0) -> str
    def translate_in_batch(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str
```

### 翻译提示词设计

精心设计的提示词确保了：
1. 保持 Markdown 格式
2. 不翻译代码块和技术术语
3. 保留行数一致
4. 自然的翻译风格

### 错误处理

- API 调用失败自动重试
- 指数退避避免频繁请求
- 详细的日志记录
- 友好的错误提示

### 扩展性

架构设计支持轻松添加新的 LLM 提供商：
1. 在 `_init_client()` 中添加新的 provider 分支
2. 在 `_call_llm_api()` 中实现 API 调用逻辑
3. 更新配置文档

## 使用方法

### 快速开始

1. 安装依赖：
```bash
pip install openai  # 或 pip install anthropic
```

2. 配置 LLM（二选一）：
   - 在 `src/config.yaml` 中取消注释并填写 `llm_config`（api_base、model、api_key）
   - 或在项目根目录 `.env` 中设置 `LLM_MODEL_URL`、`LLM_MODEL_NAME`、`LLM_MODEL_API_KEY`

3. 测试：
```bash
python test_llm_translator.py
```

4. 使用：
```bash
cd src
python MarkdownTranslator.py -f ../README.md
```

### 从传统翻译器迁移

只需修改 `config.yaml` 中的一行：
```yaml
translator: llm  # 原来是 google, bing 等
```

## 优势对比

### 相比传统翻译引擎：

| 特性 | 传统翻译 | LLM 翻译 |
|------|---------|---------|
| 上下文理解 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 技术术语 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 翻译自然度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 格式保留 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 翻译速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 成本 | 免费 | 按量计费 |
| 网络要求 | 中等 | 较高 |

## 兼容性

- ✅ 完全向后兼容现有代码
- ✅ 不影响传统翻译器功能
- ✅ 支持所有现有的配置选项
- ✅ 支持所有现有的命令行参数

## 测试建议

1. 先使用 `test_llm_translator.py` 测试基本功能
2. 用小文件测试翻译质量
3. 观察翻译成本
4. 根据需要调整 `temperature` 和 `model` 参数

## 注意事项

1. **API 密钥安全**: 不要将真实的 API Key 提交到版本控制
2. **成本控制**: 建议先小规模测试
3. **网络连接**: 部分服务需要稳定的网络连接
4. **配额限制**: 注意 API 提供商的调用频率限制

## 贡献

欢迎贡献代码添加更多 LLM 提供商支持！

## 未来计划

- [ ] 添加本地模型支持（Ollama, LM Studio）
- [ ] 支持流式输出显示翻译进度
- [ ] 添加翻译缓存减少重复调用
- [ ] 支持批量翻译优化成本
- [ ] 添加翻译质量评估

## 版本信息

- **版本**: 1.0.0
- **更新日期**: 2024-02-04
- **兼容性**: 与原项目完全兼容
