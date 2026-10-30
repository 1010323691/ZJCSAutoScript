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

    def back(self):
        logger.info('Key BACK')
        self.adb_shell('input keyevent 4')
