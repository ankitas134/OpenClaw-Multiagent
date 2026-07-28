from typing import List
import numpy as np

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_embedding(text: str) -> List[float]:
    try:
        model = get_embedding_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        print(f"[RAG] Embedding generation error: {e}")
        return [0.0] * 384

def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) == 0 or len(b) == 0:
        return 0.0
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))
