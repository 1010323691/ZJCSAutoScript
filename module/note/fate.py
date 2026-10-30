import time

from module.logger import logger
from module.note.assets import *
from module.ui.page import page_map_explore
from module.ui.ui import UI


class FateFruit(UI):
    """笔记 → 地图探索 → 命运果实卡片左下的果实礼包：显示「可领取」就点一下（每天一个，点了直接领，没有弹窗）"""

    def run(self):
        logger.hr('Fate fruit', level=2)
        self.ui_ensure(page_map_explore)
        time.sleep(0.5)
        self.device.screenshot()
        if not self.appear(FATE_CLAIMABLE, offset=(10, 10)):
            logger.info('命运果实礼包还没到时间（或今天已领）')
            return None
        logger.info('领取命运果实礼包')
        self.device.click(FATE_GIFT)
        time.sleep(1.5)
        self.device.screenshot()
        if self.appear(FATE_CLAIMABLE, offset=(10, 10)):
            logger.warning('点了果实礼包还显示「可领取」')
            return False
        return True
