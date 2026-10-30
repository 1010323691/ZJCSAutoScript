from module.base.timer import Timer
from module.logger import logger


class ModuleBase:
    def __init__(self, config, device=None):
        """
        Args:
            config (module.config.config.ZjcsConfig):
            device (module.device.device.Device): 不传就新建一个
        """
        self.config = config
        if device is None:
            from module.device.device import Device
            device = Device(config)
        self.device = device
        self.interval_timer = {}

    def appear(self, button, offset=0, interval=0, similarity=0.85, threshold=10):
        """
        Args:
            button (Button):
            offset (int, tuple): 传了就用模板匹配，否则用颜色判断
            interval (int, float): 两次返回 True 之间至少隔多少秒，防止同一个按钮被连点
            similarity (float): 模板匹配阈值
            threshold (int): 颜色判断阈值
        """
        if interval:
            timer = self.interval_timer.get(button.name)
            if timer is None or timer.limit != interval:
                timer = Timer(interval)
                self.interval_timer[button.name] = timer
            if not timer.reached():
                return False

        if offset:
            appear = button.match(self.device.image, offset=offset, similarity=similarity)
        else:
            appear = button.appear_on(self.device.image, threshold=threshold)

        if appear and interval:
            self.interval_timer[button.name].reset()
        return appear

    def appear_then_click(self, button, screenshot=False, offset=0, interval=0, similarity=0.85, threshold=10):
        if screenshot:
            self.device.screenshot()
        appear = self.appear(button, offset=offset, interval=interval, similarity=similarity, threshold=threshold)
        if appear:
            self.device.click(button)
        return appear

    def wait_until_appear(self, button, offset=0, timeout=10, skip_first_screenshot=False):
        """等按钮出现，超时返回 False"""
        timer = Timer(timeout).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            if self.appear(button, offset=offset):
                return True
            if timer.reached():
                logger.warning(f'等待 {button} 超时（{timeout} 秒）')
                return False

    def interval_reset(self, button):
        if button.name in self.interval_timer:
            self.interval_timer[button.name].reset()

    def interval_clear(self, button):
        if button.name in self.interval_timer:
            self.interval_timer[button.name].clear()
