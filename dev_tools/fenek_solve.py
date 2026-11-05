"""
菲涅克的谜题：只解当前打开的这一关（不导航、不点「继续下一关」），调识别和解法用。
打完的关可以重玩，先在游戏里手动点进要测的关，再运行：

    .venv\\Scripts\\python.exe -m dev_tools.fenek_solve
"""
from module.config.config import ZjcsConfig
from module.fenek.fenek import FenekPuzzle
from module.logger import logger

if __name__ == '__main__':
    main = FenekPuzzle(ZjcsConfig())
    ok = main.solve_level()
    logger.info(f'结果: {"解开了" if ok else "没解开"}')
