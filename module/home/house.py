import time

import cv2

from module.activity.assets import REWARD_BADGE
from module.base.button import ClickArea
from module.base.timer import Timer
from module.base.utils import crop
from module.exception import GamePageUnknownError
from module.home.assets import *
from module.home.home import HomeScene
from module.logger import logger
from module.ui.assets import GET_REWARD_CHECK
from module.ui.page import page_home
from module.ui.ui import REWARD_OFFSET

# 场景划到最右端（小屋）后，床上方经验气泡的红点范围
BUBBLE_DOT_REGION = (110, 440, 210, 540)
# 从最右端慢慢往回拖 450 像素后，小屋左侧二楼栏杆上信箱（黑猫）的红点范围。拖动有十几像素误差，范围放宽
MAIL_DOT_REGION = (420, 470, 590, 630)
# 气泡和黑猫都在红点左下方，点击位置 = 红点中心 + 这个偏移（10-30 实测两处都约 (-18, +33)）
DOT_TO_ITEM = (-18, 33)
# 有红点 0.85~0.94，没有 ≤0.55
DOT_SIMILARITY = 0.75


class HomeHouse(HomeScene):
    """
    家园小屋（用户补充，10-30）：
    - 床：领经验气泡 → 点床用「今日免费加速」（加速 2 小时）→ 再领一次气泡
    - 信箱：有红点就打开「信件」→ 全部领取
    场景物件按「固定位置附近的红点」判断（用户说明：信箱不一定是黑猫，主要看红点和位置）
    """

    def scene_to_right_end(self):
        for _ in range(6):
            # 起点避开右侧活动图标列（见 HomeScene.scene_steps）
            self.device.swipe((560, 330), (10, 330), duration=600, name='SCENE_RIGHT_FAST')
        time.sleep(1.5)
        self.device.screenshot()

    def find_dot(self, region):
        """region 里红点「!」对应物件的点击区域，没有红点返回 None"""
        image = crop(self.device.image, region)
        res = cv2.matchTemplate(image, REWARD_BADGE.template, cv2.TM_CCOEFF_NORMED)
        _, sim, _, (x, y) = cv2.minMaxLoc(res)
        if sim < DOT_SIMILARITY:
            return None
        h, w = REWARD_BADGE.template.shape[:2]
        cx = region[0] + x + w // 2 + DOT_TO_ITEM[0]
        cy = region[1] + y + h // 2 + DOT_TO_ITEM[1]
        return ClickArea(f'DOT_ITEM_{cx}_{cy}', (cx - 10, cy - 10, cx + 10, cy + 10))

    def wait_home(self, timeout=10):
        """关掉升级提示、奖励弹窗等，等回到家园"""
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.ui_page_appear(page_home):
                return True
            if timer.reached():
                raise GamePageUnknownError
            if self.ui_additional():
                continue
            time.sleep(0.5)

    def claim_bubble(self):
        """床上方的经验气泡：点一下直接领取，没有弹窗；连续领可能升级，有升级提示"""
        self.device.screenshot()
        item = self.find_dot(BUBBLE_DOT_REGION)
        if item is None:
            return False
        logger.info('领取床的经验气泡')
        # 领到了红点就没了；红点还在就是这一下没点上，再点
        self.click_until(item, lambda: self.find_dot(BUBBLE_DOT_REGION) is None, skip_first_screenshot=True)
        # 升级提示是个半透明横幅，过一会自己消失
        time.sleep(3)
        self.wait_home()
        return True

    def bed_speedup(self):
        """点床打开弹窗：是「今日免费加速」就点，点完弹窗自己关；用过了（「全局加速」）就点外面关掉，不点"""
        # 11-01 实测点床被吞过一次（2.5 秒没弹窗），没弹窗就再点
        self.click_until(BED, self.appeared(BED_DIALOG, offset=(10, 10)))
        # 弹窗有弹出动画
        time.sleep(0.5)
        self.device.screenshot()
        if not self.appear(BED_FREE_SPEEDUP, offset=(10, 10)):
            logger.info('今天的免费加速已经用过')
            # 返回键在弹窗动画期间会被吞，点弹窗外面关（11-01 实测能关）
            self.ui_close_popup(BED_DIALOG, page_home.check_button)
            return False
        logger.info('使用今日免费加速（2 小时）')
        # 用掉后同一位置会变成「全局加速」（禁点）：只在还认得出「今日免费加速」时补点，认不出就停手、点外面关
        if not self.click_until(BED_FREE_SPEEDUP, self.gone(BED_DIALOG, offset=(10, 10)),
                                abort=lambda: not self.appear(BED_FREE_SPEEDUP, offset=(10, 10)),
                                skip_first_screenshot=True):
            self.ui_close_popup(BED_DIALOG, page_home.check_button)
        self.wait_home()
        return True

    def bed(self):
        logger.hr('Bed', level=3)
        self.scene_to_right_end()
        self.claim_bubble()
        if self.bed_speedup():
            # 加速产出的经验又变成气泡
            self.claim_bubble()

    def mailbox(self):
        """紧接着床做：领气泡、关床弹窗都不会动视角（用户 10-31 说明），还在最右端，直接往回拖到信箱"""
        logger.hr('Mailbox', level=3)
        self.device.swipe((150, 450), (600, 450), duration=1500, name='SCENE_LEFT_SLOW')
        time.sleep(1.5)
        self.device.screenshot()
        item = self.find_dot(MAIL_DOT_REGION)
        if item is None:
            logger.info('信箱没有红点')
            return False
        self.device.click(item)
        timer = Timer(6).start()
        while 1:
            self.device.screenshot()
            if self.appear(MAIL_DIALOG, offset=(10, 10)):
                break
            if timer.reached():
                logger.warning('点信箱后没有出现「信件」弹窗')
                self.wait_home()
                return False
        time.sleep(0.5)
        self.device.screenshot()
        # 只在认出「全部领取」时点；按钮不在说明已经领过，旁边的「删除已读」绝对不能点
        if self.appear(MAIL_CLAIM_ALL, offset=(10, 10)):
            logger.info('信件全部领取')
            self.device.click(MAIL_CLAIM_ALL)
            # 「获得奖励」横幅盖在信件弹窗上，晚一两秒才出来；按钮先消失，不等横幅就去关弹窗会点空（10-31 卡住的原因）
            if self.wait_until_appear(GET_REWARD_CHECK, offset=REWARD_OFFSET, timeout=5):
                timer = Timer(8).start()
                while 1:
                    self.device.screenshot()
                    if self.ui_additional():
                        continue
                    if self.appear(MAIL_DIALOG, offset=(10, 10)) and not self.appear(GET_REWARD_CHECK, offset=REWARD_OFFSET):
                        break
                    if timer.reached():
                        raise GamePageUnknownError
                    time.sleep(0.5)
            else:
                logger.info('没有出现「获得奖励」弹窗')
        else:
            logger.info('没有「全部领取」按钮，信件已经领过')
        # 信件弹窗没有返回键，点弹窗外面关（用户说明 10-31）
        self.ui_close_popup(MAIL_DIALOG, page_home.check_button)
        return True

    def run(self):
        logger.hr('Home house', level=2)
        self.ui_ensure(page_home)
        self.bed()
        self.mailbox()
