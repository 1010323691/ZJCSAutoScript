import re
import time

import cv2

from module.base.button import ClickArea
from module.base.utils import crop
from module.logger import logger
from module.note.assets import *
from module.ui.assets import BACK_ARROW
from module.ui.page import page_material
from module.ui.ui import UI

# 一键购买弹窗里四行（锤子、镐子、手套、铲子）的纵坐标，每行 112 像素
ROW_Y = [444, 556, 668, 780]
ROW_STEP = 112
PLUS = [ClickArea(f'MATERIAL_PLUS_{i + 1}', (574, y - 18, 610, y + 18)) for i, y in enumerate(ROW_Y)]
MINUS = [ClickArea(f'MATERIAL_MINUS_{i + 1}', (454, y - 18, 490, y + 18)) for i, y in enumerate(ROW_Y)]
# 弹窗会记住上次的组数；目前能认出的组数
COUNT_BUTTONS = {1: MATERIAL_COUNT_1, 4: MATERIAL_COUNT_4}
# 已有识别素材的总价；配置的预期花费不在这里就不买
COST_BUTTONS = {240: MATERIAL_COST_240, 1280: MATERIAL_COST_1280}
# 黄金矿洞开采按钮下面的镐子数量；挖成一下就少 1。
# 以前看矿石血条，10-31 血条变了但游戏只算了 9 次（矿石重新长出来时血条自己也在变）
MINE_PICK_REGION = (370, 955, 442, 985)


class MaterialRealm(UI):
    def cancel(self):
        self.device.click(MATERIAL_CANCEL)
        self.wait_until_appear(PAGE_MATERIAL, offset=(10, 10), timeout=5)

    def buy(self):
        """一键购买：四种工具按配置调组数，总价等于预期花费才购买"""
        buy_count = str(self.config.MaterialRealm_BuyCount)
        if not re.fullmatch(r'[1-9]{4}', buy_count):
            logger.warning(f'组数配置 {buy_count} 不是 4 位 1~9 的数字，不购买')
            return False
        counts = [int(c) for c in buy_count]
        cost = int(self.config.MaterialRealm_ExpectedCost)
        cost_button = COST_BUTTONS.get(cost)
        if cost_button is None:
            logger.warning(f'还没有总价 {cost} 的识别素材，不购买（目前支持 {sorted(COST_BUTTONS)}）')
            return False

        self.ui_ensure(page_material)
        self.device.click(MATERIAL_ONEKEY)
        if not self.wait_until_appear(MATERIAL_DIALOG, offset=(10, 10), timeout=6):
            return False
        time.sleep(0.5)
        self.device.screenshot()
        # 弹窗会记住上次的组数，先认出每行当前是几组，再按差值点 + / -
        current = []
        for i in range(4):
            area = MATERIAL_COUNT_1.area
            area = (area[0], area[1] + ROW_STEP * i, area[2], area[3] + ROW_STEP * i)
            found = [n for n, button in COUNT_BUTTONS.items() if button.match_at(self.device.image, area)]
            if not found:
                logger.warning(f'认不出第 {i + 1} 行的组数，取消')
                self.cancel()
                return False
            current.append(found[0])
        logger.attr('MaterialCount', current)
        for i, n in enumerate(counts):
            diff = n - current[i]
            for _ in range(abs(diff)):
                self.device.click(PLUS[i] if diff > 0 else MINUS[i])
                time.sleep(0.3)
        time.sleep(0.5)
        self.device.screenshot()
        if not cost_button.match_at(self.device.image, cost_button.area, offset=5, similarity=0.95):
            logger.warning(f'总价不是 {cost} 钻石，取消，不购买')
            self.cancel()
            return False
        logger.info(f'组数 {buy_count}，总价 {cost} 钻石，购买')
        self.device.click(MATERIAL_BUY)
        self.wait_reward_popup(page_material, timeout=5)
        self.wait_until_appear(PAGE_MATERIAL, offset=(10, 10), timeout=10)
        return True

    def mine(self, times):
        """
        黄金矿洞开采 times 次（完成「探索 N 次素材秘境」类任务）。「快捷开采」必须是关的，不是关就不挖。
        矿石被挖碎重新长出来的动画期间点击不生效，所以每点一下都看镐子数量有没有变化，没变就补点。
        """
        if times <= 0:
            return True
        self.ui_ensure(page_material)
        if not self.ui_click(MATERIAL_GOLD_CAVE, check_button=MINE_CHECK, offset=(10, 10), retry_wait=3, timeout=10):
            return False
        time.sleep(1)
        self.device.screenshot()
        if not self.appear(QUICK_MINE_OFF, offset=(10, 10), similarity=0.85):
            logger.warning('「快捷开采」不是关闭状态，不开采')
            self.ui_click(BACK_ARROW, check_button=PAGE_MATERIAL, offset=(10, 10), retry_wait=3)
            return False
        done = 0
        for _ in range(times * 3):
            if done >= times:
                break
            before = crop(self.device.image, MINE_PICK_REGION)
            self.device.click(MINE_BUTTON)
            self.device.click_record.clear()
            # 数字有时晚一点才变，最多等 3 秒
            for _ in range(6):
                time.sleep(0.5)
                self.device.screenshot()
                after = crop(self.device.image, MINE_PICK_REGION)
                if cv2.matchTemplate(after, before, cv2.TM_CCOEFF_NORMED)[0][0] < 0.95:
                    done += 1
                    break
            else:
                logger.info('镐子数量没变，这一下没有生效，补点')
        logger.info(f'开采 {done}/{times} 次')
        self.ui_click(BACK_ARROW, check_button=PAGE_MATERIAL, offset=(10, 10), retry_wait=3)
        return done >= times

    def run(self):
        logger.hr('Material realm', level=2)
        self.buy()
        self.mine(int(self.config.MaterialRealm_MineTimes))
        return True
