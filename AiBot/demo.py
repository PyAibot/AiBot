import socket
import sys

from loguru import logger


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
