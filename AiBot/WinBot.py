import socket
import subprocess
import sys

from typing import Union, List, Optional, Tuple, Dict

from loguru import logger


class WinBotMain:
    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_path = ""
    log_level = "DEBUG"
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
                 "<level>{level: <8}</level> | " \
                 "<cyan>{module}.{function}:{line}</cyan> | " \
                 "<level>{message}</level>"  # 日志内容

    def __init__(self, port):
        self.log = logger

        self.log.remove()
        self.log.add(sys.stdout, level=self.log_level.upper(), format=self.log_format)

        if self.log_path:
            self.log.add(self.log_path, level=self.log_level.upper(), rotation="12:00", retention="15 days",
                         format=self.log_format)

        address_info = socket.getaddrinfo("127.0.0.1", port, socket.AF_INET, socket.SOCK_STREAM)[0]
        family, socket_type, proto, _, socket_address = address_info
        self.__sock = socket.socket(family, socket_type, proto)
        self.__sock.connect(socket_address)

    @classmethod
    def build(cls, port: int) -> "WinBotMain":
        subprocess.Popen(["WindowsDriver.exe", str(port)])
        return WinBotMain(port)

    def __send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            if argv is None:
                argv = ""
            elif isinstance(argv, bool) and argv:
                argv = "true"
            elif isinstance(argv, bool) and not argv:
                argv = "false"

            argv = str(argv)
            args_text += argv
            args_len += str(len(argv)) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        self.log.debug(rf"---> {data}")
        self.__sock.sendall(data)
        data_length, data = self.__sock.recv(65535).split(b"/", 1)

        while int(data_length) > len(data):
            data += self.__sock.recv(65535)
        self.log.debug(rf"<--- {data}")

        return data.decode("utf8").strip()

    # #############
    #   窗口操作   #
    # #############
    def find_window(self, class_name: str = None, window_name: str = None) -> Optional[str]:
        """
        查找窗口句柄，仅查找顶级窗口，不包含子窗口
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findWindow", class_name, window_name)
        if response == "null":
            return None
        return response

    def find_windows(self, class_name: str = None, window_name: str = None) -> List[str]:
        """
        查找窗口句柄数组，仅查找顶级窗口，不包含子窗口
        class_name 和 window_name 都为 None，则返回所有窗口句柄
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findWindows", class_name, window_name)
        if response == "null":
            return []
        return response.split("|")

    def find_sub_window(self, hwnd: str, class_name: str = None, window_name: str = None) -> Optional[str]:
        """
        查找子窗口句柄
        :param hwnd: 当前窗口句柄
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findSubWindow", hwnd, class_name, window_name)
        if response == "null":
            return None
        return response

    def find_parent_window(self, hwnd: str) -> Optional[str]:
        """
        查找父窗口句柄
        :param hwnd: 当前窗口句柄
        :return:
        """
        response = self.__send_data("findParentWindow", hwnd)
        if response == "null":
            return None
        return response

    def get_window_name(self, hwnd: str) -> Optional[str]:
        """
        获取窗口名称
        :param hwnd: 当前窗口句柄
        :return:
        """
        response = self.__send_data("getWindowName", hwnd)
        if response == "null":
            return None
        return response

    def show_window(self, hwnd: str, show: bool) -> bool:
        """
        显示/隐藏窗口
        :param hwnd: 当前窗口句柄
        :param show: 是否显示窗口
        :return:
        """
        return self.__send_data("showWindow", hwnd, show) == "true"

    def set_window_top(self, hwnd: str) -> bool:
        """
        设置窗口到最顶层
        :param hwnd: 当前窗口句柄
        :return:
        """
        return self.__send_data("setWindowTop", hwnd) == "true"

    # #############
    #   键鼠操作   #
    # #############
    def move_mouse(self, hwnd: str, x: float, y: float, mode: bool = False) -> bool:
        """
        移动鼠标
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("moveMouse", hwnd, x, y, mode) == "true"

    def scroll_mouse(self, hwnd: str, x: float, y: float, count: int, mode: bool = False) -> bool:
        """
        滚动鼠标
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param count: 鼠标滚动次数, 负数下滚鼠标, 正数上滚鼠标
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("rollMouse", hwnd, x, y, count, mode) == "true"

    def click_mouse(self, hwnd: str, x: float, y: float, typ: int, mode: bool = False) -> bool:
        """
        鼠标点击
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param typ: 点击类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7 双击右键:8
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("clickMouse", hwnd, x, y, typ, mode) == "true"

    def send_keys(self, text: str) -> bool:
        """
        输入文本
        :param text: 输入的文本
        :return:
        """
        return self.__send_data("sendKeys", text) == "true"

    def send_keys_by_hwnd(self, hwnd: str, text: str) -> bool:
        """
        后台输入文本(杀毒软件可能会拦截)
        :param hwnd: 窗口句柄
        :param text: 输入的文本
        :return:
        """
        return self.__send_data("sendKeysByHwnd", hwnd, text) == "true"

    def send_vk(self, vk: int, typ: int) -> bool:
        """
        输入虚拟键值(VK)
        :param vk: VK键值
        :param typ: 输入类型，按下弹起:1 按下:2 弹起:3
        :return:
        """
        return self.__send_data("sendVk", vk, typ) == "true"

    def send_vk_by_hwnd(self, hwnd: str, vk: int, typ: int) -> bool:
        """
        后台输入虚拟键值(VK)
        :param hwnd: 窗口句柄
        :param vk: VK键值
        :param typ: 输入类型，按下弹起:1 按下:2 弹起:3
        :return:
        """
        return self.__send_data("sendVkByHwnd", hwnd, vk, typ) == "true"

    # #############
    #   图色操作   #
    # #############
