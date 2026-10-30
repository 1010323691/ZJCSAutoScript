import os
import random

import cv2
import numpy as np


def load_image(file):
    """读图片为 RGB 数组。用 imdecode 而不是 imread，路径里有中文也能读"""
    data = np.fromfile(file, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f'无法读取图片: {file}')
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def save_image(image, file):
    os.makedirs(os.path.dirname(os.path.abspath(file)), exist_ok=True)
    ext = os.path.splitext(file)[1] or '.png'
    ok, buf = cv2.imencode(ext, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError(f'无法编码图片: {file}')
    buf.tofile(file)


def crop(image, area):
    """
    Args:
        image (np.ndarray): RGB 图片
        area (tuple): (x1, y1, x2, y2)，超出图片的部分会被裁掉
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = map(int, area)
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, w), min(y2, h)
    return image[y1:y2, x1:x2].copy()


def get_color(image, area):
    """区域平均颜色 (r, g, b)"""
    return tuple(np.mean(crop(image, area).reshape(-1, 3), axis=0))


def color_similar(color1, color2, threshold=10):
    """两个颜色每个通道的差都不超过 threshold"""
    diff = np.abs(np.array(color1, dtype=float) - np.array(color2, dtype=float))
    return bool(np.max(diff) <= threshold)


def area_offset(area, offset):
    return tuple(np.array(area) + np.append(offset, offset))


def area_pad(area, pad=10):
    """正数往里收，负数往外扩"""
    x1, y1, x2, y2 = area
    return x1 + pad, y1 + pad, x2 - pad, y2 - pad


def random_rectangle_point(area, n=3):
    """区域内取一个随机点，多次均匀采样取平均，让点更靠近中心"""
    x1, y1, x2, y2 = area
    x = sum(random.uniform(x1, x2) for _ in range(n)) / n
    y = sum(random.uniform(y1, y2) for _ in range(n)) / n
    return int(round(x)), int(round(y))


def point2str(x, y, length=4):
    return '(%s, %s)' % (str(int(x)).rjust(length), str(int(y)).rjust(length))
