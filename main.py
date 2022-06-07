import abc
import socket
import socketserver


def protect(*protected):
    class Protect(abc.ABCMeta):
        # 是否父类
        is_parent_class = True

        def __new__(mcs, name, bases, namespace):
            # 不是父类，需要检查属性是否被重写
            if not mcs.is_parent_class:
                attr_names = namespace.keys()
                for attr in protected:
                    if attr in attr_names:
                        raise AttributeError(f'Overriding of attribute `{attr}` not allowed.')

            # 首次调用后设置为 False
            mcs.is_parent_class = False
            return super().__new__(mcs, name, bases, namespace)

    return Protect


class ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True


class AiBotScriptMain(socketserver.BaseRequestHandler, metaclass=protect("handle", "execute")):
    def _send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            args_text += str(argv)
            args_len += str(len(bytes(str(argv), "utf8")))
            args_len += "/"

        data = args_len.rstrip("/") + "\n" + args_text

        self.request.sendall(bytes(data, "utf8"))
        return self.request.recv(1024).decode("utf8").strip()

    def show_toast(self, text: str) -> bool:
        """"""
        resp = self._send_data("showToast", text)
        return resp.split("/")[-1] == "true"

    def handle(self) -> None:
        # 执行脚本
        self.script_main()

    @abc.abstractmethod
    def script_main(self):
        """脚本入口，由子类重写
        """

    @classmethod
    def execute(cls, listen_port):
        """
        多线程启动 Socket 服务，执行脚本
        :return:
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")

        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *args, socket_address = address_info

        # 启动 Socket 服务
        sock = ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()


class AiBotScript(AiBotScriptMain):
    def script_main(self):
        self.show_toast("连接成功")
        while True:
            data = self.request.recv(1024)
            print("接收数据：", data.decode("utf8"))

            # 客户端断开
            if not data:
                break

            resp_data = b"Response: " + data.upper()
            self.request.sendall(resp_data)


if __name__ == '__main__':
    AiBotScript.execute(0)
