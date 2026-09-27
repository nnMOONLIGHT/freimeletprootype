"""Извлечение признаков из изображения без сторонних ML-библиотек."""

import numpy as np
from PIL import Image


def _resize(img, size=128):
    img = img.convert("RGB")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _color_histogram(arr, bins=8):
    hist = []
    for ch in range(3):
        h, _ = np.histogram(arr[:, :, ch], bins=bins, range=(0, 256))
        hist.extend(h / h.sum())
    return np.array(hist, dtype=np.float32)


def _hsv_stats(arr):
    r, g, b = arr[:, :, 0] / 255, arr[:, :, 1] / 255, arr[:, :, 2] / 255
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    diff = mx - mn

    s = np.where(mx == 0, 0, diff / mx)
    v = mx
    return float(s.mean()), float(v.mean()), float(s.std())


def _edge_density(gray):
    gx = np.zeros_like(gray, dtype=float)
    gy = np.zeros_like(gray, dtype=float)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    mag = np.sqrt(gx ** 2 + gy ** 2)
    return float(mag.mean() / 255), float(mag.std() / 255)


def _dominant_colors(arr, k=5):
    flat = arr.reshape(-1, 3)
    step = max(1, len(flat) // 2000)
    sample = flat[::step].astype(float)
    means = []
    for i in range(k):
        if len(sample) == 0:
            break
        center = sample[np.random.randint(len(sample))]
        dist = np.linalg.norm(sample - center, axis=1)
        cluster = sample[dist < 60]
        if len(cluster):
            means.extend(cluster.mean(axis=0) / 255)
        else:
            means.extend(center / 255)
    while len(means) < k * 3:
        means.append(0.0)
    return np.array(means[: k * 3], dtype=np.float32)


def _texture_variance(gray):
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=float)
    h, w = gray.shape
    out = []
    for y in range(1, h - 1, 4):
        for x in range(1, w - 1, 4):
            patch = gray[y - 1 : y + 2, x - 1 : x + 2].astype(float)
            out.append(abs((patch * kernel).sum()))
    if not out:
        return 0.0, 0.0
    arr = np.array(out)
    return float(arr.mean() / 1000), float(arr.std() / 1000)


def extract_features(image_path):
    img = _resize(Image.open(image_path))
    arr = np.array(img)
    gray = np.array(img.convert("L"))

    sat, val, sat_std = _hsv_stats(arr)
    edge_mean, edge_std = _edge_density(gray)
    tex_mean, tex_std = _texture_variance(gray)
    hist = _color_histogram(arr)
    dom = _dominant_colors(arr)

    warm = float(arr[:, :, 0].mean() - arr[:, :, 2].mean()) / 255
    contrast = float(gray.std()) / 128

    extra = np.array(
        [sat, val, sat_std, edge_mean, edge_std, tex_mean, tex_std, warm, contrast],
        dtype=np.float32,
    )
    return np.concatenate([hist, dom, extra])
