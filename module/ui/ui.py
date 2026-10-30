from module.base.base import ModuleBase
from module.base.timer import Timer
from module.exception import GamePageUnknownError
from module.logger import logger
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
        """
        logger.info('UI get current page')
        timer = Timer(timeout, count=5).start()
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
        logger.warning('无法识别当前页面')
        raise GamePageUnknownError

    def ui_goto(self, destination, skip_first_screenshot=True):
        logger.hr(f'UI goto {destination}', level=3)
        Page.init_connection(destination)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.ui_page_appear(destination):
                logger.info(f'Page arrive: {destination}')
                break

            clicked = False
            for page in Page.all_pages.values():
                if page.parent is None:
                    continue
                if self.ui_page_appear(page):
                    button = page.links[page.parent]
                    # 同一个跳转按钮 3 秒内只点一次，等页面切换动画
                    if self.appear_interval_ready(button, interval=3):
                        self.device.click(button)
                    clicked = True
                    break
            if clicked:
                continue
            self.ui_additional()

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

    def ui_click(self, click_button, check_button, offset=(20, 20), retry_wait=5, timeout=20,
                 skip_first_screenshot=False):
        """
        点 click_button，直到 check_button 出现。retry_wait 秒内没出现才会再点一次。

        Returns:
            bool: check_button 是否出现
        """
        logger.info(f'UI click {click_button} -> {check_button}')
        timer = Timer(timeout).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            if self.appear(check_button, offset=offset):
                return True
            if timer.reached():
                logger.warning(f'点 {click_button} 后 {timeout} 秒内没有出现 {check_button}')
                return False
            if self.appear_interval_ready(click_button, interval=retry_wait):
                self.device.click(click_button)

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
