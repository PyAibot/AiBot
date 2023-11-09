import sys

if sys.version_info < (3, 9):
    raise RuntimeError("最低支持 Python3.9 版本，请升级！")

from .AndroidBot import AndroidBotMain
from .WebBot import WebBotMain
from .WinBot import WinBotMain

__all__ = ["AndroidBotMain", "WebBotMain", "WinBotMain"]
