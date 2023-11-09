import abc
import socketserver
import socket
import threading

from ._AndroidBase import _AndroidBotBase
from ._WebBase import _WebBotBase
from ._WinBase import _WinBotBase
from ._utils import _protect, _ThreadingTCPServer, get_local_ip


class AndroidBotMain(socketserver.BaseRequestHandler, _AndroidBotBase, metaclass=_protect("handle", "execute")):
    def __init__(self, request, client_address, server):
        self._lock = threading.Lock()
        super().__init__(request, client_address, server)

    def handle(self) -> None:
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

    @staticmethod
    def build_web_driver(listen_port: int, local: bool = True, driver_params: dict = None) -> _WebBotBase:
        return _WebBotBase._build(listen_port, local, driver_params)

    @staticmethod
    def build_win_driver(listen_port: int, local: bool = True) -> _WinBotBase:
        return _WinBotBase._build(listen_port, local)
