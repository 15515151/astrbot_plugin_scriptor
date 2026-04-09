# tools/common/bm25.py
"""BM25算法实现模块 - 轻量级纯Python BM25"""

import math
from collections import Counter
from typing import List

from .text_utils import tokenize_for_bm25


class SimpleBM25:
    """轻量级纯Python BM25实现"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: List[Counter] = []
        self.idf: dict = {}
        self.doc_len: List[int] = []
        self.avgdl: float = 0.0
        self.corpus_size: int = 0

    def fit(self, corpus: List[List[str]]):
        """
        拟合语料库
        corpus: 分词后的文档列表，例如 [['我', '爱', '北京'], ['北京', '天安门']]
        """
        self.corpus_size = len(corpus)
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0

        df = {}
        for doc in corpus:
            self.doc_freqs.append(Counter(doc))
            for word in set(doc):
                df[word] = df.get(word, 0) + 1

        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: List[str]) -> List[float]:
        """计算查询与所有文档的BM25分数"""
        scores = [0.0] * self.corpus_size
        for i in range(self.corpus_size):
            doc_len = self.doc_len[i]
            doc_freqs = self.doc_freqs[i]
            score = 0.0
            for word in query:
                if word not in doc_freqs:
                    continue
                freq = doc_freqs[word]
                numerator = self.idf.get(word, 0) * freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += numerator / denominator
            scores[i] = score
        return scores

    def get_top_k(self, query: str, documents: List[str], k: int = 5) -> List[tuple[int, float]]:
        """
        获取top-k相关文档

        Args:
            query: 查询文本
            documents: 文档列表
            k: 返回数量

        Returns:
            [(doc_index, score), ...] 按score降序
        """
        query_tokens = tokenize_for_bm25(query)
        corpus = [tokenize_for_bm25(doc) for doc in documents]
        self.fit(corpus)
        scores = self.get_scores(query_tokens)

        doc_scores = [(i, score) for i, score in enumerate(scores) if score > 0]
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        return doc_scores[:k]
