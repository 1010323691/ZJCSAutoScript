import time

from module.base.timer import Timer
from module.logger import logger
from module.note.assets import *
from module.ui.assets import BATTLE_RESULT_CLOSE
from module.ui.page import page_arena
from module.ui.ui import UI

# 能认出的购买数量
QTY_BUTTONS = {1: ARENA_QTY_1, 3: ARENA_QTY_3}


class Arena(UI):
    def cancel_buy(self):
        """购买框没关掉就去点挑战，挑战会被挡住；框还在就再点取消"""
        self.click_until(ARENA_BUY_CANCEL, self.gone(ARENA_BUY_DIALOG, offset=(10, 10)), skip_first_screenshot=True)

    def buy_tickets(self, count):
        """买 count 张挑战券。核对数量显示正好是 count 才点购买"""
        if count <= 0:
            return True
        if count not in QTY_BUTTONS:
            logger.warning(f'还没有购买数量 {count} 的识别素材，不买票（目前支持 {sorted(QTY_BUTTONS)}）')
            return False
        self.device.click(ARENA_TICKET_PLUS)
        if not self.wait_until_appear(ARENA_BUY_DIALOG, offset=(10, 10), timeout=6):
            return False
        time.sleep(0.5)
        self.device.screenshot()
        current = [n for n, button in QTY_BUTTONS.items() if self.appear(button, offset=(3, 3), similarity=0.9)]
        if not current:
            logger.warning('认不出当前购买数量，取消')
            self.cancel_buy()
            return False
        for _ in range(count - current[0]):
            self.device.click(ARENA_BUY_PLUS)
            time.sleep(0.4)
        time.sleep(0.4)
        self.device.screenshot()
        if not self.appear(QTY_BUTTONS[count], offset=(3, 3), similarity=0.9):
            logger.warning(f'购买数量不是 {count}，取消')
            self.cancel_buy()
            return False
        logger.info(f'购买 {count} 张挑战券')
        self.device.click(ARENA_BUY_CONFIRM)
        self.wait_reward_popup(page_arena, timeout=5)
        return self.wait_until_appear(PAGE_ARENA, offset=(10, 10), timeout=10)

    def challenge_last(self):
        """挑战选择对手里的最后一个：确认框点挑战 → 扫荡直接出结算页 → 点空白关闭"""
        self.device.click(ARENA_LAST_CHALLENGE)
        if not self.wait_until_appear(ARENA_CHALLENGE_DIALOG, offset=(10, 10), timeout=6):
            return False
        # 确认框有弹出动画，太早点会不生效；只在确认框还在时才重点，避免点到结算页的空白处把它关掉
        time.sleep(0.6)
        self.device.click(ARENA_CHALLENGE_CONFIRM)
        timer = Timer(3).start()
        timeout = Timer(30).start()
        while 1:
            self.device.screenshot()
            if self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20)):
                break
            if timeout.reached():
                logger.warning('挑战后没有等到结算页（挑战券可能用完了）')
                return False
            if timer.reached() and self.appear(ARENA_CHALLENGE_DIALOG, offset=(10, 10)):
                self.device.click(ARENA_CHALLENGE_CONFIRM)
                timer.reset()
        self.ui_click(BATTLE_RESULT_CLOSE, check_button=PAGE_ARENA, offset=(10, 10), timeout=10,
                      skip_first_screenshot=True)
        return True

    def run(self):
        logger.hr('Arena', level=2)
        self.ui_ensure(page_arena)
        self.buy_tickets(self.config.Arena_BuyTickets)
        for count in range(1, self.config.Arena_Challenges + 1):
            logger.info(f'竞技场挑战第 {count} 次')
            if not self.challenge_last():
                break
