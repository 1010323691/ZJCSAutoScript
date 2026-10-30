# 一条龙 · 杖剑传说日常自动化

在雷电模拟器上自动做《杖剑传说》的每日任务：杂货、宝库、糖果树、小推车、小屋、日常副本、羁绊冒险、命运果实、竞技场、素材秘境、圣兽试炼、双影幻境、公会挂机、公会捐赠、公会战、公会讨伐，最后统一领奖励。常驻运行，每天服务器刷新后自动再跑一遍；游戏没开或卡死会自己重启游戏并登录。

> **推荐直接下载分发包，解压就能用，不用装 Python。**
> 👉 [下载最新版](https://github.com/1010323691/ZJCSAutoScript/releases/latest)　·　[直接下载 v1.0.0 压缩包（约 104 MB）](https://github.com/1010323691/ZJCSAutoScript/releases/download/v1.0.0/ZJCSAutoScript-v1.0.0-win64.zip)

架构参考 AzurLaneAutoScript（ALAS），详见 [docs/01_参考项目分析.md](docs/01_参考项目分析.md)；每个日常任务的规则、脚本步骤和验证情况见 [docs/02_日常一条龙流程设计.md](docs/02_日常一条龙流程设计.md)。

## 安装

### 1. 准备

- **电脑**：Windows 10 / 11 64 位，建议 8 GB 内存以上（模拟器本身要占 4 GB 左右）。
- **雷电模拟器**：按下面「模拟器设置」装好并设置。
- **WebView2 运行时**：窗口靠它显示，Windows 10 / 11 一般自带。打开时如果提示缺少，到 [微软官网](https://developer.microsoft.com/microsoft-edge/webview2/) 下载「常青版运行时」装上。

#### 模拟器设置

**推荐雷电模拟器**，到 [雷电官网](https://www.ldmnq.com/) 下载。脚本是在**雷电模拟器 14** 上开发和实测的；其他版本的雷电、MuMu、蓝叠等没测过，理论上只要分辨率对、adb 连得上也能用，但不保证。

打开模拟器右上角的「设置」，按下表改，改完点保存，**重启模拟器**生效：

| 设置项 | 位置 | 要求 | 说明 |
|---|---|---|---|
| 分辨率 | 性能设置 → 分辨率 | **手机版 720×1280，DPI 320**（必须） | 脚本按这个分辨率认界面、算点击位置，其他分辨率会直接报错退出。列表里没有就选「自定义」，宽 720、高 1280、DPI 320 |
| ADB 调试 | 其他设置 → ADB 调试 | **开启本地连接**（必须） | 关着的话脚本连不上模拟器 |
| CPU / 内存 | 性能设置 | 4 核 / 4096 MB（推荐） | 低了游戏会卡，识别容易超时 |
| 帧率 | 设置里的「帧率」 | 60（推荐） | |
| ROOT 权限 | 其他设置 | 关闭即可 | 脚本不需要 ROOT |

> 不同版本的雷电，菜单名字可能略有不同，找意思相近的项就行。分辨率一旦设好就不要再改，模拟器窗口拉大拉小没关系。

然后在模拟器里装好《杖剑传说》，**手动登录过一次**（之后脚本会自动登录）。

**多开**：脚本一次只操作一个实例。雷电第 1 个实例的序列号是 `emulator-5554`，第 2 个是 `emulator-5556`，依次加 2（多开器里的实例编号从 0 开始，实例 0 就是第 1 个）。游戏不在第 1 个实例上时，到配置界面「设置 → 设备」里改序列号。

### 2. 下载分发包

到 [Releases](https://github.com/1010323691/ZJCSAutoScript/releases/latest) 下载 `ZJCSAutoScript-v<版本>-win64.zip`，**解压**到任意目录（路径里有中文、空格都行），不要在压缩包里直接双击运行。

包里自带 Python 和所有依赖（`toolkit\`），电脑上不用装 Python，也不会和已经装的 Python 冲突。adb 用雷电自带的，不另外打包。

### 3. 第一次设置

1. 先打开雷电模拟器，再双击 `zjcs.exe`，等配置界面打开。
2. 进「设置 → 设备」：
   - **adb 路径**：填雷电安装目录里的 `adb.exe`（右键桌面上的雷电模拟器图标 →「打开文件所在的位置」，那个目录里就有）。
   - **设备序列号**：雷电第 1 个实例是 `emulator-5554`（默认值），多开时第 2 个是 `emulator-5556`，依次加 2。
   - 点「**检查连接**」，能看到模拟器截图就对了。
3. 进「每天的路线」：**所有任务默认都是关着的**，打开想让它做的任务，点开每项可以调细节（比如杂货的折扣、宝库买哪几件）。改完点保存或按 Ctrl+S。
4. 回到「运行」页，点「启动」。脚本会先跑已经到期的任务，然后常驻，每天刷新后自动再跑。

### 4. 日常使用

- **运行页**：启动 / 停止（停止会等当前任务做完，等不及可以强制停止）；任务队列里每项都能「立即执行」（插到队首）；能看实时日志和模拟器画面。
- **关掉窗口，脚本照样在后台跑**；再打开 `zjcs.exe` 会接上当前状态。同一个配置同时只能跑一个脚本。
- **改设置不用重启**：保存后脚本在下一项任务开始前就会用上。
- **日志页**：按日期看日志、每项任务的起止时间和结果、出错时保存的截图。
- **通知**：出问题停下（连续失败到上限、模拟器不在线、脚本出错）时会弹 Windows 通知，可以在「设置 → 通知」里关掉，或加上「每天跑完时」的汇总。
- 左下角可切跟随系统 / 浅色 / 深色。

### 5. 更新

**一般不用管**：每次打开 `zjcs.exe` 会先从 GitHub 取最新代码（启动页显示「正在检查更新…」），只换代码文件，`config\` 里的设置不动。

- GitHub 连不上时，就用当前版本照常打开，最多等 60 秒。
- 脚本正在后台跑时，这次先不更新，下次打开再更新。
- 启动页提示「新版本需要新的运行环境」时，要手动换新包：到 [Releases](https://github.com/1010323691/ZJCSAutoScript/releases/latest) 下载新的分发包，解压后把旧目录里的 `config\` 文件夹复制过去，设置就都还在。

### 常见问题

| 现象 | 处理 |
|---|---|
| 双击 `zjcs.exe` 弹窗提示和 WebView2 有关 | 到 [微软官网](https://developer.microsoft.com/microsoft-edge/webview2/) 下载「常青版运行时」装上 |
| 「检查连接」失败 | 确认模拟器已经打开，「其他设置 → ADB 调试」选的是「开启本地连接」（改完要重启模拟器）；adb 路径指向雷电目录里的 `adb.exe`；序列号和实例对得上（第 1 个实例 `emulator-5554`） |
| 提示分辨率不对 | 在雷电「性能设置 → 分辨率」里选手机版 720×1280、DPI 320，保存后重启模拟器 |
| 启动页显示「检查更新失败」 | 连不上 GitHub，不影响使用，用的是当前版本 |
| 提示端口 22367 被占用 | 关掉占用这个端口的程序（或者上次没关干净的配置服务）后重新打开 |

## 从源码运行（开发用）

需要 Python 3.11：

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

打开配置界面（会自动打开浏览器 http://127.0.0.1:22367；加 `--no-browser` 不自动打开）：

```bash
.venv\Scripts\python.exe gui.py
```

也可以双击项目根目录的 `zjcs.exe`：在独立窗口里打开同一个配置界面。它会自己在后台启动 `gui.py`，按 `.venv\Scripts\python.exe` → `toolkit\python.exe` → 系统 PATH 里的 Python 的顺序找解释器；关掉窗口时配置服务一起退出。再双击不会开第二个，只会把已有窗口拿到前面。源码目录（有 `.git`）不会自动更新。

改了 `webapp/` 下的代码或图标后重新编译（需要 Rust stable，第一次要下载依赖，几分钟）：

```bash
powershell -ExecutionPolicy Bypass -File webapp\build.ps1
```

打分发包（先提交，再编译好 `zjcs.exe`）：把本机建 `.venv` 的 Python 和 `.venv` 里的依赖复制进 `toolkit\`，生成 `dist\ZJCSAutoScript-v<版本>-win64.zip`，包里的 `version.json` 记打包时的提交，自动更新拿它和 GitHub 上的 main 比：

```bash
.venv\Scripts\python.exe dev_tools\package.py 1.0.0
```

推到 main 的代码，用分发包的用户下次打开就会自动拿到；改了 `requirements.txt` 或桌面壳要重新打包发 Release。

跑一遍到期的日常：

```bash
.venv\Scripts\python.exe zjcs.py
```

| 命令 | 作用 |
|---|---|
| `zjcs.py` | 按调度执行所有到期、已启用的任务，跑完退出 |
| `zjcs.py --loop` | 常驻运行，跑完后等到下一次服务器刷新（北京时间 8:00） |
| `zjcs.py --task <任务名>` | 只跑一个任务，不看调度、不写状态（调试用） |
| `zjcs.py --task Restart` | 只重启游戏并登录到家园 |
| `zjcs.py --config <名字>` | 使用 `config/<名字>.yaml` |

任务名：`GeneralShop` 杂货、`Vault` 宝库、`CandyTree` 糖果树、`Cart` 小推车、`DailyDungeon` 日常副本、`BondAdventure` 羁绊冒险、`FateFruit` 命运果实、`Arena` 竞技场、`MaterialRealm` 素材秘境、`HolyBeastTrial` 圣兽试炼、`TwinShadow` 双影幻境、`GuildIdleReward` 公会挂机、`GuildWar` 公会战、`GuildRaid` 公会讨伐、`DailyReward` 领取奖励（日常清完后统一领），另有框架自检 `UiTest`。

配置存在 `config/zjcs.yaml`（没有时用默认值），参数定义和默认值在 `module/config/argument.yaml`。任务的下次运行时间、失败次数记在 `config/zjcs.state.json`，删掉它就会全部重跑。脚本和配置界面之间通过 `config/zjcs.runtime.json`（运行状态）和 `config/zjcs.cmd/`（立即执行、停止指令）通信，运行记录追加在 `log/zjcs.history.jsonl`。

## 目录

```
zjcs.py                 入口：ZjcsAutoScript，调度循环 + 每个任务一个同名方法；出错时保存截图、重启游戏
gui.py                  配置界面的本机服务（只监听 127.0.0.1，标准库 http.server）：读写配置并按 argument.yaml 校验；启停脚本、立即执行、日志、截图、设备检测、测试通知
updater.py              启动时自动更新：zjcs.exe 打开时先跑它，从 GitHub 拉 main 最新代码替换代码文件
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
├─ package.py           打分发包（自带 Python 的 zip）
└─ screens/             素材原图（只在本地）
log/                    运行日志；出错时最近 10 张截图存到 log/error/<时间>/
```

## 新增一个识别按钮

1. 把游戏停在目标界面，截原图：`.venv\Scripts\python.exe -m dev_tools.screenshot <图名>`
2. 在 `assets/<模块>/define.yaml` 里写按钮名、原图名和区域 `[x1, y1, x2, y2]`（识别区域和点击位置不同时另写 `button:`；只点击不识别的写 `click:`）
3. 生成：`.venv\Scripts\python.exe -m dev_tools.button_extract`
4. 代码里 `from module.<模块>.assets import <按钮名>`

## 安全约定

- 只用雷电自带的 `adb.exe`，不执行 `adb kill-server` / `start-server`，以免影响同一台电脑上其他用 adb 的程序（比如别的模拟器实例上跑的脚本）。
- 不改模拟器窗口尺寸和分辨率；分辨率不是 720×1280 时直接报错退出。
- 识别不了当前页面时不盲按返回键：保存截图、重启游戏回到家园。
- 绝不碰抽卡、扭蛋和付费：主菜单顶部轮播横幅（会轮到幸运刮刮乐）不点，商城只在免费按钮的限定范围里找「领取」；糖果树认不出糖果时只点一下树身确认，进了卡池立即退出，商人推车只点车身（左边是扭蛋机）。
- 花钻石的地方都先核对：竞技场核对买券数量，素材秘境核对总价等于 `ExpectedCost`，羁绊冒险刷新核对「100 晨星」并且每天不超过 `RefreshLimit` 次（次数记在状态文件里，重跑也不会超），不对就取消。
- 没跑通的任务在配置里保持关闭；打开了也只会提示「还没打通」并跳过。
