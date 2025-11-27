# app/face/embedding.py
from PIL import Image
import hashlib

def image_to_embedding_bytes(image_bytes: bytes, dim: int = 128):
    """
    Stub embedding: buat hash SHA256 dari bytes, lalu expand menjadi list of floats.
    Ini hanya placeholder — ganti dengan model nyata (facenet, dlib, etc.)
    """
    h = hashlib.sha256(image_bytes).digest()
    # expand / repeat to reach desired dim
    vals = []
    i = 0
    while len(vals) < dim:
        b = h[i % len(h)]
        vals.append((b / 255.0))  # normalisasi 0..1
        i += 1
    return vals

def embedding_from_upload(upload_file) -> list:
    """
    upload_file: fastapi UploadFile
    Return: list[float] length dim
    """
    data = upload_file.file.read()
    upload_file.file.seek(0)
    return image_to_embedding_bytes(data)
