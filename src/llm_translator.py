import copy
import logging
import os
import re
import sys
import time
from typing import Optional
from pathlib import Path

from Utils import SymbolWidthUtil, RawData, Pbar
from config import config as app_config

# 加载环境变量
try:
    from dotenv import load_dotenv
    # 从项目根目录加载 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    logging.info(f"Loaded environment variables from {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    logging.warning(f"Failed to load .env file: {e}")

MAX_RETRY = 5


class LLMTranslateError(Exception):
    pass


class LLMTranslator:
    """
    使用大语言模型 API 进行翻译的翻译器。
    配置优先级：src/config.yaml 中的 llm_config > .env 中的 LLM_MODEL_URL / LLM_MODEL_NAME / LLM_MODEL_API_KEY。
    """

    def __init__(self):
        """初始化 LLM 翻译器：优先使用 config.yaml 的 llm_config，否则从 .env 读取"""
        llm_cfg = getattr(app_config, "llm_config", None) or {}

        # 优先 config.yaml 的 llm_config，否则 .env
        self.api_base = (llm_cfg.get("api_base") or "").strip() or os.getenv("LLM_MODEL_URL", "")
        self.model = (llm_cfg.get("model") or "").strip() or os.getenv("LLM_MODEL_NAME", "gpt-5-mini")
        self.api_key = (llm_cfg.get("api_key") or "").strip() or os.getenv("LLM_MODEL_API_KEY", "")
        self.https_proxy = os.getenv("https_proxy", "")
        self.http_proxy = os.getenv("http_proxy", "")
        self.temperature = float(llm_cfg.get("temperature", 0.3))
        self.max_tokens = int(llm_cfg.get("max_tokens", 2000))

        if not self.api_key:
            logging.error("LLM api_key not set. Configure llm_config.api_key in src/config.yaml or LLM_MODEL_API_KEY in .env")
            sys.exit(1)
        if not self.api_base:
            logging.error("LLM api_base not set. Configure llm_config.api_base in src/config.yaml or LLM_MODEL_URL in .env")
            sys.exit(1)

        # 初始化 OpenAI 客户端
        self._init_client()

        logging.info("LLM Translator initialized (config from %s)", "config.yaml" if llm_cfg else ".env")
        logging.info(f"  Model: {self.model}")
        logging.info(f"  API Base: {self.api_base}")
        if self.https_proxy or self.http_proxy:
            logging.info(f"  Proxy: {self.https_proxy or self.http_proxy}")

    def _init_client(self):
        """初始化 OpenAI 客户端（支持代理）"""
        try:
            from openai import OpenAI
            import httpx
            
            # 创建带代理的 HTTP 客户端
            # 优先使用 https_proxy，如果没有则使用 http_proxy
            proxy = self.https_proxy or self.http_proxy
            
            if proxy:
                # httpx 的新版本使用 proxy 参数（单个字符串）而不是 proxies（字典）
                http_client = httpx.Client(
                    proxy=proxy,
                    timeout=60.0,
                )
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                    http_client=http_client,
                )
            else:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                )
                
        except ImportError as e:
            logging.error(f"Failed to import required library: {e}")
            logging.error("Please install with: pip install openai httpx python-dotenv")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Failed to initialize LLM client: {e}")
            sys.exit(1)

    def _build_translation_prompt(self, text: str, src_lang: str, target_lang: str) -> str:
        """构建翻译提示词"""
        # 语言代码到全称的映射
        lang_names = {
            'zh': '简体中文',
            'zh-tw': '繁体中文',
            'en': 'English',
            'ja': '日本語',
            'ko': '한국어',
            'fr': 'Français',
            'de': 'Deutsch',
            'es': 'Español',
            'ru': 'Русский',
            'pt': 'Português',
            'hi': 'हिन्दी',
            'ar': 'العربية',
            'auto': 'auto-detect'
        }

        src_lang_name = lang_names.get(src_lang.lower(), src_lang)
        target_lang_name = lang_names.get(target_lang.lower(), target_lang)

        prompt = f"""You are a professional translator. Please translate the following text from {src_lang_name} to {target_lang_name}.

Requirements:
1. Maintain the original meaning and tone
2. Keep all markdown formatting symbols (like **, `, ##, etc.)
3. Do not translate code blocks, URLs, or technical terms in backticks
4. Preserve line breaks as much as reasonably possible
5. Only output the translated text, no explanations

Text to translate:
{text}

Translation:"""

        return prompt

    def _build_tagged_parts_prompt(
        self,
        tagged_text: str,
        src_lang: str,
        target_lang: str,
        context_before: str = "",
        context_after: str = "",
    ) -> str:
        """
        构建“带编号标记”的翻译提示词。
        目的：避免 LLM 输出行数/分段数与输入不一致导致的回填错位。
        """
        lang_names = {
            'zh': '简体中文',
            'zh-tw': '繁体中文',
            'en': 'English',
            'ja': '日本語',
            'ko': '한국어',
            'fr': 'Français',
            'de': 'Deutsch',
            'es': 'Español',
            'ru': 'Русский',
            'pt': 'Português',
            'hi': 'हिन्दी',
            'ar': 'العربية',
            'auto': 'auto-detect'
        }
        src_lang_name = lang_names.get(src_lang.lower(), src_lang)
        target_lang_name = lang_names.get(target_lang.lower(), target_lang)

        # 约定：每段形如 ⟦123⟧...⟦/123⟧，模型必须原样保留这些标记
        # 上下文窗口：提供前后文帮助理解，但禁止翻译/输出上下文；回填时只解析标签内容
        context_section = ""
        if context_before.strip():
            context_section += f"\nContext before (for reference only; DO NOT translate or output):\n{context_before}\n"
        if context_after.strip():
            context_section += f"\nContext after (for reference only; DO NOT translate or output):\n{context_after}\n"

        return f"""You are a professional translator. Translate the content between the numbered tags from {src_lang_name} to {target_lang_name}.

Requirements:
1. Keep ALL numbered tags EXACTLY unchanged (e.g., ⟦0⟧ and ⟦/0⟧ must remain as-is)
2. Translate ONLY the text inside each tag
3. Keep markdown formatting inside the text (like **, `, ##, etc.)
4. Do not translate URLs, code blocks, or technical terms in backticks
5. Context before/after is ONLY for understanding: DO NOT translate it and DO NOT output it
6. Output MUST contain ONLY the translated tagged text (with the same tags and ordering); do not add explanations

{context_section}
Tagged text to translate:
{tagged_text}

Translated tagged text:"""

    def _call_llm_api(self, prompt: str) -> Optional[str]:
        """调用 LLM API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator specialized in technical documentation and markdown content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"LLM API call failed: {e}")
            return None

    def _translate_with_prompt(self, prompt: str, retries: int = 0) -> str:
        """
        统一的重试封装：用指定 prompt 调用 LLM。
        """
        if retries >= MAX_RETRY:
            raise LLMTranslateError(f"LLM Translate failed after {MAX_RETRY} retries.")
        try:
            result = self._call_llm_api(prompt)
            if result is None:
                retries += 1
                logging.warning(f"LLM Translate failed, retry {retries}/{MAX_RETRY}")
                time.sleep(0.5 * pow(2, retries))
                return self._translate_with_prompt(prompt, retries)
            return result.strip()
        except Exception as e:
            retries += 1
            logging.error(f"LLM Translate error: {e}, retry {retries}/{MAX_RETRY}")
            time.sleep(0.5 * pow(2, retries))
            return self._translate_with_prompt(prompt, retries)

    def translate(self, source_text: str, src_lang: str, target_lang: str, retries: int = 0) -> str:
        """
        翻译文本
        :param source_text: 源文本
        :param src_lang: 源语言
        :param target_lang: 目标语言
        :param retries: 重试次数
        :return: 翻译后的文本
        """
        logging.debug(f"LLM Translating {src_lang} to {target_lang}, length={len(source_text)}, retries={retries}")

        try:
            prompt = self._build_translation_prompt(source_text, src_lang, target_lang)
            return self._translate_with_prompt(prompt, retries)
        except Exception:
            # _translate_with_prompt 内部已处理重试，这里直接抛出
            raise

    def __translate_with_skipped_chars(self, chunk,
                                       src_lang: str, target_lang: str, pbar: Pbar) -> str:
        """
        翻译时忽略在 config.py 中配置的正则表达式，翻译后保证格式不变
        :param chunk: 本次翻译的文本块
        :return: 翻译后的文本
        """
        # chunk 兼容两种结构：
        # 1) (skipped_parts, need_translate_parts, parts_count)
        # 2) (context_before, skipped_parts, need_translate_parts, parts_count, context_after)
        context_before = ""
        context_after = ""
        if isinstance(chunk, tuple) and len(chunk) == 3:
            skipped_parts, need_translate_parts, parts_count = chunk
        elif isinstance(chunk, tuple) and len(chunk) == 5:
            context_before, skipped_parts, need_translate_parts, parts_count, context_after = chunk
        else:
            raise LLMTranslateError(f"Unexpected chunk format: {type(chunk)} len={getattr(chunk, '__len__', lambda: 'n/a')()}")

        # === 关键修正：不再依赖“行数/分段数必须对齐” ===
        # 1) 为每个待翻译片段加编号标记；2) 让模型保留标记；3) 按标记回填。
        values = list(need_translate_parts.values())
        # 用换行分隔仅为可读性；真实边界依赖标记而不是换行
        tagged_text = "\n".join([f"⟦{i}⟧{v}⟦/{i}⟧" for i, v in enumerate(values)])
        prompt = self._build_tagged_parts_prompt(
            tagged_text,
            src_lang,
            target_lang,
            context_before=context_before,
            context_after=context_after,
        )
        result = self._translate_with_prompt(prompt)

        pbar.update(len(tagged_text))

        # 解析回填
        matches = re.findall(r"⟦(\d+)⟧(.*?)⟦/\1⟧", result, flags=re.DOTALL)
        translated_by_idx = {int(i): txt.strip(" ") for i, txt in matches}

        if len(translated_by_idx) != len(values):
            # 如果模型没有严格按标记输出，降级兜底：逐片段翻译，保证不残留原文
            logging.warning(
                "LLM tagged translation parse mismatch "
                f"(expected={len(values)}, got={len(translated_by_idx)}), fallback to per-part translation."
            )
            translated_by_idx = {}
            for i, v in enumerate(values):
                # 空白直接返回，避免无意义调用
                if not v.strip():
                    translated_by_idx[i] = v
                    continue
                translated_by_idx[i] = self.translate(v, src_lang, target_lang).strip(" ")

        # 更新翻译部分的内容（保持原顺序）
        for i, key in enumerate(list(need_translate_parts.keys())):
            need_translate_parts[key] = translated_by_idx.get(i, values[i])

        if not target_lang.lower().startswith("zh"):
            # 如果不是中文，则将 skipped_parts 中的全角符号变为半角符号
            skipped_parts = {key: SymbolWidthUtil.full_to_half(value) for key, value in skipped_parts.items()}

        total_parts = {**skipped_parts, **need_translate_parts}
        return "".join(total_parts[i] for i in range(parts_count))

    def translate_in_batch(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str:
        """
        分批次翻译
        :param raw_data: 原始数据
        :param src_lang: 源语言
        :param target_lang: 目标语言
        :param pbar: 进度条
        :return: 翻译后的文本
        """
        translated_text = [
            self.__translate_with_skipped_chars(chunk, src_lang, target_lang, pbar) 
            for chunk in copy.deepcopy(raw_data.chunks)
        ]
        lines = ''.join(translated_text).splitlines()

        # 将空行插入回去
        for i in raw_data.empty_line_position:
            lines.insert(i, '')

        return '\n'.join(lines) + '\n'
