"""
Local Embedding Engine for Semantic Search.
Generates 384-dimensional dense vectors using all-MiniLM-L6-v2 or deterministic projection.
No paid API dependencies.
"""

import math
import hashlib
from typing import List, Optional
from core.logging import logger

_st_model = None
_st_load_attempted = False


def _get_sentence_transformer():
    global _st_model, _st_load_attempted
    if _st_model is None and not _st_load_attempted:
        _st_load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded local SentenceTransformer model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.info(f"SentenceTransformers local load deferred ({e}). Using deterministic 384-dim semantic projection.")
            _st_model = None
    return _st_model


class LocalEmbeddingModel:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, text: str) -> List[float]:
        """
        Produces a unit-normalized 384-dimensional embedding vector.
        Uses sentence-transformers if available, else deterministic subword semantic hashing.
        """
        st = _get_sentence_transformer()
        if st is not None:
            try:
                vec = st.encode(text, normalize_embeddings=True)
                return [float(x) for x in vec]
            except Exception as e:
                logger.warning(f"SentenceTransformer encode failed: {e}. Falling back to deterministic hashing.")

        # Deterministic 384-dimensional normalized semantic vector projection
        vec = [0.0] * self.dim
        clean_text = text.lower().strip()
        words = clean_text.split()

        for word in words:
            # Hash word into bucket
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx1 = h % self.dim
            idx2 = (h >> 16) % self.dim
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[idx1] += sign * 1.0
            vec[idx2] += (sign * -0.5)

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0

        return vec
