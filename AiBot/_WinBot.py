import abc
import socket
import socketserver
import subprocess
import threading

from AiBot._AndroidBase import _AndroidBotBase
from AiBot._WebBase import _WebBotBase
from AiBot._WinBase import _WinBotBase
from AiBot._utils import _protect, _ThreadingTCPServer


class WinBotMain(socketserver.BaseRequestHandler, _WinBotBase, metaclass=_protect("handle", "execute")):
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
    def execute(cls, listen_port: int, local: bool = True):
        """
        多线程启动 Socket 服务

        :param listen_port: 脚本监听的端口
        :param local: 脚本是否部署在本地
        :return:
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")
        print("启动服务...")
        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *_, socket_address = address_info

        # 如果是本地部署，则自动启动 WindowsDriver.exe
        if local:
            try:
                subprocess.Popen(["WindowsDriver.exe", "127.0.0.1", str(listen_port)])
                print("本地启动 WindowsDriver 成功，开始执行脚本")
            except FileNotFoundError as e:
                err_msg = "\n异常排除步骤：\n1. 检查 Aibote.exe 路径是否存在中文；\n2. 是否启动 Aibote.exe 初始化环境变量；\n3. 检查电脑环境变量是否初始化成功，环境变量中是否存在 %Aibote% 开头的；\n4. 首次初始化环境变量后，是否重启开发工具；\n5. 是否以管理员权限启动开发工具；\n"
                print("\033[92m", err_msg, "\033[0m")
                raise e
        else:
            print("等待驱动连接...")

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()

    @staticmethod
    def build_android_driver(listen_port: int) -> _AndroidBotBase:
        return _AndroidBotBase.build(listen_port)

    @staticmethod
    def build_web_driver(listen_port: int, local: bool = True, driver_params: dict = None) -> _WebBotBase:
        return _WebBotBase.build(listen_port, local, driver_params)
