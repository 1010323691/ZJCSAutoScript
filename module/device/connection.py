import os
import subprocess
import sys

from module.exception import RequestHumanTakeover
from module.logger import ROOT, logger


def adb_path(path):
    """配置里的 adb 路径；相对路径按项目根目录算（默认值 bin/adb/adb.exe 是脚本自带的）"""
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


IS_MAC = sys.platform == 'darwin'
# Windows 上不弹黑色控制台窗口；其他系统没有这个标志
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def adb_devices(adb, serial=None):
    """
    adb devices 的结果：{序列号: 状态}，状态是 device 才算在线。配置界面的设备检查也用它。

    serial 是 127.0.0.1:5575 这种地址、又不在线时，先 adb connect 再查（不重启 adb 服务）。
    adb 服务只在启动时扫一遍 emulator-XXXX，之后才开的模拟器实例不会出现，按地址连就行（11-02 Mac 上 BlueStacks 第 3 个实例实测）。
    """
    def read():
        result = subprocess.run([adb, 'devices'], capture_output=True, timeout=10, creationflags=NO_WINDOW)
        devices = {}
        for line in result.stdout.decode('utf-8', errors='ignore').splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                devices[parts[0]] = parts[1]
        return devices

    devices = read()
    if serial and ':' in serial and devices.get(serial) != 'device':
        result = subprocess.run([adb, 'connect', serial], capture_output=True, timeout=10, creationflags=NO_WINDOW)
        out = (result.stdout + result.stderr).decode('utf-8', errors='ignore').strip()
        # 连不上时 adb 也常常返回 0，只能看输出
        (logger.info if out.startswith(('connected', 'already connected')) else logger.warning)(f'adb connect {serial}: {out}')
        devices = read()
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

        默认用脚本自带的 adb（bin/adb，和 ALAS 同一份）。打开配置界面时会把雷电目录里的 adb 也换成这份
        （module/device/adb_replace.py），版本一致就不会互相踢掉 adb 服务。这里不执行 kill-server / start-server。
        Mac 上用 BlueStacks 自带的 hd-adb（和 ALAS 同一份），不替换。
        """
        self.config = config
        self.adb = adb_path(config.Device_AdbExecutable)
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
        devices = adb_devices(self.adb, self.serial)
        logger.attr('AdbDevices', devices)
        state = devices.get(self.serial)
        if state != 'device':
            logger.critical(f'设备 {self.serial} 不在线（状态: {state}），请检查模拟器和配置 Device.Serial')
            raise RequestHumanTakeover
        logger.info(f'已连接设备 {self.serial}')

    def reconnect(self):
        """
        地址形式的序列号（127.0.0.1:5575）在 adb 服务重启、模拟器重启后会从设备列表里消失，不会自己回来，
        重新 adb connect；emulator-XXXX 由 adb 服务自己找回，这里什么都不做
        """
        if ':' in self.serial:
            try:
                adb_devices(self.adb, self.serial)
            except (OSError, subprocess.TimeoutExpired) as e:
                logger.warning(f'重连 {self.serial} 失败: {e}')

    def app_current(self):
        """前台应用包名"""
        return focus_package(self.adb_shell('dumpsys window | grep mCurrentFocus'))

    def app_is_running(self):
        return self.app_current() == self.package
