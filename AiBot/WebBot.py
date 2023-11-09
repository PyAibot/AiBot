import abc
import json
import random
import socket
import socketserver
import subprocess
import threading

from AiBot._WebBase import WebBotBase
from AiBot._WinBase import WinBotBase
from AiBot._AndroidBase import AndroidBotBase
from AiBot._utils import _protect, _ThreadingTCPServer, get_local_ip

AND_DRIVER: AndroidBotBase | None = None
WIN_DRIVER: WinBotBase | None = None


class WebBotMain(socketserver.BaseRequestHandler, WebBotBase, metaclass=_protect("handle", "execute")):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self._lock = threading.Lock()
        self.__sock = request

    def handle(self) -> None:
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
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")

        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *_, socket_address = address_info

        # 获取局域网 IP
        local_ip = get_local_ip()

        # 如果是本地部署，则自动启动 WebDriver.exe
        if local:
            default_params = {
                "serverIp": "127.0.0.1",
                "serverPort": listen_port,
                "browserName": "chrome",
                "debugPort": 0,
                "userDataDir": f"./UserData{random.randint(100000, 999999)}",
                "browserPath": None,
                "argument": None,
            }
            if driver_params:
                default_params.update(driver_params)
            default_params = json.dumps(default_params)
            try:
                subprocess.Popen(["WebDriver.exe", default_params])
                print("本地启动 WebDriver 成功，开始执行脚本")
            except FileNotFoundError as e:
                err_msg = "\n异常排除步骤：\n1. 检查 Aibote.exe 路径是否存在中文；\n2. 是否启动 Aibote.exe 初始化环境变量；\n3. 检查电脑环境变量是否初始化成功，环境变量中是否存在 %Aibote% 开头的；\n4. 首次初始化环境变量后，是否重启开发工具；\n5. 是否以管理员权限启动开发工具；\n"
                print("\033[92m", err_msg, "\033[0m")
                raise e

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        print(f"Server stared on {local_ip}:{socket_address[1]}")
        sock.serve_forever()

    def build_android_driver(self, listen_port: int, new_driver=False) -> AndroidBotBase:
        """
        构建 android driver

        :param listen_port: Android 脚本要监听的端口
        :param new_driver: 是否强制获取新的 Android 脚本驱动
        """
        global AND_DRIVER
        with self._lock:
            if AND_DRIVER is None or new_driver:
                AND_DRIVER = AndroidBotBase._build(listen_port)
        return AND_DRIVER

    def build_win_driver(self, listen_port: int, local: bool = True, new_driver=False) -> WinBotBase:
        """
        构建 win driver

        :param listen_port: Win 脚本要监听的端口
        :param local: 脚本是否部署在本地
        :param new_driver: 是否强制获取新的 Win 脚本驱动
        """
        global WIN_DRIVER
        with self._lock:
            if WIN_DRIVER is None or new_driver:
                WIN_DRIVER = WinBotBase._build(listen_port, local)
        return WIN_DRIVER
