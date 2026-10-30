from module.activity.assets import *
from module.guild.assets import *
from module.note.assets import *
from module.shop.assets import *
from module.ui.assets import *


class Page:
    # 所有页面，key 是页面名
    all_pages = {}

    def __init__(self, name, check_button):
        """
        Args:
            name (str): 页面名，同变量名
            check_button (Button): 只在这个页面出现的识别按钮
        """
        self.name = name
        self.check_button = check_button
        self.links = {}
        self.parent = None
        Page.all_pages[name] = self

    def link(self, button, destination):
        """在本页点 button 会去到 destination"""
        self.links[destination] = button

    @classmethod
    def init_connection(cls, destination):
        """从目标页反向 BFS，给每个页面设置 parent = 去目标页的下一跳"""
        for page in cls.all_pages.values():
            page.parent = None
        visited = {destination}
        queue = [destination]
        while queue:
            current = queue.pop(0)
            for page in cls.all_pages.values():
                if page in visited:
                    continue
                if current in page.links:
                    page.parent = current
                    visited.add(page)
                    queue.append(page)

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)


# ---------------- 底部导航的 5 个主页面 ----------------
page_role = Page('page_role', PAGE_ROLE_CHECK)
page_note = Page('page_note', PAGE_NOTE_CHECK)
page_home = Page('page_home', PAGE_HOME_CHECK)
page_guild = Page('page_guild', PAGE_GUILD_CHECK)
page_world = Page('page_world', PAGE_WORLD_CHECK)

_MAIN_PAGES = [
    (page_role, NAV_ROLE),
    (page_note, NAV_NOTE),
    (page_home, NAV_HOME),
    (page_guild, NAV_GUILD),
    (page_world, NAV_WORLD),
]
# 主页面之间都能通过底部导航直达
for _page, _ in _MAIN_PAGES:
    for _dest, _nav in _MAIN_PAGES:
        if _dest is not _page:
            _page.link(_nav, _dest)

# ---------------- 公会 ----------------
# 公会 → 远征之门（公会活动）→ 公会讨伐 / 公会战，子页面都用左下「<」返回上一层。
# 公会 → 远征之门 这一步要在场景里找建筑，不能用固定坐标，由 GuildUI.ui_goto_guild_activity 处理。
page_guild_activity = Page('page_guild_activity', PAGE_GUILD_ACTIVITY)
page_guild_raid = Page('page_guild_raid', PAGE_GUILD_RAID)

page_guild_activity.link(BACK_ARROW, page_guild)
# 公会 → 公会大厅（「公会」页，有公会捐赠）同样要在场景里找建筑，由 GuildDonate 处理
page_guild_hall = Page('page_guild_hall', PAGE_GUILD_HALL)
page_guild_hall.link(BACK_ARROW, page_guild)

# ---------------- 笔记 ----------------
page_dungeon = Page('page_dungeon', PAGE_DUNGEON)
page_dungeon_detail = Page('page_dungeon_detail', PAGE_DUNGEON_DETAIL)
page_note.link(NOTE_DUNGEON, page_dungeon)
page_dungeon.link(BACK_ARROW, page_note)
page_dungeon_detail.link(BACK_ARROW, page_dungeon)

page_bond = Page('page_bond', PAGE_BOND)
page_note.link(NOTE_BOND, page_bond)
page_bond.link(BACK_ARROW, page_note)

page_map_explore = Page('page_map_explore', PAGE_MAP_EXPLORE)
page_note.link(NOTE_MAP, page_map_explore)
page_map_explore.link(BACK_ARROW, page_note)

page_material = Page('page_material', PAGE_MATERIAL)
page_note.link(NOTE_MATERIAL, page_material)
page_material.link(BACK_ARROW, page_note)

page_compete = Page('page_compete', PAGE_COMPETE)
page_arena = Page('page_arena', PAGE_ARENA)
page_note.link(NOTE_COMPETE, page_compete)
page_compete.link(BACK_ARROW, page_note)
page_compete.link(COMPETE_ARENA, page_arena)
page_arena.link(BACK_ARROW, page_compete)

page_daily_activity = Page('page_daily_activity', PAGE_DAILY_ACTIVITY)
page_holy_beast = Page('page_holy_beast', PAGE_HOLY_BEAST)
page_note.link(NOTE_DAILY_ACTIVITY, page_daily_activity)
page_daily_activity.link(BACK_ARROW, page_note)
page_daily_activity.link(ACTIVITY_HOLY_BEAST, page_holy_beast)
page_holy_beast.link(BACK_ARROW, page_daily_activity)
page_twin_shadow = Page('page_twin_shadow', PAGE_TWIN_SHADOW)
page_daily_activity.link(ACTIVITY_TWIN_SHADOW, page_twin_shadow)
page_twin_shadow.link(BACK_ARROW, page_daily_activity)

# ---------------- 家园商店 ----------------
# 家园 → 商店 要在场景里找商人推车，由 ShopUI.enter_shop 处理
page_shop = Page('page_shop', PAGE_SHOP)
page_shop.link(BACK_ARROW, page_home)
page_guild_activity.link(GUILD_RAID_CARD, page_guild_raid)
page_guild_raid.link(BACK_ARROW, page_guild_activity)
