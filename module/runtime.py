"""
调度进程和配置界面之间的通道，全部走文件，两边谁先启动、谁中途关掉都不影响另一边：

- config/<名字>.runtime.json   调度进程写：在不在跑、正在跑哪个任务、上次为什么停下
- config/<名字>.cmd/*.json      配置界面写、调度进程读完就删：立即执行某个任务、停止
- log/<名字>.history.jsonl      调度进程追加：每个任务的开始/结束时间和结果
"""
import ctypes
import datetime
import json
import os
import time
import uuid

from module.logger import LOG_DIR, ROOT

CONFIG_DIR = os.path.join(ROOT, 'config')


def now_iso():
    return datetime.datetime.now().isoformat(timespec='seconds')


def runtime_file(config_name):
    return os.path.join(CONFIG_DIR, f'{config_name}.runtime.json')


def command_dir(config_name):
    return os.path.join(CONFIG_DIR, f'{config_name}.cmd')


def history_file(config_name):
    return os.path.join(LOG_DIR, f'{config_name}.history.jsonl')


def write_text(file, text):
    """
    先写临时文件再改名，另一边读到的永远是完整的文件。
    Windows 上目标文件正被另一个进程读着时改名会报 PermissionError，等一下重试。
    """
    tmp = f'{file}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    for retry in range(20):
        try:
            os.replace(tmp, file)
            return
        except PermissionError:
            if retry == 19:
                raise
            time.sleep(0.05)


def write_json(file, data):
    write_text(file, json.dumps(data, ensure_ascii=False, indent=2))


def read_json(file, default=None):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def pid_alive(pid):
    """进程还在、而且是 python（防止 pid 被别的程序复用）"""
    if not pid:
        return False
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:  # STILL_ACTIVE
            return False
        size = ctypes.c_ulong(1024)
        name = ctypes.create_unicode_buffer(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            return 'python' in os.path.basename(name.value).lower()
        return True
    finally:
        kernel32.CloseHandle(handle)


def read_runtime(config_name):
    """读运行状态，并按进程是否真的还在修正 alive"""
    data = read_json(runtime_file(config_name), {}) or {}
    data['alive'] = data.get('state') not in (None, 'stopped') and pid_alive(data.get('pid'))
    if data.get('state') not in (None, 'stopped') and not data['alive']:
        # 进程没了但没来得及写「已停止」：被强制结束、断电或崩溃
        data['state'] = 'stopped'
        data.setdefault('exit', 'killed')
    return data


# ---------- 指令 ----------
def send_command(config_name, command):
    """配置界面调用。一条指令一个文件，不会和调度进程同时改同一个文件"""
    folder = command_dir(config_name)
    os.makedirs(folder, exist_ok=True)
    name = f'{time.time_ns()}_{uuid.uuid4().hex[:6]}.json'
    write_json(os.path.join(folder, name), dict(command, time=now_iso()))


def take_commands(config_name):
    """调度进程调用：按时间顺序取出所有指令并删除"""
    folder = command_dir(config_name)
    if not os.path.isdir(folder):
        return []
    commands = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.json'):
            continue
        file = os.path.join(folder, name)
        command = read_json(file)
        try:
            os.remove(file)
        except OSError:
            continue
        if isinstance(command, dict):
            commands.append(command)
    return commands


def clear_commands(config_name, action):
    """配置界面启动调度前清掉没被取走的停止指令，否则一启动就会停"""
    folder = command_dir(config_name)
    if not os.path.isdir(folder):
        return
    for name in os.listdir(folder):
        file = os.path.join(folder, name)
        if name.endswith('.json') and (read_json(file) or {}).get('action') == action:
            try:
                os.remove(file)
            except OSError:
                pass


def pending_commands(config_name):
    """配置界面调用：还没被调度进程取走的指令"""
    folder = command_dir(config_name)
    if not os.path.isdir(folder):
        return []
    return [c for c in (read_json(os.path.join(folder, n)) for n in sorted(os.listdir(folder)) if n.endswith('.json'))
            if isinstance(c, dict)]


# ---------- 运行记录 ----------
def append_history(config_name, record):
    with open(history_file(config_name), 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def read_history(config_name, limit=500):
    """最近的运行记录，新的在前"""
    try:
        with open(history_file(config_name), 'r', encoding='utf-8') as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []
    records = []
    for line in reversed(lines):
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


class Runtime:
    """调度进程这一侧：维护 runtime.json"""

    def __init__(self, config_name, mode):
        self.config_name = config_name
        self.file = runtime_file(config_name)
        self.data = {}
        self.mode = mode

    def other_instance(self):
        """已经有另一个调度进程在跑，返回它的 pid"""
        data = read_runtime(self.config_name)
        if data.get('alive') and data.get('pid') != os.getpid():
            return data.get('pid')
        return None

    def start(self):
        self.data = {
            'pid': os.getpid(), 'mode': self.mode, 'state': 'starting', 'started': now_iso(),
            'task': None, 'task_started': None, 'next_run': None, 'stopping': False,
        }
        self.save()

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.save()

    def stop(self, reason, message=''):
        """
        Args:
            reason: done（--loop 以外跑完退出）/ empty（没有开着的任务）/ task（--task 单独跑完）/ stopped（按了停止）/ human（需要人工处理）/ error（脚本出错）
        """
        self.data.update(state='stopped', exit=reason, message=message, ended=now_iso(), task=None, task_started=None,
                         stopping=False)
        self.save()

    def save(self):
        write_json(self.file, self.data)
