import os

import cv2

from module.base.utils import area_offset, color_similar, crop, get_color, load_image
from module.logger import ROOT


class Button:
    def __init__(self, name, area, color=None, button=None, file=None):
        """
        坐标都基于 720x1280 竖屏。

        Args:
            name (str): 按钮名，日志和点击记录用它区分按钮
            area (tuple): 识别区域 (x1, y1, x2, y2)
            color (tuple): 识别区域的平均颜色 (r, g, b)，用于快速颜色判断
            button (tuple): 点击区域，默认等于 area
            file (str): 模板图片路径（相对项目根目录），图片就是 area 的裁剪
        """
        self.name = name
        self.area = tuple(area)
        self.color = tuple(color) if color is not None else None
        self._button = tuple(button) if button is not None else self.area
        self.file = file
        self._template = None
        self._offset = (0, 0)

    @property
    def button(self):
        """点击区域。模板匹配成功后会跟着匹配位置偏移"""
        return area_offset(self._button, self._offset)

    @property
    def template(self):
        if self._template is None:
            if not self.file:
                raise ValueError(f'按钮 {self.name} 没有模板图片')
            self._template = load_image(os.path.join(ROOT, self.file))
        return self._template

    def appear_on(self, image, threshold=10):
        """颜色判断：识别区域平均色与记录的颜色接近"""
        return color_similar(get_color(image, self.area), self.color, threshold=threshold)

    def match(self, image, offset=30, similarity=0.85):
        """
        模板匹配：在识别区域向外扩 offset 的范围里找模板。

        Args:
            image (np.ndarray): 截图
            offset (int, tuple): 搜索范围向外扩多少像素，int 或 (x, y)
            similarity (float): 0~1，越大越严格
        """
        if isinstance(offset, int):
            offset = (offset, offset)
        ox, oy = offset
        search = (self.area[0] - ox, self.area[1] - oy, self.area[2] + ox, self.area[3] + oy)
        region = crop(image, search)
        template = self.template
        if region.shape[0] < template.shape[0] or region.shape[1] < template.shape[1]:
            return False
        res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        _, sim, _, point = cv2.minMaxLoc(res)
        left, top = max(search[0], 0), max(search[1], 0)
        self._offset = (point[0] + left - self.area[0], point[1] + top - self.area[1])
        return sim > similarity

    def match_region(self, image, region, similarity=0.85, scales=(1.0,)):
        """
        在指定的大范围 region 里找模板，用于位置不固定的东西（比如家园场景里的物件）。

        Args:
            scales: 模板缩放倍数，用于会一缩一放的动画物件（例如小推车气泡）

        Returns:
            float: 最高相似度；超过 similarity 时 self.button 会移到匹配位置
        """
        region = tuple(int(v) for v in region)
        image = crop(image, region)
        best_sim, best_point, best_scale = -1., (0, 0), 1.0
        h, w = self.template.shape[:2]
        for scale in scales:
            template = self.template if scale == 1.0 else \
                cv2.resize(self.template, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            _, sim, _, point = cv2.minMaxLoc(res)
            if sim > best_sim:
                best_sim, best_point, best_scale = sim, point, scale
        if best_sim > similarity:
            # 按匹配到的中心算偏移（缩放过的模板左上角会偏），点击区域和识别区域的相对位置保持不变
            cx = best_point[0] + region[0] + w * best_scale / 2
            cy = best_point[1] + region[1] + h * best_scale / 2
            self._offset = (int(cx - (self.area[0] + self.area[2]) / 2),
                            int(cy - (self.area[1] + self.area[3]) / 2))
        return best_sim

    def match_at(self, image, area, offset=3, similarity=0.9):
        """在另一个位置 area（± offset）找这个模板，用于同一种图标出现在多行的情况，不改变点击位置"""
        x1, y1, x2, y2 = area
        region = crop(image, (x1 - offset, y1 - offset, x2 + offset, y2 + offset))
        template = self.template
        if region.shape[0] < template.shape[0] or region.shape[1] < template.shape[1]:
            return False
        res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        return cv2.minMaxLoc(res)[1] > similarity

    def match_similarity(self, image, offset=30):
        """调试用：返回最高相似度"""
        if isinstance(offset, int):
            offset = (offset, offset)
        ox, oy = offset
        search = (self.area[0] - ox, self.area[1] - oy, self.area[2] + ox, self.area[3] + oy)
        region = crop(image, search)
        res = cv2.matchTemplate(region, self.template, cv2.TM_CCOEFF_NORMED)
        return cv2.minMaxLoc(res)[1]

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)


class ClickArea(Button):
    """只用来点击、不做识别的区域，比如底部导航按钮"""

    def __init__(self, name, button):
        super().__init__(name=name, area=button, button=button)

    def appear_on(self, image, threshold=10):
        raise ValueError(f'{self.name} 只是点击区域，不能用来识别')

    def match(self, image, offset=30, similarity=0.85):
        raise ValueError(f'{self.name} 只是点击区域，不能用来识别')
