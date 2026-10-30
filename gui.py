"""
配置界面：本机网页，只监听 127.0.0.1。按 module/config/argument.yaml 读写 config/<名字>.yaml，页面在 module/webui/。
也管运行：启动 / 停止调度进程（zjcs.py --loop）、立即执行某个任务、看实时日志和模拟器画面，和调度进程之间走 module/runtime.py 的文件通道。

用法：
    .venv\\Scripts\\python.exe gui.py                 # 打开 http://127.0.0.1:22367
    .venv\\Scripts\\python.exe gui.py --port 22368 --config zjcs --no-browser
"""
import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from module.config.config import ARGUMENT_FILE, TASK_ORDER, ZjcsConfig
from module.device.connection import adb_devices, focus_package
from module.logger import LOG_DIR, ROOT, log_file
from module.notify import send_toast
from module.runtime import (clear_commands, now_iso, pending_commands, read_history, read_json, read_runtime,
                            runtime_file, send_command, write_json)

WEBUI = os.path.join(ROOT, 'module', 'webui')
STATIC = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/style.css': ('style.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
}
CONFIG_NAME = 'zjcs'
PORT = 22367
# 同时只让一个请求读写配置文件
LOCK = threading.Lock()

# 数值参数的取值范围（含两端），超出就不保存
RANGES = {
    'Device_ScreenshotInterval': (0.1, 2),
    'Scheduler_ServerTimezone': (-12, 14),
    'Scheduler_FailureLimit': (1, 10),
    'GeneralShop_RefreshTimes': (-1, 99),
    'BondAdventure_RefreshLimit': (0, 3),
    'Arena_BuyTickets': (0, 8),
    'Arena_Challenges': (0, 10),
    'MaterialRealm_ExpectedCost': (0, 100000),
    'MaterialRealm_MineTimes': (0, 30),
    'GuildDonate_Times': (0, 3),
    'GuildWar_Challenges': (0, 3),
    'GuildWar_PowerRatio': (0.5, 1),
    'GuildRaid_Challenges': (0, 2),
}


def validate(group, arg, value):
    """返回错误信息，没问题返回 None"""
    key = f'{group}_{arg}'
    if key in RANGES:
        low, high = RANGES[key]
        if not low <= value <= high:
            return f'要在 {low} 到 {high} 之间'
    if key == 'Scheduler_ServerUpdate':
        res = re.fullmatch(r'(\d{1,2}):(\d{2})', value)
        if not res or int(res.group(1)) > 23 or int(res.group(2)) > 59:
            return '要写成 08:00 这样的时间'
    if key == 'Vault_Items' and value and not re.fullmatch(r'\d+(,\d+)*', value):
        return '要写成 1,2,3 这样的格式'
    if key == 'MaterialRealm_BuyCount' and not re.fullmatch(r'\d{4}', value):
        return '要是 4 位数字，例如 4444'
    if key in ('Device_Serial', 'Device_AdbExecutable', 'Device_PackageName') and not value:
        return '不能为空'
    return None


def coerce(define, value):
    """按参数类型转换页面传来的值，转不了抛 ValueError"""
    kind = define['type']
    if kind == 'checkbox':
        if not isinstance(value, bool):
            raise ValueError
        return value
    if isinstance(value, bool):
        raise ValueError
    if kind == 'number':
        number = float(value)
        if not number.is_integer():
            raise ValueError
        return int(number)
    if kind == 'float':
        return float(value)
    if kind == 'select':
        for option in define['option']:
            if str(option) == str(value):
                return option
        raise ValueError
    return str(value).strip()


def apply(config, data):
    """
    把页面传来的配置写进 config.data，没传的参数保持原值。

    Returns:
        dict: {'Group_Arg': 错误信息}，全部合法时为空
    """
    errors = {}
    for group, args in config.argument.items():
        for arg, define in args.items():
            if arg.startswith('_') or arg not in data.get(group, {}):
                continue
            key = f'{group}_{arg}'
            try:
                value = coerce(define, data[group][arg])
            except (TypeError, ValueError):
                errors[key] = '值的格式不对'
                continue
            if key in ('Vault_Items', 'MaterialRealm_BuyCount'):
                value = re.sub(r'\s+', '', value)
            error = validate(group, arg, value)
            if error:
                errors[key] = error
                continue
            config.data[group][arg] = value
    return errors


# ---------- 运行控制 ----------
# 本界面启动的调度进程；只用来防止连点两次启动出两个进程，状态以 runtime.json 为准
SCHEDULER = None
SCREENSHOT = {'time': 0, 'png': b'', 'error': ''}
SCREENSHOT_LOCK = threading.Lock()


CONFIG_CACHE = {'key': None, 'config': None}


def current_config():
    """只读用：参数表、配置、状态三个文件都没变就复用上次读到的，状态轮询不用每 2 秒重新解析 yaml"""
    files = (ARGUMENT_FILE, os.path.join(ROOT, 'config', f'{CONFIG_NAME}.yaml'),
             os.path.join(ROOT, 'config', f'{CONFIG_NAME}.state.json'))
    key = tuple(os.stat(f).st_mtime_ns if os.path.exists(f) else 0 for f in files)
    with LOCK:
        if CONFIG_CACHE['key'] != key:
            CONFIG_CACHE.update(key=key, config=ZjcsConfig(CONFIG_NAME))
        return CONFIG_CACHE['config']


def task_names(config):
    return [t for t in TASK_ORDER if t in config.argument]


def status():
    config = current_config()
    runtime = read_runtime(CONFIG_NAME)
    commands = pending_commands(CONFIG_NAME)
    queued = {c.get('task') for c in commands if c.get('action') == 'run_now'}
    tasks = []
    for task in task_names(config):
        record = config.state.get(task, {})
        tasks.append({
            'task': task,
            'name': config.argument[task].get('_name', task),
            'enabled': config.is_enabled(task),
            'next_run': record.get('NextRun'),
            'last_run': record.get('LastRun'),
            'result': record.get('Result'),
            'failure': record.get('Failure', 0),
            'run_now': record.get('RunNow') or ('queued' if task in queued else None),
        })
    today = datetime.date.today().isoformat()
    history = [r for r in read_history(CONFIG_NAME, limit=300) if str(r.get('start', '')).startswith(today)]
    return {
        'now': now_iso(),
        'runtime': runtime,
        'stop_pending': any(c.get('action') == 'stop' for c in commands),
        'tasks': tasks,
        'history': history,
        'failure_limit': config.Scheduler_FailureLimit,
    }


def start_scheduler():
    """
    Returns:
        str: 启动不了的原因，启动了返回空字符串
    """
    global SCHEDULER
    if read_runtime(CONFIG_NAME).get('alive') or (SCHEDULER is not None and SCHEDULER.poll() is None):
        return '已经在运行了'
    clear_commands(CONFIG_NAME, 'stop')
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    # 不接输出（日志已经写文件），也不挂在界面进程下：关掉配置界面，脚本照样跑。
    # 桌面壳（zjcs.exe）用作业对象管着 gui.py，关窗口会结束整个作业；脱离作业，脚本才不会被一起结束。
    # 不在作业里、或作业不允许脱离时 CreateProcess 会拒绝，退回不带这个标志
    for extra in (subprocess.CREATE_BREAKAWAY_FROM_JOB, 0):
        try:
            SCHEDULER = subprocess.Popen([sys.executable, os.path.join(ROOT, 'zjcs.py'), '--config', CONFIG_NAME, '--loop'],
                                         cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, creationflags=flags | extra, close_fds=True)
            return ''
        except OSError:
            if not extra:
                raise
    return ''


def force_stop():
    runtime = read_runtime(CONFIG_NAME)
    pids = {runtime.get('pid')} if runtime.get('alive') else set()
    if SCHEDULER is not None and SCHEDULER.poll() is None:
        pids.add(SCHEDULER.pid)
    for pid in filter(None, pids):
        # /T 连同它开的 adb 子进程一起结束
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    clear_commands(CONFIG_NAME, 'stop')
    data = read_json(runtime_file(CONFIG_NAME), {}) or {}
    if data.get('state') != 'stopped':
        data.update(state='stopped', exit='stopped', message='强制停止', ended=now_iso(), task=None,
                    task_started=None, stopping=False)
        write_json(runtime_file(CONFIG_NAME), data)
    return bool(pids)


# ---------- 设备 ----------
def adb_run(config, args, timeout=10):
    return subprocess.run([config.Device_AdbExecutable] + args, capture_output=True, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW)


def screencap(config):
    """模拟器当前画面的 png；只读，不会点任何东西"""
    result = adb_run(config, ['-s', str(config.Device_Serial), 'exec-out', 'screencap', '-p'], timeout=15)
    if result.returncode != 0 or not result.stdout.startswith(b'\x89PNG'):
        raise RuntimeError(result.stderr.decode('utf-8', errors='ignore').strip() or '截图失败')
    return result.stdout


def cached_screenshot():
    """多个页面同时刷新时，1.5 秒内复用同一张"""
    with SCREENSHOT_LOCK:
        if time.time() - SCREENSHOT['time'] > 1.5:
            config = current_config()
            try:
                SCREENSHOT.update(png=screencap(config), error='')
            except (OSError, subprocess.TimeoutExpired, RuntimeError) as e:
                SCREENSHOT.update(png=b'', error=str(e) or type(e).__name__)
            SCREENSHOT['time'] = time.time()
        return SCREENSHOT['png'], SCREENSHOT['error']


def check_device():
    """按已保存的设备设置一步步检查：adb 能不能用 → 设备在不在线 → 能不能截图 → 游戏在不在前台"""
    config = current_config()
    serial = str(config.Device_Serial)
    steps = []

    def step(name, ok, detail):
        steps.append({'name': name, 'ok': ok, 'detail': detail})
        return ok

    try:
        devices = adb_devices(config.Device_AdbExecutable)
    except (OSError, subprocess.TimeoutExpired) as e:
        step('adb 能用', False, f'运行不了 {config.Device_AdbExecutable}：{e}')
        return {'ok': False, 'steps': steps}
    step('adb 能用', True, f'找到 {len(devices)} 台设备：{"、".join(devices) or "无"}')
    if not step('设备在线', devices.get(serial) == 'device', f'{serial} 的状态：{devices.get(serial, "没找到")}'):
        return {'ok': False, 'steps': steps}
    try:
        png = screencap(config)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as e:
        step('能截图', False, str(e))
        return {'ok': False, 'steps': steps}
    size = (int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big'))
    step('能截图', size == (720, 1280), f'分辨率 {size[0]}x{size[1]}' + ('' if size == (720, 1280) else '，脚本只支持 720x1280 竖屏'))
    focus = adb_run(config, ['-s', serial, 'shell', 'dumpsys window | grep mCurrentFocus']).stdout
    running = focus_package(focus.decode('utf-8', errors='ignore')) == config.Device_PackageName
    step('游戏在前台', running, '游戏开着' if running else '游戏没在前台（开始跑时脚本会自己启动它）')
    return {'ok': all(s['ok'] for s in steps[:3]), 'steps': steps, 'image': base64.b64encode(png).decode()}


# ---------- 日志 ----------
DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
ERROR_DIR_RE = re.compile(r'\d{8}_\d{6}')
ERROR_FILE_RE = re.compile(r'[\w.-]+\.png')


def log_dates():
    names = sorted((n for n in os.listdir(LOG_DIR) if n.endswith('_zjcs.txt') and DATE_RE.fullmatch(n[:10])), reverse=True)
    return [{'date': n[:10], 'size': os.path.getsize(os.path.join(LOG_DIR, n))} for n in names]


def read_log(date, offset, tail):
    """
    Args:
        offset: 从第几个字节接着读（实时日志用）；-1 表示只要最后 tail 行

    Returns:
        dict: text 只含完整的行，写了一半的行留到下次；offset 是下次接着读的位置
    """
    file = log_file(date)
    if not os.path.exists(file):
        return {'date': date, 'offset': 0, 'text': '', 'reset': offset != 0}
    size = os.path.getsize(file)
    # 文件比上次读到的还短：换了一天的文件，或者被清空了，从头给最后几行
    reset = offset < 0 or offset > size
    start = max(0, size - 2_000_000) if reset else offset
    with open(file, 'rb') as f:
        f.seek(start)
        data = f.read(min(size - start, 2_000_000))
    cut = data.rfind(b'\n') + 1
    data = data[:cut]
    lines = data.decode('utf-8', errors='replace').replace('\r\n', '\n').split('\n')[:-1]
    if reset and start > 0:
        lines = lines[1:]
    if len(lines) > tail:
        # 积攒太多（比如离开运行页一阵子）只给最后 tail 行，并让页面清空重来，免得中间缺一段
        lines = lines[-tail:]
        reset = True
    return {'date': date, 'offset': start + cut, 'text': '\n'.join(lines), 'reset': reset}


def error_folders(limit=60):
    root = os.path.join(LOG_DIR, 'error')
    if not os.path.isdir(root):
        return []
    folders = sorted((n for n in os.listdir(root) if ERROR_DIR_RE.fullmatch(n)), reverse=True)[:limit]
    return [{'name': n, 'files': sorted(f for f in os.listdir(os.path.join(root, n)) if ERROR_FILE_RE.fullmatch(f))}
            for n in folders]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_body(self, code, body, content_type):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, obj):
        self.send_body(code, json.dumps(obj, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def host_allowed(self):
        """只认本机地址，防止别的网站借 DNS 重绑定读写配置"""
        return self.headers.get('Host') in (f'127.0.0.1:{PORT}', f'localhost:{PORT}')

    def do_GET(self):
        path, _, query = self.path.partition('?')
        params = {k: v[-1] for k, v in parse_qs(query).items()}
        if not self.host_allowed():
            return self.send_json(403, {'error': 'forbidden'})
        if path == '/api/config':
            with LOCK:
                config = ZjcsConfig(CONFIG_NAME)
            return self.send_json(200, {'data': config.data, 'argument': config.argument, 'file': config.file})
        if path == '/api/status':
            return self.send_json(200, status())
        if path == '/api/log':
            date = params.get('date') or datetime.date.today().isoformat()
            if not DATE_RE.fullmatch(date):
                return self.send_json(400, {'error': 'bad date'})
            try:
                offset, tail = int(params.get('offset', -1)), max(1, min(int(params.get('tail', 300)), 20000))
            except ValueError:
                return self.send_json(400, {'error': 'bad request'})
            return self.send_json(200, read_log(date, offset, tail))
        if path == '/api/logs':
            return self.send_json(200, {'dates': log_dates(), 'errors': error_folders(),
                                        'history': read_history(CONFIG_NAME, limit=500)})
        if path.startswith('/api/error/'):
            parts = path.split('/')[3:]
            if len(parts) != 2 or not ERROR_DIR_RE.fullmatch(parts[0]) or not ERROR_FILE_RE.fullmatch(parts[1]):
                return self.send_json(404, {'error': 'not found'})
            file = os.path.join(LOG_DIR, 'error', parts[0], parts[1])
            if not os.path.isfile(file):
                return self.send_json(404, {'error': 'not found'})
            with open(file, 'rb') as f:
                return self.send_body(200, f.read(), 'image/png')
        if path == '/api/screenshot':
            png, error = cached_screenshot()
            if not png:
                return self.send_json(503, {'error': error})
            return self.send_body(200, png, 'image/png')
        if path in STATIC:
            name, content_type = STATIC[path]
            with open(os.path.join(WEBUI, name), 'rb') as f:
                return self.send_body(200, f.read(), content_type)
        return self.send_json(404, {'error': 'not found'})

    def do_POST(self):
        if not self.host_allowed():
            return self.send_json(404, {'error': 'not found'})
        # 只接受本页面发的请求：带自定义请求头的跨站请求要先过预检，这里不回预检，浏览器会直接拦下
        if self.headers.get('X-Zjcs') != '1' or 'application/json' not in self.headers.get('Content-Type', ''):
            return self.send_json(403, {'error': 'forbidden'})
        length = int(self.headers.get('Content-Length') or 0)
        if not 0 < length <= 1_000_000:
            return self.send_json(400, {'error': 'bad request'})
        try:
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except ValueError:
            return self.send_json(400, {'error': 'bad request'})
        if not isinstance(body, dict):
            return self.send_json(400, {'error': 'bad request'})

        if self.path == '/api/config':
            data = body.get('data')
            if not isinstance(data, dict):
                return self.send_json(400, {'error': 'bad request'})
            with LOCK:
                config = ZjcsConfig(CONFIG_NAME)
                errors = apply(config, data)
                if errors:
                    return self.send_json(400, {'errors': errors})
                config.save()
            return self.send_json(200, {'data': config.data})
        if self.path == '/api/run/start':
            error = start_scheduler()
            return self.send_json(409 if error else 200, {'error': error} if error else {'ok': True})
        if self.path == '/api/run/stop':
            if body.get('force'):
                return self.send_json(200, {'ok': force_stop()})
            runtime = read_runtime(CONFIG_NAME)
            if not runtime.get('alive'):
                return self.send_json(409, {'error': '没在运行'})
            if runtime.get('mode') == 'task':
                return self.send_json(409, {'error': '命令行单独跑的任务不接收停止指令，只能强制停止'})
            send_command(CONFIG_NAME, {'action': 'stop'})
            return self.send_json(200, {'ok': True})
        if self.path == '/api/run/task':
            task = body.get('task')
            if task not in task_names(current_config()):
                return self.send_json(400, {'error': '没有这个任务'})
            send_command(CONFIG_NAME, {'action': 'run_now', 'task': task})
            started = False
            if not read_runtime(CONFIG_NAME).get('alive'):
                started = not start_scheduler()
            return self.send_json(200, {'ok': True, 'started': started})
        if self.path == '/api/device/check':
            return self.send_json(200, check_device())
        if self.path == '/api/notify/test':
            error = send_toast('一条龙 · 测试通知', '看到这条，说明出问题时你能收到提醒。')
            return self.send_json(200, {'ok': not error, 'error': error})
        return self.send_json(404, {'error': 'not found'})


def main():
    global CONFIG_NAME, PORT
    parser = argparse.ArgumentParser(description='zjcs 配置界面')
    parser.add_argument('--port', type=int, default=22367)
    parser.add_argument('--config', default='zjcs')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    args = parser.parse_args()
    CONFIG_NAME, PORT = args.config, args.port
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    url = f'http://127.0.0.1:{PORT}'
    print(f'配置界面: {url}（Ctrl+C 退出）')
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
