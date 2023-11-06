from ._AndroidBase import _AndroidBotBase
from ._WebBase import _WebBotBase
from ._WinBase import _WinBotBase
from ._utils import _protect

WIN_DRIVER: _WinBotBase | None = None
WEB_DRIVER: _WebBotBase | None = None


class AndroidBotMain(_AndroidBotBase):
    def script_main(self):
        pass

    def build_win_driver(self) -> _WinBotBase:
        pass
