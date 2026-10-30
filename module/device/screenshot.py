import time
from collections import deque

import cv2
import numpy as np

from module.base.timer import Timer
from module.device.connection import Connection
from module.exception import ScriptError
from module.logger import logger

WIDTH, HEIGHT = 720, 1280


class Screenshot(Connection):
    def __init__(self, config):
        super().__init__(config)
        self.image = None
        # 最近的截图，出错时存到 log/error 方便排查
        self.screenshot_deque = deque(maxlen=10)
        self._screenshot_interval = Timer(config.Device_ScreenshotInterval)

    def screenshot_adb_raw(self):
        """screencap 原始像素，比 png 少一次设备端压缩"""
        data = self.adb_command(['exec-out', 'screencap'], timeout=15)
        size = WIDTH * HEIGHT * 4
        header = len(data) - size
        if header not in (12, 16):
            raise ScriptError(f'截图数据长度异常: {len(data)}，分辨率必须是 {WIDTH}x{HEIGHT}')
        w, h = np.frombuffer(data[:8], dtype=np.uint32)
        if (w, h) != (WIDTH, HEIGHT):
            raise ScriptError(f'分辨率是 {w}x{h}，脚本只支持 {WIDTH}x{HEIGHT} 竖屏')
        image = np.frombuffer(data[header:], dtype=np.uint8).reshape(HEIGHT, WIDTH, 4)
        return image[:, :, :3].copy()

    def screenshot_adb_png(self):
        data = self.adb_command(['exec-out', 'screencap', '-p'], timeout=15)
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ScriptError('截图解码失败')
        if image.shape[:2] != (HEIGHT, WIDTH):
            raise ScriptError(f'分辨率是 {image.shape[1]}x{image.shape[0]}，脚本只支持 {WIDTH}x{HEIGHT} 竖屏')
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def screenshot(self):
        self._screenshot_interval.wait()
        self._screenshot_interval.reset()
        method = self.config.Device_ScreenshotMethod
        # 战斗画面重的时候模拟器偶尔会卡几十秒，screencap 连续超时（实测 10-30 日常副本卡了 45 秒），多等几次
        for retry in range(5):
            try:
                if method == 'adb_png':
                    image = self.screenshot_adb_png()
                else:
                    image = self.screenshot_adb_raw()
                break
            except ScriptError:
                raise
            except Exception as e:
                logger.warning(f'截图失败，重试: {e}')
                time.sleep(2 + retry * 3)
        else:
            raise ScriptError('连续 5 次截图失败')
        self.image = image
        self.screenshot_deque.append((time.time(), image))
        return image
