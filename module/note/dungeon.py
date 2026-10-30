import time

from module.activity.activity import MatchActivity
from module.base.timer import Timer
from module.exception import GamePageUnknownError
from module.logger import logger
from module.note.assets import *
from module.ui.assets import BACK_ARROW
from module.ui.page import page_dungeon, page_dungeon_detail, page_home

DUNGEON_CARDS = {'最新': DUNGEON_CARD_2, '磐岩斗阵': DUNGEON_CARD_1, '曙光圣庭': DUNGEON_CARD_2}
# 从高到低试，第一个没有「解锁条件未达成」的就是能打的最高难度
DIFFICULTY_TABS = [('炼狱', DUNGEON_TAB_HELL), ('噩梦', DUNGEON_TAB_NIGHTMARE),
                   ('困难', DUNGEON_TAB_HARD), ('普通', DUNGEON_TAB_NORMAL)]
# 不是 S 评级就不领奖（不扣领奖次数）重新匹配，每次任务最多重打这么多场
RETRY_LIMIT = 3


class DailyDungeon(MatchActivity):
    def in_match_or_battle(self):
        """副本战斗的回合字样和结算页都和其他玩法不一样，单独认"""
        return super().in_match_or_battle() \
            or self.appear(DUNGEON_ROUND, offset=(30, 10)) \
            or self.appear(DUNGEON_RESULT, offset=(20, 20)) \
            or self.appear(DUNGEON_CLAIM_CONFIRM, offset=(10, 10))

    def select_highest_difficulty(self):
        for name, tab in DIFFICULTY_TABS:
            self.device.click(tab)
            time.sleep(1)
            self.device.screenshot()
            if not self.appear(DUNGEON_LOCKED, offset=(20, 10)):
                logger.info(f'能打的最高难度：{name}')
                return name
        return None

    def enter_detail(self):
        """进配置的副本，选能打的最高难度"""
        self.ui_ensure(page_dungeon)
        card = DUNGEON_CARDS.get(self.config.DailyDungeon_Dungeon, DUNGEON_CARD_2)
        if not self.ui_click(card, check_button=PAGE_DUNGEON_DETAIL, offset=(10, 10), timeout=10):
            return False
        if not self.select_highest_difficulty():
            logger.warning('所有难度都没解锁')
            return False
        return True

    def buy_extra(self):
        """
        「每日领奖次数」旁的 + → 滑条加到 2 次 → 总价是 250 晨星（100 + 150）才买。
        每天限购 2 次，今天买过价格就不是 250，取消不买。

        Returns:
            bool: 是否买了
        """
        if not self.ui_click(DUNGEON_BUY_PLUS, check_button=DUNGEON_BUY_DIALOG, offset=(10, 10),
                             retry_wait=3, timeout=10):
            logger.warning('没有打开购买领奖次数的弹窗')
            return False
        # 弹窗有弹出动画
        time.sleep(0.5)
        self.device.click(DUNGEON_BUY_ADD)
        time.sleep(1)
        self.device.screenshot()
        if self.appear(DUNGEON_BUY_COST_250, offset=(10, 5), similarity=0.9):
            logger.info('花 250 晨星购买 2 次领奖次数')
            self.device.click(DUNGEON_BUY_CONFIRM)
            bought = True
        else:
            logger.warning('买 2 次的价格不是 250 晨星（今天可能已经买过），不买')
            self.device.click(DUNGEON_BUY_CANCEL)
            bought = False
        timer = Timer(10).start()
        while 1:
            self.device.screenshot()
            if self.appear(PAGE_DUNGEON_DETAIL, offset=(10, 10)) \
                    and not self.appear(DUNGEON_BUY_DIALOG, offset=(10, 10)):
                return bought
            if timer.reached():
                raise GamePageUnknownError
            if self.ui_additional():
                continue
            time.sleep(0.5)

    def leave_result(self, timeout=15):
        """结算页左下返回。打完一场会回到副本列表页；重新登录后弹出的结算页返回会回到家园"""
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(PAGE_DUNGEON, offset=(10, 10)) or self.appear(PAGE_DUNGEON_DETAIL, offset=(10, 10)) \
                    or self.ui_page_appear(page_home):
                return True
            if timer.reached():
                logger.warning('结算页返回后没有回到副本详情页')
                return False
            if self.appear(DUNGEON_RESULT, offset=(20, 20), interval=3):
                self.device.click(BACK_ARROW)
                continue
            time.sleep(0.5)

    def handle_result(self):
        """
        结算页：S 评级才点「领取奖励」→ 确认消耗 1 次领奖次数；不是 S 就不领直接返回。

        Returns:
            bool: 是否领了（之前领过的也算），None 表示出错
        """
        self.device.screenshot()
        # 上次点了「领取奖励」还没确认就中断了：确认框开着，背景变暗认不出评级，点领取前已经确认过是 S
        confirming = self.appear(DUNGEON_CLAIM_CONFIRM, offset=(10, 10))
        if not confirming and not self.appear(DUNGEON_RATING_S, offset=(20, 20)):
            logger.info('评级不是 S，不领奖，返回重新匹配')
            return False if self.leave_result() else None
        if confirming or self.appear(DUNGEON_CLAIM, offset=(10, 10)):
            logger.info('S 评级，领取奖励')
            timer = Timer(15).start()
            while 1:
                self.device.screenshot()
                if timer.reached():
                    raise GamePageUnknownError
                if self.appear(DUNGEON_CLAIM_CONFIRM, offset=(10, 10), interval=2):
                    # 确认框有弹出动画
                    time.sleep(0.5)
                    self.device.click(DUNGEON_CLAIM_CONFIRM)
                    continue
                if self.appear(DUNGEON_CLAIM, offset=(10, 10), interval=3):
                    self.device.click(DUNGEON_CLAIM)
                    continue
                # 领完按钮变成灰色「已领取」。不能用「黄色按钮不见了」判断：确认框弹出前那一帧黄色按钮也认不出（10-30 实测）
                if self.appear(DUNGEON_CLAIMED, offset=(10, 10)):
                    break
                time.sleep(0.5)
        else:
            logger.info('S 评级，奖励已经领过')
        self.device.click_record.clear()
        return True if self.leave_result() else None

    def fight(self):
        """匹配打一场并处理结算页，返回值同 handle_result"""
        self.device.screenshot()
        if not self.appear(DUNGEON_CLAIM_CONFIRM, offset=(10, 10)) \
                and not self.match_battle(page_dungeon_detail, result_check=DUNGEON_RESULT):
            return None
        return self.handle_result()

    def run(self):
        """
        进指定副本 → 选能打的最高难度 → 买 2 次领奖次数（可选）→ 匹配战斗：
        S 评级才领奖，不是 S 不领、重新匹配（最多重打 3 场），直到「今日领奖次数已耗尽」
        """
        logger.hr('Daily dungeon', level=2)
        retried = 0
        self.device.screenshot()
        if self.in_match_or_battle():
            # 上次中断时还在战斗或结算页（匹配制，中途退出会坑队友），先把这一场处理完
            logger.info('正在战斗或结算中，先处理完这一场')
            result = self.fight()
            if result is None:
                return False
            if not result:
                retried += 1
        if not self.enter_detail():
            return False
        if self.config.DailyDungeon_BuyExtra:
            self.buy_extra()
        for count in range(1, 11):
            self.device.screenshot()
            if not self.appear(PAGE_DUNGEON_DETAIL, offset=(10, 10)) and not self.enter_detail():
                return False
            if self.appear(DUNGEON_EXHAUSTED, offset=(20, 10)):
                logger.info('今日领奖次数已耗尽')
                return True
            logger.info(f'日常副本第 {count} 场')
            result = self.fight()
            if result is None:
                return False
            if not result:
                retried += 1
                if retried > RETRY_LIMIT:
                    logger.warning(f'已经重打 {RETRY_LIMIT} 场都不是 S，停止')
                    return False
        return True
