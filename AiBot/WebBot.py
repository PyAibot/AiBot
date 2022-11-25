import re
import socket
import subprocess
import sys
import time
from ast import literal_eval

from typing import List, Optional, Tuple

from loguru import logger


class _Point:

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __getitem__(self, item: int):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError("list index out of range")

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    # def __init__(self, x, y, driver: "WinBotMain"):
    #     self.x = x
    #     self.y = y
    #     self.__driver = driver
    #
    # def click(self, offset_x: float = 0, offset_y: float = 0):
    #     """
    #     点击坐标
    #     :param offset_x: 坐标 x 轴偏移量；
    #     :param offset_y: 坐标 y 轴偏移量；
    #     :return:
    #     """
    #     self.__driver.click(self, offset_x=offset_x, offset_y=offset_y)
    #
    # def get_points_center(self, other_point: "_Point") -> "_Point":
    #     """
    #     获取两个坐标点的中间坐标
    #     :param other_point: 其他的坐标点
    #     :return:
    #     """
    #     return self.__class__(x=self.x + (other_point.x - self.x) / 2, y=self.y + (other_point.y - self.y) / 2,
    #                           driver=self.__driver)


_Region = Tuple[float, float, float, float]
_Algorithm = Tuple[int, int, int]
_SubColors = List[Tuple[int, int, str]]


class WebBotMain:
    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_path = ""
    log_level = "DEBUG"
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
                 "<level>{level: <8}</level> | " \
                 "{thread.name: <8} | " \
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
    def build(cls, host: str, port: int, browser: str, debug_port=0, user_data_dir="./UserData", browser_path=None,
              argument=None) -> "WebBotMain":
        """
        :param host: webDriver服务地址。假如值为 "127.0.0.1"脚本会自动启动WebDriver.exe，如果是远程服务地址，用户需要手动启动WebDriver.exe 并且提供启动参数。
        :param port: 端口
        :param browser: 浏览器名称 "edge"和"chrome"，其他chromium内核浏览器需要指定browserPath参数
        :param debug_port: 调试端口。默认 0 随机端口。指定端口则接管已打开的浏览器。启动浏览应指定的参数 --remote-debugging-port=19222 --user-data-dir=C:\\Users\\电脑用户名\\AppData\\Local\\Google\\Chrome\\User Data
        :param user_data_dir: 用户数据目录,默认./UserData。多进程同时操作多个浏览器数据目录不能相同
        :param browser_path: 浏览器路径
        :param argument: 浏览器启动参数。例如：无头模式: --headless   设置代理：--proxy-server=127.0.0.1:8080
        :return:
        """
        # subprocess.Popen(["WindowsDriver.exe", str(port)])
        return WebBotMain(port)

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

    #############
    # 页面和导航 #
    #############
    def goto(self, url: str) -> bool:
        """
        跳转页面
        :param url:
        :return:
        """

    def new_page(self, url: str) -> bool:
        """
        新建 Tab 并跳转页面
        :param url:
        :return:
        """

    def back(self):
        """
        后退
        :return:
        """

    def forward(self):
        """
        前进
        :return:
        """

    def refresh(self):
        """
        刷新
        :return:
        """

    def get_current_page_id(self):
        """
        获取当前页面 ID
        :return:
        """

    def get_all_page_id(self):
        """
        获取所有页面 ID
        :return:
        """

    def switch_to_page(self, page_id: str):
        """
        切换到指定页面
        :param page_id:
        :return:
        """

    def close_page(self, page_id: str):
        """
        关闭指定页面
        :param page_id:
        :return:
        """

    def ger_url(self):
        """
        获取当前 URL
        :return:
        """

    def get_title(self):
        """
        获取当前页面标题
        :return:
        """

    ###############
    # iframe 操作 #
    ###############

    def switch_to_frame(self, frame_url):
        """
        切换到指定 frame
        :param frame_url:
        :return:
        """

    def switch_to_main_frame(self):
        """
        切回主 frame
        :return:
        """

    ###########
    # 元素操作 #
    ###########
    def click_element(self, xpath: str) -> bool:
        """
        点击元素
        :param xpath:
        :return:
        """

    def get_element_text(self, xpath: str) -> Optional[str]:
        """
        获取元素文本
        :param xpath:
        :return:
        """

    def get_element_rect(self, xpath: str) -> Optional[(_Point, _Point, dict)]:
        """
        获取元素矩形坐标
        :param xpath:
        :return:
        """

    def set_element_value(self, xpath: str, value: str) -> bool:
        """
        设置元素值
        :param xpath:
        :param value:
        :return:
        """

    def set_element_attr(self, xpath: str, attr_name: str, attr_value: str) -> Optional[str]:
        """
        设置元素属性
        :param xpath:
        :param attr_name:
        :param attr_value:
        :return:
        """

    def get_element_outer_html(self, xpath: str) -> Optional[str]:
        """
        获取元素的 outerHtml
        :param xpath:
        :return:
        """

    def get_element_inner_html(self, xpath: str) -> Optional[str]:
        """
        获取元素的 innerHtml
        :param xpath:
        :return:
        """

    def is_selected(self, xpath: str) -> bool:
        """
        元素是否已选中
        :param xpath:
        :return:
        """

    def is_displayed(self, xpath: str) -> bool:
        """
        元素是否可见
        :param xpath:
        :return:
        """

    def is_available(self, xpath: str) -> bool:
        """
        元素是否可用
        :param xpath:
        :return:
        """

    def clear_element(self, xpath:str)-> bool:
        """
        清除元素值
        :param xpath:
        :return:
        """

    ###########
    # 键鼠操作 #
    ###########
