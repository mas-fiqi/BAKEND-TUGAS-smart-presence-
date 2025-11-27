# app/face/recognition.py (STUB MODE)
from typing import List
import hashlib

MODE = "stub"

def load_models(mode: str = "stub"):
    global MODE
    MODE = "stub"
    return {"mode": MODE}

def _stub_image_to_embedding(image_bytes: bytes, dim: int = 128) -> List[float]:
    h = hashlib.sha256(image_bytes).digest()
    vals = []
    i = 0
    while len(vals) < dim:
        b = h[i % len(h)]
        vals.append(b / 255.0)
        i += 1
    return vals

def get_embedding_from_bytes(image_bytes: bytes):
    return _stub_image_to_embedding(image_bytes, 128)

def compare_embeddings(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i]*b[i] for i in range(n))
    mag_a = sum(a[i]*a[i] for i in range(n))**0.5
    mag_b = sum(b[i]*b[i] for i in range(n))**0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
