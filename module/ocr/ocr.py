import cv2

from module.base.utils import crop
from module.logger import logger

_engine = None


def _get_engine():
    """RapidOCR（onnxruntime，模型在安装包里，离线运行）。第一次用时才加载，约 1 秒"""
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        logger.info('加载 OCR 模型')
        _engine = RapidOCR()
    return _engine


def ocr_lines(image, area):
    """
    识别 area 里的文字行。

    Args:
        image (np.ndarray): RGB 截图
        area (tuple): (x1, y1, x2, y2)

    Returns:
        list: [(x, y, text, score)]，x、y 是文字框中心在整张截图里的坐标，从上到下排
    """
    result, _ = _get_engine()(cv2.cvtColor(crop(image, area), cv2.COLOR_RGB2BGR))
    lines = []
    for box, text, score in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        lines.append((int(sum(xs) / 4) + area[0], int(sum(ys) / 4) + area[1], text, float(score)))
    return sorted(lines, key=lambda l: l[1])


def ocr_single_line(image, area, scale=2):
    """
    只做文字识别（不检测文字框）认一行字。放大后小数点更稳：整列识别偶尔把 3.44 认成 344（10-30 实测）

    Returns:
        str: 认不出返回空字符串
    """
    image = cv2.cvtColor(crop(image, area), cv2.COLOR_RGB2BGR)
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    result, _ = _get_engine()(image, use_det=False, use_cls=False, use_rec=True)
    return result[0][0] if result else ''
