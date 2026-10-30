"""
Windows 系统通知（右下角弹出、进通知中心）。用系统自带的 PowerShell 调 WinRT，不装额外的库。
标题和正文通过环境变量传给 PowerShell，不拼进命令行，避免引号、换行把命令弄坏。
"""
import os
import subprocess

from module.logger import logger

# 借用 PowerShell 的应用 ID：没有安装包的脚本自己注册不了，系统通知必须挂在一个已注册的应用名下
APP_ID = r'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$title = [Security.SecurityElement]::Escape($env:ZJCS_TITLE)
$body = [Security.SecurityElement]::Escape($env:ZJCS_BODY)
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$title</text><text>$body</text></binding></visual></toast>")
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:ZJCS_APP).Show($toast)
'''


def send_toast(title, body):
    """
    Returns:
        str: 失败原因，成功返回空字符串
    """
    env = dict(os.environ, ZJCS_TITLE=str(title), ZJCS_BODY=str(body), ZJCS_APP=APP_ID)
    try:
        result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', SCRIPT], env=env,
                                capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)
    if result.returncode != 0:
        return result.stderr.decode('utf-8', errors='ignore').strip()[-300:] or f'exit {result.returncode}'
    return ''


def notify(config, event, title, body):
    """
    按配置决定要不要发通知，发不出去只记日志，不影响脚本。

    Args:
        event: Human（需要人工处理）/ Finish（今天的任务都跑完了）
    """
    if not config.Notify_Enable or not getattr(config, f'Notify_{event}'):
        return
    error = send_toast(title, body)
    if error:
        logger.warning(f'系统通知发送失败: {error}')
    else:
        logger.info(f'已发送系统通知: {title}')
