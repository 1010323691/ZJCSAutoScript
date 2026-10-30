"""
打分发包：dist/ZJCSAutoScript-v<版本>-win64.zip，解压后双击 zjcs.exe 即用，不需要用户装 Python。

    .venv\\Scripts\\python.exe dev_tools\\package.py 1.0.0

先用 webapp\\build.ps1 编译好 zjcs.exe。包里的 toolkit\\ 是一份独立的 Python：
解释器和标准库从建 .venv 的那个 Python 复制，第三方库从 .venv 复制（去掉开发才用的）。
toolkit\\python311._pth 让它只认包里的路径，不受用户电脑上装的 Python、PYTHONPATH 影响。
adb 不打包，用雷电安装目录里的。
version.json 记打包时的提交，updater.py 拿它和 GitHub 上的 main 比，所以要先提交再打包。
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')

# 项目里要放进包的文件和目录
PROJECT = ['zjcs.exe', 'zjcs.py', 'gui.py', 'updater.py', 'bin', 'requirements.txt', 'README.md', 'LICENSE', 'module', 'assets', 'docs']
# 标准库里用不到的部分
STDLIB_SKIP = {'site-packages', 'test', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip', 'lib2to3', 'venv', '__pycache__'}
DLLS_SKIP = ('_tkinter', 'tcl', 'tk')
# .venv 里只有开发时才用的库
SITE_SKIP = ('pip', 'setuptools', 'pkg_resources', '_distutils_hack', 'distutils-precedence.pth',
             'pywebio', 'tornado', 'ua_parser', 'user_agents', '__pycache__')


def ignore_cache(folder, names):
    return [n for n in names if n == '__pycache__' or n.endswith('.pyc')]


def copy_python(toolkit):
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
        if name in STDLIB_SKIP:
            continue
        src = os.path.join(base, 'Lib', name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(lib, name), ignore=ignore_cache)
        else:
            shutil.copy2(src, lib)
    site = os.path.join(ROOT, '.venv', 'Lib', 'site-packages')
    for name in os.listdir(site):
        if name.startswith(SITE_SKIP):
            continue
        src = os.path.join(site, name)
        dst = os.path.join(lib, 'site-packages', name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=ignore_cache)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    # 路径相对 toolkit\ 自己；.. 是项目根目录，gui.py 和 zjcs.py 要 import module
    with open(os.path.join(toolkit, f'{tag}._pth'), 'w', encoding='utf-8') as f:
        f.write('Lib\nDLLs\nLib\\site-packages\n..\nimport site\n')


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else '1.0.0'
    name = f'ZJCSAutoScript-v{version}'
    out = os.path.join(DIST, name)
    if not os.path.isfile(os.path.join(ROOT, 'zjcs.exe')):
        sys.exit('没有 zjcs.exe，先运行 webapp\\build.ps1')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for item in PROJECT:
        src = os.path.join(ROOT, item)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(out, item), ignore=ignore_cache)
        else:
            shutil.copy2(src, out)
    os.makedirs(os.path.join(out, 'config'))
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        print('警告：有没提交的改动，包里的 version.json 记的提交和实际文件对不上')
    with open(os.path.join(out, 'version.json'), 'w', encoding='utf-8') as f:
        json.dump({'commit': commit}, f)
    toolkit = os.path.join(out, 'toolkit')
    os.makedirs(toolkit)
    copy_python(toolkit)

    archive = os.path.join(DIST, f'{name}-win64.zip')
    if os.path.exists(archive):
        os.remove(archive)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, dirs, files in os.walk(out):
            rel = os.path.relpath(folder, DIST)
            if not files and not dirs:
                z.writestr(rel.replace(os.sep, '/') + '/', '')
            for f in files:
                z.write(os.path.join(folder, f), os.path.join(rel, f))
    print(archive, f'{os.path.getsize(archive) / 1024 / 1024:.1f} MB')


if __name__ == '__main__':
    main()
