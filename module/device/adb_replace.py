"""
把雷电安装目录里的 adb.exe 换成脚本自带的那份（bin/adb，和 ALAS 带的是同一份 29.0.6）。

不同版本的 adb 服务启动时会互相关掉对方，导致断线；把雷电的也换成同一份就不会。
做法照搬 ALAS deploy 的 ReplaceAdb（deploy/Windows/emulator.py adb_replace）：
已经一样就什么都不做；否则先结束所有 adb 进程，再把原文件改名成 adb.exe.bak
（已有就 .bak1、.bak2……），把自带的 adb.exe 复制进去。只处理雷电。

配置界面（gui.py）启动时调用，设置里「替换雷电的 adb」（Device_ReplaceAdb）关掉就不做。
"""
import filecmp
import os
import re
import shutil
import subprocess
import winreg

from module.logger import ROOT, logger
from module.runtime import read_runtime

BUNDLED_ADB = os.path.join(ROOT, 'bin', 'adb', 'adb.exe')
UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
    (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
    (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall'),
]


def subkeys(hive, path):
    try:
        with winreg.OpenKey(hive, path) as key:
            return [winreg.EnumKey(key, i) for i in range(winreg.QueryInfoKey(key)[0])]
    except OSError:
        return []


def read_value(hive, path, name):
    try:
        with winreg.OpenKey(hive, path) as key:
            return str(winreg.QueryValueEx(key, name)[0])
    except OSError:
        return ''


def exe_dir(command):
    """'"D:\\APP\\LDPlayer14\\dnuninst.exe" -x' -> 'D:\\APP\\LDPlayer14'"""
    match = re.match(r'\s*"?([^"]+?\.exe)', command, re.IGNORECASE)
    return os.path.dirname(match.group(1)) if match else ''


def ldplayer_dirs(extra=()):
    """本机装的雷电目录（里面有 dnplayer.exe 和 adb.exe 的才算）"""
    found = []
    # 卸载信息：雷电 14 只在这里记了位置（Uninstall\LDPlayer14 的 DisplayIcon / UninstallString）
    for hive, path in UNINSTALL_KEYS:
        for name in subkeys(hive, path):
            if name.lower().startswith(('ldplayer', 'leidian')):
                for value in ('DisplayIcon', 'UninstallString'):
                    found.append(exe_dir(read_value(hive, f'{path}\\{name}', value)))
                found.append(read_value(hive, f'{path}\\{name}', 'InstallLocation'))
    # 老版本雷电写在 SOFTWARE\leidian\<版本>\InstallDir（雷电 14 这一项是空的）
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for name in subkeys(hive, r'SOFTWARE\leidian'):
            found.append(read_value(hive, f'SOFTWARE\\leidian\\{name}', 'InstallDir'))
    # 配置里填的 adb 如果就在雷电目录里，也算
    found += [os.path.dirname(path) for path in extra if path]

    dirs = []
    for folder in found:
        if not folder:
            continue
        folder = os.path.normcase(os.path.abspath(folder))
        if folder not in dirs and os.path.isfile(os.path.join(folder, 'dnplayer.exe')) \
                and os.path.isfile(os.path.join(folder, 'adb.exe')):
            dirs.append(folder)
    return dirs


def backup_path(adb):
    for n in range(10):
        backup = f'{adb}.bak{n}' if n else f'{adb}.bak'
        if not os.path.exists(backup):
            return backup
    # 备份太多了就覆盖第一个，和 ALAS 一样
    return f'{adb}.bak'


def kill_adb():
    """结束所有 adb 进程（ALAS 的 adb_kill：有的 adb 不听 kill-server，直接结束进程）"""
    subprocess.run(['taskkill', '/F', '/IM', 'adb.exe'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


def replace_ldplayer_adb(config_name, extra=()):
    if not os.path.isfile(BUNDLED_ADB):
        logger.warning(f'没有自带的 adb（{BUNDLED_ADB}），跳过替换')
        return
    targets = [os.path.join(d, 'adb.exe') for d in ldplayer_dirs(extra)]
    replace = [adb for adb in targets if not filecmp.cmp(adb, BUNDLED_ADB, shallow=False)]
    if not targets:
        logger.info('没找到雷电模拟器，跳过替换 adb')
        return
    if not replace:
        logger.info('雷电的 adb 已经是自带的那份，不用替换')
        return
    if read_runtime(config_name).get('alive'):
        # 结束 adb 进程会打断正在跑的任务，等下次打开再换
        logger.info('脚本正在后台跑，这次先不替换雷电的 adb')
        return
    kill_adb()
    for adb in replace:
        backup = backup_path(adb)
        try:
            shutil.move(adb, backup)
            shutil.copy(BUNDLED_ADB, adb)
            logger.info(f'已替换 {adb}（原文件改名为 {os.path.basename(backup)}）')
        except OSError as e:
            # 改名成功但没复制进去时把原文件挪回来，雷电不能没有 adb.exe
            if not os.path.exists(adb) and os.path.exists(backup):
                shutil.move(backup, adb)
            logger.warning(f'替换 {adb} 失败：{e}')
