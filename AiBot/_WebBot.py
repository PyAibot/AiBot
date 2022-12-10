import abc
import json
import socket
import socketserver
import subprocess
import sys
import threading
import time
import re
from ast import literal_eval
from typing import Optional, List, Tuple

from loguru import logger

from ._utils import _protect, _Point, _Region, _Algorithm, _SubColors


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class WebBotMain(socketserver.BaseRequestHandler, metaclass=_protect("handle", "execute")):
    raise_err = False

    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_path = ""
    log_level = "INFO"
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
                 "<level>{level: <8}</level> | " \
                 "{thread.name: <8} | " \
                 "<cyan>{module}.{function}:{line}</cyan> | " \
                 "<level>{message}</level>"  # 日志内容

    def __init__(self, request, client_address, server):
        self._lock = threading.Lock()
        self.log = logger

        self.log.remove()
        self.log.add(sys.stdout, level=self.log_level.upper(), format=self.log_format)

        if self.log_path:
            self.log.add(self.log_path, level=self.log_level.upper(), rotation="12:00", retention="15 days",
                         format=self.log_format)

        super().__init__(request, client_address, server)

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

        with self._lock:
            self.log.debug(rf"->>> {data}")
            self.request.sendall(data)
            response = self.request.recv(65535)
            if response == b"":
                raise ConnectionAbortedError(f"{self.client_address[0]}:{self.client_address[1]} 客户端断开链接。")
            data_length, data = response.split(b"/", 1)
            while int(data_length) > len(data):
                data += self.request.recv(65535)
            self.log.debug(rf"<<<- {data}")

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

    def get_element_rect(self, xpath: str) -> Optional[Tuple[_Point, _Point]]:
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

    def clear_element(self, xpath: str) -> bool:
        """
        清除元素值
        :param xpath:
        :return:
        """

    ###########
    # 键鼠操作 #
    ###########

    # ##########
    #   其他   #
    ############
    def handle(self) -> None:
        # 设置阻塞模式
        # self.request.setblocking(False)

        # 设置缓冲区
        # self.request.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        self.request.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)  # 发送缓冲区 10M

        # 执行脚本
        self.script_main()

    @abc.abstractmethod
    def script_main(self):
        """脚本入口，由子类重写
        """

    @classmethod
    def execute(cls, listen_port: int, local: bool = True, driver_params: dict = None):
        """
        多线程启动 Socket 服务
        :param listen_port: 脚本监听的端口
        :param local: 脚本是否部署在本地
        :param driver_params: Web 驱动启动参数
        :return:

        driver_params = {}
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")

        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *_, socket_address = address_info

        # 如果是本地部署，则自动启动 WebDriver.exe
        if local:
            default_params = {
                "serverIp": "127.0.0.1",
                "serverPort": listen_port,
                "browserName": "chrome",
                "debugPort": 0,
                "userDataDir": "./UserData",
                "browserPath": "null",
                "argument": "null",
            }
            if driver_params:
                default_params.update(driver_params)
            default_params = json.dumps(default_params)
            try:
                subprocess.Popen(["WebDriver.exe", default_params])
            except FileNotFoundError as e:
                err_msg = """
                异常排除步骤：
                1. 检查 Aibote.exe 路径是否存在中文；
                2. 是否启动 Aibote.exe 初始化环境变量；
                3. 检查电脑环境变量是否初始化成功，环境变量中是否存在 %Aibote% 开头的；
                4. 首次初始化环境变量后，是否重启开发工具；
                5. 是否以管理员权限启动开发工具；
                """
                print("\033[92m", err_msg, "\033[0m")
                raise e

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()
