#!/bin/bash
# Mac 一键启动：双击打开桌面壳（作用同 Windows 的 zjcs.exe，做法参考 ALAS 的 Alas.command）。
# 分发包：桌面壳和自带的 Python 都在 toolkit/ 里；源码运行：桌面壳要先在本机编译（见 CLAUDE.md「Mac」），
# 还没编译时退回用浏览器打开配置界面。
# 桌面壳在后台跑，这个终端窗口关掉也没关系；点了「启动」的脚本在自己的会话里，关窗口照样跑。

cd "$(dirname "$0")" || exit 1

# 从网上下载解压的文件都带「隔离」标记，没签名的程序会被系统拦下。
# 用户第一次在「系统设置 → 隐私与安全性」里允许了这个脚本，这里把整个目录的标记一起去掉，以后双击就能开。
if xattr -p com.apple.quarantine toolkit/zjcs >/dev/null 2>&1; then
    echo "第一次打开，正在解除系统对下载文件的拦截…"
    xattr -r -d com.apple.quarantine . 2>/dev/null
fi

python=""
for candidate in .venv/bin/python toolkit/bin/python3; do
    if [ -x "$candidate" ]; then
        python=$candidate
        break
    fi
done
if [ -z "$python" ]; then
    echo "没有找到 Python 环境：分发包请重新解压一份完整的；源码运行先按 CLAUDE.md「Mac」一节建好 .venv"
    read -r -p "按回车退出"
    exit 1
fi

shell=""
for candidate in webapp/src-tauri/target/release/zjcs toolkit/zjcs; do
    if [ -x "$candidate" ]; then
        shell=$candidate
        break
    fi
done

if [ -n "$shell" ]; then
    # 桌面壳从自己的位置往上找项目目录，已经开着时会把原窗口拿到前面
    # 追加写日志：已经开着的那个可能还在写
    mkdir -p log
    nohup "$shell" >> log/shell.txt 2>&1 &
    disown
    exit 0
fi

echo "没有编译桌面壳，先用浏览器打开配置界面"

# 配置服务已经在跑：直接打开页面，不启动第二个
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:22367/api/status; then
    open http://127.0.0.1:22367
    exit 0
fi

PYTHONNOUSERSITE=1 exec "$python" gui.py "$@"
