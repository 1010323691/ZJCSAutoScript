"""
菲涅克的谜题第二期 · 能量回路（11-27 实测，知识库 12 篇第 9 节）。

几块方形石板摆成一个形状，每块石板上有通到边上的槽（有的带菱形节点）。点一块再点另一块（或拖过去）交换两块的位置，
所有槽都对上、连成一片时线路全亮，直接弹「解谜成功」（没有宝箱）。石板不能转，只能换位置。
求解：每块石板的「槽通到哪几条边」= 它的种类；找一个排列，让每条边上的槽都和邻居对上、外圈没有伸出去的槽、整片连通。
"""
import time

import cv2
import numpy as np

from module.fenek.assets import PUZZLE_SUCCESS
from module.logger import logger

PITCH = 115
SIDES = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}
OPP = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}


def name(edges):
    return ''.join(x for x in 'ULDR' if x in edges) or '-'


class CircuitSolver:
    def __init__(self, main):
        self.main = main
        self.device = main.device

    @staticmethod
    def read(image):
        """返回 {(行, 列): (槽通到的边, 石板中心)}。image 是 RGB"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # 背景是饱和的深绿；石板（浅灰绿）、槽（暗灰）、点亮的青线都不是背景。腐蚀掉石板之间 7 像素的缝
        bg = (hsv[..., 0] > 35) & (hsv[..., 0] < 60) & (hsv[..., 1] > 70) & (hsv[..., 2] < 110)
        mask = (~bg).astype(np.uint8)
        mask = cv2.erode(mask, np.ones((9, 9), np.uint8))
        # 先腐蚀再切掉上下（先切的话靠近 y=420 的石板会被削掉一截，中心算偏，11-27 能量回路 5 有一条边认丢了）
        mask[:420] = 0
        mask[1100:] = 0
        n, _, st, _ = cv2.connectedComponentsWithStats(mask, 8)
        boxes = [st[i] for i in range(1, n) if 80 < st[i][2] < 115 and 80 < st[i][3] < 115]
        if not boxes:
            return {}
        x0 = min(b[0] + b[2] / 2 for b in boxes)
        y0 = min(b[1] + b[3] / 2 for b in boxes)
        tiles = {}
        for b in boxes:
            cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
            edges = set()
            for s, (dr, dc) in SIDES.items():
                # 边的中点往里 6 像素：槽是暗灰（亮度 < 115），点亮的是青色
                px, py = int(cx + dc * 48), int(cy + dr * 48)
                patch = image[py - 3:py + 4, px - 3:px + 4].reshape(-1, 3).astype(int)
                dark = patch.max(1).mean() < 115
                cyan = ((patch[:, 2] > 180) & (patch[:, 0] < 170)).mean() > 0.3
                if dark or cyan:
                    edges.add(s)
            tiles[(round((cy - y0) / PITCH), round((cx - x0) / PITCH))] = (frozenset(edges), (int(cx), int(cy)))
        return tiles

    @staticmethod
    def solve(tiles):
        slots = sorted(tiles)
        kinds = [tiles[s][0] for s in slots]
        sset = set(slots)
        assign = {}
        used = [False] * len(kinds)
        found = []

        def ok(slot, e):
            for s, (dr, dc) in SIDES.items():
                nb = (slot[0] + dr, slot[1] + dc)
                if nb not in sset:
                    if s in e:
                        return False
                elif nb in assign and (s in e) != (OPP[s] in kinds[assign[nb]]):
                    return False
            return True

        def connected():
            start = next(iter(assign))
            seen = {start}
            stack = [start]
            while stack:
                p = stack.pop()
                for s in kinds[assign[p]]:
                    dr, dc = SIDES[s]
                    nb = (p[0] + dr, p[1] + dc)
                    if nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            return len(seen) == len(assign)

        def rec(i):
            if found:
                return
            if i == len(slots):
                if connected():
                    found.append(dict(assign))
                return
            tried = set()
            for k in range(len(kinds)):
                if used[k] or kinds[k] in tried:
                    continue
                tried.add(kinds[k])
                if ok(slots[i], kinds[k]):
                    used[k] = True
                    assign[slots[i]] = k
                    rec(i + 1)
                    used[k] = False
                    del assign[slots[i]]

        rec(0)
        if not found:
            return None
        want = {s: kinds[k] for s, k in found[0].items()}
        cur = {s: kinds[i] for i, s in enumerate(slots)}
        swaps = []
        for s in slots:
            if cur[s] == want[s]:
                continue
            cand = [t for t in slots if t != s and cur[t] == want[s] and cur[t] != want[t]]
            cand.sort(key=lambda t: want[t] != cur[s])  # 能一次换对两块的优先
            t = cand[0]
            swaps.append((s, t))
            cur[s], cur[t] = cur[t], cur[s]
        return swaps

    def run(self):
        from module.fenek.fenek import tap_point
        for attempt in range(3):
            self.device.screenshot()
            if self.main.appear(PUZZLE_SUCCESS, offset=(10, 10)):
                return True
            tiles = self.read(self.device.image)
            logger.info(f'能量回路 {len(tiles)} 块: ' + ' '.join(f'{k}{name(v[0])}' for k, v in sorted(tiles.items())))
            if len(tiles) < 3:
                logger.warning('认不出石板')
                time.sleep(1)
                continue
            swaps = self.solve(tiles)
            if swaps is None:
                logger.warning('能量回路无解（可能有石板的槽认错了）')
                time.sleep(1)
                continue
            logger.info(f'交换: {swaps}')
            for a, b in swaps:
                tap_point(self.device, tiles[a][1], 'HUILU_SELECT')
                time.sleep(0.7)
                tap_point(self.device, tiles[b][1], 'HUILU_SWAP')
                time.sleep(1.2)
            if self.main.wait_until_appear(PUZZLE_SUCCESS, offset=(10, 10), timeout=6):
                return True
            logger.warning('换完没出现「解谜成功」，重新认')
        return False
