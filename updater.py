"""
启动时自动更新。zjcs.exe 每次打开先用自带的 Python 跑它，跑完再启动 gui.py。

从 GitHub 取 main 分支最新提交，和 version.json 里记的不一样就下载这个提交的源码 zip，
替换代码文件（MANAGED 里的），config/ 里的配置、toolkit/ 和 zjcs.exe 不动。
每行输出一条进度，桌面壳显示在启动页上。不管成功失败都正常退出，失败就先用当前版本。

不更新的情况：源码目录（有 .git，开发用）、调度脚本正在后台跑（换文件会影响正在跑的任务）、
新版本换了依赖（自带的 Python 里没有，要重新下载分发包）。
"""
import glob
import json
import os
import shutil
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = '1010323691/ZJCSAutoScript'
BRANCH = 'main'
VERSION_FILE = os.path.join(ROOT, 'version.json')
# 由更新替换的代码文件；新版本里没有的会被删掉
MANAGED = ['module', 'assets', 'docs', 'gui.py', 'zjcs.py', 'updater.py', 'requirements.txt', 'README.md', 'LICENSE']
WORK = os.path.join(ROOT, '.update')


def say(text):
    print(text, flush=True)


def fetch(url, timeout, accept=None):
    request = urllib.request.Request(url, headers={'User-Agent': 'zjcs-updater', **({'Accept': accept} if accept else {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def local_commit():
    try:
        with open(VERSION_FILE, encoding='utf-8') as f:
            return json.load(f).get('commit', '')
    except (OSError, ValueError):
        return ''


def scheduler_running():
    sys.path.insert(0, ROOT)
    from module.runtime import read_runtime
    for file in glob.glob(os.path.join(ROOT, 'config', '*.runtime.json')):
        if read_runtime(os.path.basename(file)[:-len('.runtime.json')]).get('alive'):
            return True
    return False


def requirements(folder):
    try:
        with open(os.path.join(folder, 'requirements.txt'), encoding='utf-8') as f:
            return sorted(line.strip() for line in f if line.strip() and not line.startswith('#'))
    except OSError:
        return []


def apply(new_root, commit):
    """先把旧文件挪到备份目录，再把新文件挪进来；中途出错就挪回去"""
    backup = os.path.join(WORK, 'old')
    os.makedirs(backup)
    moved, placed = [], []
    try:
        for name in MANAGED:
            if os.path.exists(os.path.join(ROOT, name)):
                os.replace(os.path.join(ROOT, name), os.path.join(backup, name))
                moved.append(name)
        for name in MANAGED:
            if os.path.exists(os.path.join(new_root, name)):
                os.replace(os.path.join(new_root, name), os.path.join(ROOT, name))
                placed.append(name)
    except OSError:
        for name in placed:
            path = os.path.join(ROOT, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        for name in moved:
            os.replace(os.path.join(backup, name), os.path.join(ROOT, name))
        raise
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump({'commit': commit}, f)


def update():
    if os.path.isdir(os.path.join(ROOT, '.git')):
        return
    say('正在检查更新…')
    current = local_commit()
    latest = fetch(f'https://api.github.com/repos/{REPO}/commits/{BRANCH}', 8, 'application/vnd.github.sha').decode().strip()
    if latest == current:
        return
    if scheduler_running():
        say('脚本正在后台跑，这次先不更新')
        return
    say('发现新版本，正在下载…')
    data = fetch(f'https://codeload.github.com/{REPO}/zip/{latest}', 40)
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    archive = os.path.join(WORK, 'source.zip')
    with open(archive, 'wb') as f:
        f.write(data)
    with zipfile.ZipFile(archive) as z:
        z.extractall(os.path.join(WORK, 'new'))
    # 压缩包里只有一层「仓库名-提交」目录
    new_root = glob.glob(os.path.join(WORK, 'new', '*'))[0]
    if requirements(new_root) != requirements(ROOT):
        say('新版本需要新的运行环境，请到 GitHub Releases 下载新的分发包')
        return
    say('正在更新…')
    apply(new_root, latest)
    say(f'已更新到 {latest[:7]}')


def main():
    try:
        update()
    except Exception as e:
        say(f'检查更新失败，先用当前版本（{type(e).__name__}: {e}）'[:120])
    finally:
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == '__main__':
    main()
