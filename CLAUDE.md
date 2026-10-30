# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

《杖剑传说》日常自动化（「一条龙」），架构参考 AzurLaneAutoScript（ALAS），对照分析见 `docs/01_参考项目分析.md`。每个日常任务的规则、脚本步骤、验证情况和待验证项见 `docs/02_日常一条龙流程设计.md`，改任务逻辑前先读对应小节。`README.md` 只写给最终用户（安装、设置、更新、常见问题），开发内容写在这里。

## 开发流程（必须遵守）

一切开发都以知识库为依据。新功能、新任务、改识别和改判定逻辑，都按下面四步走，前一步没完成不进下一步：

1. **查知识库**：先读 `kb/` 里对应的篇和 `docs/02` 的对应小节。知识库里没记的游戏机制、界面和弹窗，不能凭猜测写进代码，要先走第 2 步补上，拿不准的问用户。
2. **模拟一遍流程，保留证据**：在游戏实例（本机 `emulator-5556`）上用 adb 单步把整个流程走一遍，每一步都截图（`python -m dev_tools.screenshot <模块>_<序号>_<说明>`，存在 `dev_tools/screens/`）。把观察到的界面、按钮位置、弹窗、分支和结果写进知识库对应篇，配图放 `kb/screenshots/`。走流程时遵守下面的安全约定；会消耗道具、次数或钻石的步骤，先问用户。
3. **根据证据写代码**：`define.yaml` 里的原图和区域直接取自第 2 步的截图，代码里的判定和分支要能在知识库里找到依据。证据没覆盖到的情况，回到第 2 步补，不要自己推测。
4. **跑代码实测**：用 `zjcs.py --task <任务名>` 在真实游戏上跑，看日志，失败时还要看 `log/error/` 里的截图。跑通了才算通过。没跑通就回到第 2 步或第 3 步，不能只凭「代码看起来对」就交付。通过后在 `docs/02` 对应小节记下验证日期和结果，知识库同步更新。

## 常用命令

环境：Windows，Python 3.11，依赖装在 `.venv`。没有测试套件和 lint。

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

.venv\Scripts\python.exe gui.py                                   # 配置界面 http://127.0.0.1:22367，会自动开浏览器
.venv\Scripts\python.exe gui.py --port 22368 --config selftest --no-browser   # 用别的配置和端口调界面，不碰真实配置
.venv\Scripts\python.exe zjcs.py                                  # 跑一遍到期、已启用的任务后退出
.venv\Scripts\python.exe zjcs.py --loop                           # 常驻，跑完等下一次服务器刷新
.venv\Scripts\python.exe zjcs.py --task <任务名>                  # 只跑一个任务，不看调度、不写状态（调单个任务用这个）
.venv\Scripts\python.exe zjcs.py --task UiTest                    # 框架自检；--task Restart 只重启游戏登录到家园
.venv\Scripts\python.exe -m dev_tools.screenshot <图名>           # 截一张全分辨率原图到 dev_tools/screens/
.venv\Scripts\python.exe -m dev_tools.button_extract              # 按 define.yaml 裁模板、重新生成 module/<模块>/assets.py

powershell -ExecutionPolicy Bypass -File webapp\build.ps1         # 编译桌面壳，输出到根目录 zjcs.exe（需要 Rust stable）
.venv\Scripts\python.exe dev_tools\package.py 1.0.0               # 打分发包 dist\ZJCSAutoScript-v<版本>-win64.zip
```

`--config <名字>` 对应 `config/<名字>.yaml`。测试调度或界面时用单独的配置名（比如 `selftest`）；**不要在真实配置 `zjcs` 上点「启动」「立即执行」**，那会真的去跑游戏任务。

## 进程结构

```
zjcs.exe（Tauri 2 桌面壳，webapp/src-tauri）
 ├─ 先跑 updater.py：从 GitHub 拉 main 最新代码覆盖代码文件
 └─ 再启动 gui.py（标准库 http.server，只听 127.0.0.1:22367）→ 窗口打开配置界面 module/webui/
      └─ 点「启动」时 gui.py 启动 zjcs.py --loop（脱离桌面壳的作业对象，关窗口不会结束它）
```

- 桌面壳找 Python 的顺序：`.venv\Scripts\python.exe` → `toolkit\python.exe`（分发包自带）→ PATH。配置服务已经在跑就直接连，不启动第二个，也不跑更新。
- `gui.py` 和调度进程（`zjcs.py`）之间不走网络，走 `module/runtime.py` 的文件通道：`config/<名>.runtime.json` 是运行状态（调度进程写），`config/<名>.cmd/*.json` 一条指令一个文件（立即执行、停止，调度进程读完删掉），`log/<名>.history.jsonl` 是运行记录。同一配置只允许一个调度进程（按 runtime.json 里的 pid 判断）。
- 配置界面是纯原生 JS，没有构建步骤，`gui.py` 每次从磁盘读文件，改完刷新页面就行，不用重新编译 exe。

## 调度和任务

- `module/config/config.py` 的 `TASK_ORDER` 决定执行顺序；每个任务的下次运行时间、连续失败次数、立即执行标记记在 `config/<名>.state.json`。服务器每天 `Scheduler_ServerUpdate`（北京时间 8:00）刷新，按 `ServerTimezone` 换算成本机时间。立即执行的任务排在队首，关着的任务也能立即执行。
- 调度进程每跑一项任务前 `config.reload()`，所以界面保存的配置下一项任务就生效。
- `zjcs.py` 的 `ZjcsAutoScript.run()` 用 `underscore(任务名)` 找同名方法（`GeneralShop` → `general_shop`），方法里实例化 `module/<模块>/` 下的类并调用 `run()`。返回结果的约定：
  - 返回 `False`：任务自己判断没做完，记一次失败，不重启游戏。
  - 抛 `GameStuckError`、`GameTooManyClickError`、`GamePageUnknownError`、`GameNotRunningError`：保存最近截图到 `log/error/<时间>/`，重启游戏回家园，记一次失败。
  - 抛 `TaskNotImplemented`：还没打通，跳过。
  - 抛 `ScriptError`、`RequestHumanTakeover`：停机并发通知。
  - 同一任务连续失败 `Scheduler_FailureLimit` 次就请求人工。
- 新增一个日常任务要同时改：`TASK_ORDER`、`argument.yaml` 里的同名分组、`zjcs.py` 的同名方法、`module/webui/app.js` 的 `ROUTE`（路线分组）和 `SPEC`（界面上的一句话说明和设置项）。

## 配置定义

`module/config/argument.yaml` 是参数的唯一定义：配置读取按它补默认值，`gui.py` 按它校验保存的值，界面按它生成表单。读取时参数名是 `分组_参数`（例如 `config.Device_Serial`）。`app.js` 的 `SPEC` 给已知分组写了专门的界面，新加但没写 `SPEC` 的分组会按参数类型自动生成控件。用户配置 `config/zjcs.yaml` 只在本地，不进仓库。

## 识别素材

- 每个模块的 `assets/<模块>/define.yaml` 定义按钮：原图名、识别区域 `[x1,y1,x2,y2]`，另写 `button:` 表示点击位置不同，只写 `click:` 表示只点击不识别。
- `dev_tools/button_extract.py` 从 `dev_tools/screens/` 的原图裁出模板 png，生成 `module/<模块>/assets.py`。**`assets.py` 是生成文件，不要手改**，改 `define.yaml` 后重新生成。`dev_tools/screens/` 只在本地，不进仓库。
- 所有坐标基于 720×1280 竖屏；截图分辨率不对时 `module/device/screenshot.py` 直接抛 `ScriptError`。

## 分发与自动更新

- `dev_tools/package.py` 把建 `.venv` 的基础 Python（解释器、标准库）和 `.venv` 的 site-packages（去掉 pip、pywebio 等开发用的库）复制进 `toolkit\`，写 `toolkit\python311._pth` 隔离掉用户电脑上的 Python。它还把 `git rev-parse HEAD` 写进 `version.json`，所以**要先提交再打包**。
- `updater.py` 拿 `version.json` 和 GitHub `main` 的最新提交比，不同就下载源码 zip，替换 `MANAGED` 里的文件。以下情况不更新：源码目录（有 `.git`）、调度进程正在跑、`requirements.txt` 变了（会提示用户下载新分发包）。
- 因此**推到 main 的代码，用分发包的用户下次打开就会拿到**。没验证过的改动不要直接推 main。改了 `requirements.txt` 或 `webapp/`（桌面壳）后，自动更新覆盖不到，要重新编译、打包，发新的 GitHub Release（`gh release create v<版本> dist\...zip`）。

## 安全约定（不能违反）

- **设备**：本机实例 0（`emulator-5554`）跑着别的游戏和 ALAS，不要碰；本机游戏在 `emulator-5556`（真实配置里写的）。分发版的默认序列号是 5554，所以测试时不要删掉或替换 `config/zjcs.yaml`。adb 默认用自带的 `bin/adb/adb.exe`（从 ALAS 的 adbutils 复制的 29.0.6，和 ALAS 同一份）。`gui.py` 启动时按 `Device_ReplaceAdb` 调 `module/device/adb_replace.py` 替换雷电目录里的 adb：不一致时先结束所有 adb 进程，原文件改名 `.bak`，调度进程在跑时跳过。这会让同机其他用 adb 的程序（本机 ALAS）断开一下，是用户确认过的做法（照搬 ALAS 的 ReplaceAdb）。除此之外不要执行 `adb kill-server` / `start-server`，也不改模拟器窗口尺寸和分辨率。
- **游戏操作**：绝不抽卡、扭蛋。不点主菜单轮播横幅（会轮到刮刮乐）、付费按钮、羁绊冒险「挑战」、糖果树卡池的「结缘」按钮、「删除已读」、床的「全局加速」、组队邀请。花钻石或晨星的地方都先核对数量或价格，对不上就取消。
- **不要擅自假设**：游戏机制、界面操作、执行逻辑或配置规则不明确时，先问用户，不要自己决定；只实现用户明确提出的内容。完整禁点清单和每项授权的上限，在私有知识库 01 篇第 3 节。
- **知识库**：`kb/` 是单独的私有仓库 `1010323691/ZJCSAutoScript-KB`，本仓库 `.gitignore` 排除了它（截图里有账号信息）。改了知识库要进 `kb/` 单独提交、推送。本仓库是公开的，不要把 kb 内容、`dev_tools/screens/`、`config/zjcs.yaml`、日志加进来。
