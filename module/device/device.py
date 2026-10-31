import time
from collections import deque

from module.base.timer import Timer
from module.device.control import Control
from module.device.screenshot import Screenshot
from module.exception import GameNotRunningError, GameStuckError, GameTooManyClickError
from module.logger import logger
from module.ui.assets import GIFT_POPUP_CLOSE, GIFT_POPUP_FOOTER, GIFT_POPUP_TIMER


class Device(Screenshot, Control):
    """
    设备 = 截图 + 点击，截图时顺手关掉付费礼包弹窗，再加两道保险：
    - 卡死检测：一段时间内只截图、没有点击，抛 GameStuckError
    - 连点检测：最近 15 次点击里同一个按钮占 12 次，抛 GameTooManyClickError
    """
    stuck_timer = Timer(60, count=60).start()
    stuck_timer_long = Timer(300, count=300).start()
    stuck_long_wait = False

    def __init__(self, config):
        super().__init__(config)
        self.click_record = deque(maxlen=15)

    def screenshot(self):
        self.stuck_record_check()
        image = super().screenshot()
        # 付费礼包弹窗任何操作之后都可能弹出，挡住页面，在这里统一关掉，各任务不用管
        for _ in range(3):
            if not self.gift_popup_appear(image):
                break
            logger.info('关闭付费礼包弹窗')
            super().click(GIFT_POPUP_CLOSE)
            time.sleep(1.5)
            image = super().screenshot()
        return image

    @staticmethod
    def gift_popup_appear(image):
        return GIFT_POPUP_TIMER.match(image, offset=(30, 150)) and GIFT_POPUP_FOOTER.match(image, offset=(30, 150))

    # ---------- 卡死检测 ----------
    def stuck_record_clear(self):
        self.stuck_timer.reset()
        self.stuck_timer_long.reset()

    def stuck_record_check(self):
        timer = self.stuck_timer_long if self.stuck_long_wait else self.stuck_timer
        if timer.reached():
            logger.warning(f'等待超过 {timer.limit} 秒没有任何进展')
            if not self.app_is_running():
                raise GameNotRunningError
            raise GameStuckError

    def long_wait(self, enable=True):
        """匹配、战斗等需要长时间等待时打开，把卡死判定放宽到 5 分钟"""
        self.stuck_long_wait = enable
        self.stuck_record_clear()

    # ---------- 连点检测 ----------
    def click_record_check(self):
        names = [str(b) for b in self.click_record]
        for name in set(names):
            if names.count(name) >= 12:
                logger.warning(f'按钮 {name} 被连续点击太多次: {names}')
                self.click_record.clear()
                raise GameTooManyClickError(name)

    def click(self, button):
        self.click_record_check()
        super().click(button)
        self.click_record.append(str(button))
        self.stuck_record_clear()

    def swipe(self, p1, p2, duration=400, name='SWIPE'):
        super().swipe(p1, p2, duration=duration, name=name)
        self.stuck_record_clear()

    def back(self):
        super().back()
        self.click_record.append('BACK')
        self.stuck_record_clear()
