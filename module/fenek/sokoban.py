"""
菲涅克的谜题第二期 · 推箱子（11-27 实测，知识库 12 篇第 8 节）。

沙地上一片岩块围出的场地，几个木箱、几个「X」目标，把箱子都推到目标上（箱子发光），场景里出现宝箱，点开弹「解谜成功」。
- 点地面：角色自己找路走过去（绕开箱子）。点紧挨着的箱子：往「角色→箱子」的方向推一格。
- 点不挨着的箱子，角色会走到箱子旁边从那一侧推（11-27 实测把箱子推反了），所以一定要等角色走到推的位置再点箱子。
- 格距 103。墙、箱子是立体画的，图往上冒：按「底边」算格子，格子中心 = 底边 - 51。下一行的墙 / 箱子会盖住上一行的下半截。
- 开局场地上沿在头像后面：在沙地上慢拖画面往下。
"""
import time
from collections import deque

import cv2

from module.base.timer import Timer
from module.fenek.assets import SOKO_BOX, SOKO_BOX_ON, SOKO_TARGET, SOKO_WALL, YINFU_CHEST, PUZZLE_SUCCESS
from module.logger import logger

GRID = 103
DIRS = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}
# 模板左上角 -> 所在格子中心（墙模板从岩块顶面下 10 像素截；目标模板在「X」上沿；箱子模板在箱子顶下 9 像素）
WALL_TO_CENTER = (41, 71)
TARGET_TO_CENTER = (38, 37)
BOX_TO_CENTER = (42, 65)
SCENE = (0, 130, 720, 1000)  # 头像下面、聊天框上面
CHEST_REGION = (0, 130, 720, 1050)  # 宝箱出在场地下面一格，拖两次画面后在 y≈1000（11-27）


def peaks(image, template, threshold, gap=40):
    res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    out = []
    while True:
        _, sim, _, (x, y) = cv2.minMaxLoc(res)
        if sim < threshold:
            return out
        out.append((x, y, sim))
        res[max(0, y - gap):y + gap, max(0, x - gap):x + gap] = -1


class SokobanSolver:
    def __init__(self, main):
        self.main = main
        self.device = main.device
        self.known_targets = None  # 第一次认到的目标位置（箱子推上去会盖住「X」，之后就看不到了）

    # ---------- 识别 ----------
    @staticmethod
    def box_score(image, center):
        """格子上是不是箱子（发不发光都算）。箱子中间会出现推动方向的箭头，只比左右两条边"""
        cx, cy = center
        x1, y1 = cx - 42 - 12, cy - 65 - 12
        roi = image[max(0, y1):y1 + 80 + 24, max(0, x1):x1 + 85 + 24]
        best = 0
        for t in (SOKO_BOX.template, SOKO_BOX_ON.template):
            if roi.shape[0] < t.shape[0] or roi.shape[1] < t.shape[1]:
                continue
            sc = [cv2.minMaxLoc(cv2.matchTemplate(roi, part, cv2.TM_CCOEFF_NORMED))[1] for part in (t[:, :26], t[:, -26:])]
            best = max(best, sum(sc) / 2)
        return best

    def read_board(self, image):
        """
        返回 (origin, walls, boxes, targets, size)：origin 是格子 (0,0) 的中心；坐标都是 (行, 列)，按墙的外框从 0 开始。
        认不出返回 None
        """
        img = image.copy()
        img[:SCENE[1]] = 0
        img[SCENE[3]:] = 0
        walls = peaks(img, SOKO_WALL.template, 0.8)
        if len(walls) < 6:
            return None
        # 墙的相位：以分数最高的那块墙为准（取中位数时，相位跨 0/102 边界会落到中间，筛不出墙）
        xs = [x + WALL_TO_CENTER[0] for x, _, _ in walls]
        ys = [y + WALL_TO_CENTER[1] for _, y, _ in walls]
        px, py = xs[0] % GRID, ys[0] % GRID  # peaks 按分数从高到低返回
        x0 = min(x for x in xs if abs((x - px + 51) % GRID - 51) < 15)
        y0 = min(y for y in ys if abs((y - py + 51) % GRID - 51) < 15)
        # 高阈值只用来定相位；目标旁边的墙会被「X」的光照亮，分数掉到 0.6（11-27 推箱子 2），逐格按 0.5 判（地面最高 0.31）
        res = cv2.matchTemplate(img, SOKO_WALL.template, cv2.TM_CCOEFF_NORMED)
        seed = {(round((y - y0) / GRID), round((x - x0) / GRID)) for x, y in zip(xs, ys)}
        rs = [r for r, _ in seed]
        cs = [c for _, c in seed]
        cells = set()
        for r in range(min(rs) - 1, max(rs) + 2):
            for c in range(min(cs) - 1, max(cs) + 2):
                tx, ty = x0 + c * GRID - WALL_TO_CENTER[0], y0 + r * GRID - WALL_TO_CENTER[1]
                if tx < -6 or ty < SCENE[1] - 6 or tx + 6 >= res.shape[1] or ty + 6 >= res.shape[0]:
                    continue
                if res[max(0, ty - 6):ty + 7, max(0, tx - 6):tx + 7].max() > 0.5:
                    cells.add((r, c))
        r0 = min(r for r, _ in cells)
        c0 = min(c for _, c in cells)
        cells = {(r - r0, c - c0) for r, c in cells}
        x0, y0 = x0 + c0 * GRID, y0 + r0 * GRID
        rows = max(r for r, _ in cells) + 1
        cols = max(c for _, c in cells) + 1
        origin = (x0, y0)
        targets = set()
        for x, y, _ in peaks(img, SOKO_TARGET.template, 0.8):
            cx, cy = x + TARGET_TO_CENTER[0], y + TARGET_TO_CENTER[1]
            targets.add((round((cy - y0) / GRID), round((cx - x0) / GRID)))
        boxes = set()
        for r in range(rows):
            for c in range(cols):
                if (r, c) in cells:
                    continue
                if self.box_score(image, self.center(origin, (r, c))) > 0.6:
                    boxes.add((r, c))
        return origin, cells, boxes, targets, (rows, cols)

    @staticmethod
    def center(origin, cell):
        return int(origin[0] + cell[1] * GRID), int(origin[1] + cell[0] * GRID)

    # ---------- 求解 ----------
    @staticmethod
    def solve(rows, cols, walls, boxes, targets, player, nobox, timeout=30):
        """BFS 推箱子（按推的次数最少），状态 = 箱子位置 + 角色能走到的最小格。返回 [(箱子格, 方向), ...]"""

        def inside(p):
            return 0 <= p[0] < rows and 0 <= p[1] < cols

        def reach(bx, p):
            seen = {p}
            q = deque([p])
            while q:
                a = q.popleft()
                for d in DIRS.values():
                    n = (a[0] + d[0], a[1] + d[1])
                    if inside(n) and n not in walls and n not in bx and n not in seen:
                        seen.add(n)
                        q.append(n)
            return seen

        def dead(p):
            # 不是目标、又卡在墙角（上下有一面墙且左右有一面墙）的格子，箱子推进去就出不来
            if p in targets:
                return False

            def wl(q):
                return q in walls or not inside(q)
            return (wl((p[0] - 1, p[1])) or wl((p[0] + 1, p[1]))) and (wl((p[0], p[1] - 1)) or wl((p[0], p[1] + 1)))

        start = frozenset(boxes)
        key0 = (start, min(reach(start, player)))
        prev = {key0: None}
        q = deque([(start, player)])
        timer = Timer(timeout).start()
        while q:
            if timer.reached():
                logger.warning('推箱子求解超时')
                return None
            bx, p = q.popleft()
            rs = reach(bx, p)
            key = (bx, min(rs))
            if bx <= targets:
                path = []
                while prev[key]:
                    key, mv = prev[key]
                    path.append(mv)
                return path[::-1]
            for b in bx:
                for name, d in DIRS.items():
                    stand = (b[0] - d[0], b[1] - d[1])
                    to = (b[0] + d[0], b[1] + d[1])
                    if stand not in rs or not inside(to) or to in walls or to in bx or to in nobox or dead(to):
                        continue
                    nb = frozenset(bx - {b} | {to})
                    nk = (nb, min(reach(nb, b)))
                    if nk in prev:
                        continue
                    prev[nk] = (key, (b, name))
                    q.append((nb, b))
        return None

    # ---------- 操作 ----------
    def tap(self, point, name):
        from module.fenek.fenek import tap_point
        tap_point(self.device, point, name)

    def pan(self):
        """在沙地上慢拖画面往下，让场地上沿离开头像（拖 300 像素上沿还在 y≈35，再拖 150）"""
        for dy in (300, 150):
            self.device.swipe((620, 700), (620, 700 + dy), duration=1500, name='SOKO_PAN')
            time.sleep(0.8)

    def player_cell(self, origin, rows, cols, walls, image):
        from module.fenek.fenek import character_position
        pos = character_position(image)
        if pos is None:
            return None
        # 火焰翅膀的重心大约在角色所站格子中心上方 15 像素
        r = round((pos[1] + 15 - origin[1]) / GRID)
        c = round((pos[0] - origin[0]) / GRID)
        return r, c

    def close_info(self):
        """点到角色 / 幻兽弹出的玩家信息、幻兽详情：按返回键关掉（只查看，不点里面的按钮）"""
        from module.fenek.assets import PET_INFO, PLAYER_INFO
        for _ in range(3):
            self.device.screenshot()
            if self.main.appear(PLAYER_INFO, offset=(20, 20)) or self.main.appear(PET_INFO, offset=(20, 20)):
                logger.info('关掉玩家信息面板')
                self.device.back()
                time.sleep(1)
                continue
            return

    def pathlen(self, rows, cols, walls, bx, a, z):
        seen = {a: 0}
        q = deque([a])
        while q:
            p = q.popleft()
            if p == z:
                return seen[p]
            for d in DIRS.values():
                n = (p[0] + d[0], p[1] + d[1])
                if 0 <= n[0] < rows and 0 <= n[1] < cols and n not in walls and n not in bx and n not in seen:
                    seen[n] = seen[p] + 1
                    q.append(n)
        return 15

    def attempt(self):
        """认一次、解一次、推一遍。返回 True 推完了，False 中途出错（需要重新认）"""
        self.device.screenshot()
        board = self.read_board(self.device.image)
        if board is None:
            logger.warning('认不出推箱子场地')
            return False
        origin, walls, boxes, targets, (rows, cols) = board
        # 场地下面的沙地也能走（角色开局站在那里），但不往那里推箱子。至少留一行：拖两次画面后场地下沿在 y≈930，
        # 按屏幕算一行都放不下，角色又在聊天框后面认不到，不留就没有能当起点的格子
        extra = max(1, int((SCENE[3] - 60 - origin[1]) // GRID) - rows + 1)
        nobox = {(r, c) for r in range(rows, rows + extra) for c in range(cols)}
        rows += extra
        player = self.player_cell(origin, rows, cols, walls, self.device.image)
        if player is None or player in walls or player in boxes or not (0 <= player[0] < rows and 0 <= player[1] < cols):
            player = (rows - 1, cols // 2)
        logger.info(f'推箱子 {rows}×{cols}，墙 {len(walls)}，箱子 {sorted(boxes)}，目标 {sorted(targets)}，角色 {player}')
        if targets and len(targets) == len(boxes) and self.known_targets is None:
            self.known_targets = set(targets)
        if self.known_targets and boxes == self.known_targets:
            # 箱子在目标上会盖住「X」（发光和不发光的箱子模板分不开），按第一次认到的目标位置判断推完了没有
            logger.info('箱子都在目标上了')
            return True
        if self.known_targets:
            # 同一次进关的重试：推上目标的箱子盖住了「X」，按第一次认到的目标求解
            targets = set(self.known_targets)
        if len(boxes) != len(targets) or not boxes:
            logger.warning('箱子和目标数量对不上')
            return False
        sol = self.solve(rows, cols, walls, boxes, targets, player, nobox)
        if sol is None:
            logger.warning('推箱子无解')
            return False
        logger.info(f'推 {len(sol)} 次: {sol}')
        pos = player
        cur = set(boxes)
        for b, name in sol:
            d = DIRS[name]
            stand = (b[0] - d[0], b[1] - d[1])
            to = (b[0] + d[0], b[1] + d[1])
            ok = False
            for retry in range(3):
                # 第一次没推动先只重点箱子：角色多半已经站在站位格上，再点站位格就点到角色自己，弹出玩家信息（11-27 重玩推箱子 4）
                if (stand != pos and retry == 0) or retry == 2:
                    dist = self.pathlen(rows, cols, walls, cur, pos, stand)
                    self.tap(self.center(origin, stand), 'SOKO_WALK')
                    time.sleep(1.0 + dist * 0.5)
                self.close_info()
                # 点之前确认箱子真在这一格：判错一步以后点到的是空格，角色走过去，下一下就点到角色自己（11-27 重玩推箱子 3）
                self.device.screenshot()
                if self.box_score(self.device.image, self.center(origin, b)) < 0.56:
                    time.sleep(1)
                    self.device.screenshot()
                    if self.box_score(self.device.image, self.center(origin, b)) < 0.56:
                        logger.warning(f'箱子不在 {b}，重新认')
                        return False
                # 往上推时角色的头伸进箱子那格的下沿：点箱子偏上 25 像素（第一期石板谜题的经验，知识库 12 篇 4.2）
                bx, by = self.center(origin, b)
                self.tap((bx, by - 25 if name == 'U' else by), 'SOKO_PUSH')
                timer = Timer(4).start()
                hits = 0
                while not timer.reached():
                    time.sleep(0.4)
                    self.device.screenshot()
                    image = self.device.image
                    if self.box_score(image, self.center(origin, to)) > 0.6 and self.box_score(image, self.center(origin, b)) < 0.56:
                        # 箱子滑动途中也可能过线：连着两次都到位才算，再等滑动结束，不然下一下会被游戏吞掉
                        hits += 1
                        if hits >= 2:
                            ok = True
                            time.sleep(0.5)
                            break
                    else:
                        hits = 0
                if ok:
                    break
                if self.box_score(self.device.image, self.center(origin, b)) < 0.56:
                    # 角色推完站在原格，火焰翅膀可能盖住目标格：等它站定再看一次
                    time.sleep(1.5)
                    self.device.screenshot()
                    image = self.device.image
                    if self.box_score(image, self.center(origin, to)) > 0.55:
                        ok = True
                        break
                    logger.warning(f'箱子 {b} 不在原位也不在 {to}，重新认')
                    return False
                logger.info(f'箱子 {b} 没推动，再推一次（第 {retry + 2} 次，第 3 次会重新走到 {stand}）')
            if not ok:
                return False
            pos = b
            cur.discard(b)
            cur.add(to)
        return True

    def find_chest(self, timeout=6):
        timer = Timer(timeout).start()
        while not timer.reached():
            self.device.screenshot()
            if self.main.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                return True
            from module.fenek.fenek import open_chest
            if open_chest(self.main, CHEST_REGION):
                return True
            time.sleep(0.5)
        return False

    def run(self):
        self.pan()
        for _ in range(3):
            if self.attempt():
                if self.find_chest():
                    return True
                logger.warning('推完没出宝箱，重新认')
            time.sleep(1)
            self.device.screenshot()
            if self.main.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                return True
        return False
