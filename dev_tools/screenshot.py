"""
截一张全分辨率（720x1280）截图，存到 dev_tools/screens/<name>.png，做素材用。
只截图，不点击。

用法：
    .venv\\Scripts\\python.exe -m dev_tools.screenshot page_home
"""
import os
import sys

from module.base.utils import save_image
from module.config.config import ZjcsConfig
from module.device.screenshot import Screenshot
from module.logger import ROOT, logger

if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'screen'
    config = ZjcsConfig()
    image = Screenshot(config).screenshot()
    file = os.path.join(ROOT, 'dev_tools', 'screens', f'{name}.png')
    save_image(image, file)
    logger.info(f'已保存 {file}')
