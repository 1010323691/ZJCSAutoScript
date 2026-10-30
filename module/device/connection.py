import subprocess

from module.exception import RequestHumanTakeover
from module.logger import logger


def adb_devices(adb):
    """adb devices 的结果：{序列号: 状态}，状态是 device 才算在线。配置界面的设备检查也用它"""
    result = subprocess.run([adb, 'devices'], capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    devices = {}
    for line in result.stdout.decode('utf-8', errors='ignore').splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            devices[parts[0]] = parts[1]
    return devices


def focus_package(out):
    """从 dumpsys window | grep mCurrentFocus 的输出里取前台应用包名"""
    # mCurrentFocus=Window{6a362ba u0 com.leiting.zjcs/com.leiting.unity.AppActivity}
    for token in out.split():
        if '/' in token:
            return token.split('/')[0]
    return ''


class Connection:
    def __init__(self, config):
        """
        通过 adb 可执行文件发命令。

        只用雷电自带的 adb（和本机其他脚本同一个版本），不执行 kill-server / start-server，
        避免 adb server 版本不一致时互相踢掉，影响同机运行的其他模拟器实例。
        """
        self.config = config
        self.adb = config.Device_AdbExecutable
        self.serial = str(config.Device_Serial)
        self.package = config.Device_PackageName
        self.check_device()

    def adb_command(self, args, timeout=10):
        cmd = [self.adb, '-s', self.serial] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning(f'adb 命令超时: {" ".join(args)}')
            raise
        return result.stdout

    def adb_shell(self, cmd, timeout=10):
        out = self.adb_command(['shell', cmd], timeout=timeout)
        return out.decode('utf-8', errors='ignore')

    def check_device(self):
        devices = adb_devices(self.adb)
        logger.attr('AdbDevices', devices)
        state = devices.get(self.serial)
        if state != 'device':
            logger.critical(f'设备 {self.serial} 不在线（状态: {state}），请检查模拟器和配置 Device.Serial')
            raise RequestHumanTakeover
        logger.info(f'已连接设备 {self.serial}')

    def app_current(self):
        """前台应用包名"""
        return focus_package(self.adb_shell('dumpsys window | grep mCurrentFocus'))

    def app_is_running(self):
        return self.app_current() == self.package
