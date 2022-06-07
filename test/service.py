import socket
import socketserver
import time


class ThreadingTCPServerPlus(socketserver.ThreadingTCPServer):
    daemon_threads = True


class MyTCPHandler(socketserver.BaseRequestHandler):

    def _send_data(self, *args):
        args_len = ""
        args_text = ""

        for argv in args:
            args_text += str(argv)
            args_len += str(len(bytes(str(argv), "utf8")))
            args_len += "/"

        data = args_len.rstrip("/") + "\n" + args_text

        self.request.sendall(bytes(data, "utf8"))
        return self.request.recv(1024).strip()

    def show_toast(self, text: str) -> bool:
        resp = self._send_data("showToast", text)

        r = resp.decode("utf8").split("/")
        print(r)
        print(type(r))
        return True

    def handle(self) -> None:
        # 连接成功
        self.show_toast("连接成功 hhhh  6666")

        time.sleep(5)

        while True:
            self.request.sendall(b"9/3\nshowToastRPC")

            data = self.request.recv(1024).strip()
            print(f"接收到来自 {self.client_address} 的数据：{data.decode('utf8')}")

            # 客户端断开连接
            if not data:
                break

            time.sleep(3)


if __name__ == '__main__':
    HOST, PORT = "0.0.0.0", 6666

    with ThreadingTCPServerPlus((HOST, PORT), MyTCPHandler) as server:
        # 激活服务器；
        # 它将一直运行，直到使用 Ctrl-C 组合键中断程序
        server.serve_forever()
