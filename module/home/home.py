import time

import cv2
import numpy as np

from module.base.button import ClickArea
from module.base.utils import crop
from module.home.assets import *
from module.logger import logger
from module.ui.assets import BACK_ARROW
from module.ui.page import page_home
from module.ui.ui import UI

# 场景物件出现的范围（避开顶部资源栏、右侧活动入口和边缘提示图标、下方任务条）
SCENE_REGION = (0, 250, 640, 960)
# 气泡和糖果都有一缩一放的动画，按多个缩放倍数匹配
BUBBLE_SCALES = (0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1)
CANDY_SCALES = (0.9, 0.95, 1.0, 1.05)
# 糖果树是一大团粉色。整棵树在画面里时粉色像素 7.5～11 万；黄昏天空也偏粉，非树画面最多约 5.7 万
TREE_PINK_PIXELS = 65000


class HomeScene(UI):
    def scene_to_left_end(self):
        """家园场景一直往左滑到底（飞艇）"""
        for _ in range(4):
            self.device.swipe((100, 450), (650, 450), duration=600, name='SCENE_LEFT')
        time.sleep(1)

    def scene_steps(self, steps=4):
        """从最左端开始，每次往右看大约半屏，每到一个位置截一张图"""
        self.scene_to_left_end()
        for step in range(steps):
            self.device.swipe((650, 450), (350, 450), duration=1500, name='SCENE_RIGHT')
            time.sleep(1)
            self.device.screenshot()
            yield step

    def leave_unexpected_page(self):
        """点了场景物件后进了别的页面（例如幻兽结缘卡池），立刻点左下返回，什么都不点"""
        self.device.screenshot()
        if self.ui_page_appear(page_home):
            return False
        if self.appear(BACK_ARROW, offset=(20, 20)):
            logger.warning('进入了意料之外的页面，立即返回')
            self.ui_click(BACK_ARROW, check_button=page_home.check_button, offset=(10, 10), retry_wait=3,
                          timeout=15, skip_first_screenshot=True)
            return True
        return False


class Cart(HomeScene):
    def run(self):
        """找到小推车头顶的奖杯气泡，点一次领取挂机产出"""
        logger.hr('Cart', level=2)
        self.ui_ensure(page_home)
        for _ in self.scene_steps():
            # 白天/夜晚、动画大小不同时相似度在 0.75~1.00，其他画面不超过 0.35
            sim = CART_BUBBLE.match_region(self.device.image, SCENE_REGION, similarity=0.6, scales=BUBBLE_SCALES)
            if sim > 0.6:
                logger.info(f'找到小推车气泡（相似度 {sim:.2f}）')
                self.device.click(CART_BUBBLE)
                self.wait_reward_popup(page_home)
                self.leave_unexpected_page()
                return True
        logger.info('没有找到小推车气泡，可能暂时没有挂机产出')
        # 没东西可收是正常情况，不算失败（run 返回 False 会被记成失败）
        return None


class CandyTree(HomeScene):
    def find_candy(self):
        best = 0, None
        for button in [CANDY_1, CANDY_2, CANDY_3, CANDY_4]:
            # 同一光照下有糖果 0.85 以上，换了光照可能只有 0.78；其他画面（270 张截图）不超过 0.54
            sim = button.match_region(self.device.image, SCENE_REGION, similarity=0.7, scales=CANDY_SCALES)
            if sim > best[0]:
                best = sim, button
        return best

    def find_tree(self):
        """整棵糖果树在画面里时，返回树身上的点击区域（粉色区域的中位点），否则 None"""
        hsv = cv2.cvtColor(crop(self.device.image, SCENE_REGION), cv2.COLOR_RGB2HSV)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        mask = ((h >= 150) | (h <= 5)) & (s >= 40) & (s <= 170) & (v >= 150)
        if mask.sum() < TREE_PINK_PIXELS:
            return None
        ys, xs = np.nonzero(mask)
        x, y = int(np.median(xs)) + SCENE_REGION[0], int(np.median(ys)) + SCENE_REGION[1]
        return ClickArea('CANDY_TREE', (x - 10, y - 10, x + 10, y + 10))

    def run(self):
        """
        树上有糖果时点第一下是收获，没有糖果时点树会进幻兽结缘卡池（只看不抽，马上退出）。
        - 认出糖果：点糖果
        - 认不出（糖果样子随光照变化很大）：按用户说明直接点树身，进了卡池就左下返回，什么都不点
        """
        logger.hr('Candy tree', level=2)
        self.ui_ensure(page_home)
        for _ in self.scene_steps():
            sim, button = self.find_candy()
            if sim > 0.7:
                logger.info(f'找到糖果（相似度 {sim:.2f}）')
                self.device.click(button)
                self.wait_reward_popup(page_home, timeout=3)
                self.leave_unexpected_page()
                return True
            tree = self.find_tree()
            if tree is None:
                continue
            logger.info('没认出糖果，点一下树身')
            self.device.click(tree)
            # 卡池页打开要一两秒，等够 5 秒还在家园才算收获了糖果
            for _ in range(5):
                time.sleep(1)
                if self.leave_unexpected_page():
                    logger.info('进了幻兽结缘卡池，说明树上没有糖果，已退出')
                    return None
            logger.info('点树后没有进卡池，糖果已收获')
            return True
        logger.warning('家园场景里没找到糖果树')
        # 没找到树不影响别的任务，不算失败（run 返回 False 会被记成失败）
        return None
