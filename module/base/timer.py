import time


class Timer:
    def __init__(self, limit, count=0):
        """
        Args:
            limit (int, float): 计时上限（秒）
            count (int): 至少被 reached() 访问多少次才算到时，
                用来防止截图很慢时一次访问就超时
        """
        self.limit = limit
        self.count = count
        self._start = 0.
        self._access = 0

    def start(self):
        if not self.started():
            self._start = time.time()
            self._access = 0
        return self

    def started(self):
        return bool(self._start)

    def current(self):
        if self.started():
            return time.time() - self._start
        return 0.

    def reached(self):
        self._access += 1
        return time.time() - self._start > self.limit and self._access > self.count

    def reset(self):
        self._start = time.time()
        self._access = 0
        return self

    def clear(self):
        self._start = 0.
        self._access = self.count
        return self

    def wait(self):
        diff = self._start + self.limit - time.time()
        if diff > 0:
            time.sleep(diff)

    def __str__(self):
        return f'Timer(limit={round(self.current(), 3)}/{self.limit}, count={self._access}/{self.count})'

    __repr__ = __str__
