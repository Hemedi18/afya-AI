from __future__ import annotations

import base64 as _b64
from io import BytesIO
from math import sqrt
from typing import Iterable, List, Tuple

from PIL import Image, ImageOps


EMBEDDING_SIZE = 32 * 32


def _normalize_vector(values: Iterable[float]) -> List[float]:
    vals = [float(v) for v in values]
    norm = sqrt(sum(v * v for v in vals)) or 1.0
    return [v / norm for v in vals]


def build_face_embedding(file_obj) -> List[float]:
    raw = file_obj.read()
    image = Image.open(BytesIO(raw))
    image = ImageOps.exif_transpose(image)
    image = image.convert('L').resize((32, 32), Image.Resampling.LANCZOS)
    image = ImageOps.equalize(image)
    pixels = list(image.getdata())
    return _normalize_vector([p / 255.0 for p in pixels])


def cosine_similarity(v1: Iterable[float], v2: Iterable[float]) -> float:
    a = list(v1)
    b = list(v2)
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def find_best_match(probe_embedding: Iterable[float], candidate_embeddings: Iterable[Tuple[int, Iterable[float]]]) -> Tuple[int | None, float]:
    best_user_id = None
    best_score = -1.0
    for user_id, emb in candidate_embeddings:
        score = cosine_similarity(probe_embedding, emb)
        if score > best_score:
            best_score = score
            best_user_id = user_id
    return best_user_id, max(0.0, best_score)


# ─── Live-scan helpers ────────────────────────────────────────────────────────

def build_face_embedding_from_b64(b64_data: str) -> List[float]:
    """Build embedding from a base64 data-URL string (canvas.toDataURL output)."""
    data = b64_data
    if ',' in data:
        data = data.split(',', 1)[1]
    raw = _b64.b64decode(data)
    return build_face_embedding(BytesIO(raw))


def check_liveness_multiframe(embeddings: List[List[float]]) -> Tuple[bool, str]:
    """
    Multi-frame liveness check via inter-frame cosine-distance analysis.
    A static photo / on-screen image → near-zero distance → fail.
    A live person → micro-movements → small but non-zero distance → pass.
    """
    if len(embeddings) < 2:
        return False, 'not_enough_frames'

    diffs: List[float] = []
    for i in range(len(embeddings) - 1):
        sim = cosine_similarity(embeddings[i], embeddings[i + 1])
        diffs.append(1.0 - sim)

    avg_diff = sum(diffs) / len(diffs)

    # Too static → printed/screen photo
    # Lower threshold to reduce false positives for real live users who stay very still.
    if avg_diff < 0.00025:
        return False, 'static_image'

    # Way too unstable → camera shaking / wrong subject
    if avg_diff > 0.30:
        return False, 'unstable'

    return True, 'ok'


def check_frame_quality(b64_data: str) -> Tuple[bool, str]:
    """Light quality check: brightness, variance, minimum size."""
    try:
        data = b64_data
        if ',' in data:
            data = data.split(',', 1)[1]
        raw = _b64.b64decode(data)
        image = Image.open(BytesIO(raw))
        image = ImageOps.exif_transpose(image)
        w, h = image.size
        if w < 64 or h < 64:
            return False, 'image_too_small'
        gray = image.convert('L')
        pixels = list(gray.getdata())
        mean_v = sum(pixels) / len(pixels)
        if mean_v < 18:
            return False, 'too_dark'
        if mean_v > 238:
            return False, 'too_bright'
        variance = sum((p - mean_v) ** 2 for p in pixels) / len(pixels)
        if variance < 80:
            return False, 'poor_quality'
        return True, 'ok'
    except Exception:
        return False, 'bad_image'
