import time

import cv2
import numpy as np

from module.base.button import ClickArea
from module.base.timer import Timer
from module.base.utils import crop
from module.exception import GamePageUnknownError
from module.logger import logger
from module.note.assets import *
from module.ui.page import page_bond, page_note
from module.ui.ui import UI

# 地图上委派节点所在的范围（标题栏以下、队伍以上）；节点位置每次刷新都会变，按徽标找
NODE_REGION = (0, 100, 720, 800)
# 「委派结束 / 委派开始」弹窗分隔线可能出现的范围
POPUP_REGION = (250, 300, 470, 560)
# 详情面板左上的委派名称，文字颜色就是品质
TITLE_REGION = (65, 115, 275, 165)
# 品质：橙色和金色在策略里都是「立刻派出」，不用区分
BLUE, PURPLE, HIGH = 0, 1, 2
QUALITY_NAME = {BLUE: '蓝', PURPLE: '紫', HIGH: '橙/金'}
# 标题文字的色相范围（OpenCV 0~180）：实测蓝 100~109、紫 130~139，背景地图是绿色 30~49 不计入；
# 橙/金还没见过，按常规色相取 30 以下和 160 以上
HUE_RANGES = {BLUE: [(95, 120)], PURPLE: [(120, 160)], HIGH: [(0, 30), (160, 180)]}
# 这么多像素都是同一种颜色才算认出来
HUE_MIN_PIXELS = 500
# 4 个委派里至少有这么多个紫色及以上就不再刷新（用户规则：蓝蓝紫紫可以接受）
GOOD_TARGET = 2
# 笔记页「奇景委派：x/4」能认出的剩余次数
COUNT_BUTTONS = {4: BOND_COUNT_4, 3: BOND_COUNT_3, 0: BOND_COUNT_0}


class BondAdventure(UI):
    # 今天还能派出几次，派一次减一
    budget = 4

    # ---------------- 识别 ----------------
    def dispatch_count(self):
        """笔记页卡片上今天还能派几次；认不出返回 None"""
        self.ui_ensure(page_note)
        for count, button in COUNT_BUTTONS.items():
            if button.match_at(self.device.image, button.area, offset=5, similarity=0.9):
                logger.attr('BondCount', f'{count}/4')
                return count
        logger.warning('认不出今天还剩几次委派（目前只认 0、3、4）')
        return None

    def find_nodes(self, badge, similarity=0.85):
        """地图上带某种徽标的节点，返回节点本体的点击区域（徽标左下），从上到下排"""
        image = crop(self.device.image, NODE_REGION)
        res = cv2.matchTemplate(image, badge.template, cv2.TM_CCOEFF_NORMED)
        ax, ay = badge.area[:2]
        bx1, by1, bx2, by2 = badge._button
        nodes = []
        while 1:
            _, sim, _, (x, y) = cv2.minMaxLoc(res)
            if sim < similarity:
                break
            x0, y0 = x + NODE_REGION[0], y + NODE_REGION[1]
            nodes.append(ClickArea(f'BOND_NODE_{x0}_{y0}',
                                   (x0 + bx1 - ax, y0 + by1 - ay, x0 + bx2 - ax, y0 + by2 - ay)))
            res[max(y - 20, 0):y + 20, max(x - 20, 0):x + 20] = -1
        return sorted(nodes, key=lambda b: b.area[1])

    def popup_appear(self):
        return BOND_POPUP.match_region(self.device.image, POPUP_REGION) > 0.8

    def panel_quality(self):
        """详情面板标题文字的颜色 → 品质；认不出返回 None"""
        hsv = cv2.cvtColor(crop(self.device.image, TITLE_REGION), cv2.COLOR_RGB2HSV)
        mask = (hsv[..., 1] > 95) & (hsv[..., 2] > 170)
        hue = hsv[..., 0][mask]
        count = {q: int(sum(np.count_nonzero((hue >= lo) & (hue < hi)) for lo, hi in ranges))
                 for q, ranges in HUE_RANGES.items()}
        quality = max(count, key=count.get)
        if count[quality] < HUE_MIN_PIXELS:
            logger.warning(f'认不出委派品质，颜色像素数 {count}')
            return None
        return quality

    # ---------------- 页面切换 ----------------
    def wait_map(self, timeout=15):
        """关掉弹窗 / 面板，回到地图"""
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(PAGE_BOND, offset=(10, 10)):
                # 弹窗关掉后节点状态要过一会才刷新
                time.sleep(1)
                self.device.screenshot()
                return True
            if timer.reached():
                logger.warning('没有回到羁绊冒险地图')
                raise GamePageUnknownError
            if self.popup_appear():
                if self.appear_interval_ready(BOND_POPUP_BLANK, interval=2):
                    self.device.click(BOND_POPUP_BLANK)
                continue
            if self.appear(BOND_PANEL, offset=(10, 10), interval=2):
                self.device.back()

    def open_node(self, node, timeout=6):
        """点节点，返回出现的是 'popup'（委派结束）还是 'panel'（委派详情），都没出现返回 None"""
        self.device.click(node)
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.popup_appear():
                return 'popup'
            if self.appear(BOND_PANEL, offset=(10, 10)):
                return 'panel'
            if timer.reached():
                logger.warning(f'点 {node} 后没有出现弹窗或委派面板')
                return None

    # ---------------- 操作 ----------------
    def claim(self):
        """领取完成的委派：带红色「!」的节点点一下就是「委派结束」弹窗，关掉后原位置换成新委派"""
        for _ in range(8):
            nodes = self.find_nodes(BOND_RED_BADGE)
            if not nodes:
                return
            logger.info(f'领取完成的委派（还有 {len(nodes)} 个）')
            self.open_node(nodes[0])
            self.wait_map()
            self.device.click_record.clear()

    def start_in_panel(self):
        """委派面板里：快速选择 → 开始委派 → 关掉「委派开始」弹窗"""
        if self.budget <= 0:
            logger.info('今天的委派次数用完了')
            self.wait_map()
            return False
        self.device.click(BOND_QUICK)
        time.sleep(1)
        self.device.click(BOND_START)
        timer = Timer(6).start()
        while 1:
            self.device.screenshot()
            if self.popup_appear():
                break
            if timer.reached():
                logger.warning('点开始委派后没有出现「委派开始」（可能成员不够），跳过这个委派')
                self.wait_map()
                return False
        self.wait_map()
        self.device.click_record.clear()
        self.budget -= 1
        return True

    def dispatch(self, node, quality):
        logger.info(f'派出 {QUALITY_NAME[quality]}色委派 {node}')
        if self.open_node(node) != 'panel':
            self.wait_map()
            return False
        return self.start_in_panel()

    def survey(self, locked):
        """
        打开每个可委派的节点看品质。橙/金当场派出，不再刷新它。

        Args:
            locked (list): 本次已经派出的品质，派出的会加进去

        Returns:
            list: 还没派的 [(节点, 品质)]
        """
        self.device.screenshot()
        remain = []
        for node in self.find_nodes(BOND_BLUE_BADGE):
            if self.open_node(node) != 'panel':
                self.wait_map()
                continue
            # 面板有淡入动画，颜色稳定了再认
            time.sleep(0.5)
            self.device.screenshot()
            quality = self.panel_quality()
            if quality is None:
                quality = BLUE
            logger.info(f'{node} 品质：{QUALITY_NAME[quality]}')
            if quality == HIGH:
                logger.info('橙/金色委派，立刻派出')
                if self.start_in_panel():
                    locked.append(quality)
                continue
            self.wait_map()
            remain.append((node, quality))
        return remain

    # ---------------- 刷新 ----------------
    def _refresh_record(self):
        record = self.config.state.setdefault('BondAdventure', {})
        day = self.config.next_server_update().isoformat(timespec='seconds')
        if record.get('RefreshDay') != day:
            record['RefreshDay'] = day
            record['RefreshUsed'] = 0
        return record

    def refresh(self):
        """
        用晨星刷新一次没派出的委派（已派出的不会变）。
        只认「100 晨星」：按钮价格或确认框文字不是 100 就不刷；
        出现「还有高品质景点没委派」说明品质判断有误，取消。

        Returns:
            bool: 是否刷新了
        """
        record = self._refresh_record()
        limit = int(self.config.BondAdventure_RefreshLimit)
        if record['RefreshUsed'] >= limit:
            logger.info(f'今天已经刷新 {record["RefreshUsed"]} 次，到达上限 {limit}，不再刷新')
            return False
        self.device.screenshot()
        if not self.appear(BOND_REFRESH, offset=(10, 10)):
            logger.warning('刷新按钮上的价格不是 100 晨星，不刷新')
            return False
        self.device.click(BOND_REFRESH)
        timer = Timer(6).start()
        while 1:
            self.device.screenshot()
            if self.appear(BOND_HQ_WARN, offset=(10, 10)):
                logger.warning('游戏提示还有高品质委派没派，取消刷新')
                break
            if self.appear(BOND_COST_100, offset=(10, 10)):
                # 确认框有弹出动画
                time.sleep(0.5)
                # 点之前就记次数：万一点了没认出生效（抛错），宁可多记一次，也不会超过每日上限多花晨星
                record['RefreshUsed'] += 1
                self.config.save_state()
                logger.info(f'花 100 晨星刷新委派（今天第 {record["RefreshUsed"]} 次）')
                # 确认框还在就是这一下没点上（同一个确认框点几下只扣一次），再点
                self.click_until(BOND_DIALOG_CONFIRM, self.gone(BOND_COST_100, offset=(10, 10)),
                                 skip_first_screenshot=True)
                self.wait_map()
                return True
            if timer.reached():
                logger.warning('没有等到「100 晨星」刷新确认框，取消')
                break
        if not self.appear(PAGE_BOND, offset=(10, 10)):
            self.device.click(BOND_DIALOG_CANCEL)
        self.wait_map()
        return False

    # ---------------- 主流程 ----------------
    def run(self):
        """
        领完成的委派 → 看可委派的品质 → 按用户策略派出，必要时刷新：
        - 橙/金：立刻派出（锁定，不再刷新它）
        - 4 个里紫色及以上够 2 个：剩下的全部派出（蓝蓝紫紫可以接受）
        - 不够：先把紫色派出锁定，剩 2 个以上没派才刷新；只剩 1 个不值得刷，直接派
        - 刷新到达每日上限：全部派出
        - 先在笔记页看今天还剩几次：0 次只领奖；认不出不刷新
        """
        logger.hr('Bond adventure', level=2)
        count = self.dispatch_count()
        self.ui_ensure(page_bond)
        # 刚进地图时节点还没画出来（实测进页面那一帧找不到红色「!」），等一下再找
        self.wait_map()
        self.claim()
        if count == 0:
            logger.info('今天的委派次数已用完，只领奖')
            return True
        # 认不出剩余次数时照常派（派不出去会跳过），但不花晨星刷新
        self.budget = 4 if count is None else count
        can_refresh = count is not None
        # 本次派出的品质。之前已经在进行中的委派品质不知道，不算进「紫色及以上」，最多多刷几次（有上限）
        locked = []
        while self.budget > 0:
            remain = self.survey(locked)
            if not remain or self.budget <= 0:
                break
            good = sum(q >= PURPLE for q in locked) + sum(q >= PURPLE for _, q in remain)
            logger.attr('BondQuality', f'已派出 {[QUALITY_NAME[q] for q in locked]}，'
                                       f'待派 {[QUALITY_NAME[q] for _, q in remain]}')
            remain.sort(key=lambda x: -x[1])
            if good >= GOOD_TARGET or len(remain) <= 1:
                for node, quality in remain:
                    self.dispatch(node, quality)
                break
            # 紫色先派出锁定，刷新只换剩下的
            for node, quality in [r for r in remain if r[1] == PURPLE]:
                if self.dispatch(node, quality):
                    locked.append(quality)
            blues = [r for r in remain if r[1] == BLUE]
            if len(blues) <= 1 or not can_refresh or not self.refresh():
                for node, quality in blues:
                    self.dispatch(node, quality)
                break
        self.device.screenshot()
        left = len(self.find_nodes(BOND_BLUE_BADGE))
        if left:
            logger.warning(f'还有 {left} 个委派没派出')
        else:
            logger.info('委派都已派出')
        return True
