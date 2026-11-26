"""
菲涅克的谜题第二期 · 石碑谜题（11-27 实测，知识库 12 篇第 10 节）。注意和第一期的「石板谜题」（module/fenek/fenek.py ShibanSolver）不是一个玩法。

草地上几块石碑，每块 1~3 级高：1 级只有顶上的「冠」，2 级冠下有红褐色碑身，3 级碑身上亮两只青色的眼睛。
点一块石碑（角色走过去碰它），它和上下左右相邻的石碑各升 1 级，3 级再升回到 1 级。全部到 3 级场景里出现宝箱。
就是模 3 的「点灯」：解线性方程组 A·t ≡ 3 - h (mod 3)。每点一下重新认一遍高度再解（点击在角色走路时会被吞掉，11-27 实测）。
"""
import time

import cv2

from module.base.timer import Timer
from module.fenek.assets import PUZZLE_SUCCESS, SHIBEI_CROWN
from module.logger import logger

GRID = 103
SCENE = (0, 130, 720, 1000)
# 冠上金色菱形到石碑底边的距离（1/2/3 级）
DIAMOND_TO_BOTTOM = {1: 17, 2: 44, 3: 79}


class SteleSolver:
    def __init__(self, main):
        self.main = main
        self.device = main.device
        self.origin = None   # 第 0 列中心 x、第 0 行底边 y
        self.cells = None

    @staticmethod
    def crowns(image):
        """所有冠：(菱形 x, 菱形 y, 高度)"""
        img = image.copy()
        img[:SCENE[1]] = 0
        img[SCENE[3]:] = 0
        res = cv2.matchTemplate(img, SHIBEI_CROWN.template, cv2.TM_CCOEFF_NORMED)
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        out = []
        while True:
            _, sim, _, (x, y) = cv2.minMaxLoc(res)
            if sim < 0.65:
                break
            res[max(0, y - 30):y + 30, max(0, x - 40):x + 40] = -1
            dx, dy = x + 29, y + 37
            # 菱形下面一截：3 级是整块红褐碑身（~0.4），2 级露出一半（~0.2），1 级没有（~0）
            below = hsv[dy + 15:dy + 55, dx - 30:dx + 30]
            red = ((below[..., 0] < 18) & (below[..., 1] > 100) & (below[..., 2] > 90) & (below[..., 2] < 230)).mean()
            h = 3 if red > 0.3 else 2 if red > 0.1 else 1
            out.append((dx, dy, h))
        return out

    def read(self):
        """返回 {(行, 列): 高度}。第一次读时定下格子原点，之后按原点归格"""
        stones = self.crowns(self.device.image)
        if not stones:
            return {}
        if self.origin is None:
            x0 = min(x for x, _, _ in stones)
            b0 = min(y + DIAMOND_TO_BOTTOM[h] for _, y, h in stones)
            self.origin = (x0, b0)
        x0, b0 = self.origin
        cells = {}
        for x, y, h in stones:
            r, c = round((y + DIAMOND_TO_BOTTOM[h] - b0) / GRID), round((x - x0) / GRID)
            cells[(r, c)] = h
        return cells

    @staticmethod
    def solve(cells):
        """高斯消元（模 3），返回 {格: 点几次}，无解返回 None"""
        keys = sorted(cells)
        n = len(keys)
        idx = {k: i for i, k in enumerate(keys)}
        m = [[0] * (n + 1) for _ in range(n)]
        for k, i in idx.items():
            m[i][i] = 1
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (k[0] + d[0], k[1] + d[1])
                if nb in idx:
                    m[i][idx[nb]] = 1
            m[i][n] = (3 - cells[k]) % 3
        piv = []
        r = 0
        for c in range(n):
            p = next((i for i in range(r, n) if m[i][c] % 3), None)
            if p is None:
                continue
            m[r], m[p] = m[p], m[r]
            inv = 1 if m[r][c] == 1 else 2
            m[r] = [(v * inv) % 3 for v in m[r]]
            for i in range(n):
                if i != r and m[i][c]:
                    f = m[i][c]
                    m[i] = [(m[i][j] - f * m[r][j]) % 3 for j in range(n + 1)]
            piv.append(c)
            r += 1
        if any(m[i][n] for i in range(r, n)):
            return None
        t = [0] * n
        for i, c in enumerate(piv):
            t[c] = m[i][n]
        return {keys[i]: t[i] for i in range(n) if t[i]}

    @staticmethod
    def apply(cells, cell):
        """按规则算点一下之后的高度"""
        out = dict(cells)
        for d in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (cell[0] + d[0], cell[1] + d[1])
            if nb in out:
                out[nb] = out[nb] % 3 + 1
        return out

    def settle(self, last, pred, tries=8):
        """
        点完以后读高度。角色走到石碑跟前会挡住碑身（11-27 石碑 4 把 3 级读成 2 级，局面变成无解），升起还有动画，
        所以：读到和预测一样就用；连着 3 次读到「没变」说明这下被吞了（角色在走路时点的），用原来的；
        别的读数要连续两次一样、并且有解才用；都不满足就按预测走（之后每一步还会再读）
        """
        prev = None
        same_as_last = 0
        for _ in range(tries):
            self.device.screenshot()
            if self.main.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                return {k: 3 for k in pred}
            cur = self.read()
            if set(cur) == self.cells:
                if cur == pred:
                    return cur
                if cur == last:
                    same_as_last += 1
                    if same_as_last >= 3:
                        logger.info('高度没变，这一下没点上')
                        return last
                elif cur == prev and self.solve(cur) is not None:
                    logger.info(f'读到的高度和预测不一样，按读到的: {cur}')
                    return cur
            prev = cur
            time.sleep(0.8)
        logger.warning(f'石碑高度读不稳，按预测的: {pred}')
        return pred

    def tap_cell(self, cell):
        from module.fenek.fenek import tap_point
        x0, b0 = self.origin
        tap_point(self.device, (int(x0 + cell[1] * GRID), int(b0 + cell[0] * GRID - 22)), 'SHIBEI_STONE')

    def find_chest(self, timeout=6):
        from module.fenek.fenek import open_chest
        timer = Timer(timeout).start()
        while not timer.reached():
            self.device.screenshot()
            if self.main.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                return True
            if open_chest(self.main, SCENE):
                return True
            time.sleep(0.5)
        return False

    def run(self):
        # 开局石碑一半在聊天框下面：在右边草地上慢拖画面往上
        self.device.swipe((620, 900), (620, 550), duration=1500, name='SHIBEI_PAN')
        # 开局连读三次取认到最多的：拖完画面还在动、角色可能挡住一块，只读一次漏一块整关都会建错
        first = {}
        for _ in range(3):
            time.sleep(0.8)
            self.device.screenshot()
            self.origin = None
            cur = self.read()
            if len(cur) > len(first):
                first, origin = cur, self.origin
        self.origin = origin if first else None
        logger.info(f'石碑 {len(first)} 块: {first}')
        if len(first) < 2:
            logger.warning('认不出石碑')
            return False
        self.cells = set(first)
        last = first
        for _ in range(40):
            if all(h == 3 for h in last.values()):
                logger.info('石碑全部 3 级')
                return self.find_chest()
            sol = self.solve(last)
            if not sol:
                logger.warning(f'石碑无解: {last}')
                return False
            cell = next(iter(sol))
            logger.info(f'高度 {last}，还要点 {sol}，点 {cell}')
            self.tap_cell(cell)
            pred = self.apply(last, cell)
            time.sleep(2.5)
            last = self.settle(last, pred)
        return False
