import abc
import socketserver
import socket
import threading
import time

from ._AndroidBase import AndroidBotBase
from ._WebBase import WebBotBase
from ._WinBase import WinBotBase
from ._utils import _protect, _ThreadingTCPServer, get_local_ip

WIN_DRIVER: WinBotBase | None = None
WEB_DRIVER: WebBotBase | None = None


class AndroidBotMain(socketserver.BaseRequestHandler, AndroidBotBase, metaclass=_protect("handle", "execute")):
    def __init__(self, request, client_address, server):
        self._lock = threading.Lock()
        super().__init__(request, client_address, server)

    def handle(self) -> None:
        # def heart_check():
        #     try:
        #         while True:
        #             time.sleep(5)
        #             self.get_android_id()
        #     except Exception:
        #         self.log.error("心跳检测中断")
        #
        # t = threading.Thread(target=heart_check)
        # t.join()
        # t.start()
        self.script_main()

    @abc.abstractmethod
    def script_main(self):
        """脚本入口，由子类重写
        """

    @classmethod
    def execute(cls, listen_port: int):
        """
        启动 Socket 服务，执行脚本

        :return:
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")

        # 获取 IPv4 可用地址
        address_info = \
            socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[0]
        *_, socket_address = address_info

        # 获取局域网 IP
        local_ip = get_local_ip()

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.request_queue_size = int(getattr(cls, "request_queue_size", 5))
        print(f"Server stared on {local_ip}:{socket_address[1]}")
        sock.serve_forever()

    def build_web_driver(self, listen_port: int, local: bool = True, driver_params: dict = None,
                         new_driver=False) -> WebBotBase:
        """
        构建 web driver

        :param listen_port: Web 脚本要监听的端口
        :param local: 脚本是否部署在本地
        :param driver_params: Web 驱动启动参数
        :param new_driver: 是否强制获取新的 Web 脚本驱动
        """
        global WEB_DRIVER
        with self._lock:
            if WEB_DRIVER is None or new_driver:
                WEB_DRIVER = WebBotBase._build(listen_port, local, driver_params)
        return WEB_DRIVER

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
