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
                # 其余是加载、健康忠告、正在登录，等着就行
                time.sleep(1)
        finally:
            self.device.long_wait(False)

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
