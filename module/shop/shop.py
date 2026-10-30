import time

import cv2

from module.base.button import ClickArea
from module.base.timer import Timer
from module.base.utils import crop
from module.exception import GamePageUnknownError
from module.home.home import HomeScene
from module.logger import logger
from module.shop.assets import *
from module.ui.page import page_home, page_shop

# 折扣滑块的 8 档：3 折在 x=190，往右每档 48.6 像素，最右是「全部」
DISCOUNT_LEVELS = [3, 4, 5, 6, 7, 8, 9, '全部']
KNOB_X0, KNOB_STEP = 190, 48.6
KNOB_REGION = (160, 560, 560, 615)
MERCHANT_REGION = (0, 600, 640, 960)


class ShopUI(HomeScene):
    def wait_invite_gone(self, timeout=30):
        """「挑战赛组队邀请」会挡住推车招牌（10-30 实测）。是别的玩家发来的，不点拒绝也不点查看，等它自己消失"""
        if not self.appear(TEAM_INVITE, offset=(20, 20)):
            return
        logger.info('有组队邀请挡着，等它消失')
        timer = Timer(timeout).start()
        while not timer.reached():
            time.sleep(2)
            self.device.screenshot()
            if not self.appear(TEAM_INVITE, offset=(20, 20)):
                return
        logger.warning(f'组队邀请 {timeout} 秒还没消失')

    def enter_shop(self):
        """家园场景里找到商人推车，点车身进商店。点一次没进商店就先退回来，绝不连点"""
        if self.ui_get_current_page() == page_shop:
            return
        self.ui_goto(page_home, skip_first_screenshot=True)
        for _ in self.scene_steps(6):
            self.wait_invite_gone()
            # 场景有昼夜循环，两套模板都试
            for board in (MERCHANT_BOARD, MERCHANT_BOARD_DAY):
                sim = board.match_region(self.device.image, MERCHANT_REGION, similarity=0.8)
                if sim > 0.8:
                    break
            else:
                continue
            logger.info(f'找到商人推车（{board}，相似度 {sim:.2f}）')
            self.device.click(board)
            if self.wait_until_appear(PAGE_SHOP, offset=(10, 10), timeout=6):
                return
            self.leave_unexpected_page()
        logger.warning('家园场景里没找到商人推车')
        raise GamePageUnknownError


class GeneralShop(ShopUI):
    def set_discount(self, target):
        """把「一键购买限购道具」滑块调到 target 档（3~9 或 全部）并确认"""
        if target not in DISCOUNT_LEVELS:
            logger.warning(f'折扣配置 {target} 不在 {DISCOUNT_LEVELS} 里，不改滑块')
            return False
        self.device.click(SHOP_GEAR)
        if not self.wait_until_appear(DISCOUNT_DIALOG, offset=(10, 10), timeout=6):
            return False
        target_index = DISCOUNT_LEVELS.index(target)
        for _ in range(12):
            time.sleep(0.4)
            self.device.screenshot()
            if DISCOUNT_KNOB.match_region(self.device.image, KNOB_REGION, similarity=0.8) <= 0.8:
                logger.warning('没认出折扣滑块')
                self.device.click(DIALOG_CANCEL)
                return False
            x = (DISCOUNT_KNOB.button[0] + DISCOUNT_KNOB.button[2]) / 2
            index = min(max(int(round((x - KNOB_X0) / KNOB_STEP)), 0), len(DISCOUNT_LEVELS) - 1)
            logger.attr('Discount', DISCOUNT_LEVELS[index])
            if index == target_index:
                self.ui_click(DIALOG_CONFIRM, check_button=PAGE_SHOP, offset=(10, 10), timeout=10,
                              skip_first_screenshot=True)
                return True
            self.device.click(DISCOUNT_PLUS if index < target_index else DISCOUNT_MINUS)
        self.device.click(DIALOG_CANCEL)
        return False

    def onekey_buy(self):
        """一键购买当前所有符合折扣的限购商品（点了直接买，没有确认框）"""
        self.device.screenshot()
        if self.appear(ONEKEY_ZERO, offset=(10, 5)):
            logger.info('没有符合折扣的商品')
            return True
        self.device.click(SHOP_ONEKEY)
        for _ in range(10):
            time.sleep(0.5)
            self.device.screenshot()
            if self.appear(ONEKEY_ZERO, offset=(10, 5)):
                logger.info('一键购买完成')
                return True
            self.ui_additional()
        logger.warning('一键购买后金额没有变成 0，可能罗拉不够，停止')
        return False

    def refresh(self):
        """刷新一次。只在价格是罗拉时刷新；点了次数没变化或弹出对话框就停"""
        self.device.screenshot()
        if not self.appear(REFRESH_COIN, offset=(40, 5)):
            logger.info('刷新价格不是罗拉（或次数已用完），停止刷新')
            return False
        before = crop(self.device.image, REFRESH_COUNT.area)
        self.device.click(SHOP_REFRESH)
        # 游戏有时反应慢，最多等 4 秒看次数有没有变化
        for _ in range(8):
            time.sleep(0.5)
            self.device.screenshot()
            if self.appear(DIALOG_CANCEL, offset=(20, 20)):
                logger.info('刷新弹出了对话框，取消并停止')
                self.device.click(DIALOG_CANCEL)
                return False
            after = crop(self.device.image, REFRESH_COUNT.area)
            if cv2.matchTemplate(after, before, cv2.TM_CCOEFF_NORMED)[0][0] < 0.95:
                time.sleep(0.5)
                return True
        logger.info('刷新次数没有变化，停止刷新')
        return False

    def run(self):
        logger.hr('General shop', level=2)
        self.enter_shop()
        self.device.click(SHOP_TAB_GENERAL)
        time.sleep(1)
        self.set_discount(self.config.GeneralShop_Discount)
        limit = self.config.GeneralShop_RefreshTimes
        limit = 99 if limit < 0 else limit
        refreshed = 0
        while 1:
            if not self.onekey_buy():
                break
            if refreshed >= limit:
                break
            if not self.refresh():
                break
            refreshed += 1
            logger.info(f'已刷新 {refreshed} 次')
        logger.info(f'杂货商店完成，本次刷新 {refreshed} 次')


# 宝库商品格子：3 列，前 3 行不用滑动就能看到（第 1~9 件）
VAULT_COLS = [132, 360, 589]
VAULT_STAMP_Y = [296, 580, 862]
VAULT_PRICE_Y = [407, 689, 973]
# 「限购2次」的商品要点两次，每件最多点这么多次
VAULT_MAX_CLICKS = 3


class Vault(ShopUI):
    """
    买配置里的第几件商品（用户规则 Q4：默认前 5 件；10-30 补充：限购多次的买满到售罄）。
    点价格直接买，没有确认框（10-30 实测：免费、100 钻、50 钻、30 钻都是）。
    """

    def vault_sold(self, index):
        cx, cy = VAULT_COLS[(index - 1) % 3], VAULT_STAMP_Y[(index - 1) // 3]
        image = crop(self.device.image, (cx - 50, cy - 35, cx + 50, cy + 35))
        # 售罄 0.92 以上，没售罄 0.34 以下
        return cv2.matchTemplate(image, VAULT_SOLD.template, cv2.TM_CCOEFF_NORMED).max() > 0.7

    def buy_item(self, index):
        cx, cy = VAULT_COLS[(index - 1) % 3], VAULT_PRICE_Y[(index - 1) // 3]
        price = ClickArea(f'VAULT_ITEM_{index}', (cx - 40, cy - 15, cx + 40, cy + 15))
        for _ in range(VAULT_MAX_CLICKS):
            self.device.screenshot()
            if not self.appear(VAULT_TAB_ON, offset=(10, 10)):
                # 例如钻石不足弹了充值框，不碰，返回并停下
                logger.warning('点商品后离开了宝库页，返回并停止购买')
                self.device.back()
                raise GamePageUnknownError
            if self.vault_sold(index):
                logger.info(f'第 {index} 件已售罄')
                return
            logger.info(f'购买第 {index} 件')
            self.device.click(price)
            time.sleep(1.5)
        logger.warning(f'第 {index} 件点了 {VAULT_MAX_CLICKS} 次还没售罄')

    def run(self):
        logger.hr('Vault', level=2)
        items = [int(x) for x in str(self.config.Vault_Items).replace('，', ',').split(',') if x.strip()]
        self.enter_shop()
        self.device.click(SHOP_TAB_VAULT)
        if not self.wait_until_appear(VAULT_TAB_ON, offset=(10, 10), timeout=6):
            raise GamePageUnknownError
        time.sleep(1)
        for index in items:
            if not 1 <= index <= 9:
                logger.warning(f'只支持第 1~9 件（不用滑动的范围），跳过第 {index} 件')
                continue
            self.buy_item(index)
            self.device.click_record.clear()
