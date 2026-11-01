import time

from module.activity.assets import *
from module.base.timer import Timer
from module.logger import logger
from module.ui.assets import BATTLE_RESULT_CLOSE, BATTLE_ROUND
from module.ui.page import page_holy_beast, page_twin_shadow
from module.ui.ui import UI

# 进度条上三个宝箱红点所在的范围（不含底部页签上的红点）
REWARD_REGION = (40, 860, 700, 930)


class MatchActivity(UI):
    """圣兽试炼、双影幻境：匹配 → 等匹配成功 → 接受 → 全自动战斗 → 关结算页"""

    def in_match_or_battle(self):
        """正在匹配确认、战斗中或结算页（例如上次中断后接手）"""
        return self.appear(BATTLE_ROUND, offset=(90, 10)) \
            or self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20)) \
            or self.appear(MATCH_ACCEPT, offset=(20, 20), similarity=0.75)

    def match_battle(self, page, timeout=900, result_check=None):
        """
        Args:
            result_check (Button): 战斗结束后有自己结算页的玩法（日常副本），出现就返回，结算页由调用方处理
        """
        self.device.screenshot()
        if not self.in_match_or_battle():
            self.ui_ensure(page, skip_first_screenshot=True)
        self.device.long_wait(True)
        timer = Timer(timeout).start()
        match_count = 0
        battle_finished = False
        try:
            while 1:
                # 一场 10 回合的战斗可能超过 5 分钟，这里由本循环的总超时管，不用通用的卡死判定
                self.device.stuck_record_clear()
                self.device.screenshot()
                if timer.reached():
                    logger.warning(f'{timeout} 秒内没有打完')
                    return False
                if result_check is not None and self.appear(result_check, offset=(20, 20)):
                    logger.info('战斗结束，到达结算页')
                    return True
                # 黄色按钮上有扫光动画，相似度会在 0.83~1.00 浮动，其他画面不超过 0.33，阈值用 0.75
                if self.appear(MATCH_ACCEPT, offset=(20, 20), interval=2, similarity=0.75):
                    logger.info('匹配成功，接受')
                    self.device.click(MATCH_ACCEPT)
                    continue
                if self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20), interval=2):
                    logger.info('战斗结束，关闭结算页')
                    self.device.click(BATTLE_RESULT_CLOSE)
                    battle_finished = True
                    continue
                if self.ui_page_appear(page):
                    if battle_finished:
                        logger.info('已回到活动页面')
                        return True
                    if self.appear(MATCH_CANCEL, offset=(20, 10)):
                        # 匹配中，等着
                        pass
                    elif self.appear(MATCH_START, offset=(20, 10), interval=5, similarity=0.75):
                        if match_count >= 3:
                            logger.warning('匹配了 3 次都没有进入战斗，停止')
                            return False
                        match_count += 1
                        logger.info(f'开始匹配（第 {match_count} 次）')
                        self.device.click(MATCH_START)
                        continue
                time.sleep(0.5)
        finally:
            self.device.long_wait(False)

    def claim_reward(self, page):
        """打完后领进度奖励：有红色「!」的宝箱点一下就全部领取，没有红点就跳过"""
        self.ui_ensure(page)
        sim = REWARD_BADGE.match_region(self.device.image, REWARD_REGION, similarity=0.8)
        if sim <= 0.8:
            logger.info('没有可领取的进度奖励')
            return False
        logger.info(f'领取进度奖励（相似度 {sim:.2f}）')
        self.device.click(REWARD_BADGE)
        return self.wait_reward_popup(page)


class HolyBeastTrial(MatchActivity):
    def run(self):
        logger.hr('Holy beast trial', level=2)
        result = self.match_battle(page_holy_beast)
        self.claim_reward(page_holy_beast)
        return result


class TwinShadow(MatchActivity):
    def run(self):
        """
        不打无尽模式：有「无尽模式」这一行时，要认出圆圈是未选中才匹配，认不出就不匹配。
        有的期数（11-01「欢乐时光」）整行不显示，没有无尽模式可选，照常匹配。
        """
        logger.hr('Twin shadow', level=2)
        self.device.screenshot()
        if not self.in_match_or_battle():
            self.ui_ensure(page_twin_shadow, skip_first_screenshot=True)
            # 页面刚切过来，等一下下面的选项行
            time.sleep(1)
            self.device.screenshot()
            if not self.appear(ENDLESS_LABEL, offset=(10, 10), similarity=0.85):
                logger.info('这一期没有「无尽模式」选项，直接匹配')
            elif not self.appear(ENDLESS_OFF, offset=(5, 5), similarity=0.9):
                logger.warning('「无尽模式」不是未选中状态，不匹配')
                return False
        result = self.match_battle(page_twin_shadow)
        self.claim_reward(page_twin_shadow)
        return result
