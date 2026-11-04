"""
打分发包，解压后双击就能用，不需要用户装 Python：

    Windows：.venv\\Scripts\\python.exe dev_tools\\package.py 1.1.0
             → dist/ZJCSAutoScript-v1.1.0-win64.zip，双击 zjcs.exe。先用 webapp\\build.ps1 编译好 zjcs.exe。
    Mac：    .venv/bin/python dev_tools/package.py 1.1.0
             → dist/ZJCSAutoScript-v1.1.0-mac-arm64.zip，双击 zjcs.command。先 cargo build 好桌面壳（见 CLAUDE.md「Mac」）。
    Mac 上打 Windows 包：.venv/bin/python dev_tools/package.py 1.1.0 --win-from <旧的 -win64.zip>
             → 代码用当前的，toolkit\\ 和 zjcs.exe 从旧包里原样拿（Mac 上做不出 Windows 的 Python 和 zjcs.exe）。
             只在 requirements.txt 和 webapp/ 都没变时能用，变了要回 Windows 上打。

包里的 toolkit/ 是一份独立的 Python：解释器和标准库从建 .venv 的那个 Python 复制，第三方库从 .venv 复制（去掉开发才用的）。
- Windows：toolkit\\python311._pth 让它只认包里的路径，不受用户电脑上装的 Python、PYTHONPATH 影响。
- Mac：建 .venv 的是 uv 的独立版 Python（python-build-standalone），整个目录挪到哪都能跑；
  隔离靠桌面壳启动时去掉 PYTHONHOME、PYTHONPATH，设 PYTHONNOUSERSITE。桌面壳放在 toolkit/zjcs。
adb 不打包：Windows 用雷电安装目录里的，Mac 用 BlueStacks 自带的。
version.json 记打包时的提交，updater.py 拿它和 GitHub 上的 main 比，所以要先提交、推到 main 再打包。
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')

# 项目里要放进包的文件和目录（两个平台都放 zjcs.command：它在 updater 的 MANAGED 里，缺了每次启动都会重新拉一遍）
PROJECT = ['zjcs.py', 'gui.py', 'updater.py', 'zjcs.command', 'bin', 'requirements.txt', 'README.md', 'LICENSE', 'module', 'assets', 'docs']
# 标准库里用不到的部分
STDLIB_SKIP = {'site-packages', 'test', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip', 'lib2to3', 'venv', '__pycache__'}
DLLS_SKIP = ('_tkinter', 'tcl', 'tk')
# .venv 里只有开发时才用的库
SITE_SKIP = ('pip', 'setuptools', 'pkg_resources', '_distutils_hack', 'distutils-precedence.pth',
             'pywebio', 'tornado', 'ua_parser', 'user_agents', '__pycache__')
MAC_SHELL = os.path.join(ROOT, 'webapp', 'src-tauri', 'target', 'release', 'zjcs')


def ignore_cache(folder, names):
    return [n for n in names if n == '__pycache__' or n.endswith('.pyc')]


def copy_tree(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, ignore=ignore_cache, symlinks=True)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def copy_site_packages(site, dst):
    for name in os.listdir(site):
        if not name.startswith(SITE_SKIP):
            copy_tree(os.path.join(site, name), os.path.join(dst, name))


def copy_python_windows(toolkit):
    base = sys.base_prefix
    tag = f'python{sys.version_info.major}{sys.version_info.minor}'
    for name in ('python.exe', 'pythonw.exe', 'python3.dll', f'{tag}.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt'):
        shutil.copy2(os.path.join(base, name), toolkit)
    os.makedirs(os.path.join(toolkit, 'DLLs'))
    for name in os.listdir(os.path.join(base, 'DLLs')):
        if not name.lower().startswith(DLLS_SKIP):
            shutil.copy2(os.path.join(base, 'DLLs', name), os.path.join(toolkit, 'DLLs'))
    lib = os.path.join(toolkit, 'Lib')
    os.makedirs(lib)
    for name in os.listdir(os.path.join(base, 'Lib')):
        if name not in STDLIB_SKIP:
            copy_tree(os.path.join(base, 'Lib', name), os.path.join(lib, name))
    copy_site_packages(os.path.join(ROOT, '.venv', 'Lib', 'site-packages'), os.path.join(lib, 'site-packages'))
    # 路径相对 toolkit\ 自己；.. 是项目根目录，gui.py 和 zjcs.py 要 import module
    with open(os.path.join(toolkit, f'{tag}._pth'), 'w', encoding='utf-8') as f:
        f.write('Lib\nDLLs\nLib\\site-packages\n..\nimport site\n')


def copy_python_mac(toolkit):
    base = sys.base_prefix
    if not os.path.isfile(os.path.join(base, 'BUILD')):
        print(f'警告：{base} 看起来不是 uv 的独立版 Python，挪到别的电脑上可能跑不起来')
    version = f'{sys.version_info.major}.{sys.version_info.minor}'
    tag = f'python{version}'
    os.makedirs(os.path.join(toolkit, 'bin'))
    shutil.copy2(os.path.join(base, 'bin', tag), os.path.join(toolkit, 'bin', tag))
    for link in ('python3', 'python'):
        os.symlink(tag, os.path.join(toolkit, 'bin', link))
    # uv 的 python3.11 是静态链接的，不需要 libpython3.11.dylib
    lib = os.path.join(toolkit, 'lib')
    stdlib = os.path.join(base, 'lib', tag)
    for name in os.listdir(stdlib):
        if name not in STDLIB_SKIP:
            copy_tree(os.path.join(stdlib, name), os.path.join(lib, tag, name))
    dynload = os.path.join(lib, tag, 'lib-dynload')
    for name in os.listdir(dynload):
        if name.startswith('_tkinter'):
            os.remove(os.path.join(dynload, name))
    copy_site_packages(os.path.join(ROOT, '.venv', 'lib', tag, 'site-packages'), os.path.join(lib, tag, 'site-packages'))
    shutil.copy2(MAC_SHELL, os.path.join(toolkit, 'zjcs'))


def copy_from_windows_package(archive, out):
    """从旧的 Windows 分发包里拿 toolkit\\ 和 zjcs.exe"""
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            parts = info.filename.split('/', 1)
            if len(parts) < 2 or not (parts[1] == 'zjcs.exe' or parts[1].startswith('toolkit/')):
                continue
            target = os.path.join(out, *parts[1].split('/'))
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst)
    for need in ('zjcs.exe', os.path.join('toolkit', 'python.exe')):
        if not os.path.isfile(os.path.join(out, need)):
            sys.exit(f'{archive} 里没有 {need}，不是 Windows 分发包')


def write_zip(out, archive):
    if os.path.exists(archive):
        os.remove(archive)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, dirs, files in os.walk(out):
            rel = os.path.relpath(folder, os.path.dirname(out))
            if not files and not dirs:
                z.writestr(rel.replace(os.sep, '/') + '/', '')
            for f in files:
                z.write(os.path.join(folder, f), os.path.join(rel, f))


def write_mac_zip(out, archive):
    # ditto 保留符号链接和可执行权限，和 Finder「压缩」的结果一样，双击就能解压
    if os.path.exists(archive):
        os.remove(archive)
    subprocess.run(['ditto', '-c', '-k', '--norsrc', '--keepParent', out, archive], check=True)


def main():
    args = sys.argv[1:]
    win_from = None
    if '--win-from' in args:
        i = args.index('--win-from')
        win_from = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    version = args[0] if args else '1.0.0'
    platform = 'win64' if win_from or os.name == 'nt' else 'mac-arm64'
    if platform == 'mac-arm64' and sys.platform != 'darwin':
        sys.exit('只支持在 Windows 或 Mac 上打包')

    if platform == 'win64' and not win_from and not os.path.isfile(os.path.join(ROOT, 'zjcs.exe')):
        sys.exit('没有 zjcs.exe，先运行 webapp\\build.ps1')
    if platform == 'mac-arm64' and not os.path.isfile(MAC_SHELL):
        sys.exit('没有编译桌面壳，先 cargo build --release --manifest-path webapp/src-tauri/Cargo.toml')

    name = f'ZJCSAutoScript-v{version}'
    out = os.path.join(DIST, platform, name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for item in PROJECT:
        copy_tree(os.path.join(ROOT, item), os.path.join(out, item))
    os.makedirs(os.path.join(out, 'config'))
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        print('警告：有没提交的改动，包里的 version.json 记的提交和实际文件对不上')
    with open(os.path.join(out, 'version.json'), 'w', encoding='utf-8') as f:
        json.dump({'commit': commit}, f)

    toolkit = os.path.join(out, 'toolkit')
    archive = os.path.join(DIST, f'{name}-{platform}.zip')
    if win_from:
        copy_from_windows_package(win_from, out)
        write_zip(out, archive)
    elif platform == 'win64':
        shutil.copy2(os.path.join(ROOT, 'zjcs.exe'), out)
        os.makedirs(toolkit)
        copy_python_windows(toolkit)
        write_zip(out, archive)
    else:
        os.makedirs(toolkit)
        copy_python_mac(toolkit)
        write_mac_zip(out, archive)
    print(archive, f'{os.path.getsize(archive) / 1024 / 1024:.1f} MB')


if __name__ == '__main__':
    main()
