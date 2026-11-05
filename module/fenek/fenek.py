"""
精彩活动 · 菲涅克的谜题（限时活动，11-05 实测）。

18 关按顺序解锁：音符晶灯 1~6、元素链接 1~6、石板谜题 1~6。关卡列表里当前能打的那关图标右上有红点「!」，
打完的关奖励打勾、可以重玩。每关解开后弹「解谜成功」，点「继续下一关」直接进下一关。

不用道具：场景右侧的菲涅克石像 / 右上角的狐狸头像是「供奉黄金甲虫帮我解谜」，绝不点（用户 11-05：不可以使用道具直接破关）。

规则、截图、各关的数据见私有知识库 12 篇；流程设计见 docs/02 第 3.15 节。
"""
import heapq
import time

import cv2
import numpy as np

from module.activity.assets import REWARD_BADGE
from module.base.button import ClickArea
from module.base.timer import Timer
from module.base.utils import area_offset
from module.exception import GamePageUnknownError, GameStuckError, GameTooManyClickError, TaskNotImplemented
from module.fenek.assets import *
from module.logger import logger
from module.reward.assets import EVENT_CHECK, EVENT_ENTRY
from module.reward.reward import LIST_REGION as EVENT_LIST_REGION, DailyReward
from module.ui.assets import BACK_ARROW
from module.ui.page import page_home

# 关卡列表里红点「!」在当前关卡图标的右上方，图标中心在红点的左下（11-05：红点 (285,184) → 音符晶灯1 (200,250)）
LEVEL_FROM_DOT = (-85, 65)
LIST_REGION = (0, 100, 720, 1180)
MAX_LEVELS = 18


def open_chest(main, region):
    """
    解开后场景里出现的宝箱（音符晶灯、石板谜题同一个样子）。找到就点开，直到「解谜成功」。
    宝箱可能是上次解开没点的（重启后游戏会直接回到这一关，宝箱还在）
    """
    if YINFU_CHEST.match_region(main.device.image, region, similarity=0.8) > 0.8:
        logger.info('宝箱出现，解开了')
        x1, y1, x2, y2 = YINFU_CHEST.button
        chest = ClickArea('PUZZLE_CHEST', (x1 + 15, y1 + 15, x2 - 15, y2 - 15))
        main.click_until(chest, main.appeared(PUZZLE_SUCCESS), handle_popups=False)
        return True
    return False


def character_position(image):
    """
    角色（火焰翅膀，大片高饱和的橙黄色）的位置，认不出返回 None。
    点到角色自己会打开玩家信息面板（11-05 两次误点），点场景里的空地之前用它避开。
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 0] >= 5) & (hsv[..., 0] <= 30) & (hsv[..., 1] > 150) & (hsv[..., 2] > 200)).astype(np.uint8)
    m[:120] = 0
    m[990:] = 0
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    n, _, stats, centroids = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    k = 1 + int(np.argmax(stats[1:, 4]))
    if stats[k, 4] < 3000:
        return None
    return int(centroids[k][0]), int(centroids[k][1])


def tap_point(device, point, name):
    """点一个像素点（±5 抖动）。先清点击记录：解谜时同一格会连着点好几次，不算「点太多次卡住」"""
    x, y = point
    device.click_record.clear()
    device.click(ClickArea(name, (x - 5, y - 5, x + 5, y + 5)))


class YinfuSolver:
    """
    音符晶灯：踩开关石台 → 晶石柱依次亮起、头顶冒出同色音符（同一根会重复亮）→ 按顺序点柱子，
    角色走过去敲响 → 全对后场景中间出现宝箱 → 点宝箱弹「解谜成功」。
    点错不罚，也不用重踩开关，从头再按一遍正确顺序就行（11-05 第 2 关实测）。
    """
    # 晶石柱：灰色地面上饱和度高的竖条（宽 18~50、高 35~80）。角色（火焰翅膀）、称号横幅按大小排除
    CRYSTAL_AREA = (50, 60, 670, 600)
    # 音符在柱子右上方冒出再往上飘：和踩开关前的画面比，这一块变了多少像素
    NOTE_DX, NOTE_DY = (16, 52), (-70, -20)
    NOTE_ON, NOTE_OFF = 60, 25
    # 点柱子后柱子四角闪一下白色的目标框（约 0.5 秒），用来确认点上了
    MARKER_DX, MARKER_DY = ((-57, -40), (40, 57)), ((-43, -28), (54, 71))
    # 听旋律时角色要从开关走开再踩回去；只在确定角色站在开关上时点这里（点到角色自己会打开玩家信息）
    REST = (360, 720)
    WALK_SPEED = 150  # 像素/秒，实测约 180，留余量

    def __init__(self, main):
        self.main = main
        self.device = main.device

    def shot(self):
        return self.device.screenshot_fast()

    def tap(self, point, name):
        tap_point(self.device, point, name)

    # ---------- 识别 ----------
    @classmethod
    def crystals(cls, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = ((hsv[..., 1] > 110) & (hsv[..., 2] > 120)).astype(np.uint8)
        x1, y1, x2, y2 = cls.CRYSTAL_AREA
        mask[:y1] = 0
        mask[y2:] = 0
        mask[:, :x1] = 0
        mask[:, x2:] = 0
        # 左上头像和等级条
        mask[:66, :290] = 0
        mask[:120, :112] = 0
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
        out = []
        for i in range(1, n):
            _, _, w, h, a = stats[i]
            # 下限放到 200：浅色的柱子（11-05 重玩第 6 关的绿柱，饱和度中位数只有 95）只有一小半过阈值
            # 重心在 560 以下的是开局角色头顶的称号横幅（最低的柱子在 540 左右）
            if 200 < a < 2300 and 12 <= w <= 50 and 25 <= h <= 80 and centroids[i][1] < 560:
                out.append((int(centroids[i][0]), int(centroids[i][1])))
        return out

    def stable_crystals(self):
        """连截 3 张，至少 2 张都认出的才算（11-05 第 6 关有一次第一张漏了左上角的粉色柱）"""
        seen = []
        for _ in range(3):
            for c in self.crystals(self.shot()):
                for s in seen:
                    if abs(s[0] - c[0]) < 25 and abs(s[1] - c[1]) < 25:
                        s[2] += 1
                        break
                else:
                    seen.append([c[0], c[1], 1])
            time.sleep(0.3)
        return sorted([(s[0], s[1]) for s in seen if s[2] >= 2], key=lambda c: (c[1] // 60, c[0]))

    def find_switch(self):
        sim = YINFU_SWITCH.match_region(self.device.image, (40, 420, 300, 700), similarity=0.85)
        if sim > 0.85:
            x1, y1, x2, y2 = YINFU_SWITCH.button
            return (x1 + x2) // 2, (y1 + y2) // 2
        return None

    @classmethod
    def note_px(cls, image, base, c):
        x, y = c
        ys = slice(max(0, y + cls.NOTE_DY[0]), y + cls.NOTE_DY[1])
        xs = slice(x + cls.NOTE_DX[0], x + cls.NOTE_DX[1])
        diff = np.abs(image[ys, xs].astype(int) - base[ys, xs].astype(int)).max(axis=2)
        return int((diff > 50).sum())

    @classmethod
    def marker_px(cls, image, c):
        x, y = c
        n = 0
        for x1, x2 in cls.MARKER_DX:
            for y1, y2 in cls.MARKER_DY:
                n += int((image[y + y1:y + y2, x + x1:x + x2].min(axis=2) > 232).sum())
        return n

    # ---------- 听 ----------
    def listen(self, cs, switch):
        """
        踩开关，记下音符出现的顺序。音符冒出后要飘 0.5 秒左右才消失，同一根柱子要等像素数回落才算下一次；
        同一帧里两根一起冒出时，像素多的先出现（11-05 第 5 关两个音符只差 0.1 秒）。
        """
        base = self.shot()
        self.tap(switch, 'YINFU_SWITCH')
        start = time.time()
        armed = [True] * len(cs)
        seq, last = [], None
        while 1:
            image = self.shot()
            new = []
            for j, c in enumerate(cs):
                v = self.note_px(image, base, c)
                if armed[j] and v > self.NOTE_ON:
                    new.append((-v, j))
                    armed[j] = False
                elif not armed[j] and v < self.NOTE_OFF:
                    armed[j] = True
            for _, j in sorted(new):
                seq.append(j)
                last = time.time()
            if last and time.time() - last > 2.5:
                break
            if not last and time.time() - start > 10:
                logger.warning('踩开关 10 秒没听到音符')
                break
            if time.time() - start > 25:
                break
        logger.info(f'听到 {len(seq)} 个音符: {seq}')
        return seq

    def read_melody(self, cs, switch):
        """旋律每次一样。连听两次结果相同才算数，最多听 5 次（偶尔会多认或漏认一个）"""
        reads = []
        for i in range(5):
            if i:
                # 角色这时站在开关上，走开再踩回去
                self.tap(self.REST, 'YINFU_REST')
                time.sleep(3)
            reads.append(self.listen(cs, switch))
            if len(reads) >= 2 and reads[-1] and reads[-1] == reads[-2]:
                return reads[-1]
        logger.warning(f'连听 5 次结果都不一致: {reads}')
        return None

    # ---------- 敲 ----------
    def play(self, cs, seq, pos):
        """
        按顺序点柱子。确认目标框闪了（点上了），再按距离等角色走到、敲响（走路约 180 像素/秒，
        到了以后再过约 0.5 秒才响）。不靠音符判断有没有敲响：角色站在柱子旁边，火焰翅膀会挡住、干扰。
        """
        for k in seq:
            target = cs[k]
            dist = ((target[0] - pos[0]) ** 2 + (target[1] - pos[1]) ** 2) ** 0.5
            for attempt in range(3):
                self.tap(target, f'YINFU_CRYSTAL_{k}')
                t = time.time()
                marked = False
                while time.time() - t < 0.9:
                    if self.marker_px(self.shot(), target) > 150:
                        marked = True
                        break
                if marked:
                    break
                logger.info(f'柱子 {k} 没出现目标框，再点一次')
            wait = dist / self.WALK_SPEED + 1.0
            time.sleep(max(0., wait - (time.time() - t)))
            pos = target

    def run(self):
        self.device.screenshot()
        if open_chest(self.main, (220, 200, 500, 460)):
            return True
        # 先让角色站到柱子下面的空地上：站在柱子中间会挡住柱子，头顶的称号横幅也会被当成柱子
        # （11-05 重玩第 6 关，上次没走完的角色站在中间，认成 7 根）。已经站在那里就不点，点到角色会打开玩家信息
        char = character_position(self.device.image)
        if char is None or abs(char[0] - self.REST[0]) > 80 or abs(char[1] - (self.REST[1] - 60)) > 120:
            self.tap(self.REST, 'YINFU_REST')
            time.sleep(3)
        cs = self.stable_crystals()
        logger.info(f'晶石柱 {len(cs)} 根: {cs}')
        if len(cs) < 2:
            logger.warning('认不出晶石柱')
            return False
        self.device.screenshot()
        switch = self.find_switch()
        if switch is None:
            # 角色站在开关上挡住了（上次没打完），走开再找
            self.tap(self.REST, 'YINFU_REST')
            time.sleep(3)
            self.device.screenshot()
            switch = self.find_switch()
        if switch is None:
            logger.warning('找不到开关石台')
            return False
        logger.info(f'开关石台 {switch}')
        for rnd in range(3):
            seq = self.read_melody(cs, switch)
            if not seq:
                return False
            # 听完角色站在开关上
            self.play(cs, seq, switch)
            timer = Timer(4).start()
            while not timer.reached():
                self.device.screenshot()
                if open_chest(self.main, (220, 200, 500, 460)):
                    return True
            logger.warning(f'敲完没出现宝箱（第 {rnd + 1} 轮），重新听')
        return False


class YuansuSolver:
    """
    元素链接：棋盘 N×N（第 1 关 4×4、第 2 关 5×5），格子上有成对的同色符文。
    从一个符文拖到同色的另一个，路径经过的石板点亮；所有同色连上、所有石板都亮就解开，直接弹「解谜成功」。
    不同颜色的路径不能重叠。
    """
    # 棋盘外框（各关一样大，格子大小 = 528 / N）
    BOARD_X = (96, 624)
    BOARD_Y = (400, 1000)
    BG_GRAY = 75

    def __init__(self, main):
        self.main = main
        self.device = main.device

    @staticmethod
    def _runs(mask):
        idx = np.where(mask)[0]
        out = []
        if not len(idx):
            return out
        s = p = idx[0]
        for v in idx[1:]:
            if v != p + 1:
                out.append((s, p))
                s = v
            p = v
        out.append((s, p))
        return [r for r in out if r[1] - r[0] > 40]

    @classmethod
    def read_board(cls, image):
        """
        Returns:
            list, list, dict: 每列中心 x、每行中心 y、{(行, 列): (色相, 饱和度, 亮度)} 只含有符文的格子
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(float)
        tile = np.abs(gray - cls.BG_GRAY) > 12
        xr = cls._runs(tile[430:950, :].mean(axis=0) > 0.5)
        yr = cls._runs(tile[:, 100:620].mean(axis=1) > 0.5)
        yr = [r for r in yr if r[0] >= cls.BOARD_Y[0] and r[1] <= cls.BOARD_Y[1]]
        xr = [r for r in xr if r[0] >= cls.BOARD_X[0] - 5 and r[1] <= cls.BOARD_X[1] + 5]
        cx = [int((a + b) // 2) for a, b in xr]
        cy = [int((a + b) // 2) for a, b in yr]
        cells = {}
        if len(cx) < 2 or len(cy) < 2:
            return cx, cy, cells
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        h = int((cx[1] - cx[0]) * 0.28)
        for r, y in enumerate(cy):
            for c, x in enumerate(cx):
                p = hsv[y - h:y + h, x - h:x + h].reshape(-1, 3)
                sat = p[(p[:, 1] > 90) & (p[:, 2] > 90)]
                if len(sat) > 0.08 * len(p):
                    cells[(r, c)] = (float(np.median(sat[:, 0])), float(np.median(sat[:, 1])),
                                     float(np.median(sat[:, 2])))
        return cx, cy, cells

    @staticmethod
    def color_dist(a, b):
        dh = min(abs(a[0] - b[0]), 180 - abs(a[0] - b[0]))
        return dh * 3 + abs(a[1] - b[1]) * 0.3 + abs(a[2] - b[2]) * 0.3

    @classmethod
    def pair(cls, cells):
        """按颜色两两配对（总颜色差最小的完美匹配）。返回 [(起点, 终点), ...] 和最大的一对颜色差"""
        keys = list(cells)
        best = [None, 1e18]

        def rec(rest, acc, cost):
            if cost >= best[1]:
                return
            if not rest:
                best[0], best[1] = list(acc), cost
                return
            a = rest[0]
            for b in rest[1:]:
                rec([x for x in rest if x not in (a, b)], acc + [(a, b)], cost + cls.color_dist(cells[a], cells[b]))

        if len(keys) % 2 or not keys:
            return None, None
        rec(keys, [], 0)
        worst = max(cls.color_dist(cells[a], cells[b]) for a, b in best[0])
        return best[0], worst

    @staticmethod
    def solve(rows, cols, pairs, timeout=20):
        """回溯：每次延伸选择最少的那条路径；剪枝看空格的出路和每对是否还连得通。要求铺满所有格子"""
        grid = [[-1] * cols for _ in range(rows)]
        for k, (a, b) in enumerate(pairs):
            grid[a[0]][a[1]] = k
            grid[b[0]][b[1]] = k
        paths = [[a] for a, _ in pairs]
        done = [False] * len(pairs)
        deadline = time.time() + timeout

        def nb(r, c):
            return [(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= r + dr < rows and 0 <= c + dc < cols]

        def ok():
            heads = set()
            for k in range(len(pairs)):
                if not done[k]:
                    heads.add(paths[k][-1])
                    heads.add(pairs[k][1])
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] == -1:
                        free = sum(1 for q in nb(r, c) if grid[q[0]][q[1]] == -1 or q in heads)
                        if free < 1 or (free < 2 and not any(q in heads for q in nb(r, c))):
                            return False
            for k in range(len(pairs)):
                if done[k]:
                    continue
                s, t = paths[k][-1], pairs[k][1]
                seen, stack, found = {s}, [s], False
                while stack and not found:
                    u = stack.pop()
                    for q in nb(*u):
                        if q == t:
                            found = True
                            break
                        if q not in seen and grid[q[0]][q[1]] == -1:
                            seen.add(q)
                            stack.append(q)
                if not found:
                    return False
            return True

        def rec():
            if time.time() > deadline:
                raise TimeoutError
            todo = [k for k in range(len(pairs)) if not done[k]]
            if not todo:
                return all(grid[r][c] != -1 for r in range(rows) for c in range(cols))
            best = None
            for k in todo:
                head = paths[k][-1]
                opts = [q for q in nb(*head) if grid[q[0]][q[1]] == -1 or q == pairs[k][1]]
                if best is None or len(opts) < len(best[1]):
                    best = (k, opts)
            k, opts = best
            for q in opts:
                if q == pairs[k][1]:
                    done[k] = True
                    paths[k].append(q)
                    if ok() and rec():
                        return True
                    paths[k].pop()
                    done[k] = False
                else:
                    grid[q[0]][q[1]] = k
                    paths[k].append(q)
                    if ok() and rec():
                        return True
                    paths[k].pop()
                    grid[q[0]][q[1]] = -1
            return False

        try:
            return paths if rec() else None
        except TimeoutError:
            logger.warning(f'{timeout} 秒没解出来')
            return None

    def run(self):
        self.device.screenshot()
        cx, cy, cells = self.read_board(self.device.image)
        logger.info(f'棋盘 {len(cy)}×{len(cx)}，符文 {len(cells)} 个: {cells}')
        if len(cx) < 3 or len(cx) != len(cy):
            logger.warning('认不出棋盘')
            return False
        pairs, worst = self.pair(cells)
        if pairs is None or worst > 20:
            # 颜色差大说明有符文没认出来或认错了，配不成对
            logger.warning(f'符文配不成对: {pairs}，最大颜色差 {worst}')
            return False
        logger.info(f'符文配对: {pairs}')
        paths = self.solve(len(cy), len(cx), pairs)
        if paths is None:
            logger.warning('没有解')
            return False
        for attempt in range(2):
            for k, path in enumerate(paths):
                logger.info(f'路径 {k}: {path}')
                self.device.drag_path([(cx[c], cy[r]) for r, c in path], name=f'YUANSU_PATH_{k}')
                time.sleep(0.8)
            if self.main.wait_until_appear(PUZZLE_SUCCESS, offset=(10, 10), timeout=5):
                return True
            logger.warning('连完没出现「解谜成功」，再画一遍')
        return False


class ShibanSolver:
    """
    石板谜题：草地上一片石板（格距约 103 像素），走一笔把所有石板点亮，场景中间出现宝箱 → 点宝箱弹「解谜成功」。
    规则（11-05 第 1、2 关实测，第 2 关路线是用户给的）：
    - 普通石板：踩上去变青色；每踩一次亮灭翻转，踩奇数次是亮的（第 6 关要踩 3 次才走得通）
    - 「Z 字」石板：必须踩两次才亮（用户 11-05 说明；常见走法是从它拐进死胡同再出来）
    - 箭头石板：要顺着箭头方向走进去才亮；出来可以拐弯，也可以停在上面结束（第 2 关终点就是「^」）
    - 漩涡：踩上去传送到空白石板（单向），两格都算踩过
    - 走到草地上全部熄灭重来，所以开局先走到起点外侧的草地，再一格一格点
    开局石板有一半被聊天框挡着，先往上拖画面。
    """
    PITCH = 103
    SCAN = (0, 130, 720, 990)   # 聊天框以上、头像以下
    DIRS = {'up': (-1, 0), 'down': (1, 0), 'left': (0, -1), 'right': (0, 1)}
    STEP_WAIT = 1.4             # 相邻两格走过去约 0.6 秒，留余量
    WALK_SPEED = 150            # 像素/秒，实测约 180，留余量
    # 火焰翅膀的重心比角色所站石板的中心高 36 ~ 低 4 像素（11-05 第 6 关几十帧实测，随动画变），取中间：重心往下 15 是格子中心。
    # 原来按「往下 40」算，重心偏低时会算到下面一行：以为角色站在石板上，「先下到旁边草地」点到了角色自己
    CHAR_DY = 15

    def __init__(self, main):
        self.main = main
        self.device = main.device
        self.misclick = False   # 点到了角色、打开过玩家信息（relocate 里发现并关掉）
        self.statue = None      # 菲涅克石像所在的格子（草地上，走路时绕开）

    def tap(self, point, name):
        tap_point(self.device, point, name)

    # ---------- 识别 ----------
    @classmethod
    def tile_mask(cls, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        stone = (hsv[..., 1] < 70) & (hsv[..., 2] > 150)
        lit = (hsv[..., 0] > 80) & (hsv[..., 0] < 100) & (hsv[..., 1] > 60) & (hsv[..., 2] > 180)
        m = (stone | lit).astype(np.uint8)
        x1, y1, x2, y2 = cls.SCAN
        m[:y1] = 0
        m[y2:] = 0
        return m

    @classmethod
    def read_board(cls, image):
        """
        石板在 103 像素的格子上。搜格子的相位：让「88×88 的框里大部分是石板色」的格子最多。
        Returns:
            dict: {(行, 列): (中心 x, 中心 y)}，行列从 0 开始，左上角是最小的行列
        """
        m = cls.tile_mask(image)
        ii = cv2.integral(m)
        # 窗口接近石板大小（约 96）：错位的格子在边上会框到草地，满格数就少了（50 的窗口错开 1/4 格也是满的）
        h = 44

        def fill(cx, cy):
            return (ii[cy + h, cx + h] - ii[cy - h, cx + h] - ii[cy + h, cx - h] + ii[cy - h, cx - h]) / (4 * h * h)

        x1, y1, x2, y2 = cls.SCAN

        def lattice(ox, oy):
            cells = []
            for cx in range(x1 + h + ox, x2 - h, cls.PITCH):
                for cy in range(y1 + h + oy, y2 - h, cls.PITCH):
                    f = fill(cx, cy)
                    if f > 0.75:
                        cells.append((f, cx, cy))
            # 比总的填充量，不比格子数：错开十几像素时格子数常常一样（相邻石板挨着），
            # 只有对正了边上那圈格子才最满（11-05 第 3 关按格子数选，竖直偏了 19 像素，花纹全认错）
            return sum(c[0] for c in cells), [(cx, cy) for _, cx, cy in cells]

        best = (0, None, (0, 0))
        for ox in range(0, cls.PITCH, 3):
            for oy in range(0, cls.PITCH, 3):
                score, cells = lattice(ox, oy)
                if score > best[0]:
                    best = (score, cells, (ox, oy))
        bx, by = best[2]
        for ox in range(bx - 2, bx + 3):
            for oy in range(by - 2, by + 3):
                score, cells = lattice(ox % cls.PITCH, oy % cls.PITCH)
                if score > best[0]:
                    best = (score, cells, (ox, oy))
        if not best[1]:
            return {}
        cells = best[1]
        xs0, ys0 = min(c[0] for c in cells), min(c[1] for c in cells)
        out = {}
        for cx, cy in cells:
            out[(round((cy - ys0) / cls.PITCH), round((cx - xs0) / cls.PITCH))] = (int(cx), int(cy))
        # 只留和最大一片连着的（远处的岩石不算）
        keys = set(out)
        start = max(keys, key=lambda k: sum((k[0] + dr, k[1] + dc) in keys for dr, dc in cls.DIRS.values()))
        seen, stack = {start}, [start]
        while stack:
            r, c = stack.pop()
            for dr, dc in cls.DIRS.values():
                q = (r + dr, c + dc)
                if q in keys and q not in seen:
                    seen.add(q)
                    stack.append(q)
        return {k: v for k, v in out.items() if k in seen}

    @staticmethod
    def _templates():
        gray = lambda b: cv2.cvtColor(b.template, cv2.COLOR_RGB2GRAY)
        up, right = gray(SHIBAN_UP), gray(SHIBAN_RIGHT)
        return {'normal': gray(SHIBAN_NORMAL), 'z': gray(SHIBAN_Z), 'up': up, 'right': right,
                'down': cv2.rotate(up, cv2.ROTATE_180), 'left': cv2.rotate(right, cv2.ROTATE_180),
                'swirl': gray(SHIBAN_SWIRL)}

    @classmethod
    def classify(cls, image, cells):
        """每块石板按中间花纹分类。最像的不到 0.6、或者和第二像的差不到 0.2，就认不出（可能是新花纹或者已经亮了）"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        templates = cls._templates()
        kinds, unknown = {}, []
        for k, (x, y) in cells.items():
            region = gray[y - 44:y + 44, x - 44:x + 44]
            scores = sorted(((float(cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED).max()), name)
                             for name, t in templates.items()), reverse=True)
            if scores[0][0] < 0.7:
                # 空白石板没有花纹，模板匹配对它不灵（和什么都像 0.6 左右），看中间 48×48 的边缘多少：
                # 空白 0%，箭头 6~10%（模板都在 0.73 以上），其他 16% 以上。框大了会框到石板边框，中心偏几像素就不准
                edges = float((cv2.Canny(gray[y - 24:y + 24, x - 24:x + 24], 40, 100) > 0).mean() * 100)
                if edges < 3:
                    kinds[k] = 'blank'
                    continue
            if scores[0][0] < 0.6 or scores[0][0] - scores[1][0] < 0.2:
                unknown.append((k, [(round(s, 2), n) for s, n in scores[:2]]))
            kinds[k] = scores[0][1]
        return kinds, unknown

    @classmethod
    def lit_count(cls, image, cells):
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        n = 0
        for x, y in cells.values():
            p = hsv[y - 30:y + 30, x - 30:x + 30]
            if ((p[..., 0] > 80) & (p[..., 0] < 100) & (p[..., 1] > 60)).mean() > 0.3:
                n += 1
        return n

    # ---------- 解 ----------
    @classmethod
    def solve(cls, kinds, timeout=20):
        """
        先按「出箭头格只能直着走」解（第 1~3 关都是这样走通的），没有解再放开成「出来往哪走都行」
        （第 4 关的「<」左边没有石板，又不能当终点，只能拐出来）
        """
        deadline = time.time() + timeout
        for revisit in (False, True):
            for straight, swirl_start in ((True, False), (False, False), (True, True), (False, True)):
                left = deadline - time.time()
                if left <= 0:
                    logger.warning(f'{timeout} 秒没解出来')
                    return None
                path = cls._solve(kinds, straight_exit=straight, swirl_start=swirl_start, revisit=revisit,
                                  timeout=left)
                if path is not None:
                    if revisit:
                        logger.info('按「普通石板踩 3 次又亮」才解出来')
                    if not straight:
                        logger.info('按「箭头格出来可以拐弯」才解出来')
                    if swirl_start:
                        logger.info('按「从草地直接踩上漩涡起步」才解出来')
                    return path
        return None

    @classmethod
    def _solve(cls, kinds, straight_exit=True, swirl_start=False, revisit=False, timeout=20):
        """
        一笔走完。普通格、空白格踩奇数次（每踩一次亮灭翻转，先找只踩 1 次的解）；Z 字格必须踩 2 次（用户 11-05：两次才能激活，不是允许两次）；箭头格顺箭头方向进入 1 次；
        踩上漩涡格就传送到空白格（两格都算踩过，接着从空白格走）。起点要挨着草地，不能是箭头格或漩涡格。

        Returns:
            list: [(格子, 要不要点), ...]，传送落地的那一步不用点；没有解返回 None
        """
        tiles = set(kinds)
        swirls = [k for k, v in kinds.items() if v == 'swirl']
        blanks = [k for k, v in kinds.items() if v == 'blank']
        if len(swirls) > 1 or (swirls and len(blanks) != 1):
            # 只见过一对（第 4 关），多个漩涡不知道怎么配对
            logger.warning(f'漩涡 {swirls}、空白 {blanks} 配不成一对')
            return None
        teleport = {swirls[0]: blanks[0]} if swirls else {}
        # 普通、空白石板每踩一次亮灭翻转（11-05 第 6 关实测踩 3 次又亮），revisit 时允许踩 3 次；Z 字踩满 2 次才亮
        cap = {k: 2 if v == 'z' else (3 if revisit and v in ('normal', 'blank') else 1) for k, v in kinds.items()}

        def satisfied(k):
            if kinds[k] in ('normal', 'blank'):
                return visits[k] % 2 == 1
            return visits[k] == cap[k]

        nb = lambda p: [(p[0] + dr, p[1] + dc) for dr, dc in cls.DIRS.values() if (p[0] + dr, p[1] + dc) in tiles]
        starts = [k for k in tiles if kinds[k] not in cls.DIRS and (swirl_start or kinds[k] != 'swirl')
                  and len(nb(k)) < 4]
        # 只有一个邻居的格子多半是起点或终点，先试
        starts.sort(key=lambda k: len(nb(k)))
        deadline = time.time() + timeout
        visits = {k: 0 for k in tiles}
        path = []

        def can_enter(prev, q):
            if visits[q] >= cap[q]:
                return False
            step = (q[0] - prev[0], q[1] - prev[1])
            if kinds[q] in cls.DIRS and step != cls.DIRS[kinds[q]]:
                return False
            if straight_exit and kinds[prev] in cls.DIRS and step != cls.DIRS[kinds[prev]]:
                return False
            if q in teleport and visits[teleport[q]] >= cap[teleport[q]]:
                return False
            return True

        def connected():
            rest = [k for k in tiles if not satisfied(k)]
            if not rest:
                return True
            head = path[-1][0]
            seen, stack = {head}, [head]
            while stack:
                u = stack.pop()
                nexts = list(nb(u))
                if u in teleport:
                    nexts.append(teleport[u])
                for q in nexts:
                    if q not in seen and visits[q] < cap[q]:
                        seen.add(q)
                        stack.append(q)
            return all(k in seen for k in rest)

        order = sorted(tiles)
        failed = set()

        def rec():
            if time.time() > deadline:
                raise TimeoutError
            if all(satisfied(k) for k in tiles):
                return True
            head = path[-1][0]
            # 同一个位置、同样的踩踏次数，之前走不通的不再试（允许重复踩时状态会大量重复）
            state = (head, tuple(visits[k] for k in order))
            if state in failed:
                return False
            if not connected():
                failed.add(state)
                return False
            for q in nb(head):
                if not can_enter(head, q):
                    continue
                visits[q] += 1
                path.append((q, True))
                if q in teleport:
                    visits[teleport[q]] += 1
                    path.append((teleport[q], False))
                if rec():
                    return True
                if q in teleport:
                    path.pop()
                    visits[teleport[q]] -= 1
                path.pop()
                visits[q] -= 1
            failed.add(state)
            return False

        try:
            for s0 in starts:
                visits[s0] = 1
                path[:] = [(s0, True)]
                if s0 in teleport:
                    visits[teleport[s0]] += 1
                    path.append((teleport[s0], False))
                if rec():
                    return list(path)
                visits[s0] = 0
                if s0 in teleport:
                    visits[teleport[s0]] -= 1
        except TimeoutError:
            logger.warning(f'{timeout} 秒没解出来')
        return None

    # ---------- 走 ----------
    # 能放心点的范围：头像以下、聊天框以上（点到聊天框会打开聊天窗口，11-05 误点过一次）
    SAFE = (40, 210, 680, 960)      # 要点的石板在这个范围里；太靠上时站在上面的角色一半在头像那条（y<120 不找角色）

    def relocate(self, expect=None, char_on=None):
        """
        镜头会跟着角色走（11-05 第 4 关走到左边、传送之后都整体挪了一两格），每步之前重新认石板，
        把认到的那几块和整张图对上，更新每块石板的屏幕坐标。
        只看到一部分石板时好几种对法重叠一样多，选原点离预期最近的：expect 是预期的原点
        （刚拖过画面就是原来的原点加上拖动距离，否则就是原来的原点）。
        char_on 是角色现在站的格子：按角色的位置推原点，比用上一次的原点准
        （11-05 第 6 关传送后镜头跳了三行，按旧原点对错了三行，下一下点到了石板外面的草地上，全部熄灭）
        """
        self.device.screenshot()
        if expect is None and char_on is not None:
            char = character_position(self.device.image)
            if char is not None:
                expect = (char[0] - char_on[1] * self.PITCH, char[1] + self.CHAR_DY - char_on[0] * self.PITCH)
        expect = expect or self.origin
        for _ in range(3):
            # 点到了角色：玩家信息面板盖住了场景，后面再点会点到面板上的按钮
            # （11-05 接着点到了「幻兽」按钮，打开幻兽详情，后面 100 多下都点在面板上）。关掉，这一轮作废
            if self.main.appear(STATUE_LEAVE, offset=(20, 20)):
                # 点到了石像：「供奉黄金甲虫帮你解惑」，只点「离开」
                logger.warning('点到了菲涅克石像，点「离开」')
                self.device.click(STATUE_LEAVE)
            elif self.main.appear(PLAYER_INFO, offset=(20, 20)) or self.main.appear(PET_INFO, offset=(20, 20)):
                logger.warning('点到了角色，打开了玩家信息，按返回关掉')
                self.device.back()
            else:
                break
            time.sleep(1.5)
            self.device.screenshot()
            self.misclick = True
        vis = self.read_board(self.device.image)
        cands = {}
        for (vr, vc), (vx, vy) in vis.items():
            for t in self.kinds:
                dr, dc = t[0] - vr, t[1] - vc
                if (dr, dc) in cands:
                    continue
                matched = [((r, c), p) for (r, c), p in vis.items() if (r + dr, c + dc) in self.kinds]
                xs = [p[0] - (c + dc) * self.PITCH for (r, c), p in matched]
                ys = [p[1] - (r + dr) * self.PITCH for (r, c), p in matched]
                cands[(dr, dc)] = (len(matched), (float(np.median(xs)), float(np.median(ys))))
        if not cands:
            return False
        top = max(n for n, _ in cands.values())
        if top < 3:
            return False
        best = min((v for v in cands.values() if v[0] >= max(3, top * 0.8)),
                   key=lambda v: abs(v[1][0] - expect[0]) + abs(v[1][1] - expect[1]) - v[0] * 5)
        x0, y0 = best[1]
        moved = abs(x0 - self.origin[0]) > 20 or abs(y0 - self.origin[1]) > 20
        self.origin = (x0, y0)
        self.pos = {t: (int(x0 + t[1] * self.PITCH), int(y0 + t[0] * self.PITCH)) for t in self.kinds}
        if moved:
            logger.info(f'镜头动了，石板原点 ({int(x0)}, {int(y0)})')
        return True

    def safe(self, point):
        x1, y1, x2, y2 = self.SAFE
        return x1 < point[0] < x2 and y1 < point[1] < y2

    def bring_into_view(self, point):
        """point 不在安全范围就拖画面，把它拖到屏幕中间附近，再重新认石板。返回拖完后的坐标"""
        for _ in range(3):
            if self.safe(point):
                return point
            dx = int(np.clip(360 - point[0], -300, 300))
            dy = int(np.clip(560 - point[1], -350, 350))
            self.drag(dx, dy)
            old = self.origin
            self.relocate(expect=(old[0] + dx, old[1] + dy))
            point = (point[0] + int(self.origin[0] - old[0]), point[1] + int(self.origin[1] - old[1]))
        return point if self.safe(point) else None

    def drag(self, dx, dy):
        """
        拖画面 (dx, dy)。拖得太短会被当成点一下，角色就走过去了（11-05 拖 16 像素，角色走上石板还踩了漩涡），
        所以每次至少拖 200：要拖的少就先多拖 200 再拖回来。慢慢拖（1.5 秒），快拖有惯性
        """
        def one(ddx, ddy):
            x0 = int(np.clip(360 - ddx // 2, 150, 570))
            y0 = int(np.clip(600 - ddy // 2, 250, 900))
            self.device.swipe((x0, y0), (x0 + ddx, y0 + ddy), duration=1500, name='SHIBAN_PAN')
            time.sleep(1.2)

        if max(abs(dx), abs(dy)) >= 200:
            one(dx, dy)
            return
        ex = 200 if dx >= 0 else -200
        ey = 0
        if abs(dy) > abs(dx):
            ex, ey = 0, (200 if dy >= 0 else -200)
        one(dx + ex, dy + ey)
        one(-ex, -ey)

    def board_box(self):
        """
        整片石板的外框 (左, 上, 右, 下)，以及左右屏幕边上是不是还有露出一截的石板（读格子时只算露全的）。
        11-05 第 5 关有 7 列（721 像素宽），右边一列只露出一条，没认出来，按缺一格的图找不到解
        """
        self.device.screenshot()
        cells = self.read_board(self.device.image)
        if not cells:
            return None
        h = self.PITCH // 2
        xs = [x for x, _ in cells.values()]
        ys = [y for _, y in cells.values()]
        left, top, right, bottom = min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h
        m = self.tile_mask(self.device.image)
        y1, y2 = max(top, self.SCAN[1]), min(bottom, self.SCAN[3])
        more_left = left > 12 and m[y1:y2, 0:10].mean() > 0.12
        more_right = right < 708 and m[y1:y2, 710:720].mean() > 0.12
        # 上下同理：上面一行藏在头像后面（y<130 不读）时，读到的上沿还在 145 以下，看起来是放下了（11-05 第 6 关少读一行）
        x1, x2 = max(left, 0), min(right, 720)
        t1, t2 = max(top - 30, self.SCAN[1]), top - 8
        b1, b2 = bottom + 8, min(bottom + 30, self.SCAN[3])
        more_top = t2 - t1 >= 8 and m[t1:t2, x1:x2].mean() > 0.12
        more_bottom = b2 - b1 >= 8 and m[b1:b2, x1:x2].mean() > 0.12
        return left, top, right, bottom, more_left, more_right, more_top, more_bottom

    def pan(self):
        """
        开局石板有一半在聊天框下面，要拖画面让整片石板露出来：上沿拖到头像下面（y≈170），左右露全。
        第 5 关石板有 7 行，固定拖一下会把最上面一行拖到头像后面去，所以按位置算，拖完再看，最多调 4 次。

        Returns:
            bool: 整片石板都在画面里（头像以下、聊天框以上、左右没有露一截的）
        """
        def fits(box):
            left, top, right, bottom, more_left, more_right, more_top, more_bottom = box
            if not (top >= 145 and bottom <= 955) or more_left or more_right or more_top or more_bottom:
                return False
            # 左右：都离开屏幕边，或者都贴着屏幕边（7 列正好一屏宽）。只贴一边时那边外面可能还有整列看不到
            touch_l, touch_r = left <= 12, right >= 708
            return touch_l == touch_r and left >= -8 and right <= 728

        for _ in range(4):
            box = self.board_box()
            if box is None:
                self.drag(0, -450)
                continue
            if fits(box):
                return True
            left, top, right, bottom, more_left, more_right, more_top, more_bottom = box
            dy = 170 - top if (top < 145 or bottom > 955) else 0
            if more_top:
                dy = 170 - (top - self.PITCH)
            elif more_bottom:
                dy = -(self.PITCH + 10)
            dx = 0
            touch_l, touch_r = left <= 12, right >= 708
            if more_right or (touch_r and not touch_l):
                # 往左拖，最多拖到左边贴边，看右边还有没有
                dx = -min(left - 3, self.PITCH + 10)
            elif more_left or (touch_l and not touch_r):
                dx = min(717 - right, self.PITCH + 10)
            if abs(dx) < 3 and abs(dy) < 3:
                break
            self.drag(int(np.clip(dx, -500, 500)), int(np.clip(dy, -600, 600)))
        box = self.board_box()
        if box is not None and not fits(box):
            logger.warning(f'石板放不进一屏: {box}')
        return box is not None and fits(box)

    def char_cell(self, char):
        """角色所在的格子（按火焰翅膀的重心，见 CHAR_DY）"""
        x0, y0 = self.origin
        return round((char[1] + self.CHAR_DY - y0) / self.PITCH), round((char[0] - x0) / self.PITCH)

    def grass_route(self, start, goal):
        """
        从 start 格走到 goal 格的路线（石板四周留 2 格），返回要点的格子列表。
        直接点远处的草地，角色会抄近路从石板上走过去，踩上漩涡还会被传走（11-05 第 6 关），所以尽量只走草地。
        只走草地走不到时（第 6 关中间有一块被石板围住的草地，角色站在那里出不去），踩最少的石板穿过去，
        不踩漩涡；踩过的石板会亮，但走回草地就全部熄灭，不影响后面重新走。
        """
        rows = [r for r, _ in self.kinds]
        cols = [c for _, c in self.kinds]
        r1, r2, c1, c2 = min(rows) - 2, max(rows) + 2, min(cols) - 2, max(cols) + 2
        # 草地一步代价 1，石板一步代价 100（能不踩就不踩）
        cost = {start: 0}
        prev = {start: None}
        heap = [(0, start)]
        while heap:
            d, u = heapq.heappop(heap)
            if u == goal:
                break
            if d > cost[u]:
                continue
            for dr, dc in self.DIRS.values():
                q = (u[0] + dr, u[1] + dc)
                if not (r1 <= q[0] <= r2 and c1 <= q[1] <= c2) or self.kinds.get(q) == 'swirl' or q == self.statue:
                    continue
                nd = d + (100 if q in self.kinds else 1)
                if nd < cost.get(q, 1e9):
                    cost[q] = nd
                    prev[q] = u
                    heapq.heappush(heap, (nd, q))
        if goal not in prev:
            return None
        cells = [goal]
        while prev[cells[-1]] is not None:
            cells.append(prev[cells[-1]])
        cells.reverse()
        crossed = [c for c in cells if c in self.kinds]
        if crossed:
            logger.info(f'只走草地出不去，从石板上穿过去: {crossed}')
        # 草地上只点拐弯的地方和终点（直线走在草地上不会踩到石板）；石板上和上石板前的那格一格一格点，免得角色自己找路
        out = []
        for i in range(1, len(cells)):
            if i == len(cells) - 1 or cells[i] in self.kinds or cells[i + 1] in self.kinds \
                    or cells[i - 1] in self.kinds:
                out.append(cells[i])
            else:
                d1 = (cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1])
                d2 = (cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
                if d1 != d2:
                    out.append(cells[i])
        return out

    def find_statue(self):
        """
        石板旁边草地上的菲涅克石像在哪一格。点到它会弹「供奉黄金甲虫帮你解惑」对话
        （11-05 石板谜题 1：开局角色站在石像旁边，去起点的第一下点在石像上）。看不到就沿用上次的
        """
        x1, y1, x2, y2 = self.SCAN
        r = cv2.matchTemplate(self.device.image[y1:y2, x1:x2], SHIBAN_STATUE.template, cv2.TM_CCOEFF_NORMED)
        _, sim, _, loc = cv2.minMaxLoc(r)
        if sim < 0.85:
            return self.statue
        h, w = SHIBAN_STATUE.template.shape[:2]
        x0, y0 = self.origin
        cx, cy = loc[0] + x1 + w // 2, loc[1] + y1 + h // 2
        self.statue = (round((cy - y0) / self.PITCH), round((cx - x0) / self.PITCH))
        return self.statue

    def cell_point(self, cell):
        x0, y0 = self.origin
        return int(x0 + cell[1] * self.PITCH), int(y0 + cell[0] * self.PITCH)

    def walk_grass(self, goal):
        """沿草地走到 goal 格。角色站在石板上时先走到旁边的草地"""
        self.relocate()
        char = character_position(self.device.image)
        for dy in (300, -600):
            if char is not None:
                break
            # 拖画面把石板上沿放到头像下面之后，站在石板上方草地的角色会被顶到屏幕最上面（y<120 不找）。上下拖一下再找
            logger.info('画面里找不到角色，拖一下画面再找')
            self.drag(0, dy)
            self.relocate(expect=(self.origin[0], self.origin[1] + dy))
            char = character_position(self.device.image)
        if char is None:
            logger.warning('找不到角色')
            return False
        # 角色站在石板上也一样按路线走：grass_route 会从石板上踩最少的格子下到草地（四周都是石板时也走得出去，
        # 比如第 6 关一轮作废时停在 (5,1)）
        start = self.char_cell(char)
        self.find_statue()
        route = self.grass_route(start, goal)
        if route is None:
            logger.warning(f'从 {start} 到 {goal} 找不到路')
            return False
        pos = start
        for cell in route:
            self.relocate()
            point = self.bring_into_view(self.cell_point(cell))
            if point is None:
                logger.warning(f'草地 {cell} 拖不进画面')
                return False
            char = character_position(self.device.image)
            if char is not None and abs(char[0] - point[0]) < 52 and abs(char[1] + self.CHAR_DY - point[1]) < 50:
                # 角色已经站在这格：按火焰翅膀估的格子会差一行，点下去会点到角色自己（11-05 开局第一下就点开了玩家信息）
                pos = cell
                continue
            if cell[0] < pos[0] and cell[1] == pos[1] and abs(cell[0] - pos[0]) == 1:
                # 往上走一格：点中间偏上，离角色的头远一点（同 tap_cell）
                point = (point[0], point[1] - 25)
            self.tap(point, 'SHIBAN_GRASS')
            time.sleep((abs(cell[0] - pos[0]) + abs(cell[1] - pos[1])) * self.PITCH / self.WALK_SPEED + 1.0)
            pos = cell
        return True

    def reset_far(self):
        """走到离石板最远的草地上（全部熄灭，角色也不挡花纹）"""
        # 离所有石板至少 2 格（角色约 140 像素高、火焰翅膀左右各 110，挨着石板会挡住花纹），选离角色最近的
        char = character_position(self.device.image)
        here = self.char_cell(char) if char else (0, 0)
        rows = [r for r, _ in self.kinds]
        cols = [c for _, c in self.kinds]
        best = None
        for r in range(min(rows) - 2, max(rows) + 3):
            for c in range(min(cols) - 2, max(cols) + 3):
                if min(max(abs(r - a), abs(c - b)) for a, b in self.kinds) < 2 or (r, c) == self.statue:
                    continue
                d = abs(r - here[0]) + abs(c - here[1])
                if best is None or d < best[0]:
                    best = (d, (r, c))
        if best is None:
            logger.warning('石板旁边找不到能站的草地')
            return False
        logger.info(f'到草地 {best[1]} 上重置')
        return self.walk_grass(best[1])

    def tap_cell(self, p, prev, retry=False):
        """
        点石板 p。认出的格子中心比石板图案中心高约 10 像素，游戏按图案判断点的是哪格（11-05 第 6 关：
        往上走点「中心上 40」，抖一下就过了图案上沿，角色走到了再上面一格）。
        - 往上走：点中心上 25（图案中心上 35）。角色脚在本格图案下沿，头只伸进上面一格下沿 25 像素，点中间以上碰不到头
        - 其余方向点图案中心
        - retry：上一次点了没动，多半是点到了跟在后面的幻兽（来回踩时幻兽正站在要去的那格上），点离角色远的那一边
        """
        point = self.bring_into_view(self.pos[p])
        if point is None:
            logger.warning(f'石板 {p} 拖不进画面')
            return False
        x, y = point
        dr, dc = (p[0] - prev[0], p[1] - prev[1]) if prev is not None else (0, 0)
        if dr == -1:
            point = (x + (30 if retry else 0), y - 25)
        elif retry:
            point = (x + dc * 28 + (30 if dr else 0), y + 10 + dr * 20)
        else:
            point = (x, y + 10)
        self.tap(point, f'SHIBAN_{p[0]}_{p[1]}')
        return True

    def char_near(self, cell):
        """角色是不是站在 cell 上（按刚认的石板位置和火焰翅膀的重心，见 CHAR_DY）。找不到角色返回 None"""
        char = character_position(self.device.image)
        if char is None:
            return None
        x, y = self.cell_point(cell)
        return abs(char[0] - x) < 46 and abs(char[1] + self.CHAR_DY - y) < 45

    def step(self, p, prev):
        """
        从 prev 走一步到 p，确认走到了；没走到（点到幻兽之类）就再点一次。
        Returns:
            bool: False 表示这一轮作废（点到了角色，或者认不出角色在哪）
        """
        for attempt in range(2):
            self.relocate(char_on=prev)
            if self.misclick:
                logger.warning(f'走到 {p} 之前发现点到了角色，这一轮作废')
                return False
            if not self.tap_cell(p, prev, retry=attempt > 0):
                return False
            time.sleep(self.STEP_WAIT)
            if self.kinds[p] == 'swirl' or prev is None:
                # 踩漩涡会传送走；第一步从草地上来，不用确认
                return True
            for _ in range(2):
                if self.relocate() and self.char_near(p):
                    return True
                time.sleep(0.8)
            # 认不出石板位置或角色时不敢再点（真走到了再点一次会多踩一下），这一轮作废
            if not self.relocate() or not self.char_near(prev):
                logger.warning(f'点了 {p}，看不出角色在 {p} 还是 {prev}，这一轮作废')
                return False
            logger.warning(f'点了 {p}，角色还在 {prev}，再点一次')
        return False

    def find_chest(self):
        """宝箱在石板中间附近。镜头被拖走时先把石板中间拖回画面再找"""
        timer = Timer(4).start()
        while not timer.reached():
            self.device.screenshot()
            if open_chest(self.main, (0, 130, 720, 990)):
                return True
            time.sleep(0.3)
        xs = [p[0] for p in self.pos.values()]
        ys = [p[1] for p in self.pos.values()]
        center = ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)
        if not self.safe(center) and self.bring_into_view(center):
            self.device.screenshot()
            return open_chest(self.main, (0, 130, 720, 990))
        return False

    def run(self):
        self.device.screenshot()
        if open_chest(self.main, (0, 130, 720, 990)):
            return True
        if not self.pan():
            logger.warning('石板太大，一屏放不下（或者认不出），不会解')
            return False
        self.device.screenshot()
        if open_chest(self.main, (0, 130, 720, 990)):
            return True
        cells = self.read_board(self.device.image)
        kinds, unknown = self.classify(self.device.image, cells)
        if unknown or self.lit_count(self.device.image, cells):
            # 上次走了一半（亮着的石板认不出来），或者角色站在石板上、旁边挡住了花纹：
            # 先沿草地走到离石板最远的地方，全部熄灭，再认（11-05 第 5、6 关都遇到过）
            logger.info(f'石板上有亮的或认不出的 {unknown}，先到草地上重置')
            # 认不出的也先按最像的算：重置时 grass_route 要靠它绕开漩涡
            self.kinds = dict(kinds)
            self.pos = dict(cells)
            r0, c0 = next(iter(cells))
            self.origin = (cells[(r0, c0)][0] - c0 * self.PITCH, cells[(r0, c0)][1] - r0 * self.PITCH)
            if not self.reset_far():
                return False
            if not self.pan():
                return False
            # 踩回草地后石板是慢慢熄灭的，没灭完就认，花纹对不上（11-05 第 4 关重玩时有 3 块认不出）。等全灭
            timer = Timer(4).start()
            while 1:
                self.device.screenshot()
                cells = self.read_board(self.device.image)
                if not self.lit_count(self.device.image, cells) or timer.reached():
                    break
                time.sleep(0.5)
        if len(cells) < 3:
            logger.warning(f'认不出石板: {cells}')
            return False
        kinds, unknown = self.classify(self.device.image, cells)
        if unknown:
            # 再看一次（角色、幻兽刚走开，或者熄灭动画还没完）
            time.sleep(1.5)
            self.device.screenshot()
            cells = self.read_board(self.device.image)
            kinds, unknown = self.classify(self.device.image, cells)
        logger.info(f'石板 {len(cells)} 块: {kinds}')
        if unknown:
            logger.warning(f'有认不出的石板: {unknown}')
            return False
        path = self.solve(kinds, timeout=60)
        if path is None:
            logger.warning('按已知规则找不到一笔走完的路线')
            return False
        logger.info(f'路线: {[p for p, _ in path]}')
        self.kinds = kinds
        self.pos = dict(cells)
        r0, c0 = next(iter(cells))
        self.origin = (cells[(r0, c0)][0] - c0 * self.PITCH, cells[(r0, c0)][1] - r0 * self.PITCH)
        start = path[0][0]
        outside = [(start[0] + dr, start[1] + dc) for dr, dc in self.DIRS.values()
                   if (start[0] + dr, start[1] + dc) not in kinds]
        for rnd in range(3):
            # 先沿草地走到起点外侧，石板全部熄灭
            self.misclick = False
            for cell in outside:
                if self.walk_grass(cell):
                    break
            else:
                logger.warning(f'走不到起点 {start} 外侧的草地')
                return False
            if self.misclick:
                logger.warning('去起点的路上点到了角色，重新走')
                continue
            prev = None
            for p, need_tap in path:
                if not need_tap:
                    # 漩涡传送，镜头会跟着跳过去
                    logger.info(f'传送到 {p}')
                    time.sleep(2.5)
                    prev = p
                    continue
                if not self.step(p, prev):
                    break
                prev = p
            if self.find_chest():
                return True
            logger.warning(f'走完没出现宝箱（第 {rnd + 1} 轮），回草地重走')
        return False


class FenekPuzzle(DailyReward):
    def grey_floor(self):
        hsv = cv2.cvtColor(self.device.image[150:500, 100:620], cv2.COLOR_RGB2HSV)
        return float(((hsv[..., 1] < 40) & (hsv[..., 2] > 170)).mean())

    def detect_game(self, timeout=10):
        """进关后认是哪种小游戏；也可能已经是「解谜成功」页"""
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(FENEK_CHECK, offset=(10, 10)):
                # 还在关卡列表（刚点进关，画面没切过去）
                if timer.reached():
                    return None
                time.sleep(0.5)
                continue
            if self.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                return 'success'
            if self.appear(YUANSU_CHECK, offset=(10, 30)):
                return 'yuansu'
            if SHIBAN_SCENE.match_region(self.device.image, (0, 150, 720, 800), similarity=0.75) > 0.75:
                # 石板谜题场景里也有石像，但石像模板是在灰色石地上截的，草地上只有 0.83 左右，按树林认（0.88 以上，别处 0.35 以下）
                return 'shiban'
            if YINFU_STATUE.match_region(self.device.image, (480, 430, 720, 780), similarity=0.85) > 0.85 \
                    and self.grey_floor() > 0.5:
                # 音符晶灯是大片浅灰石地（0.80~0.90），石板谜题是草地（0.02）
                return 'yinfu'
            if self.panned_shiban():
                return 'shiban'
            if timer.reached():
                return None
            time.sleep(0.5)

    def panned_shiban(self):
        """拖过画面的石板谜题：看不到树林了，但左下有「<」、草地上有一片石板"""
        # 关卡列表的关卡图标也是灰色方块，先排除列表和活动汇总（11-05 刚点进关时还是列表画面，误认过一次）
        if self.appear(FENEK_CHECK, offset=(10, 10)) or self.appear(EVENT_CHECK, offset=(10, 10)):
            return False
        return self.appear(BACK_ARROW, offset=(20, 20)) and len(ShibanSolver.read_board(self.device.image)) >= 6

    def enter_current_level(self):
        """关卡列表里找红点，点它左下的关卡图标。没有红点说明全打完了"""
        for _ in range(2):
            self.device.screenshot()
            if REWARD_BADGE.match_region(self.device.image, LIST_REGION, similarity=0.7) > 0.7:
                x1, y1, x2, y2 = area_offset(REWARD_BADGE.area, REWARD_BADGE._offset)
                x, y = (x1 + x2) // 2 + LEVEL_FROM_DOT[0], (y1 + y2) // 2 + LEVEL_FROM_DOT[1]
                logger.info(f'当前关卡在 ({x}, {y})')
                self.device.click(ClickArea('FENEK_LEVEL', (x - 15, y - 15, x + 15, y + 15)))
                return True
            # 列表一般会自己滚到当前关，没看到就等一下动画再看
            time.sleep(1.5)
        return False

    def solve_level(self):
        game = self.detect_game()
        logger.attr('FenekGame', game)
        if game == 'success':
            return True
        if game == 'yinfu':
            return YinfuSolver(self).run()
        if game == 'yuansu':
            return YuansuSolver(self).run()
        if game == 'shiban':
            return ShibanSolver(self).run()
        raise TaskNotImplemented('菲涅克的谜题：认不出这一关的玩法')

    def leave_level(self, timeout=120):
        """
        超时放宽到 120 秒：网络不好时退出关卡会一直「加载中」一分多钟（11-05 两次，用户说是网络卡）。
        关卡里左下「<」回关卡列表。路上开着玩家信息面板（点到了角色）就按返回键关掉。
        不用通用的「点上方空白处」：场景里那是空地，角色会走过去，第二下就点到角色自己（11-05 实测）
        """
        # 加载慢时一直是同一个画面，把卡死判定放宽（同登录），超时由本函数自己管
        self.device.long_wait(True)
        try:
            timer = Timer(timeout).start()
            while 1:
                self.device.screenshot()
                if self.appear(FENEK_CHECK, offset=(10, 10)):
                    return True
                if self.ui_page_appear(page_home):
                    # 关卡中途退出（确认框点「确定」）会直接回家园，不回列表
                    return True
                if timer.reached():
                    logger.warning(f'{timeout} 秒没回到关卡列表')
                    return False
                if self.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                    # 最后一关的成功页只有居中的「退出」（11-05 石板谜题 6）
                    exit_button = PUZZLE_EXIT_ONLY if self.appear(PUZZLE_EXIT_ONLY, offset=(10, 10)) else PUZZLE_EXIT
                    self.click_until(exit_button, self.gone(PUZZLE_SUCCESS, offset=(10, 10)), handle_popups=False)
                    continue
                if self.appear(STATUE_LEAVE, offset=(20, 20), interval=2):
                    # 误点石像的「供奉黄金甲虫」对话：只点「离开」
                    self.device.click(STATUE_LEAVE)
                    continue
                if self.appear(LEAVE_CONFIRM, offset=(20, 20), interval=2):
                    # 「是否退出当前活动关卡」：退出，本关进度不保留
                    self.device.click(LEAVE_CONFIRM_OK)
                    continue
                if self.appear(BACK_ARROW, offset=(20, 20), interval=3):
                    self.device.click(BACK_ARROW)
                    continue
                if self.appear(PLAYER_INFO, offset=(20, 20), interval=3) or self.appear(PET_INFO, offset=(20, 20), interval=3):
                    logger.info('关掉玩家信息面板')
                    self.device.back()
                    continue
                time.sleep(0.5)
        finally:
            self.device.long_wait(False)

    def locate(self, timeout=15):
        """
        认出现在在活动的哪一步：'level'（关卡里或「解谜成功」页）/ 'list' / 'event' / 'home'。
        认不出就当成在关卡里（重启后游戏会直接回到上次的关卡），只按左下「<」往外退
        """
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(FENEK_CHECK, offset=(10, 10)):
                return 'list'
            if self.appear(EVENT_CHECK, offset=(10, 10)):
                return 'event'
            if self.ui_page_appear(page_home):
                return 'home'
            if self.appear(PUZZLE_SUCCESS, offset=(10, 10)) or self.appear(YUANSU_CHECK, offset=(10, 30)) \
                    or YINFU_STATUE.match_region(self.device.image, (480, 430, 720, 780), similarity=0.85) > 0.85 \
                    or SHIBAN_SCENE.match_region(self.device.image, (0, 150, 720, 800), similarity=0.75) > 0.75 \
                    or self.panned_shiban():
                return 'level'
            if self.appear(PLAYER_INFO, offset=(20, 20), interval=3) or self.appear(PET_INFO, offset=(20, 20), interval=3):
                logger.info('关掉玩家信息面板')
                self.device.back()
                continue
            if self.appear(STATUE_LEAVE, offset=(20, 20), interval=3):
                self.device.click(STATUE_LEAVE)
                continue
            if timer.reached():
                return None
            time.sleep(0.5)

    def goto_list(self):
        """
        不管从哪里开始，走到关卡列表，返回 'list'；已经在关卡里返回 'level'（直接接着打，不退出：
        11-05 从石板谜题退出两次卡在「加载中」一分多钟）。返回 None 表示活动汇总里没有这个活动
        """
        where = self.locate()
        logger.attr('FenekLocate', where)
        if where == 'level':
            return 'level'
        if where is None:
            # 认不出就按「<」往外退
            if self.leave_level():
                return 'list'
            raise GamePageUnknownError
        if where == 'list':
            return 'list'
        if where == 'home':
            if not self.ui_click(EVENT_ENTRY, check_button=EVENT_CHECK, offset=(10, 10), retry_wait=3, timeout=15):
                raise GamePageUnknownError
        if self.open_event_card(EVENT_FENEK, FENEK_CHECK, need_dot=False):
            return 'list'
        # open_event_card 在「找到卡片但点进去没反应」时也返回 False：卡片还在就是进不去，不能当成活动结束（会白丢一天）
        self.device.screenshot()
        if self.appear(FENEK_CHECK, offset=(10, 10)):
            return 'list'
        if self.find(EVENT_FENEK, EVENT_LIST_REGION, similarity=0.8):
            raise GamePageUnknownError('活动汇总里有菲涅克的谜题，但点不进去')
        return None

    def play_levels(self, enter=True):
        """从关卡列表进当前关（enter=False 时已经在关卡里），一关接一关打。返回解开的关数，没解开返回 None"""
        if enter:
            time.sleep(1.5)
            if not self.enter_current_level():
                logger.info('关卡列表里没有红点，全部打完了')
                return 0
        solved = 0
        for _ in range(MAX_LEVELS):
            if not self.solve_level():
                logger.warning('这一关没解开')
                return None
            solved += 1
            # 「解谜成功」页：有「继续下一关」就接着打，没有就退出
            self.wait_until_appear(PUZZLE_SUCCESS, offset=(10, 10), timeout=5)
            time.sleep(1)
            self.device.screenshot()
            if self.appear(PUZZLE_NEXT, offset=(10, 10)):
                self.click_until(PUZZLE_NEXT, self.gone(PUZZLE_SUCCESS, offset=(10, 10)), handle_popups=False)
                time.sleep(2)
                continue
            logger.info('没有「继续下一关」，退出')
            break
        return solved

    def run(self):
        logger.hr('Fenek puzzle', level=1)
        where = self.goto_list()
        if where is None:
            logger.info('活动汇总里没有菲涅克的谜题（活动可能已结束）')
            self.back_home()
            return True
        try:
            solved = self.play_levels(enter=where == 'list')
        except (GameStuckError, GameTooManyClickError, GamePageUnknownError, TaskNotImplemented):
            # 游戏还在、只是卡住或认不出时，先自己退回列表：框架的恢复会「点上方空白处」，在场景里会点到角色。
            # 游戏没了（GameNotRunningError）、要停机（ScriptError / RequestHumanTakeover）就直接抛，不在这里空转。
            # 退的时候再出错只记一下，抛原来的异常
            try:
                self.leave_level()
            except Exception as e:
                logger.warning(f'出错后退出关卡也失败: {type(e).__name__} {e}')
            raise
        self.leave_level()
        self.back_home()
        if solved is None:
            return False
        logger.info(f'菲涅克的谜题：本次解开 {solved} 关')
        return True
