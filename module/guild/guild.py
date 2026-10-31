import datetime
import re
import time

import cv2

from module.activity.assets import REWARD_BADGE
from module.base.button import ClickArea
from module.base.timer import Timer
from module.exception import GamePageUnknownError
from module.guild.assets import *
from module.logger import logger
from module.ocr.ocr import ocr_lines, ocr_single_line
from module.ui.assets import BACK_ARROW, BATTLE_RESULT_CLOSE, GET_REWARD_CHECK
from module.ui.page import page_guild, page_guild_activity, page_guild_hall, page_guild_raid
from module.ui.ui import UI

# 公会场景里建筑标签可能出现的范围（避开顶部公会名、底部聊天框）
GUILD_SCENE_REGION = (0, 100, 720, 1040)
# 讨伐页「挑战」按钮右上角红点的范围
RAID_DOT_REGION = (455, 930, 525, 1000)


class GuildUI(UI):
    def ui_goto_guild_activity(self):
        """去远征之门（公会活动页）。已经在公会活动或它的子页面时直接返回上去"""
        page = self.ui_get_current_page()
        if page in (page_guild_activity, page_guild_raid):
            self.ui_goto(page_guild_activity, skip_first_screenshot=False)
            return
        self.ui_goto(page_guild, skip_first_screenshot=True)
        self.goto_building(GUILD_EXPEDITION_LABEL, PAGE_GUILD_ACTIVITY, '远征之门')

    def goto_building(self, label, check, name):
        """公会场景里找建筑标签并点进去。当前视野没有就滑到最左端再一步步往右找"""
        if self.click_building(label, check, name):
            return
        for _ in range(4):
            self.device.swipe((100, 450), (650, 450), duration=600, name='SCENE_LEFT')
        time.sleep(1)
        if self.click_building(label, check, name):
            return
        for _ in range(4):
            self.device.swipe((650, 450), (350, 450), duration=1500, name='SCENE_RIGHT')
            time.sleep(1)
            if self.click_building(label, check, name):
                return
        logger.warning(f'公会场景里没找到{name}')
        raise GamePageUnknownError

    def click_building(self, label, check, name):
        self.device.screenshot()
        sim = label.match_region(self.device.image, GUILD_SCENE_REGION, similarity=0.85)
        if sim <= 0.85:
            return False
        logger.info(f'找到{name}（相似度 {sim:.2f}）')
        return self.ui_click(label, check_button=check, offset=(10, 10), timeout=10, skip_first_screenshot=True)


class GuildIdleReward(UI):
    def run(self):
        """点一下远征之门下方的挂机卡片，直接领取，没有红点也能领"""
        logger.hr('Guild idle reward', level=2)
        self.ui_ensure(page_guild)
        self.device.click(GUILD_IDLE_CARD)
        if not self.wait_reward_popup(page_guild, timeout=10):
            logger.warning('点了挂机卡片但没有出现「获得奖励」')


class GuildRaid(GuildUI):
    def raid_remain(self):
        """今日剩余讨伐次数，认不出数字时当作 0。偏移要很小，否则「2」会匹配到「1/2」后面的那个 2"""
        if self.appear(RAID_REMAIN_2, offset=(2, 2), similarity=0.95):
            return 2
        if self.appear(RAID_REMAIN_1, offset=(2, 2), similarity=0.95):
            return 1
        if not self.appear(RAID_REMAIN_0, offset=(2, 2), similarity=0.95):
            logger.warning('认不出剩余讨伐次数，按 0 处理')
        return 0

    def raid_dot(self):
        """「挑战」按钮右上角的红点：有剩余次数、且上一场后台战斗已经打完"""
        return REWARD_BADGE.match_region(self.device.image, RAID_DOT_REGION, similarity=0.7) > 0.7

    def wait_battle_result(self, timeout=300):
        """
        最小化后战斗在后台继续，打完**不弹结算页**（10-30 实测）。按用户说明看讨伐页：
        - 左上角剩余次数 0/2：不用等最后一场打完，直接算完成
        - 还有次数：「挑战」按钮右上角重新出现红点，就是这一场打完了
        """
        self.device.long_wait(True)
        timer = Timer(timeout).start()
        # 刚最小化回来那一下红点可能还没刷新，过几秒再开始判断
        settle = Timer(3).start()
        try:
            while 1:
                self.device.screenshot()
                if timer.reached():
                    logger.warning(f'{timeout} 秒内没有等到讨伐打完')
                    return False
                # 以前的设计是等结算页，万一弹了照样关掉
                if self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20), interval=2):
                    self.device.click(BATTLE_RESULT_CLOSE)
                    continue
                if settle.reached() and self.appear(PAGE_GUILD_RAID, offset=(10, 10)):
                    if self.raid_remain() <= 0:
                        logger.info('剩余讨伐次数 0，不等最后一场打完')
                        return True
                    if self.raid_dot():
                        logger.info('「挑战」按钮重新出现红点，这次讨伐打完了')
                        return True
                time.sleep(2)
        finally:
            self.device.long_wait(False)

    def run(self):
        """挑战 → 开始战斗 → 立刻点左下最小化返回 → 等这一场打完（见 wait_battle_result），打到次数用完"""
        logger.hr('Guild raid', level=2)
        self.ui_goto_guild_activity()
        self.ui_goto(page_guild_raid, skip_first_screenshot=False)
        for count in range(1, self.config.GuildRaid_Challenges + 1):
            self.device.screenshot()
            remain = self.raid_remain()
            logger.attr('RaidRemain', remain)
            if remain <= 0:
                logger.info('今日讨伐次数已用完')
                break
            logger.info(f'公会讨伐第 {count} 次')
            if not self.ui_click(RAID_CHALLENGE, check_button=RAID_START, timeout=15):
                return False
            if not self.ui_click(RAID_START, check_button=BATTLE_MINIMIZE, timeout=20):
                return False
            self.ui_click(BATTLE_MINIMIZE, check_button=PAGE_GUILD_RAID, offset=(10, 10), timeout=20)
            if not self.wait_battle_result():
                return False


# 第几次捐赠（已捐次数 0/1/2）→ 按钮上应有的模板和确认框里的晨星数。第 4 次要 100 晨星，不做
DONATE_STEPS = [
    (DONATE_COUNT_0, DONATE_FREE, None),
    (DONATE_COUNT_1, DONATE_20, DONATE_CONFIRM_20),
    (DONATE_COUNT_2, DONATE_50, DONATE_CONFIRM_50),
]


class GuildDonate(GuildUI):
    """
    公会大厅 → 公会捐赠（用户要求，10-30）：每天捐 3 次，第 1 次免费，第 2、3 次各 20、50 晨星。
    已捐次数和按钮价格都对得上才点；付费的还要确认框里的晨星数也对得上才点确定。
    """

    def donate_done(self):
        for done, (count, _, _) in enumerate(DONATE_STEPS):
            if self.appear(count, offset=(5, 5), similarity=0.92):
                return done
        return None

    def run(self):
        logger.hr('Guild donate', level=2)
        if self.ui_get_current_page() != page_guild_hall:
            self.ui_goto(page_guild, skip_first_screenshot=True)
            self.goto_building(GUILD_HALL_LABEL, PAGE_GUILD_HALL, '公会大厅')
        if not self.ui_click(PAGE_GUILD_HALL, check_button=DONATE_DIALOG, offset=(10, 10), timeout=10):
            return False
        times = min(int(self.config.GuildDonate_Times), len(DONATE_STEPS))
        for _ in range(times + 1):
            time.sleep(1)
            self.device.screenshot()
            done = self.donate_done()
            if done is None or done >= times:
                logger.info(f'今天已捐赠 {"3 次以上" if done is None else f"{done} 次"}，不再捐')
                break
            _, button, confirm = DONATE_STEPS[done]
            if not self.appear(button, offset=(5, 5), similarity=0.92):
                logger.warning(f'已捐 {done} 次，但按钮价格和预期不符，停止')
                break
            logger.info(f'第 {done + 1} 次捐赠')
            self.device.click(button)
            if confirm is None:
                continue
            timer = Timer(6).start()
            while 1:
                self.device.screenshot()
                if self.appear(confirm, offset=(5, 5), similarity=0.92):
                    # 确认框有弹出动画
                    time.sleep(0.5)
                    self.device.click(confirm)
                    break
                if timer.reached():
                    logger.warning('没有等到晨星数对得上的确认框，停止')
                    self.device.back()
                    return False
        self.device.click_record.clear()
        # 关掉捐赠弹窗。原来按返回键，10-31 捐完正赶上动画被吞掉，弹窗一直开着，下一个任务认不出页面
        self.ui_close_popup(DONATE_DIALOG, PAGE_GUILD_HALL)
        return True


# 公会战开放时间（用户规则 Q13）：周一、三、五，本机时间 11:00～23:00
GUILD_WAR_WEEKDAYS = (0, 2, 4)
GUILD_WAR_OPEN = datetime.time(11, 0)
GUILD_WAR_CLOSE = datetime.time(23, 0)
# 对战地图两列：左边我方、右边敌方，两列一起滚动。y < 195 是顶部公会名和比分
OWN_COLUMN = (30, 195, 290, 1200)
ENEMY_COLUMN = (440, 195, 690, 1200)
# 战力行要完整在画面里才认，被上下边缘切到的会认错（10-30 实测 20.2 认成 20.21）
POWER_Y_RANGE = (305, 1150)
POWER_RE = re.compile(r'(\d+(?:\.\d+)?)亿')
# 相对战力行的位置：名字在上方 27 像素；「击破」「已挑战」印章在上方约 84 像素；头像在上方 62～195 像素
NAME_DY = -27
STAMP_DY = (-110, -50)
AVATAR_DY = -80
# 自己那一条名字是黄色的，其他人是白色。黄色像素占比：自己 0.16～0.25，别人 ≤ 0.01
OWN_YELLOW_RATIO = 0.05
SCROLL_LIMIT = 15


class GuildWar(GuildUI):
    """
    用户规则 Q13（10-30）：周一、三、五 11:00～23:00 开放，每天最多打 3 场。
    从上往下找第一个战力 ≤ 自身战力 × 80% 的对手，打过的不再打。
    盖了「击破」「已挑战」章的对手都打不了，直接跳过（用户确认，10-30）。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attacked = set()

    def check_open_time(self):
        """
        Returns:
            bool: 现在是不是开放时间。还没到今天的开放时间就申请 11:01 再跑
        """
        now = datetime.datetime.now()
        if now.weekday() not in GUILD_WAR_WEEKDAYS:
            logger.info('今天不是公会战日（周一、三、五）')
            return False
        if now.time() < GUILD_WAR_OPEN:
            logger.info('公会战还没开放')
            self.config.task_delay('GuildWar', datetime.datetime.combine(now.date(), GUILD_WAR_OPEN)
                                   + datetime.timedelta(minutes=1))
            return False
        if now.time() >= GUILD_WAR_CLOSE:
            logger.info('今天的公会战已经结束')
            return False
        return True

    def enter_map(self):
        """
        远征之门 → 公会战卡片 → 进入对战 → 对战地图。进来默认就在最上面（用户说明，10-30）

        Returns:
            bool: 没有「进入对战」按钮（没开放）返回 False
        """
        self.device.screenshot()
        if self.appear(PAGE_GUILD_WAR_MAP, offset=(10, 10)):
            # 上次中断时停在地图中间，重进一次回到最上面
            return self.reenter_map()
        self.ui_goto_guild_activity()
        self.device.click(GUILD_WAR_CARD)
        if not self.wait_until_appear(GUILD_WAR_ENTER, offset=(10, 10), timeout=8):
            logger.warning('公会战页面没有「进入对战」按钮')
            self.leave_war()
            return False
        return self.ui_click(GUILD_WAR_ENTER, check_button=PAGE_GUILD_WAR_MAP, offset=(10, 10), timeout=15,
                             skip_first_screenshot=True)

    def reenter_map(self):
        """退回公会战页面再点「进入对战」，地图回到最上面。比一次次往上拖快"""
        if self.ui_click(BACK_ARROW, check_button=GUILD_WAR_ENTER, offset=(10, 10), retry_wait=3, timeout=15):
            return self.ui_click(GUILD_WAR_ENTER, check_button=PAGE_GUILD_WAR_MAP, offset=(10, 10), timeout=15,
                                 skip_first_screenshot=True)
        logger.warning('从地图返回后没有看到「进入对战」')
        return False

    def leave_war(self):
        """左下返回，回到远征之门"""
        self.ui_click(BACK_ARROW, check_button=PAGE_GUILD_ACTIVITY, offset=(10, 10), retry_wait=3, timeout=20)

    @staticmethod
    def parse_power(text):
        """'哭14.2亿' -> 14.2。没有小数点却 ≥ 100 的是漏认了小数点，返回 None"""
        res = POWER_RE.search(text.replace(' ', ''))
        if not res:
            return None
        value = float(res.group(1))
        if '.' not in res.group(1) and value >= 100:
            return None
        return value

    def scan_column(self, area):
        """
        识别当前画面一列里完整显示的成员。

        Returns:
            list: [(战力行 y, 名字, 战力, 印章)]，从上到下。印章是「击破」「已挑战」或空字符串
        """
        lines = ocr_lines(self.device.image, area)
        members = []
        for x, y, text, _ in lines:
            if '亿' not in text or not POWER_Y_RANGE[0] <= y <= POWER_Y_RANGE[1]:
                continue
            # 整列识别偶尔漏小数点，单独把这一行放大再认一次
            power = self.parse_power(ocr_single_line(self.device.image, (area[0] + 60, y - 16, area[2] - 60, y + 16)))
            if power is None:
                power = self.parse_power(text)
            if power is None:
                logger.warning(f'认不出战力：{text}')
                continue
            name = ''.join(t for _, ny, t, _ in lines if abs(ny - (y + NAME_DY)) <= 10)
            stamp = ''.join(t for _, sy, t, _ in lines
                            if STAMP_DY[0] <= sy - y <= STAMP_DY[1] and ('击破' in t or '挑战' in t))
            members.append((y, name, power, stamp))
        return members

    def is_own(self, y):
        """左列这一条是不是自己（名字是黄色的）"""
        x1 = OWN_COLUMN[0]
        hsv = cv2.cvtColor(self.device.image[y - 42:y - 22, x1 + 90:x1 + 190], cv2.COLOR_RGB2HSV)
        yellow = (hsv[..., 0] >= 18) & (hsv[..., 0] <= 35) & (hsv[..., 1] >= 90) & (hsv[..., 2] >= 170)
        return yellow.mean() > OWN_YELLOW_RATIO

    def map_signature(self):
        """右列文字和位置。头像有火焰动画，整张图比较判断不了有没有滚动，只看文字"""
        return [(y, text) for _, y, text, _ in ocr_lines(self.device.image, ENEMY_COLUMN)]

    @staticmethod
    def same_signature(a, b):
        return len(a) == len(b) and all(ta == tb and abs(ya - yb) <= 15 for (ya, ta), (yb, tb) in zip(a, b))

    def scroll_down(self):
        """
        往下慢拖约 450 像素，两列一起滚，相邻两屏有重叠，不会漏人。只往下拖：进地图默认在最上面（用户说明，10-30）

        Returns:
            bool: 画面有没有动（没动说明到底了）
        """
        before = self.map_signature()
        self.device.swipe((360, 950), (360, 500), duration=1500, name='WAR_MAP_DOWN')
        time.sleep(1)
        self.device.screenshot()
        return not self.same_signature(before, self.map_signature())

    def get_own_power(self, limit_ratio):
        """
        从最上面往下找左列名字是黄色的那一条，顺便记下路过的敌方。

        Returns:
            tuple: (自身战力, 已经滑过去的敌方里有没有能打的)，没找到自己返回 (None, False)
        """
        passed = {}
        for _ in range(SCROLL_LIMIT):
            enemies = self.scan_column(ENEMY_COLUMN)
            for y, name, power, _ in self.scan_column(OWN_COLUMN):
                if self.is_own(y):
                    logger.attr('OwnPower', f'{name} {power}亿')
                    limit = power * limit_ratio
                    visible = {e[1] for e in enemies}
                    missed = [n for n, (p, stamp) in passed.items() if n not in visible and not stamp and p <= limit]
                    return power, bool(missed)
            for _, name, power, stamp in enemies:
                passed[name] = (power, stamp)
            if not self.scroll_down():
                break
        return None, False

    def find_target(self, limit):
        """
        从当前画面往下找第一个能打的对手：没被「击破」、今天没挑战过、战力 ≤ limit。
        当前画面上面的人之前都看过、不符合条件，打完一场地图停在原位，接着往下找就行。

        Returns:
            tuple: (战力行 y, 名字, 战力)，没有返回 None
        """
        self.device.screenshot()
        for _ in range(SCROLL_LIMIT):
            for y, name, power, stamp in self.scan_column(ENEMY_COLUMN):
                if stamp or name in self.attacked:
                    continue
                if power <= limit:
                    logger.info(f'目标：{name} {power}亿')
                    return y, name, power
            if not self.scroll_down():
                break
        return None

    def attack(self, y, name):
        """
        点对手头像 → 进攻对手弹窗（读剩余挑战次数）→ 前往挑战 → 开始战斗 → 关掉结算 → 回到地图

        Returns:
            bool: 打了返回 True；剩余次数 0 返回 False；出错返回 None
        """
        self.device.click(ClickArea(f'WAR_ENEMY_{name}', (555, y + AVATAR_DY - 10, 575, y + AVATAR_DY + 10)))
        if not self.wait_until_appear(GUILD_WAR_ATTACK, offset=(10, 10), timeout=6):
            logger.warning('点头像后没有出现「进攻对手」弹窗')
            return None
        time.sleep(0.5)
        self.device.screenshot()
        text = ocr_single_line(self.device.image, (200, 990, 520, 1030), scale=1)
        logger.attr('WarRemain', text)
        res = re.search(r'(\d+)$', text.strip())
        if res is None:
            logger.warning(f'认不出剩余挑战次数：{text}')
            self.device.back()
            return None
        if int(res.group(1)) <= 0:
            logger.info('今日公会战挑战次数已用完')
            self.device.back()
            return False
        logger.info(f'挑战 {name}')
        self.attacked.add(name)
        if not self.ui_click(GUILD_WAR_GOTO, check_button=GUILD_WAR_START, offset=(10, 10), timeout=15):
            return None
        self.device.long_wait(True)
        try:
            if not self.ui_click(GUILD_WAR_START, check_button=BATTLE_RESULT_CLOSE, offset=(10, 10),
                                 retry_wait=5, timeout=300):
                return None
        finally:
            self.device.long_wait(False)
        timer = Timer(20).start()
        while 1:
            self.device.screenshot()
            if self.appear(PAGE_GUILD_WAR_MAP, offset=(10, 10)) \
                    and not self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20)):
                return True
            if timer.reached():
                raise GamePageUnknownError
            if self.appear(BATTLE_RESULT_CLOSE, offset=(20, 20), interval=2):
                self.device.click(BATTLE_RESULT_CLOSE)
                continue
            if self.ui_additional():
                continue
            time.sleep(0.5)

    def run(self):
        logger.hr('Guild war', level=2)
        if not self.check_open_time():
            return None
        if not self.enter_map():
            return None
        own, missed = self.get_own_power(self.config.GuildWar_PowerRatio)
        if own is None:
            logger.warning('地图上没找到自己的战力')
            return False
        limit = round(own * self.config.GuildWar_PowerRatio, 2)
        logger.attr('PowerLimit', f'{limit}亿')
        if missed:
            logger.info('找自己战力时滑过了能打的对手，重进地图从最上面找')
            if not self.reenter_map():
                return False
        for count in range(1, self.config.GuildWar_Challenges + 1):
            target = self.find_target(limit)
            if target is None:
                logger.info('没有符合条件的对手了')
                break
            logger.info(f'公会战第 {count} 场')
            result = self.attack(target[0], target[1])
            if result is None:
                return False
            if result is False:
                break
            self.device.click_record.clear()
        self.leave_war()
        return True
