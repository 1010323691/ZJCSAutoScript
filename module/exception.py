class ScriptError(Exception):
    """开发者的错：代码逻辑或资源有问题，需要改代码"""
    pass


class TaskEnd(Exception):
    """任务提前正常结束"""
    pass


class TaskNotImplemented(Exception):
    """任务已规划但还没打通（等待探索或用户确认）"""
    pass


class GameStuckError(Exception):
    """长时间没有任何进展，游戏可能卡住了"""
    pass


class GameTooManyClickError(Exception):
    """短时间内反复点击同一个按钮，大概率点击没有生效"""
    pass


class GameNotRunningError(Exception):
    """游戏不在前台"""
    pass


class GamePageUnknownError(Exception):
    """无法识别当前页面"""
    pass


class RequestHumanTakeover(Exception):
    """脚本无法自行处理，需要人工介入"""
    pass
