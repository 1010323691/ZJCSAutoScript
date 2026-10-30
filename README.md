# zjcs 自动化（杖剑传说日常一条龙）

架构参考 AzurLaneAutoScript（ALAS），详见 [docs/01_参考项目分析.md](docs/01_参考项目分析.md)。
每个日常任务的规则、脚本步骤、验证情况和待验证时间表见 [docs/02_日常一条龙流程设计.md](docs/02_日常一条龙流程设计.md)。游戏界面知识库（`kb/`，含截图）只留在本地，不进仓库。

## 运行

环境：Windows，雷电模拟器实例 1（`emulator-5556`，720×1280 竖屏）。游戏没开或卡死时脚本会自己重启游戏并自动登录。

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

打开配置界面（会自动打开浏览器 http://127.0.0.1:22367；加 `--no-browser` 不自动打开）。平时用它就够了：

- 运行：启动 / 停止脚本（停止会等当前任务做完，等不及可以强制停止），任务队列里每项都能「立即执行」（插到队首），实时日志和模拟器画面；
- 每天的路线、设置：改完点保存或按 Ctrl+S，脚本在下一项任务开始前就会用上，不用重启；
- 日志：按日期看日志、运行记录（每项任务的起止时间和结果）、出错时保存的截图；
- 活动、工具：预留给限时活动任务和手动才跑的一次性功能；
- 左下角可切跟随系统 / 浅色 / 深色。

关掉配置界面，它启动的脚本照样在后台跑；再打开会接上当前状态。同一个配置同时只能跑一个脚本（命令行和界面启动的都算）。

```bash
.venv\Scripts\python.exe gui.py
```

也可以双击项目根目录的 `zjcs.exe`：在独立窗口里打开同一个配置界面，不用浏览器。它会自己在后台启动 `gui.py`，按 `.venv\Scripts\python.exe` → `toolkit\python.exe` → 系统 PATH 里的 Python 的顺序找解释器，所以上面的 Python 环境仍然要先装好；关掉窗口时配置服务一起退出。窗口靠系统自带的 Microsoft Edge WebView2 运行时显示（Windows 10/11 一般都有，缺了会弹窗提示去哪下载）。再双击不会开第二个，只会把已有窗口拿到前面。

改了 `webapp/` 下的代码或图标后重新编译（需要 Rust stable，第一次要下载依赖，几分钟）：

```bash
powershell -ExecutionPolicy Bypass -File webapp\build.ps1
```

跑一遍到期的日常：

```bash
.venv\Scripts\python.exe zjcs.py
```

| 命令 | 作用 |
|---|---|
| `zjcs.py` | 按调度执行所有到期、已启用的任务，跑完退出 |
| `zjcs.py --loop` | 常驻运行，跑完后等到下一次服务器刷新（本机 09:00） |
| `zjcs.py --task <任务名>` | 只跑一个任务，不看调度、不写状态（调试用） |
| `zjcs.py --task Restart` | 只重启游戏并登录到家园 |
| `zjcs.py --config <名字>` | 使用 `config/<名字>.yaml` |

出问题停下（连续失败到上限、模拟器不在线、脚本出错）时会弹 Windows 通知，可以在配置界面的「设置 → 通知」里关掉或加上「每天跑完时」的汇总。

任务名：`GeneralShop` 杂货、`Vault` 宝库、`CandyTree` 糖果树、`Cart` 小推车、`DailyDungeon` 日常副本、`BondAdventure` 羁绊冒险、`FateFruit` 命运果实、`Arena` 竞技场、`MaterialRealm` 素材秘境、`HolyBeastTrial` 圣兽试炼、`TwinShadow` 双影幻境、`GuildIdleReward` 公会挂机、`GuildWar` 公会战、`GuildRaid` 公会讨伐、`DailyReward` 领取奖励（日常清完后统一领），另有框架自检 `UiTest`。

配置存在 `config/zjcs.yaml`（没有时用默认值），参数定义和默认值在 `module/config/argument.yaml`。任务的下次运行时间、失败次数记在 `config/zjcs.state.json`，删掉它就会全部重跑。脚本和配置界面之间通过 `config/zjcs.runtime.json`（运行状态）和 `config/zjcs.cmd/`（立即执行、停止指令）通信，运行记录追加在 `log/zjcs.history.jsonl`。

## 目录

```
zjcs.py                 入口：ZjcsAutoScript，调度循环 + 每个任务一个同名方法；出错时保存截图、重启游戏
gui.py                  配置界面的本机服务（只监听 127.0.0.1，标准库 http.server）：读写配置并按 argument.yaml 校验；启停脚本、立即执行、日志、截图、设备检测、测试通知
zjcs.exe                桌面壳（webapp/build.ps1 编译出来的）：后台启动 gui.py，在独立窗口里打开配置界面
webapp/                 桌面壳源码（Tauri 2）：src-tauri/ 启动配置服务和窗口，shell/ 启动页，icons/ 图标
config/                 zjcs.yaml（用户配置）、zjcs.state.json（调度状态）
module/
├─ logger.py            日志（控制台 + log/日期_zjcs.txt，常驻跨零点自动换文件）
├─ runtime.py           脚本和配置界面之间的文件通道：运行状态、指令、运行记录、单实例
├─ notify.py            Windows 系统通知（PowerShell 调 WinRT，不装额外的库）
├─ exception.py         异常分级（卡死、连点、页面未知、游戏退出、需要人工……）
├─ base/                Button（模板 / 多尺度区域匹配）、ClickArea、ModuleBase(appear / appear_then_click / interval)、Timer
├─ device/              Connection(adb) → Screenshot + Control → Device（卡死检测、连点检测、游戏是否在运行）
├─ config/              argument.yaml 参数定义、配置读取、调度（TASK_ORDER、服务器时区换算、失败计数）
├─ ui/                  Page 页面图、UI(ui_goto / ui_ensure / ui_click / 奖励弹窗 / 结算页)
├─ handler/             重启游戏、自动登录（关公告、点击开始游戏）
├─ home/                家园场景滑动查找：小推车、糖果树
├─ shop/                家园商店：进店、杂货（折扣滑块、一键购买、刷新）
├─ note/                笔记：日常副本、羁绊冒险（奇景委派）、竞技场、素材秘境
├─ activity/            匹配战斗（圣兽试炼、双影幻境，日常副本复用）
├─ guild/               公会场景找远征之门：挂机奖励、公会讨伐
├─ webui/               配置界面页面（index.html、style.css、app.js，不依赖任何库；只做桌面端，深浅色跟随系统）
└─ reward/              清完日常后统一领奖励：按入口红点决定进不进（精彩活动、商城免费项、好友、馈赠、任务）
assets/<模块>/          模板图片 + define.yaml（按钮区域定义）
dev_tools/
├─ screenshot.py        截一张全分辨率截图到 dev_tools/screens/
├─ button_extract.py    按 define.yaml 裁模板、生成 module/<模块>/assets.py
└─ screens/             素材原图
log/                    运行日志；出错时最近 10 张截图存到 log/error/<时间>/
```

## 新增一个识别按钮

1. 把游戏停在目标界面，截原图：`.venv\Scripts\python.exe -m dev_tools.screenshot <图名>`
2. 在 `assets/<模块>/define.yaml` 里写按钮名、原图名和区域 `[x1, y1, x2, y2]`（识别区域和点击位置不同时另写 `button:`；只点击不识别的写 `click:`）
3. 生成：`.venv\Scripts\python.exe -m dev_tools.button_extract`
4. 代码里 `from module.<模块>.assets import <按钮名>`

## 安全约定

- 只用雷电自带的 `adb.exe`，不执行 `adb kill-server` / `start-server`，以免影响实例 0 上运行的 ALAS。
- 不改模拟器窗口尺寸和分辨率；分辨率不是 720×1280 时直接报错退出。
- 识别不了当前页面时不盲按返回键：保存截图、重启游戏回到家园。
- 绝不碰抽卡、扭蛋和付费：主菜单顶部轮播横幅（会轮到幸运刮刮乐）不点，商城只在免费按钮的限定范围里找「领取」；糖果树只在识别到糖果时点糖果本身（没糖果时点树会进卡池），商人推车只点车身（左边是扭蛋机）。
- 花钻石的地方都先核对：竞技场核对买券数量，素材秘境核对总价等于 `ExpectedCost`，羁绊冒险刷新核对「100 晨星」并且每天不超过 `RefreshLimit` 次（次数记在状态文件里，重跑也不会超），不对就取消。
- 没跑通的任务在配置里保持关闭；打开了也只会提示「还没打通」并跳过。
