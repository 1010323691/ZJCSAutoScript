import time

from module.base.utils import point2str, random_rectangle_point
from module.device.connection import Connection
from module.logger import logger


class Control(Connection):
    def click(self, button):
        x, y = random_rectangle_point(button.button)
        logger.info(f'Click {point2str(x, y)} @ {button}')
        self.adb_shell(f'input tap {x} {y}')

    def swipe(self, p1, p2, duration=400, name='SWIPE'):
        logger.info(f'Swipe {point2str(*p1)} -> {point2str(*p2)} @ {name}')
        self.adb_shell(f'input swipe {p1[0]} {p1[1]} {p2[0]} {p2[1]} {int(duration)}')
        time.sleep(duration / 1000)

    def drag_path(self, points, name='DRAG'):
        """
        按住 points[0]，依次拖过各点，在最后一点松开（菲涅克的谜题·元素链接画路径用）。
        相邻两点之间补一个中点，转弯不会被当成斜着划过去。所有事件拼成一条 shell 命令发，中间不断手。
        input motionevent 要 Android 10 以上（11-05 BlueStacks Air 的 Android 13 实测可用）。
        """
        points = [(int(x), int(y)) for x, y in points]
        logger.info(f'Drag {" -> ".join(point2str(x, y, length=0) for x, y in points)} @ {name}')
        cmds = [f'input motionevent DOWN {points[0][0]} {points[0][1]}']
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            cmds.append(f'input motionevent MOVE {(x1 + x2) // 2} {(y1 + y2) // 2}')
            cmds.append(f'input motionevent MOVE {x2} {y2}')
        cmds.append(f'input motionevent UP {points[-1][0]} {points[-1][1]}')
        out = self.adb_shell('; '.join(cmds), timeout=30)
        if 'Unknown' in out or 'Error' in out or 'usage' in out.lower():
            # Android 9 及以下没有 input motionevent，命令不会拖，只会打印用法或报错
            logger.error(f'设备不支持 input motionevent（要 Android 10 以上），拖不了路径: {out.strip()[:200]}')

    def back(self):
        logger.info('Key BACK')
        self.adb_shell('input keyevent 4')
