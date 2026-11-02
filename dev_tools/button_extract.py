"""
按 assets/<module>/define.yaml 从截图里裁出按钮模板，生成 module/<module>/assets.py。
对应 ALAS 的 dev_tools/button_extract.py，区别是区域写在 yaml 里，不用手工涂黑截图。

define.yaml 写法：
    PAGE_HOME_CHECK:            # 识别用按钮：从截图裁模板，记录平均色
      screen: page_home         # dev_tools/screens/page_home.png
      area: [x1, y1, x2, y2]
      button: [x1, y1, x2, y2]  # 可选，点击区域，默认等于 area
    NAV_HOME:                   # 只点击、不识别
      click: [x1, y1, x2, y2]

用法：
    .venv\\Scripts\\python.exe -m dev_tools.button_extract
"""
import os

import yaml

from module.base.utils import crop, get_color, load_image, save_image
from module.logger import ROOT, logger

ASSETS = os.path.join(ROOT, 'assets')
SCREENS = os.path.join(ROOT, 'dev_tools', 'screens')
HEADER = '# 本文件由 dev_tools/button_extract.py 生成，不要手改。改 assets/{module}/define.yaml 后重新生成。\n'


def extract_module(module):
    with open(os.path.join(ASSETS, module, 'define.yaml'), 'r', encoding='utf-8') as f:
        define = yaml.safe_load(f) or {}

    lines = [HEADER.format(module=module), 'from module.base.button import Button, ClickArea\n', '\n']
    screens = {}
    for name, item in define.items():
        if 'click' in item:
            lines.append(f'{name} = ClickArea(name={name!r}, button={tuple(item["click"])})\n')
            continue
        screen = item['screen']
        area = tuple(int(v) for v in item['area'])
        button = tuple(int(v) for v in item.get('button', area))
        file = f'./assets/{module}/{name}.png'
        if screen not in screens:
            path = os.path.join(SCREENS, f'{screen}.png')
            screens[screen] = load_image(path) if os.path.exists(path) else None
        image = screens[screen]
        if image is None:
            # 原图只在截它的那台电脑上（dev_tools/screens 不进仓库）：沿用已裁好的模板，平均色从模板算，结果一样
            template = load_image(os.path.join(ROOT, file))
            color = tuple(int(round(c)) for c in get_color(template, (0, 0, area[2] - area[0], area[3] - area[1])))
        else:
            color = tuple(int(round(c)) for c in get_color(image, area))
            save_image(crop(image, area), os.path.join(ROOT, file))
        lines.append(f'{name} = Button(name={name!r}, area={area}, color={color}, button={button}, file={file!r})\n')

    out = os.path.join(ROOT, 'module', module, 'assets.py')
    with open(out, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    logger.info(f'{module}: {len(define)} 个按钮 -> {out}')


if __name__ == '__main__':
    for module in sorted(os.listdir(ASSETS)):
        if os.path.exists(os.path.join(ASSETS, module, 'define.yaml')):
            extract_module(module)
