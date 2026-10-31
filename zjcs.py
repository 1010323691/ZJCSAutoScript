"""
杖剑传说（zjcs）自动化脚本入口，结构参考 AzurLaneAutoScript 的 alas.py。

用法：
    .venv\\Scripts\\python.exe zjcs.py                # 按调度执行所有到期的已启用任务，跑完退出
    .venv\\Scripts\\python.exe zjcs.py --loop         # 常驻：跑完后等到下一次刷新继续
    .venv\\Scripts\\python.exe zjcs.py --task UiTest  # 只跑指定任务，不看调度、不写状态

配置界面（gui.py）也是用 --loop 启动它；两边通过 module/runtime.py 里的文件通信，同一个配置同时只能跑一个。
"""
import argparse
import datetime
import logging
import os
import re
import sys
import time
from functools import cached_property

from module.base.utils import save_image
from module.config.config import TASK_ORDER, ZjcsConfig
from module.exception import (GameNotRunningError, GamePageUnknownError, GameStuckError, GameTooManyClickError,
                              RequestHumanTakeover, ScriptError, TaskEnd, TaskNotImplemented)
from module.logger import LOG_DIR, logger
from module.notify import notify
from module.runtime import Runtime, append_history, now_iso, take_commands


def underscore(name):
    """GeneralShop -> general_shop"""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


class ZjcsAutoScript:
    def __init__(self, config_name='zjcs', runtime=None):
        logger.hr('Start', level=0)
        self.config_name = config_name
        self.runtime = runtime or Runtime(config_name, 'once')
        self.stop_requested = False
        # 当前任务保存的错误截图目录，写进运行记录，配置界面里点得开
        self.error_folder = None
        # main() 里挂上的 LastProblem，每个任务开始时清空，停下的原因只取本任务里的错误
        self.problem = None

    @cached_property
    def config(self):
        return ZjcsConfig(self.config_name)

    @cached_property
    def device(self):
        from module.device.device import Device
        return Device(self.config)

    def run(self, command):
        """
        执行一个任务。

        Returns:
            str: 'success' / 'skip'（还没实现）/ 'failed'
        """
        try:
            if command != 'Restart' and not self.device.app_is_running():
                logger.warning('游戏不在前台，先启动游戏')
                self.restart()
            self.device.screenshot()
            if self.__getattribute__(underscore(command))() is False:
                # 任务自己判断没做完（比如等不到结算、匹配不上），不抛异常也要记失败，按连续失败上限重试
                logger.warning(f'任务 {command} 没有完成')
                self.save_error_log()
                return 'failed'
            return 'success'
        except TaskEnd:
            return 'success'
        except TaskNotImplemented as e:
            logger.warning(f'任务 {command} 还没打通，跳过: {e}')
            return 'skip'
        except (GameStuckError, GameTooManyClickError, GamePageUnknownError, GameNotRunningError) as e:
            logger.error(f'任务 {command} 出错: {type(e).__name__} {e}')
            self.save_error_log()
            # 先试着不重启回到家园（多半是没关掉的弹窗，点外面就关）；回不去再重启游戏。
            # 本任务都记一次失败，连续失败到上限会停下来请求人工
            if isinstance(e, GameNotRunningError) or not self.recover():
                self.restart()
            return 'failed'
        except (ScriptError, RequestHumanTakeover):
            self.save_error_log()
            raise

    def recover(self):
        """
        出错后先不重启：识别当前页面（认不出时会点上方空白处关弹窗，见 UI.ui_get_current_page），
        能回到家园就接着跑下一项（用户 10-31：认不出的弹窗一般点一下四周就关）。
        """
        from module.ui.page import page_home
        from module.ui.ui import UI
        logger.info('先试着不重启，回到家园')
        self.device.stuck_record_clear()
        self.device.click_record.clear()
        try:
            UI(self.config, device=self.device).ui_ensure(page_home)
        except (GameStuckError, GameTooManyClickError, GamePageUnknownError, GameNotRunningError) as e:
            logger.warning(f'回不到家园（{type(e).__name__}），重启游戏')
            return False
        logger.info('已回到家园，不用重启')
        return True

    def restart(self):
        from module.handler.login import LoginHandler
        LoginHandler(self.config, device=self.device).app_restart()

    def save_error_log(self):
        """把最近的截图存到 log/error/<时间>/，方便排查"""
        if 'device' not in self.__dict__:
            return
        folder = os.path.join(LOG_DIR, 'error', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        for ts, image in self.device.screenshot_deque:
            name = datetime.datetime.fromtimestamp(ts).strftime('%H%M%S_%f')[:-3]
            save_image(image, os.path.join(folder, f'{name}.png'))
        self.error_folder = os.path.basename(folder)
        logger.info(f'错误截图已保存: {folder}')

    # ---------------- 任务 ----------------
    def ui_test(self):
        from module.ui.ui import UI
        return UI(self.config, device=self.device).ui_test()

    def general_shop(self):
        from module.shop.shop import GeneralShop
        return GeneralShop(self.config, device=self.device).run()

    def vault(self):
        from module.shop.shop import Vault
        return Vault(self.config, device=self.device).run()

    def candy_tree(self):
        from module.home.home import CandyTree
        return CandyTree(self.config, device=self.device).run()

    def cart(self):
        from module.home.home import Cart
        return Cart(self.config, device=self.device).run()

    def home_house(self):
        from module.home.house import HomeHouse
        return HomeHouse(self.config, device=self.device).run()

    def daily_dungeon(self):
        from module.note.dungeon import DailyDungeon
        return DailyDungeon(self.config, device=self.device).run()

    def bond_adventure(self):
        from module.note.bond import BondAdventure
        return BondAdventure(self.config, device=self.device).run()

    def fate_fruit(self):
        from module.note.fate import FateFruit
        return FateFruit(self.config, device=self.device).run()

    def arena(self):
        from module.note.arena import Arena
        return Arena(self.config, device=self.device).run()

    def material_realm(self):
        from module.note.material import MaterialRealm
        return MaterialRealm(self.config, device=self.device).run()

    def holy_beast_trial(self):
        from module.activity.activity import HolyBeastTrial
        return HolyBeastTrial(self.config, device=self.device).run()

    def twin_shadow(self):
        from module.activity.activity import TwinShadow
        return TwinShadow(self.config, device=self.device).run()

    def guild_idle_reward(self):
        from module.guild.guild import GuildIdleReward
        return GuildIdleReward(self.config, device=self.device).run()

    def guild_donate(self):
        from module.guild.guild import GuildDonate
        return GuildDonate(self.config, device=self.device).run()

    def guild_war(self):
        from module.guild.guild import GuildWar
        return GuildWar(self.config, device=self.device).run()

    def guild_raid(self):
        from module.guild.guild import GuildRaid
        return GuildRaid(self.config, device=self.device).run()

    def daily_reward(self):
        from module.reward.reward import DailyReward
        return DailyReward(self.config, device=self.device).run()

    # ---------------- 调度 ----------------
    def task_name(self, task):
        return self.config.argument.get(task, {}).get('_name', task)

    def handle_commands(self):
        """
        处理配置界面发来的指令。只在两个任务之间调用，所以停止都是「做完当前任务再停」。

        Returns:
            bool: 是否要停下
        """
        for command in take_commands(self.config_name):
            action = command.get('action')
            if action == 'run_now':
                self.config.request_run_now(command.get('task'))
            elif action == 'stop' and not self.stop_requested:
                logger.info('收到停止指令')
                self.stop_requested = True
                self.runtime.update(stopping=True)
        return self.stop_requested

    def run_task(self, task):
        """执行一个任务，并写运行记录"""
        started = now_iso()
        self.error_folder = None
        if self.problem:
            self.problem.message = ''
        self.runtime.update(state='running', task=task, task_started=started, next_run=None)
        logger.hr(task, level=1)
        result = 'error'
        try:
            result = self.run(task)
        except RequestHumanTakeover:
            result = 'human'
            raise
        finally:
            # runtime 里的 task 留到下一个任务开始、进入等待或停下时再换，界面不会在两项之间闪成「正在启动」
            append_history(self.config_name, {'task': task, 'start': started, 'end': now_iso(), 'result': result,
                                              'error': self.error_folder})
        logger.info(f'任务 {task} 结果: {result}')
        return result

    def run_single(self, task):
        if task not in TASK_ORDER + ['Restart']:
            logger.critical(f'没有任务 {task}，可选: {", ".join(TASK_ORDER + ["Restart"])}')
            return 1
        result = self.run_task(task)
        return 0 if result == 'success' else 1

    def notify_finish(self, results):
        labels = {'success': '完成', 'skip': '跳过', 'failed': '失败'}
        counts = [f'{label} {sum(1 for _, r in results if r == key)}' for key, label in labels.items()
                  if any(r == key for _, r in results)]
        failed = [self.task_name(t) for t, r in results if r == 'failed']
        body = '，'.join(counts) + (f'。失败的：{"、".join(failed)}' if failed else '')
        notify(self.config, 'Finish', 'ZJCSAutoScript 跑完了', body)

    def wait_until(self, next_run):
        """
        等到 next_run。每 2 秒看一次指令；每 10 秒重读一次配置，刚打开的任务从没跑过，会马上到期。

        Returns:
            bool: 是否要停下
        """
        self.runtime.update(state='waiting', next_run=next_run.isoformat(timespec='seconds'), task=None, task_started=None)
        tick = 0
        while datetime.datetime.now() < next_run:
            if self.handle_commands():
                return True
            if self.config.run_now_tasks():
                return False
            tick += 1
            if tick % 5 == 0:
                self.config.reload()
                earliest = self.config.earliest_next_run()
                if earliest is not None and earliest < next_run:
                    return False
            time.sleep(2)
        return False

    def loop(self, forever=False):
        """
        Returns:
            str: 停下的原因，done（到期的都跑完了）/ empty（没有开着的任务）/ stopped（按了停止）
        """
        results = []
        while 1:
            if self.handle_commands():
                logger.info('已按指令停止')
                return 'stopped'
            self.config.reload()
            task = self.config.get_next_task()
            if task is None:
                next_run = self.config.earliest_next_run()
                if results:
                    self.notify_finish(results)
                    results = []
                if next_run is None:
                    logger.info('没有开着的任务，退出')
                    return 'empty'
                if not forever:
                    logger.info('没有到期的任务，退出')
                    return 'done'
                logger.info(f'没有到期的任务，等待到 {next_run}')
                if self.wait_until(next_run):
                    logger.info('已按指令停止')
                    return 'stopped'
                continue

            # 手动立即执行的不算进「每天跑完」的汇总，只点了一项时也不会发
            manual = task in self.config.run_now_tasks()
            result = self.run_task(task)
            if not manual:
                results.append((task, result))
            self.config.task_done(task, success=result == 'success', skip=result == 'skip')


class LastProblem(logging.Handler):
    """记住最后一条错误日志，停下时作为原因显示在配置界面和通知里"""

    def __init__(self):
        super().__init__(logging.ERROR)
        self.message = ''

    def emit(self, record):
        self.message = record.getMessage()


def main():
    parser = argparse.ArgumentParser(description='杖剑传说自动化')
    parser.add_argument('--config', default='zjcs', help='配置名，对应 config/<名字>.yaml')
    parser.add_argument('--task', help='只执行指定任务，例如 UiTest')
    parser.add_argument('--loop', action='store_true', help='常驻运行，等待下一次刷新')
    args = parser.parse_args()

    runtime = Runtime(args.config, 'task' if args.task else 'loop' if args.loop else 'once')
    other = runtime.other_instance()
    if other:
        # 两个进程同时操作同一台模拟器会互相干扰
        logger.critical(f'配置 {args.config} 已经有一个脚本在运行（pid {other}），不重复启动')
        return 1
    problem = LastProblem()
    logger.addHandler(problem)
    runtime.start()
    script = ZjcsAutoScript(args.config, runtime=runtime)
    script.problem = problem

    def stop_with_problem(reason, message):
        runtime.stop(reason, message)
        try:
            notify(script.config, 'Human', 'ZJCSAutoScript 停下了，需要你看一下', message)
        except Exception as e:
            logger.warning(f'发通知时出错: {e}')

    try:
        if args.task:
            code = script.run_single(args.task)
            runtime.stop('task')
            return code
        runtime.stop(script.loop(forever=args.loop))
        return 0
    except RequestHumanTakeover:
        # 抛出前一般已经用 critical 写了原因（连续失败、设备不在线），拿它当停下的原因
        reason = problem.message or '需要人工处理'
        logger.critical('需要人工处理，脚本已停止')
        stop_with_problem('human', reason)
        return 1
    except ScriptError as e:
        logger.critical(f'脚本错误: {e}')
        stop_with_problem('error', f'脚本错误: {e}')
        return 1
    except KeyboardInterrupt:
        logger.info('已手动中断')
        runtime.stop('stopped')
        return 1
    except Exception as e:
        logger.exception(f'没有处理的异常: {e}')
        stop_with_problem('error', f'{type(e).__name__}: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
