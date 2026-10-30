import datetime
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, 'log')


def log_file(date=None):
    return os.path.join(LOG_DIR, f'{date or datetime.date.today()}_zjcs.txt')


class DailyFileHandler(logging.FileHandler):
    """常驻运行跨过零点后换到当天的文件，配置界面按日期找日志才找得到"""

    def __init__(self):
        self.date = datetime.date.today()
        super().__init__(log_file(self.date), encoding='utf-8', delay=True)

    def emit(self, record):
        today = datetime.date.today()
        if today != self.date:
            self.date = today
            self.close()
            self.baseFilename = log_file(today)
        super().emit(record)


def _build_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    # Windows 控制台默认 GBK，统一成 UTF-8，避免中文日志乱码
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except Exception:
            pass

    log = logging.getLogger('zjcs')
    log.setLevel(logging.INFO)
    log.propagate = False
    fmt = logging.Formatter('%(asctime)s.%(msecs)03d | %(levelname)-7s | %(message)s', '%Y-%m-%d %H:%M:%S')

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    log.addHandler(console)

    file = DailyFileHandler()
    file.setFormatter(fmt)
    log.addHandler(file)
    return log


logger = _build_logger()


def hr(title, level=1):
    """分隔标题，level 1 最醒目，与 ALAS 的 logger.hr 用法一致"""
    title = str(title)
    if level == 0:
        logger.info('=' * 60)
        logger.info(title.upper().center(60))
        logger.info('=' * 60)
    elif level == 1:
        logger.info(f'{"=" * 20} {title.upper()} {"=" * 20}')
    elif level == 2:
        logger.info(f'{"-" * 16} {title} {"-" * 16}')
    else:
        logger.info(f'<<< {title} >>>')


def attr(name, value):
    logger.info(f'[{name}] {value}')


logger.hr = hr
logger.attr = attr
