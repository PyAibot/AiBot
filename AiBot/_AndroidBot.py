import abc
import socketserver
import socket
import time

from ._AndroidBase import _AndroidBotBase
from ._WebBase import _WebBotBase
from ._WinBase import _WinBotBase

WIN_DRIVER: _WinBotBase | None = None
WEB_DRIVER: _WebBotBase | None = None


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class AndroidBotMain(_AndroidBotBase):
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
        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.request_queue_size = int(getattr(cls, "request_queue_size", 5))
        print(f"Server stared on {socket_address[0]}:{socket_address[1]}")
        print("服务已启动")
        print("等待设备连接...")

        sock.serve_forever()

    @staticmethod
    def build_win_driver(port: int, local: bool = True) -> _WinBotBase:
        _WinBotBase.execute(port, local=local)
        while WIN_DRIVER is not None:
            return WIN_DRIVER
        else:
            time.sleep(0.5)
