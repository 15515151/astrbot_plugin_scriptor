# tools/integration/embedding.py
"""Dual-Track Embedding Engine - 第三方Embedding服务集成"""

import logging

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

logger = logging.getLogger("astrbot")


class DualTrackEmbeddingFunction(EmbeddingFunction):
    """
    双轨制Embedding引擎
    支持通过OpenAI兼容API (如Ollama, Xinference) 或本地SentenceTransformers运行
    """

    def __init__(self, provider: str = "local", api_base: str = "", api_key: str = "", model: str = ""):
        self.provider = provider.lower()
        self.api_base = api_base
        self.api_key = api_key
        self.model = model

        self._local_model = None
        self._api_client = None

        if self.provider == "api":
            self._init_api_client()
        else:
            self._init_local_model()

    def _init_api_client(self):
        """初始化OpenAI兼容的API客户端"""
        try:
            from openai import OpenAI

            self._api_client = OpenAI(base_url=self.api_base, api_key=self.api_key or "dummy_key")
            logger.info(f"[Embedding] API客户端已初始化: {self.api_base}, 模型: {self.model}")
        except ImportError:
            logger.error("[Embedding] 缺少openai库，降级为本地模型")
            self.provider = "local"
            self._init_local_model()
        except Exception as e:
            logger.error(f"[Embedding] API客户端初始化失败: {e}，降级为本地模型")
            self.provider = "local"
            self._init_local_model()

    def _init_local_model(self):
        """初始化本地SentenceTransformers模型 (支持从魔搭社区下载)"""
        try:
            import os

            from chromadb.utils import embedding_functions

            # 设置环境变量，强制 sentence-transformers 从魔搭社区 (ModelScope) 下载模型
            os.environ["USE_MODELSCOPE"] = "True"

            # 策略：1. 用户配置的模型 -> 2. 极轻量中文模型 (bge-small) -> 3. 抛出异常触发降级
            model_candidates = [self.model, "AI-ModelScope/bge-small-zh-v1.5"]  # 极轻量中文模型，适合 NAS

            last_error = None
            for model_name in model_candidates:
                if not model_name:
                    continue
                try:
                    logger.info(f"[Embedding] 尝试从魔搭社区初始化本地模型: {model_name}")

                    # 尝试使用 ModelScope 的 snapshot_download 来确保模型被正确下载
                    try:
                        from modelscope import snapshot_download

                        model_dir = snapshot_download(model_name)
                        logger.info(f"[Embedding] 魔搭模型下载/缓存成功: {model_dir}")
                        # 使用下载后的本地路径初始化
                        self._local_model = embedding_functions.SentenceTransformerEmbeddingFunction(
                            model_name=model_dir
                        )
                    except ImportError:
                        logger.warning("[Embedding] 未安装 modelscope 库，尝试直接通过 sentence-transformers 加载")
                        self._local_model = embedding_functions.SentenceTransformerEmbeddingFunction(
                            model_name=model_name
                        )

                    logger.info(f"[Embedding] 本地模型已就绪: {model_name}")
                    return
                except Exception as e:
                    last_error = e
                    logger.warning(f"[Embedding] 模型 {model_name} 加载失败: {e}")

            # 如果所有模型都加载失败，抛出异常，由 search_engine.py 捕获并降级为纯文本搜索
            if last_error:
                raise RuntimeError(f"所有本地 Embedding 模型加载失败: {last_error}")

        except ImportError:
            logger.error("[Embedding] 缺少必要的库 (sentence-transformers)")
            raise

    def __call__(self, input: Documents) -> Embeddings:
        """计算文本的Embedding向量"""
        if not input:
            return []

        if self.provider == "api" and self._api_client:
            for attempt in range(3):
                try:
                    response = self._api_client.embeddings.create(input=input, model=self.model)
                    return [data.embedding for data in response.data]
                except Exception as e:
                    logger.warning(f"[Embedding] API调用失败 (尝试 {attempt + 1}/3): {e}")
                    if attempt == 2:
                        logger.warning("[Embedding] API连续失败，降级为本地模型")
                        break
                    import time

                    time.sleep(0.5 * (attempt + 1))

        if not self._local_model:
            try:
                self._init_local_model()
            except Exception as local_e:
                logger.error(f"[Embedding] 本地模型初始化失败: {local_e}")
                raise RuntimeError(f"无可用的Embedding引擎: {local_e}")

        if self._local_model:
            try:
                return self._local_model(input)
            except Exception as e:
                logger.error(f"[Embedding] 本地模型计算失败: {e}")
                raise RuntimeError(f"Embedding计算失败: {e}")

        raise RuntimeError("没有可用的Embedding引擎")
