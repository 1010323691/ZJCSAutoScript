import time

import numpy as np

from module.activity.assets import REWARD_BADGE
from module.base.button import ClickArea
from module.base.timer import Timer
from module.exception import GamePageUnknownError
from module.logger import logger
from module.reward.assets import *
from module.ui.assets import BACK_ARROW
from module.ui.page import page_home
from module.ui.ui import UI

# 列表区域：标题栏以下、底部页签以上
LIST_REGION = (0, 90, 720, 1170)
# 各列表的「领取」按钮大小不一（任务 1.0，馈赠、月卡约 0.8），按多个缩放倍数找
CLAIM_SCALES = (0.8, 0.85, 0.9, 0.95, 1.0, 1.05)
# 左下返回是白色细箭头（不是通用黑底返回按钮）的页面
THIN_BACK_PAGES = [EVENT_CHECK, SEASON_CHECK, MALL_CHECK, MALL_CARD_CHECK]

# 入口和页签上红点「!」的位置。外层入口没有红点就说明里面领过了，直接跳过，不再点进去找
DOT_HOME_EVENT = (660, 105, 715, 155)       # 家园右上「精彩活动」
DOT_HOME_MENU = (670, 960, 720, 1015)       # 家园右下方块（主菜单）
DOT_MENU_TASK = (320, 615, 370, 670)        # 主菜单「任务」卡片
DOT_MENU_MALL = (640, 615, 690, 670)        # 主菜单「商城」卡片
DOT_MENU_FRIEND = (125, 755, 175, 805)      # 主菜单「好友」
DOT_MENU_GIFT = (510, 890, 560, 940)        # 主菜单「馈赠」
DOT_SEASON_JM = (200, 990, 255, 1045)       # 赛季活动「晶芒淬炼」
DOT_JM_TABS = [(170, 435, 235, 480), (400, 435, 455, 480), (625, 435, 680, 480)]
DOT_JM_BAR = (60, 300, 720, 370)            # 晶芒淬炼顶部积分条
DOT_MIBAO_TAB = (305, 1170, 350, 1215)      # 秘宝大作战「获取能量」页签
DOT_MALL_DAILY = (650, 670, 700, 720)       # 商城「每日特惠」卡片
DOT_MALL_DAILY_GIFT = (100, 330, 175, 385)  # 每日特惠左上「每日赠礼」
DOT_MALL_PASS = (650, 180, 700, 230)        # 商城「巡礼之证」卡片
DOT_MALL_CARD_TAB = (445, 1160, 495, 1210)  # 商城底部「月卡」页签
DOT_PASS_GOAL_TAB = (665, 1170, 715, 1218)  # 巡礼之证底部「巡礼目标」页签
DOT_PASS_GOALS = [(185, 1070, 230, 1115), (400, 1070, 445, 1115), (612, 1070, 660, 1115)]
DOT_PASS_LEVEL = (130, 340, 350, 1060)      # 巡礼之证左列（免费线）等级奖励
DOT_TASK_DAILY_TAB = (230, 1170, 275, 1215)
DOT_TASK_COMMISSION_TAB = (450, 1170, 495, 1215)
DOT_FRIEND_HEART = (360, 1055, 410, 1100)


class DailyReward(UI):
    """
    日常清完后统一领奖励：精彩活动（每日签到、秘宝大作战、赛季活动·晶芒淬炼）、
    商城免费项（每日赠礼、月卡）、好友、馈赠总览、任务（日常、委托提交）。
    绝不点主菜单顶部的轮播横幅（会轮到幸运刮刮乐）和任何付费按钮。
    """

    def find(self, button, region, similarity=0.85, scales=(1.0,)):
        return button.match_region(self.device.image, region, similarity=similarity, scales=scales) > similarity

    def red_dot(self, region, screenshot=False):
        """region 里有没有红点「!」（有红点 0.85~0.99，没有 ≤0.26）"""
        if screenshot:
            self.device.screenshot()
        return self.find(REWARD_BADGE, region, similarity=0.7)

    def card_dot(self, card):
        """活动汇总卡片的红点在卡片文字右上方；card 要先用 find 定位过"""
        x1, y1, x2, _ = card.button
        return self.red_dot((x2 - 5, y1 - 25, x2 + 45, y1 + 25))

    def close_reward_popup(self, check, timeout=8):
        """
        点了领取之后：等「获得奖励」弹窗（有的领取没有弹窗）并关掉，直到回到 check 所在页面。
        """
        timer = Timer(timeout).start()
        settle = Timer(1.5).start()
        while 1:
            self.device.screenshot()
            # 「获得奖励」弹窗，以及「点击空白处关闭」类弹窗（委托提交后的好感度提升）
            if self.ui_additional():
                settle.reset()
                continue
            if self.appear(check, offset=(10, 10)) and settle.reached():
                return True
            if timer.reached():
                logger.warning(f'领取后没有回到 {check}')
                return False
            time.sleep(0.3)

    def claim_all(self, check, button=CLAIM_BUTTON, region=LIST_REGION, scales=CLAIM_SCALES, max_swipes=3):
        """把列表里的「领取」一个个点完；当前屏没有了就往下滑，滑不动或滑够次数就结束"""
        claimed = 0
        swipes = 0
        for _ in range(60):
            self.device.screenshot()
            if self.find(button, region, scales=scales):
                self.device.click(button)
                # 每次点的是不同的条目，不算连点
                self.device.click_record.clear()
                if not self.close_reward_popup(check):
                    raise GamePageUnknownError
                claimed += 1
                continue
            if swipes >= max_swipes:
                break
            before = self.device.image
            self.device.swipe((360, 900), (360, 450), duration=600, name='LIST_DOWN')
            time.sleep(1)
            self.device.screenshot()
            swipes += 1
            if np.mean(np.abs(before.astype(int) - self.device.image.astype(int))) < 2:
                break
        logger.info(f'{check}: 领取 {claimed} 次')
        return claimed

    def list_to_top(self, start=400, end=1000):
        """滑回列表顶部；起点要在列表里面，从标题区滑有的页面滑不动"""
        for _ in range(2):
            self.device.swipe((360, start), (360, end), duration=400, name='LIST_TOP')
        time.sleep(1)

    def back_home(self, timeout=20):
        """左下返回，直到回到家园"""
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.ui_page_appear(page_home):
                return True
            if timer.reached():
                raise GamePageUnknownError
            if self.ui_additional():
                continue
            # 活动汇总、赛季活动、商城页左下是白色细箭头，和通用返回按钮长得不一样，认出页面就直接点左下
            if self.appear(BACK_ARROW, offset=(20, 20), interval=2) \
                    or any(self.appear(page, offset=(10, 10), interval=2) for page in THIN_BACK_PAGES):
                self.device.click(BACK_ARROW)
                continue
            time.sleep(0.5)

    def ensure_home(self):
        """回到家园：领奖页面大多不在页面图里，认不出时连按左下返回"""
        try:
            self.ui_ensure(page_home)
        except GamePageUnknownError:
            self.back_home()

    def wait_any(self, buttons, timeout=10):
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            for button in buttons:
                if self.appear(button, offset=(10, 10)):
                    return button
            if timer.reached():
                return None
            time.sleep(0.5)

    def open_menu(self):
        self.ensure_home()
        if not self.ui_click(MENU_ENTRY, check_button=MENU_CHECK, offset=(10, 10), retry_wait=3, timeout=15):
            raise GamePageUnknownError

    # ---------------- 精彩活动 ----------------
    def open_event_card(self, card, check):
        """活动汇总里找卡片（活动会增减，位置不固定），先回到顶部，找不到就往下滑；卡片没红点就不进"""
        self.list_to_top()
        for _ in range(3):
            self.device.screenshot()
            if self.find(card, LIST_REGION, similarity=0.8):
                if not self.card_dot(card):
                    logger.info(f'{card} 没有红点，跳过')
                    return False
                return self.ui_click(card, check_button=check, offset=(10, 10), retry_wait=3, timeout=10,
                                     skip_first_screenshot=True)
            self.device.swipe((360, 900), (360, 450), duration=600, name='LIST_DOWN')
            time.sleep(1)
        logger.info(f'活动汇总里没有 {card}（活动可能已结束）')
        return False

    def back_to(self, check, timeout=15):
        """
        左下返回，直到 check 出现。
        已经退到家园就停：家园左下是「角色」页签，接着点会进角色页（10-30 秘宝领完返回时发生过）。
        """
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(check, offset=(10, 10)):
                return True
            if timer.reached():
                logger.warning(f'点 {BACK_ARROW} 后 {timeout} 秒内没有出现 {check}')
                return False
            if self.ui_page_appear(page_home):
                logger.warning(f'返回时退到了家园，没有经过 {check}')
                return False
            if self.ui_additional():
                continue
            if self.appear_interval_ready(BACK_ARROW, interval=3):
                self.device.click(BACK_ARROW)

    def ensure_event(self):
        """确认在精彩活动汇总页，不在（比如上一步退回了家园）就从家园重新进"""
        self.device.screenshot()
        if self.appear(EVENT_CHECK, offset=(10, 10)):
            return
        self.ensure_home()
        if not self.ui_click(EVENT_ENTRY, check_button=EVENT_CHECK, offset=(10, 10), retry_wait=3, timeout=15):
            raise GamePageUnknownError

    def event_signin(self):
        if not self.open_event_card(EVENT_SIGNIN, SIGNIN_CHECK):
            return
        self.device.screenshot()
        if self.find(SIGNIN_CLAIM, (30, 240, 690, 1150), similarity=0.8):
            logger.info('领取每日签到')
            self.device.click(SIGNIN_CLAIM)
            self.close_reward_popup(SIGNIN_CHECK)
        else:
            logger.info('今天已经签到过')
        self.back_to(EVENT_CHECK)

    def fate_explore(self):
        """
        秘宝大作战「命运探索1次」还是「前往」时：前往 → 大地图右下「探索」（不点「探索10次」）
        → 确认消耗 1 枚命运果实 → 返回（地图返回直接回家园）。
        """
        self.list_to_top(start=650, end=1150)
        self.device.screenshot()
        if not self.find(FATE_ROW, (0, 480, 720, 1170), similarity=0.85):
            return False
        cy = (FATE_ROW.button[1] + FATE_ROW.button[3]) // 2
        if not GOTO_TEXT.match_at(self.device.image, (560, cy, 624, cy + 30), offset=8, similarity=0.85):
            return False
        logger.info('命运探索：前往大地图')
        self.device.click(ClickArea('FATE_GOTO', (545, cy - 5, 640, cy + 35)))
        if not self.wait_until_appear(MAP_EXPLORE, offset=(10, 10), timeout=30):
            raise GamePageUnknownError
        if not self.ui_click(MAP_EXPLORE, check_button=FATE_CONFIRM, offset=(10, 10), retry_wait=3, timeout=10):
            raise GamePageUnknownError
        self.ui_click(FATE_CONFIRM_OK, check_button=MAP_EXPLORE, offset=(10, 10), retry_wait=3, timeout=15)
        time.sleep(2)
        self.back_home()
        return True

    def event_mibao(self):
        if not self.open_event_card(EVENT_MIBAO, MIBAO_CHECK):
            return
        if self.config.DailyReward_Fate and self.fate_explore():
            # 地图返回直接回家园，重新进精彩活动 → 秘宝大作战领能量
            if not self.ui_click(EVENT_ENTRY, check_button=EVENT_CHECK, offset=(10, 10), retry_wait=3, timeout=15):
                raise GamePageUnknownError
            if not self.open_event_card(EVENT_MIBAO, MIBAO_CHECK):
                return
        # 只领「获取能量」页的任务能量，「封印宝藏」兑换不做（封印宝藏页签上的蓝点不管）
        if self.red_dot(DOT_MIBAO_TAB, screenshot=True):
            self.list_to_top(start=650, end=1150)
            self.claim_all(MIBAO_CHECK, region=(0, 480, 720, 1170))
        self.back_to(EVENT_CHECK)

    def event_season(self):
        if not self.open_event_card(EVENT_SEASON, SEASON_CHECK):
            return
        if self.red_dot(DOT_SEASON_JM, screenshot=True)                 and self.ui_click(SEASON_JM, check_button=JM_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            for tab, dot in zip([JM_TAB_1, JM_TAB_2, JM_TAB_3], DOT_JM_TABS):
                if not self.red_dot(dot, screenshot=True):
                    continue
                self.device.click(tab)
                time.sleep(1.5)
                self.list_to_top(start=650, end=1150)
                self.claim_all(JM_CHECK, region=(0, 520, 720, 1170))
            # 顶部积分条：达到的档位上有红点，点奖励图标（领完任务积分可能刚够）
            for _ in range(5):
                if not self.red_dot(DOT_JM_BAR, screenshot=True):
                    break
                logger.info('领取积分档位奖励')
                self.device.click(REWARD_BADGE)
                self.close_reward_popup(JM_CHECK)
            self.back_to(SEASON_CHECK)
        self.back_to(EVENT_CHECK)

    def events(self):
        logger.hr('Event rewards', level=2)
        self.ensure_home()
        if not self.red_dot(DOT_HOME_EVENT, screenshot=True):
            logger.info('精彩活动没有红点，跳过')
            return
        if not self.ui_click(EVENT_ENTRY, check_button=EVENT_CHECK, offset=(10, 10), retry_wait=3, timeout=15):
            raise GamePageUnknownError
        if self.config.DailyReward_SignIn:
            self.event_signin()
        if self.config.DailyReward_Mibao:
            self.ensure_event()
            self.event_mibao()
        if self.config.DailyReward_Season:
            self.ensure_event()
            self.event_season()
        self.back_home()

    # ---------------- 主菜单 ----------------
    def back_to_menu(self):
        """各子页面左下返回，直到回到主菜单"""
        timer = Timer(20).start()
        while 1:
            self.device.screenshot()
            if self.appear(MENU_CHECK, offset=(10, 10)):
                return True
            if timer.reached():
                raise GamePageUnknownError
            if self.ui_additional():
                continue
            if self.appear(BACK_ARROW, offset=(20, 20), interval=2)                     or any(self.appear(page, offset=(10, 10), interval=2) for page in THIN_BACK_PAGES):
                self.device.click(BACK_ARROW)
                continue
            time.sleep(0.5)

    def mall(self):
        """只领免费的「每日赠礼」、巡礼之证、月卡每日奖励，付费按钮一律不点"""
        logger.hr('Mall free rewards', level=2)
        self.device.click(MENU_MALL)
        page = self.wait_any([MALL_CHECK, MALL_CARD_CHECK])
        if page is None:
            raise GamePageUnknownError
        if page is MALL_CARD_CHECK:
            # 上次停在月卡页，先切回「活动」页签需要的卡片列表
            self.back_to_menu()
            self.device.click(MENU_MALL)
            if self.wait_any([MALL_CHECK]) is None:
                raise GamePageUnknownError
        # 每日特惠 → 左上「每日赠礼」
        if self.red_dot(DOT_MALL_DAILY, screenshot=True) and self.ui_click(
                MALL_DAILY_CARD, check_button=MALL_DAILY_CHECK, offset=(20, 20), retry_wait=3, timeout=10):
            if self.red_dot(DOT_MALL_DAILY_GIFT, screenshot=True):
                logger.info('领取每日赠礼')
                self.device.click(MALL_DAILY_GIFT)
                self.close_reward_popup(MALL_DAILY_CHECK)
            self.back_to(MALL_CHECK)
        if self.config.DailyReward_Pass and self.red_dot(DOT_MALL_PASS, screenshot=True):
            self.mall_pass()
        # 月卡页：只在月卡卡片的按钮范围里找「领取」，避开下面 68 元的七日祈愿
        if self.red_dot(DOT_MALL_CARD_TAB, screenshot=True) and self.ui_click(
                MALL_TAB_CARD, check_button=MALL_CARD_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            self.claim_all(MALL_CARD_CHECK, region=(400, 480, 700, 580), max_swipes=0)
        self.back_to_menu()

    def mall_pass(self):
        """
        巡礼之证：先领「巡礼目标」三组任务的经验，再领「巡礼之证」页左列免费等级奖励。
        右列（女神赐福）、「购买等级」「68元解锁赐福」都是付费的，绝不点。
        """
        if not self.ui_click(MALL_PASS_CARD, check_button=PASS_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            return
        if self.red_dot(DOT_PASS_GOAL_TAB, screenshot=True):
            self.device.click(PASS_TAB_GOAL)
            time.sleep(1.5)
            for tab, dot in zip([PASS_GOAL_DAILY, PASS_GOAL_WEEKLY, PASS_GOAL_SEASON], DOT_PASS_GOALS):
                if not self.red_dot(dot, screenshot=True):
                    continue
                self.device.click(tab)
                time.sleep(1.5)
                self.list_to_top(start=500, end=1050)
                self.claim_all(PASS_CHECK, region=(0, 330, 720, 1070))
            self.device.click(PASS_TAB_MAIN)
            time.sleep(1.5)
        # 左列可领的等级奖励带红点，点图标（点一个会把已达到的等级一起领完）
        for _ in range(5):
            if not self.red_dot(DOT_PASS_LEVEL, screenshot=True):
                break
            logger.info('领取巡礼之证免费等级奖励')
            self.device.click(REWARD_BADGE)
            self.close_reward_popup(PASS_CHECK)
        self.back_to(MALL_CHECK)

    def friend(self):
        logger.hr('Friend', level=2)
        if self.ui_click(MENU_FRIEND, check_button=FRIEND_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            # 爱心按钮 →「友情币获得」弹窗（协助好友、匹配战斗攒的友情币）→ 领取 → 点弹窗外关闭
            if self.red_dot(DOT_FRIEND_HEART, screenshot=True):
                logger.info('领取友情币')
                if self.ui_click(FRIEND_HEART, check_button=FRIEND_DIALOG, offset=(10, 10), retry_wait=3, timeout=10):
                    self.device.click(FRIEND_DIALOG_CLAIM)
                    time.sleep(1.5)
                    self.ui_click(FRIEND_DIALOG_CLOSE, check_button=FRIEND_CHECK, offset=(10, 10), retry_wait=3,
                                  timeout=10)
        self.back_to_menu()

    def gift(self):
        """馈赠总览点一个「领取」就会把所有可领的一起领完"""
        logger.hr('Gift overview', level=2)
        if self.ui_click(MENU_GIFT, check_button=GIFT_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            self.list_to_top()
            self.claim_all(GIFT_CHECK, max_swipes=3)
        self.back_to_menu()

    def task(self):
        logger.hr('Task rewards', level=2)
        self.device.click(MENU_TASK)
        if self.wait_any([TASK_CHECK, COMMISSION_CHECK]) is None:
            raise GamePageUnknownError
        self.device.screenshot()
        if self.red_dot(DOT_TASK_DAILY_TAB)                 and self.ui_click(TASK_TAB_DAILY, check_button=TASK_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            self.list_to_top()
            self.claim_all(TASK_CHECK)
        if self.config.DailyReward_Commission and self.red_dot(DOT_TASK_COMMISSION_TAB, screenshot=True)                 and self.ui_click(TASK_TAB_COMMISSION, check_button=COMMISSION_CHECK, offset=(10, 10), retry_wait=3,
                                  timeout=10):
            self.list_to_top()
            self.claim_all(COMMISSION_CHECK, button=SUBMIT_BUTTON, scales=(1.0,), max_swipes=2)
        self.back_to_menu()

    def menu(self):
        """主菜单：方块图标和各卡片都按红点决定进不进；任务放最后，领别的奖励也会完成一些任务"""
        self.ensure_home()
        if not self.red_dot(DOT_HOME_MENU, screenshot=True):
            logger.info('主菜单没有红点，跳过')
            return
        self.open_menu()
        sections = [
            ('Mall', DOT_MENU_MALL, self.mall),
            ('Friend', DOT_MENU_FRIEND, self.friend),
            ('Gift', DOT_MENU_GIFT, self.gift),
            ('Task', DOT_MENU_TASK, self.task),
        ]
        for name, dot, func in sections:
            if not getattr(self.config, f'DailyReward_{name}'):
                continue
            if self.red_dot(dot, screenshot=True):
                func()
            else:
                logger.info(f'主菜单 {name} 没有红点，跳过')
        self.back_home()

    def run(self):
        logger.hr('Daily reward', level=1)
        self.events()
        self.menu()
