#!/bin/bash
# Mac 一键启动：双击打开配置界面（作用同 Windows 的 zjcs.exe，但用浏览器代替桌面壳，也不跑自动更新）。
# 终端窗口就是配置服务，关掉它只关配置界面；点了「启动」的脚本在自己的会话里，照样跑。

cd "$(dirname "$0")" || exit 1

python=.venv/bin/python
if [ ! -x "$python" ]; then
    echo "没有找到 $python，先按 CLAUDE.md「Mac」一节建好 .venv"
    read -r -p "按回车退出"
    exit 1
fi

# 配置服务已经在跑：直接打开页面，不启动第二个
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:22367/api/status; then
    open http://127.0.0.1:22367
    exit 0
fi

exec "$python" gui.py "$@"
