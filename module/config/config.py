import datetime
import json
import os

import yaml

from module.exception import RequestHumanTakeover
from module.logger import ROOT, logger
from module.runtime import write_json, write_text

# 日常任务的执行顺序，和需求清单顺序一致
TASK_ORDER = [
    'UiTest',
    'GeneralShop',
    'Vault',
    'CandyTree',
    'Cart',
    'HomeHouse',
    'DailyDungeon',
    'BondAdventure',
    'FateFruit',
    'Arena',
    'MaterialRealm',
    'HolyBeastTrial',
    'TwinShadow',
    'GuildIdleReward',
    'GuildDonate',
    'GuildWar',
    'GuildRaid',
    'DailyReward',
]


ARGUMENT_FILE = os.path.join(ROOT, 'module', 'config', 'argument.yaml')


def load_argument():
    """读参数定义表 argument.yaml"""
    with open(ARGUMENT_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class ZjcsConfig:
    def __init__(self, config_name='zjcs'):
        self.config_name = config_name
        self.file = os.path.join(ROOT, 'config', f'{config_name}.yaml')
        self.state_file = os.path.join(ROOT, 'config', f'{config_name}.state.json')
        self.argument = load_argument()

        self.load_data()
        if not os.path.exists(self.file):
            self.save()
            logger.info(f'首次运行，已按默认值生成配置: {self.file}')

        # 运行状态（下次运行时间、连续失败次数）单独存 json
        self.state = {}
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)

    def load_data(self):
        """读 yaml：默认值来自参数定义表，用户配置覆盖默认值"""
        user = {}
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding='utf-8') as f:
                user = yaml.safe_load(f) or {}
        self.data = {}
        for group, args in self.argument.items():
            self.data[group] = {}
            for arg, define in args.items():
                if arg.startswith('_'):
                    continue
                self.data[group][arg] = user.get(group, {}).get(arg, define['value'])
        self._flat = {}
        for group, args in self.data.items():
            for arg, value in args.items():
                self._flat[f'{group}_{arg}'] = value

    def reload(self):
        """常驻运行时每个任务开始前重读，配置界面保存的改动不用重启就生效"""
        try:
            self.load_data()
        except (OSError, yaml.YAMLError) as e:
            logger.warning(f'重读配置失败，继续用旧配置: {e}')

    def save(self):
        """配置界面保存时调用，把 self.data 写回 yaml"""
        # 常驻的调度进程随时会重读，不能让它读到写了一半的文件
        write_text(self.file, '# 由配置界面（gui.py）生成，也可以手改。参数含义见 module/config/argument.yaml\n'
                   + yaml.safe_dump(self.data, allow_unicode=True, sort_keys=False))

    def __getattr__(self, item):
        # 用 config.Group_Arg 读配置，例如 config.Device_Serial、config.Arena_BuyTickets
        flat = self.__dict__.get('_flat', {})
        if item in flat:
            return flat[item]
        raise AttributeError(f'配置里没有 {item}')

    # ---------- 调度 ----------
    def is_enabled(self, task):
        return bool(self._flat.get(f'{task}_Enable', False))

    def next_server_update(self, now=None):
        """下一次服务器刷新时间，换算成本机时间（naive datetime）"""
        now = now or datetime.datetime.now()
        server_tz = datetime.timezone(datetime.timedelta(hours=float(self.Scheduler_ServerTimezone)))
        now_server = now.astimezone(server_tz)
        hour, minute = map(int, str(self.Scheduler_ServerUpdate).split(':'))
        update = now_server.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if update <= now_server:
            update += datetime.timedelta(days=1)
        return update.astimezone().replace(tzinfo=None)

    def get_next_run(self, task):
        value = self.state.get(task, {}).get('NextRun')
        if value:
            return datetime.datetime.fromisoformat(value)
        return datetime.datetime(2000, 1, 1)

    def run_now_tasks(self):
        """配置界面点了「立即执行」的任务，按点击先后排；没开开关的也执行这一次"""
        tasks = [t for t in TASK_ORDER if self.state.get(t, {}).get('RunNow')]
        return sorted(tasks, key=lambda t: self.state[t]['RunNow'])

    def pending_tasks(self, now=None):
        now = now or datetime.datetime.now()
        due = [t for t in TASK_ORDER if self.is_enabled(t) and self.get_next_run(t) <= now]
        first = self.run_now_tasks()
        return first + [t for t in due if t not in first]

    def get_next_task(self):
        """返回下一个该执行的任务名；都执行过了返回 None"""
        pending = self.pending_tasks()
        return pending[0] if pending else None

    def request_run_now(self, task):
        """插到队首：当前任务做完马上执行它"""
        if task not in TASK_ORDER:
            return False
        record = self.state.setdefault(task, {})
        if not record.get('RunNow'):
            record['RunNow'] = datetime.datetime.now().isoformat(timespec='seconds')
            self.save_state()
            logger.info(f'任务 {task} 插到队首，当前任务做完就执行')
        return True

    def earliest_next_run(self):
        runs = [self.get_next_run(t) for t in TASK_ORDER if self.is_enabled(t)]
        return min(runs) if runs else None

    def task_done(self, task, success=True, skip=False):
        """
        Args:
            success: 成功则推迟到下一次服务器刷新
            skip: 任务还没实现，也推迟到下一次刷新，但不算失败
        """
        record = self.state.setdefault(task, {})
        now = datetime.datetime.now()
        record['LastRun'] = now.isoformat(timespec='seconds')
        # 立即执行只管一次，失败了按正常调度重试
        record.pop('RunNow', None)
        if success or skip:
            record['Failure'] = 0
            next_run = self.next_server_update(now)
            # 任务申请了今天晚些时候再跑（例如公会战还没开放），就用申请的时间
            delay = record.pop('DelayUntil', None)
            if delay and now < datetime.datetime.fromisoformat(delay) < next_run:
                next_run = datetime.datetime.fromisoformat(delay)
            record['NextRun'] = next_run.isoformat(timespec='seconds')
            record['Result'] = 'skip' if skip else 'success'
            logger.info(f'任务 {task} 下次运行: {record["NextRun"]}')
        else:
            record['Failure'] = record.get('Failure', 0) + 1
            record['Result'] = 'failed'
            if record['Failure'] >= self.Scheduler_FailureLimit:
                self.save_state()
                logger.critical(f'任务 {task} 连续失败 {record["Failure"]} 次，停止运行，请人工检查')
                raise RequestHumanTakeover
        self.save_state()

    def task_delay(self, task, until):
        """任务结束后不推到下一次服务器刷新，而是 until（本机时间）再跑一次"""
        self.state.setdefault(task, {})['DelayUntil'] = until.isoformat(timespec='seconds')
        logger.info(f'任务 {task} 申请 {until} 再运行')

    def save_state(self):
        # 配置界面随时在读，不能让它读到写了一半的文件
        write_json(self.state_file, self.state)
