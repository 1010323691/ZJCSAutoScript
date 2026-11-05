import time

from module.base.timer import Timer
from module.exception import GameNotRunningError, RequestHumanTakeover
from module.handler.assets import ANNOUNCE_CHECK, LOGIN_CHECK
from module.logger import logger
from module.ui.assets import BACK_ARROW
from module.ui.page import page_home
from module.ui.ui import UI

APP_ACTIVITY = 'com.leiting.unity.AppActivity'


class LoginHandler(UI):
    def app_stop(self):
        logger.info('App stop')
        self.device.adb_shell(f'am force-stop {self.device.package}')
        time.sleep(2)

    def app_start(self):
        logger.info('App start')
        # 直接启动游戏主 Activity；包的启动入口是隐私协议页，绕开它避免弹协议
        self.device.adb_shell(f'am start -n {self.device.package}/{APP_ACTIVITY}')

    def handle_app_login(self, timeout=180):
        """
        从启动到家园：健康忠告 → 标题页自动登录 → 公告弹窗 → 点击任意处开始游戏 → 家园。
        """
        logger.hr('App login', level=2)
        self.device.long_wait(True)
        timer = Timer(timeout).start()
        try:
            while 1:
                self.device.screenshot()
                if timer.reached():
                    logger.critical(f'{timeout} 秒内没能进入游戏')
                    raise RequestHumanTakeover

                if self.ui_page_appear(page_home):
                    logger.info('登录完成，已在家园')
                    return True
                if self.appear(ANNOUNCE_CHECK, offset=(20, 20)):
                    # 公告弹窗：点左下返回关闭
                    if self.appear(BACK_ARROW, offset=(20, 20), interval=3):
                        self.device.click(BACK_ARROW)
                    continue
                if self.appear(LOGIN_CHECK, offset=(20, 20), interval=5):
                    self.device.click(LOGIN_CHECK)
                    continue
                if self.resumed_activity():
                    continue
                # 其余是加载、健康忠告、正在登录，等着就行
                time.sleep(1)
        finally:
            self.device.long_wait(False)

    def resumed_activity(self):
        """
        重启后游戏会直接回到上次没退出的活动关卡（11-05 菲涅克的谜题：重启后停在石板谜题的场景里，
        一直等不到家园，180 秒后停机）。认出关卡、「解谜成功」页、关卡列表、活动汇总，就往外退到家园。
        """
        from module.fenek.assets import (FENEK_CHECK, LEAVE_CONFIRM, LEAVE_CONFIRM_OK, PUZZLE_EXIT, PUZZLE_EXIT_ONLY,
                                         PUZZLE_SUCCESS, SHIBAN_SCENE, YINFU_STATUE, YUANSU_CHECK)
        from module.reward.assets import EVENT_CHECK
        if self.appear(PUZZLE_SUCCESS, offset=(10, 10), interval=3):
            # 最后一关的成功页只有居中的「退出」
            self.device.click(PUZZLE_EXIT_ONLY if self.appear(PUZZLE_EXIT_ONLY, offset=(10, 10)) else PUZZLE_EXIT)
            return True
        if self.appear(LEAVE_CONFIRM, offset=(20, 20), interval=3):
            self.device.click(LEAVE_CONFIRM_OK)
            return True
        if self.appear(FENEK_CHECK, offset=(10, 10)) or self.appear(EVENT_CHECK, offset=(10, 10)) \
                or self.appear(YUANSU_CHECK, offset=(10, 30)) \
                or YINFU_STATUE.match_region(self.device.image, (480, 430, 720, 780), similarity=0.85) > 0.85 \
                or SHIBAN_SCENE.match_region(self.device.image, (0, 150, 720, 800), similarity=0.75) > 0.75:
            if self.appear_interval_ready(BACK_ARROW, interval=3):
                logger.info('重启后回到了活动页面，按左下返回')
                self.device.click(BACK_ARROW)
            return True
        return False

    def app_restart(self):
        logger.hr('App restart', level=1)
        self.app_stop()
        self.app_start()
        # 闪退后再启动，进程有时要十几秒才出现在前台
        timer = Timer(20).start()
        while not self.device.app_is_running():
            if timer.reached():
                logger.critical('游戏没能启动')
                raise GameNotRunningError
            time.sleep(2)
        self.handle_app_login()
