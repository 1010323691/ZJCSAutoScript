import math
import time

import numpy as np

from module.base.base import ModuleBase
from module.base.timer import Timer
from module.base.utils import crop
from module.exception import GamePageUnknownError
from module.logger import logger
from module.ui.assets import POPUP_OUTSIDE
from module.ui.page import Page, page_guild, page_home, page_note, page_role, page_world

# 「获得奖励」横幅的位置随物品多少上下变化
REWARD_OFFSET = (20, 60)


class UI(ModuleBase):
    def ui_page_appear(self, page, offset=(10, 10)):
        return self.appear(page.check_button, offset=offset)

    def ui_get_current_page(self, skip_first_screenshot=False, timeout=10):
        """
        识别当前页面。识别不了就等待，超时抛 GamePageUnknownError。

        不会盲按返回键：有些页面按返回会关掉主菜单或弹出退出确认，
        按错了反而更难恢复，交给人工处理。
        兜底：认不出 3 秒就点一下上方空白处，大多数没关掉的弹窗点外面就关（用户 10-31），最多点 2 次。
        """
        logger.info('UI get current page')
        timer = Timer(timeout, count=5).start()
        dismiss = Timer(3, count=3).start()
        dismissed = 0
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            for page in Page.all_pages.values():
                if self.ui_page_appear(page):
                    logger.attr('UI', page.name)
                    return page
            if self.ui_additional():
                timer.reset()
                continue
            if timer.reached():
                break
            if dismissed < 2 and dismiss.reached():
                logger.info('认不出当前画面，点上方空白处试着关掉弹窗')
                self.device.click(POPUP_OUTSIDE)
                dismissed += 1
                dismiss.reset()
        logger.warning('无法识别当前页面')
        raise GamePageUnknownError

    def ui_goto(self, destination, skip_first_screenshot=True, timeout=30):
        """
        按页面关系一跳一跳点到 destination。每到一个新页面重新计时，timeout 秒还没离开当前这一步就抛
        GamePageUnknownError（以前没有超时，只能等连点检测或 60 秒卡死检测兜底）。
        """
        logger.hr(f'UI goto {destination}', level=3)
        Page.init_connection(destination)
        # 兜底：一直认不出页面（半路弹出没见过的弹窗）就隔 3 秒点一下上方空白处，最多 3 次
        unknown = Timer(3, count=3).start()
        dismissed = 0
        timer = Timer(timeout).start()
        last_page = None
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.ui_page_appear(destination):
                logger.info(f'Page arrive: {destination}')
                break
            if timer.reached():
                logger.warning(f'{timeout} 秒没能从 {last_page} 往 {destination} 走一步')
                raise GamePageUnknownError

            clicked = False
            for page in Page.all_pages.values():
                if page.parent is None:
                    continue
                if self.ui_page_appear(page):
                    if page != last_page:
                        last_page = page
                        timer.reset()
                    button = page.links[page.parent]
                    # 同一个跳转按钮 3 秒内只点一次，等页面切换动画
                    if self.appear_interval_ready(button, interval=3):
                        self.device.click(button)
                    clicked = True
                    break
            if clicked:
                unknown.reset()
                continue
            if self.ui_additional():
                unknown.reset()
                continue
            if dismissed < 3 and unknown.reached():
                logger.info('切换页面时认不出画面，点上方空白处试着关掉弹窗')
                self.device.click(POPUP_OUTSIDE)
                dismissed += 1
                unknown.reset()

    def ui_ensure(self, destination, skip_first_screenshot=False):
        """确保在目标页面；本来就在返回 False，切换过返回 True"""
        current = self.ui_get_current_page(skip_first_screenshot=skip_first_screenshot)
        if current == destination:
            logger.info(f'Already at {destination}')
            return False
        self.ui_goto(destination, skip_first_screenshot=True)
        return True

    def appear_interval_ready(self, button, interval):
        """点击节流：对只点击的按钮做 interval 判断"""
        timer = self.interval_timer.get(button.name)
        if timer is None or timer.limit != interval:
            timer = Timer(interval)
            self.interval_timer[button.name] = timer
        if timer.reached():
            timer.reset()
            return True
        return False

    # ---------- 点了没生效就重点（用户 11-01：模拟器偶尔卡两三秒，点完不能当成已经到下一步） ----------
    def click_until(self, button, success, retry_wait=3, max_clicks=3, abort=None, handle_popups=True,
                    raise_error=True, skip_first_screenshot=False):
        """
        点 button，直到 success() 为真。每点一下最多等 retry_wait 秒，没生效就再点，最多点 max_clicks 次。

        会扣东西的按钮（购买、捐赠确认、刷新、开采……）只能配「能证明上一下没生效」的 success，
        例如确认框还在、次数没变；状态说不清时不要用它盲点。

        Args:
            success: 无参函数，看当前截图判断点击是否生效，常用 appeared / gone / color_is
            abort: 无参函数，返回真就不再点、返回 False（例如弹出了不该碰的对话框）
            handle_popups: 每轮先处理奖励弹窗、结算页（ui_additional）
            raise_error: 点满次数还没生效时抛 GamePageUnknownError（走回家园 → 重启 → 连续失败找人工），否则返回 False

        Returns:
            bool: 生效返回 True
        """
        clicks = 0
        timer = Timer(retry_wait)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            if success():
                return True
            if abort is not None and abort():
                return False
            if handle_popups and self.ui_additional():
                continue
            if clicks and not timer.reached():
                time.sleep(0.3)
                continue
            if clicks >= max_clicks:
                logger.warning(f'点了 {clicks} 次 {button} 都没生效')
                if raise_error:
                    raise GamePageUnknownError
                return False
            if clicks:
                logger.info(f'点 {button} 没生效，再点一次（第 {clicks + 1} 次）')
            # 次数自己数，不让连点检测误判
            self.device.click_record.clear()
            self.device.click(button)
            clicks += 1
            timer.reset()

    def appeared(self, button, offset=(20, 20)):
        """click_until 的成功条件：button 出现"""
        return lambda: self.appear(button, offset=offset)

    def gone(self, button, offset=(20, 20)):
        """click_until 的成功条件：button 消失（弹窗关掉、领取按钮没了）"""
        return lambda: not self.appear(button, offset=offset)

    def color_is(self, area, color, tolerance=30):
        """click_until 的成功条件：area 的平均颜色接近 color（RGB），用于页签选中时变色"""
        def check():
            mean = crop(self.device.image, area).reshape(-1, 3).mean(axis=0)
            return bool(np.all(np.abs(mean - np.array(color)) < tolerance))
        return check

    def ui_click(self, click_button, check_button, offset=(20, 20), retry_wait=5, timeout=20,
                 skip_first_screenshot=False):
        """
        点 click_button，直到 check_button 出现。retry_wait 秒内没出现才会再点一次，总共约 timeout 秒。

        Returns:
            bool: check_button 是否出现
        """
        logger.info(f'UI click {click_button} -> {check_button}')
        if self.click_until(click_button, self.appeared(check_button, offset=offset), retry_wait=retry_wait,
                            max_clicks=max(1, math.ceil(timeout / retry_wait)), handle_popups=False,
                            raise_error=False, skip_first_screenshot=skip_first_screenshot):
            return True
        logger.warning(f'点 {click_button} 后 {timeout} 秒内没有出现 {check_button}')
        return False

    def handle_reward_popup(self, page, timeout=10):
        """关掉「获得奖励」弹窗，直到回到 page"""
        from module.ui.assets import GET_REWARD_CHECK
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(GET_REWARD_CHECK, offset=REWARD_OFFSET, interval=2):
                self.device.click(GET_REWARD_CHECK)
                continue
            if self.ui_page_appear(page):
                return True
            if timer.reached():
                logger.warning(f'关闭奖励弹窗后没有回到 {page}')
                return False

    def ui_additional(self):
        """处理会挡住页面的通用弹窗（奖励弹窗、战斗结算页），处理了返回 True"""
        from module.ui.assets import BATTLE_RESULT_CLOSE, GET_REWARD_CHECK
        if self.appear(GET_REWARD_CHECK, offset=REWARD_OFFSET, interval=2):
            self.device.click(GET_REWARD_CHECK)
            return True
        if self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20), interval=2):
            self.device.click(BATTLE_RESULT_CLOSE)
            return True
        return False

    def ui_close_popup(self, popup, until, timeout=10):
        """
        点弹窗外面（上方空白处）关掉 popup，直到 until 出现。没关上就隔 2 秒再点。
        返回键在弹窗的动画期间会被吞掉（10-31 信件、公会捐赠都因此没关上），点外面更稳。
        """
        timer = Timer(timeout).start()
        while 1:
            self.device.screenshot()
            if self.appear(until, offset=(10, 10)):
                return True
            if timer.reached():
                logger.warning(f'{popup} 关了 {timeout} 秒还没回到 {until}')
                raise GamePageUnknownError
            if self.ui_additional():
                continue
            if self.appear(popup, offset=(10, 10), interval=2):
                self.device.click(POPUP_OUTSIDE)
                continue
            time.sleep(0.5)

    def reward_popup(self):
        """当前截图里有没有「获得奖励」弹窗"""
        from module.ui.assets import GET_REWARD_CHECK
        return self.appear(GET_REWARD_CHECK, offset=REWARD_OFFSET)

    def wait_reward_popup(self, page, timeout=5):
        """点了领取类按钮后，等「获得奖励」弹窗出现（有动画，会晚一两秒）并关掉，回到 page"""
        from module.ui.assets import GET_REWARD_CHECK
        if self.wait_until_appear(GET_REWARD_CHECK, offset=REWARD_OFFSET, timeout=timeout):
            return self.handle_reward_popup(page)
        logger.info('没有出现「获得奖励」弹窗')
        return False

    def ui_test(self):
        """框架自检：依次切换 5 个主页面，最后回到家园"""
        logger.hr('UI test', level=1)
        self.ui_get_current_page()
        for page in [page_role, page_note, page_guild, page_world, page_home]:
            self.ui_goto(page, skip_first_screenshot=False)
        logger.info('UI test 完成')
